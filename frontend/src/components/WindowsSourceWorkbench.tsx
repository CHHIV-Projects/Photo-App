"use client";

import { useCallback, useEffect, useState } from "react";

import {
  advanceWindowsSourceUiRun,
  confirmWindowsSourceUiRun,
  getLatestWindowsSourceUiRun,
  getWindowsSourceUiRun,
  getWindowsSourceUiOperation,
  getWindowsSourceUiProfile,
  prepareWindowsSourceUiInventory,
  reviewWindowsSourceUiCandidates,
  resolveWindowsSourceUiRoute,
  startWindowsSourceUiRouteCheck,
  startWindowsSourceUiProbe,
} from "@/lib/api";
import type {
  SourceProfileSummary,
  WindowsSourceUiCandidateReview,
  WindowsSourceUiProfileStatus,
  WindowsSourceUiRouteCheck,
  WindowsSourceUiWorkflowStatus,
} from "@/types/ui-api";

import styles from "./ingestion-view.module.css";


const WINDOWS_START_URI = "photoorganizer-helper://start";
const LAUNCH_TIMEOUT_MS = 30_000;
const OPERATION_TIMEOUT_MS = 120_000;

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

function invokeWindowsAccess(): void {
  window.location.href = WINDOWS_START_URI;
}

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KiB`;
  if (value < 1024 * 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MiB`;
  return `${(value / (1024 * 1024 * 1024)).toFixed(2)} GiB`;
}

type Props = {
  profile: SourceProfileSummary;
  onComplete?: (workflow: WindowsSourceUiWorkflowStatus) => void;
  launchWindowsAccess?: () => void;
  launchTimeoutMs?: number;
  operationTimeoutMs?: number;
  wait?: (milliseconds: number) => Promise<void>;
};

export default function WindowsSourceWorkbench({
  profile,
  onComplete,
  launchWindowsAccess = invokeWindowsAccess,
  launchTimeoutMs = LAUNCH_TIMEOUT_MS,
  operationTimeoutMs = OPERATION_TIMEOUT_MS,
  wait = delay,
}: Props) {
  const [access, setAccess] = useState<WindowsSourceUiProfileStatus | null>(null);
  const [phase, setPhase] = useState<"idle" | "starting" | "checking" | "route" | "preparing" | "review" | "running" | "complete" | "failed">("idle");
  const [routeCheck, setRouteCheck] = useState<WindowsSourceUiRouteCheck | null>(null);
  const [review, setReview] = useState<WindowsSourceUiCandidateReview | null>(null);
  const [workflow, setWorkflow] = useState<WindowsSourceUiWorkflowStatus | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const refreshAccess = useCallback(async () => {
    const current = await getWindowsSourceUiProfile(profile.source_id);
    setAccess(current);
    return current;
  }, [profile.source_id]);

  const pollAccess = useCallback(async () => {
    const deadline = Date.now() + launchTimeoutMs;
    while (Date.now() < deadline) {
      const current = await refreshAccess();
      if (current.online) return current;
      await wait(1000);
    }
    throw new Error("Windows access could not be started.");
  }, [launchTimeoutMs, refreshAccess, wait]);

  const pollOperation = useCallback(async (token: string) => {
    const deadline = Date.now() + operationTimeoutMs;
    let currentToken = token;
    while (Date.now() < deadline) {
      const current = await getWindowsSourceUiOperation(currentToken);
      currentToken = current.operation_token;
      if (current.stage === "ready") return current;
      if (current.stage === "failed") throw new Error(current.safe_message);
      await wait(1000);
    }
    throw new Error("The Windows Source check timed out safely.");
  }, [operationTimeoutMs, wait]);

  const prepareFromProbe = useCallback(async (probeToken: string) => {
    const readyProbe = await pollOperation(probeToken);
    setPhase("preparing");
    setMessage("Preparing files");
    const inventory = await prepareWindowsSourceUiInventory(
      profile.source_id,
      readyProbe.operation_token,
    );
    await pollOperation(inventory.operation_token);
    const candidateReview = await reviewWindowsSourceUiCandidates(profile.source_id, inventory.operation_token);
    setReview(candidateReview);
    setPhase("review");
    setMessage(candidateReview.safe_message);
  }, [pollOperation, profile.source_id]);

  const pollRoutes = useCallback(async (initial: WindowsSourceUiRouteCheck) => {
    let current = initial;
    const deadline = Date.now() + operationTimeoutMs;
    while (current.stage === "checking_routes" && Date.now() < deadline) {
      await wait(1000);
      current = await resolveWindowsSourceUiRoute(profile.source_id, current.observation_tokens);
    }
    setRouteCheck(current);
    if (current.stage === "ambiguous") {
      setPhase("route");
      setMessage(current.safe_message);
      return;
    }
    if (current.stage !== "checking_source" || !current.probe_operation_token) {
      throw new Error(current.safe_message);
    }
    await prepareFromProbe(current.probe_operation_token);
  }, [operationTimeoutMs, prepareFromProbe, profile.source_id, wait]);

  const prepare = useCallback(async () => {
    setPhase("checking");
    setMessage("Checking source");
    if (["external_device", "removable_media"].includes(profile.endpoint_source_type ?? "")) {
      await pollRoutes(await startWindowsSourceUiRouteCheck(profile.source_id));
      return;
    }
    const probe = await startWindowsSourceUiProbe(profile.source_id);
    await prepareFromProbe(probe.operation_token);
  }, [pollRoutes, prepareFromProbe, profile.endpoint_source_type, profile.source_id]);

  const chooseRoute = useCallback(async (accessNodeId: string) => {
    if (!routeCheck) return;
    setPhase("checking");
    setMessage("Verifying the selected route...");
    try {
      const selected = await resolveWindowsSourceUiRoute(
        profile.source_id,
        routeCheck.observation_tokens,
        accessNodeId,
      );
      if (selected.stage !== "checking_source" || !selected.probe_operation_token) {
        throw new Error(selected.safe_message);
      }
      await prepareFromProbe(selected.probe_operation_token);
    } catch (error) {
      setPhase("failed");
      setMessage(error instanceof Error ? error.message : "The selected route is no longer available.");
    }
  }, [prepareFromProbe, profile.source_id, routeCheck]);

  const runFromClick = useCallback(() => {
    setMessage(null);
    setReview(null);
    setWorkflow(null);
    if (!access?.online) {
      // Keep this synchronous in the click event so browsers retain user activation.
      launchWindowsAccess();
      setPhase("starting");
      setMessage("Starting Windows access...");
      void pollAccess().then(prepare).catch((error: unknown) => {
        setPhase("failed");
        setMessage(error instanceof Error ? error.message : "Windows access could not be started.");
      });
      return;
    }
    void prepare().catch((error: unknown) => {
      setPhase("failed");
      setMessage(error instanceof Error ? error.message : "The Windows Source could not be prepared.");
    });
  }, [access?.online, launchWindowsAccess, pollAccess, prepare]);

  const pollWorkflow = useCallback(async (token: string, initial: WindowsSourceUiWorkflowStatus) => {
    let current = initial;
    while (!["complete", "failed", "paused"].includes(current.stage)) {
      await wait(1500);
      try {
        current = await getWindowsSourceUiRun(token);
        setWorkflow(current);
      } catch {
        setMessage("Progress could not be refreshed; the durable backend workflow continues.");
      }
    }
    setPhase(current.stage === "complete" ? "complete" : "failed");
    setMessage(current.safe_message);
    if (current.stage === "complete") onComplete?.(current);
  }, [onComplete, wait]);

  useEffect(() => {
    setPhase("idle");
    setReview(null);
    setWorkflow(null);
    setRouteCheck(null);
    setMessage(null);
    void Promise.all([refreshAccess(), getLatestWindowsSourceUiRun(profile.source_id)])
      .then(([, latest]) => {
        if (!latest) return;
        setWorkflow(latest);
        if (latest.stage === "inventorying") {
          setPhase("preparing");
          setMessage(latest.safe_message);
          void pollOperation(latest.workflow_token)
            .then(() => reviewWindowsSourceUiCandidates(profile.source_id, latest.workflow_token))
            .then((candidateReview) => {
              setReview(candidateReview);
              setPhase("review");
              setMessage(candidateReview.safe_message);
            })
            .catch((error: unknown) => {
              setPhase("failed");
              setMessage(error instanceof Error ? error.message : "The complete proposal could not be restored.");
            });
          return;
        }
        if (latest.stage === "awaiting_confirmation") {
          void reviewWindowsSourceUiCandidates(profile.source_id, latest.workflow_token)
            .then((candidateReview) => {
              setReview(candidateReview);
              setPhase("review");
              setMessage(candidateReview.safe_message);
            });
          return;
        }
        setPhase(latest.stage === "complete" ? "complete" : latest.stage === "failed" || latest.stage === "paused" ? "failed" : "running");
        setMessage(latest.safe_message);
        if (latest.stage === "complete") {
          onComplete?.(latest);
        }
        if (["transferring_files", "processing_library"].includes(latest.stage)) {
          void pollWorkflow(latest.workflow_token, latest);
        }
      })
      .catch(() => setMessage("Windows access status is unavailable."));
  }, [onComplete, pollOperation, pollWorkflow, profile.source_id, refreshAccess]);

  const confirmRun = useCallback(async () => {
    if (!review) return;
    setPhase("running");
    setMessage("Transferring files");
    try {
      const current = await confirmWindowsSourceUiRun(review.workflow_token);
      setWorkflow(current);
      await pollWorkflow(review.workflow_token, current);
    } catch (error) {
      setPhase("failed");
      setMessage(error instanceof Error ? error.message : "Ingestion stopped safely.");
    }
  }, [pollWorkflow, review]);

  const accessLabel = phase === "starting" ? "Starting" : access?.windows_access === "ready" ? "Ready" : access?.windows_access === "setup_required" ? "Setup required" : "Not available";
  const sourceTypeLabel = profile.endpoint_source_type === "external_device"
    ? "External"
    : profile.endpoint_source_type === "removable_media"
      ? "Removable"
      : "Local";

  return (
    <section className={styles.runPanel} aria-label={`Windows ${sourceTypeLabel} ingestion workbench`}>
      <div className={styles.runPanelHeader}>
        <div>
          <h3 className={styles.runPanelTitle}>{`Windows ${sourceTypeLabel} Ingestion`}</h3>
          <p className={styles.helperText}>Windows access starts on demand and the backend verifies readiness before any file transfer.</p>
        </div>
      </div>
      <div className={styles.detailGrid}>
        <div className={styles.detailCard}><span className={styles.detailLabel}>Windows access</span><span>{accessLabel}</span></div>
        <div className={styles.detailCard}><span className={styles.detailLabel}>Source</span><span>{phase === "checking" || phase === "preparing" || phase === "review" || phase === "running" || phase === "complete" ? "Ready" : "Not ready"}</span></div>
        <div className={styles.detailCard}><span className={styles.detailLabel}>Profile</span><span>{profile.source_label}</span><span className={styles.detailMeta}>{profile.endpoint_alias}</span></div>
        <div className={styles.detailCard}><span className={styles.detailLabel}>Folder</span><span>{review?.windows_root ?? profile.source_root_path}</span><span className={styles.detailMeta}>Windows-native path; no Linux root is fabricated.</span></div>
      </div>
      {review && phase === "review" && (
        <section className={styles.creationReview} aria-label="Windows ingestion candidate review">
          <h4 className={styles.detailHeading}>Files ready for confirmation</h4>
          <div className={styles.runMetrics}>
            <span><strong>Files to process:</strong> {review.files_to_process}</span>
            <span><strong>Inventory entries:</strong> {review.inventory_candidates}</span>
            <span><strong>Predictable rejections:</strong> {review.predictable_rejections}</span>
            <span><strong>Internal chunks:</strong> {review.expected_chunks}</span>
            <span><strong>Total size:</strong> {formatBytes(review.total_bytes)}</span>
            <span><strong>Source:</strong> {review.profile_name}</span>
            <span><strong>Folder:</strong> {review.windows_root}</span>
          </div>
          <button type="button" className={styles.runButton} onClick={() => void confirmRun()}>Start Ingestion</button>
        </section>
      )}
      {phase === "route" && routeCheck?.stage === "ambiguous" && (
        <section className={styles.creationReview} aria-label="Choose Windows access route">
          <h4 className={styles.detailHeading}>Use computer</h4>
          <p className={styles.helperText}>The same Source device is currently available through more than one registered computer.</p>
          <div className={styles.rowActions}>
            {routeCheck.routes.map((route) => (
              <button key={route.access_node_id} type="button" className={styles.button} onClick={() => void chooseRoute(route.access_node_id)}>
                {route.computer_alias}
              </button>
            ))}
          </div>
        </section>
      )}
      {workflow && (
        <div className={styles.runMetrics} aria-label="Windows ingestion progress">
          <span><strong>Stage:</strong> {workflow.stage === "inventorying" ? "Preparing proposal" : workflow.stage === "awaiting_confirmation" ? "Awaiting confirmation" : workflow.stage === "transferring_files" ? "Transferring files" : workflow.stage === "processing_library" ? "Processing library" : workflow.stage === "paused" ? "Paused" : workflow.stage === "complete" ? "Complete" : "Stopped"}</span>
          <span><strong>Files:</strong> {workflow.files_completed} / {workflow.files_total}</span>
          <span><strong>Chunks:</strong> {workflow.chunks_completed} / {workflow.chunks_total}</span>
          <span><strong>Remaining:</strong> {workflow.files_remaining}</span>
          <span><strong>Transferred:</strong> {formatBytes(workflow.transferred_bytes)} / {formatBytes(workflow.expected_bytes)}</span>
          {workflow.stage === "complete" && <><span><strong>New library items:</strong> {workflow.new_library_items}</span><span><strong>Already represented:</strong> {workflow.already_represented}</span><span><strong>Failed:</strong> {workflow.failed_items}</span></>}
        </div>
      )}
      {message && <p className={phase === "failed" ? styles.bannerError : phase === "complete" ? styles.bannerSuccess : styles.helperText}>{message}</p>}
      {(phase === "idle" || phase === "failed") && (
        <div className={styles.rowActions}>
          <button type="button" className={styles.runButton} onClick={runFromClick}>Run Ingestion</button>
          {phase === "failed" && workflow?.stage !== "paused" && <button type="button" className={styles.button} onClick={() => void refreshAccess()}>Try Again</button>}
          {phase === "failed" && workflow?.stage === "paused" && <button type="button" className={styles.button} onClick={() => {
            launchWindowsAccess();
            void pollAccess()
              .then(() => advanceWindowsSourceUiRun(workflow.workflow_token))
              .then((current) => {
                setWorkflow(current);
                setPhase("running");
                setMessage(current.safe_message);
                return pollWorkflow(current.workflow_token, current);
              })
              .catch((error: unknown) => {
                setPhase("failed");
                setMessage(error instanceof Error ? error.message : "The approved run could not be resumed.");
              });
          }}>Resume approved run</button>}
        </div>
      )}
      {phase === "complete" && (
        <button type="button" className={styles.runButton} onClick={runFromClick}>Run Again</button>
      )}
    </section>
  );
}

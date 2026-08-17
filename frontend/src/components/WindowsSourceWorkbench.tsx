"use client";

import { useCallback, useEffect, useState } from "react";

import {
  advanceWindowsSourceUiRun,
  confirmWindowsSourceUiRun,
  getWindowsSourceUiOperation,
  getWindowsSourceUiProfile,
  prepareWindowsSourceUiInventory,
  reviewWindowsSourceUiCandidates,
  startWindowsSourceUiProbe,
} from "@/lib/api";
import type {
  SourceProfileSummary,
  WindowsSourceUiCandidateReview,
  WindowsSourceUiProfileStatus,
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
  onComplete?: () => void;
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
  const [phase, setPhase] = useState<"idle" | "starting" | "checking" | "preparing" | "review" | "running" | "complete" | "failed">("idle");
  const [review, setReview] = useState<WindowsSourceUiCandidateReview | null>(null);
  const [workflow, setWorkflow] = useState<WindowsSourceUiWorkflowStatus | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const refreshAccess = useCallback(async () => {
    const current = await getWindowsSourceUiProfile(profile.source_id);
    setAccess(current);
    return current;
  }, [profile.source_id]);

  useEffect(() => {
    setPhase("idle");
    setReview(null);
    setWorkflow(null);
    setMessage(null);
    void refreshAccess().catch(() => setMessage("Windows access status is unavailable."));
  }, [refreshAccess]);

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
    while (Date.now() < deadline) {
      const current = await getWindowsSourceUiOperation(token);
      if (current.stage === "ready") return current;
      if (current.stage === "failed") throw new Error(current.safe_message);
      await wait(1000);
    }
    throw new Error("The Windows Source check timed out safely.");
  }, [operationTimeoutMs, wait]);

  const prepare = useCallback(async () => {
    setPhase("checking");
    setMessage("Checking source");
    const probe = await startWindowsSourceUiProbe(profile.source_id);
    await pollOperation(probe.operation_token);
    setPhase("preparing");
    setMessage("Preparing files");
    const inventory = await prepareWindowsSourceUiInventory(profile.source_id, probe.operation_token);
    await pollOperation(inventory.operation_token);
    const candidateReview = await reviewWindowsSourceUiCandidates(profile.source_id, inventory.operation_token);
    setReview(candidateReview);
    setPhase("review");
    setMessage(candidateReview.safe_message);
  }, [pollOperation, profile.source_id]);

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
    while (current.stage !== "complete" && current.stage !== "failed") {
      await wait(1500);
      current = await advanceWindowsSourceUiRun(token);
      setWorkflow(current);
    }
    setPhase(current.stage === "complete" ? "complete" : "failed");
    setMessage(current.safe_message);
    if (current.stage === "complete") onComplete?.();
  }, [onComplete, wait]);

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

  return (
    <section className={styles.runPanel} aria-label="Windows Local ingestion workbench">
      <div className={styles.runPanelHeader}>
        <div>
          <h3 className={styles.runPanelTitle}>Windows Local Ingestion</h3>
          <p className={styles.helperText}>Windows access starts on demand and the backend verifies readiness before any file transfer.</p>
        </div>
      </div>
      <div className={styles.detailGrid}>
        <div className={styles.detailCard}><span className={styles.detailLabel}>Windows access</span><span>{accessLabel}</span></div>
        <div className={styles.detailCard}><span className={styles.detailLabel}>Source</span><span>{phase === "checking" || phase === "preparing" || phase === "review" || phase === "running" || phase === "complete" ? "Ready" : "Not ready"}</span></div>
        <div className={styles.detailCard}><span className={styles.detailLabel}>Profile</span><span>{profile.source_label}</span><span className={styles.detailMeta}>{profile.endpoint_alias}</span></div>
        <div className={styles.detailCard}><span className={styles.detailLabel}>Folder</span><span>{profile.source_root_path}</span><span className={styles.detailMeta}>Windows-native path; no Linux root is fabricated.</span></div>
      </div>
      {review && phase === "review" && (
        <section className={styles.creationReview} aria-label="Windows ingestion candidate review">
          <h4 className={styles.detailHeading}>Files ready for confirmation</h4>
          <div className={styles.runMetrics}>
            <span><strong>Files to process:</strong> {review.files_to_process}</span>
            <span><strong>Total size:</strong> {formatBytes(review.total_bytes)}</span>
            <span><strong>Source:</strong> {review.profile_name}</span>
            <span><strong>Folder:</strong> {review.windows_root}</span>
          </div>
          <button type="button" className={styles.runButton} onClick={() => void confirmRun()}>Start Ingestion</button>
        </section>
      )}
      {workflow && (
        <div className={styles.runMetrics} aria-label="Windows ingestion progress">
          <span><strong>Stage:</strong> {workflow.stage === "transferring_files" ? "Transferring files" : workflow.stage === "processing_library" ? "Processing library" : workflow.stage === "complete" ? "Complete" : "Stopped"}</span>
          <span><strong>Files:</strong> {workflow.files_completed} / {workflow.files_total}</span>
          <span><strong>Transferred:</strong> {formatBytes(workflow.transferred_bytes)} / {formatBytes(workflow.expected_bytes)}</span>
          {workflow.stage === "complete" && <><span><strong>New library items:</strong> {workflow.new_library_items}</span><span><strong>Already represented:</strong> {workflow.already_represented}</span><span><strong>Failed:</strong> {workflow.failed_items}</span></>}
        </div>
      )}
      {message && <p className={phase === "failed" ? styles.bannerError : phase === "complete" ? styles.bannerSuccess : styles.helperText}>{message}</p>}
      {(phase === "idle" || phase === "failed") && (
        <div className={styles.rowActions}>
          <button type="button" className={styles.runButton} onClick={runFromClick}>Run Ingestion</button>
          {phase === "failed" && <button type="button" className={styles.button} onClick={() => void refreshAccess()}>Try Again</button>}
        </div>
      )}
    </section>
  );
}

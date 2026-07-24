"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getAdminSummary,
  getDuplicateProcessingStatus,
  getFaceProcessingStatus,
  getHeicPreviewStatus,
  getLivePhotoPairingStatus,
  getPlaceGeocodingStatus,
  runDuplicateProcessing,
  runFaceProcessing,
  runHeicPreviewGeneration,
  runLivePhotoPairing,
  runPlaceGeocoding,
  stopDuplicateProcessing,
  stopFaceProcessing,
  stopHeicPreviewGeneration,
  stopPlaceGeocoding,
} from "@/lib/api";
import type {
  AdminDuplicateProcessingStatusResponse,
  AdminFaceProcessingStatusResponse,
  AdminHeicPreviewStatusResponse,
  AdminLivePhotoPairingStatusResponse,
  AdminPlaceGeocodingStatusResponse,
  AdminSummaryResponse,
} from "@/types/ui-api";

import styles from "./admin-view.module.css";

export default function AdminView() {
  const [summary, setSummary] = useState<AdminSummaryResponse | null>(null);
  const [duplicateStatus, setDuplicateStatus] = useState<AdminDuplicateProcessingStatusResponse | null>(null);
  const [placeGeocodingStatus, setPlaceGeocodingStatus] = useState<AdminPlaceGeocodingStatusResponse | null>(null);
  const [faceProcessingStatus, setFaceProcessingStatus] = useState<AdminFaceProcessingStatusResponse | null>(null);
  const [heicPreviewStatus, setHeicPreviewStatus] = useState<AdminHeicPreviewStatusResponse | null>(null);
  const [livePhotoPairingStatus, setLivePhotoPairingStatus] = useState<AdminLivePhotoPairingStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isDuplicateActionLoading, setIsDuplicateActionLoading] = useState(false);
  const [isPlaceGeocodingActionLoading, setIsPlaceGeocodingActionLoading] = useState(false);
  const [isFaceProcessingActionLoading, setIsFaceProcessingActionLoading] = useState(false);
  const [isHeicPreviewActionLoading, setIsHeicPreviewActionLoading] = useState(false);
  const [isLivePhotoPairingActionLoading, setIsLivePhotoPairingActionLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const heicPreviewSummary = useMemo(() => {
    const raw = heicPreviewStatus?.current.last_run_summary;
    if (!raw) {
      return null;
    }

    try {
      const parsed = JSON.parse(raw) as Record<string, unknown>;
      return {
        heicGenerated: typeof parsed.heic_generated === "number" ? parsed.heic_generated : null,
        tiffGenerated: typeof parsed.tiff_generated === "number" ? parsed.tiff_generated : null,
        mismatchGenerated: typeof parsed.mismatch_generated === "number" ? parsed.mismatch_generated : null,
      };
    } catch {
      return null;
    }
  }, [heicPreviewStatus?.current.last_run_summary]);

  const loadSummary = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage("");

    try {
      const response = await getAdminSummary();
      setSummary(response);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to load admin summary.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadDuplicateStatus = useCallback(async () => {
    try {
      const response = await getDuplicateProcessingStatus();
      setDuplicateStatus(response);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to load duplicate processing status.");
    }
  }, []);

  const loadPlaceGeocodingStatus = useCallback(async () => {
    try {
      const response = await getPlaceGeocodingStatus();
      setPlaceGeocodingStatus(response);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to load place geocoding status.");
    }
  }, []);

  const loadFaceProcessingStatus = useCallback(async () => {
    try {
      const response = await getFaceProcessingStatus();
      setFaceProcessingStatus(response);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to load face processing status.");
    }
  }, []);

  const loadHeicPreviewStatus = useCallback(async () => {
    try {
      const response = await getHeicPreviewStatus();
      setHeicPreviewStatus(response);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to load HEIC preview status.");
    }
  }, []);

  const loadLivePhotoPairingStatus = useCallback(async () => {
    try {
      const response = await getLivePhotoPairingStatus();
      setLivePhotoPairingStatus(response);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to load Live Photo pairing status.");
    }
  }, []);

  const loadAll = useCallback(async () => {
    await Promise.all([
      loadSummary(),
      loadDuplicateStatus(),
      loadPlaceGeocodingStatus(),
      loadFaceProcessingStatus(),
      loadHeicPreviewStatus(),
      loadLivePhotoPairingStatus(),
    ]);
  }, [
    loadDuplicateStatus,
    loadFaceProcessingStatus,
    loadHeicPreviewStatus,
    loadLivePhotoPairingStatus,
    loadPlaceGeocodingStatus,
    loadSummary,
  ]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const runDuplicateJob = useCallback(async () => {
    setIsDuplicateActionLoading(true);
    setErrorMessage("");
    try {
      await runDuplicateProcessing();
      await loadDuplicateStatus();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to start duplicate processing.");
    } finally {
      setIsDuplicateActionLoading(false);
    }
  }, [loadDuplicateStatus]);

  const stopDuplicateJob = useCallback(async () => {
    setIsDuplicateActionLoading(true);
    setErrorMessage("");
    try {
      await stopDuplicateProcessing();
      await loadDuplicateStatus();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to request duplicate processing stop.");
    } finally {
      setIsDuplicateActionLoading(false);
    }
  }, [loadDuplicateStatus]);

  const runPlaceGeocodingJob = useCallback(async () => {
    setIsPlaceGeocodingActionLoading(true);
    setErrorMessage("");
    try {
      await runPlaceGeocoding();
      await loadPlaceGeocodingStatus();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to start place geocoding.");
    } finally {
      setIsPlaceGeocodingActionLoading(false);
    }
  }, [loadPlaceGeocodingStatus]);

  const stopPlaceGeocodingJob = useCallback(async () => {
    setIsPlaceGeocodingActionLoading(true);
    setErrorMessage("");
    try {
      await stopPlaceGeocoding();
      await loadPlaceGeocodingStatus();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to request place geocoding stop.");
    } finally {
      setIsPlaceGeocodingActionLoading(false);
    }
  }, [loadPlaceGeocodingStatus]);

  const runFaceProcessingJob = useCallback(async () => {
    if (!faceProcessingStatus || ["running", "stop_requested"].includes(faceProcessingStatus.current.status)) {
      await loadFaceProcessingStatus();
      return;
    }
    setIsFaceProcessingActionLoading(true);
    setErrorMessage("");
    try {
      const response = await runFaceProcessing();
      if (!response.accepted) {
        setErrorMessage(response.message);
      }
      await loadFaceProcessingStatus();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to start face processing.");
    } finally {
      setIsFaceProcessingActionLoading(false);
    }
  }, [faceProcessingStatus, loadFaceProcessingStatus]);

  const stopFaceProcessingJob = useCallback(async () => {
    setIsFaceProcessingActionLoading(true);
    setErrorMessage("");
    try {
      await stopFaceProcessing();
      await loadFaceProcessingStatus();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to request face processing stop.");
    } finally {
      setIsFaceProcessingActionLoading(false);
    }
  }, [loadFaceProcessingStatus]);

  const runHeicPreviewJob = useCallback(async () => {
    setIsHeicPreviewActionLoading(true);
    setErrorMessage("");
    try {
      await runHeicPreviewGeneration();
      await loadHeicPreviewStatus();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to start display preview generation.");
    } finally {
      setIsHeicPreviewActionLoading(false);
    }
  }, [loadHeicPreviewStatus]);

  const stopHeicPreviewJob = useCallback(async () => {
    setIsHeicPreviewActionLoading(true);
    setErrorMessage("");
    try {
      await stopHeicPreviewGeneration();
      await loadHeicPreviewStatus();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to request display preview stop.");
    } finally {
      setIsHeicPreviewActionLoading(false);
    }
  }, [loadHeicPreviewStatus]);

  const runLivePhotoPairingJob = useCallback(async () => {
    setIsLivePhotoPairingActionLoading(true);
    setErrorMessage("");
    try {
      await runLivePhotoPairing();
      await loadLivePhotoPairingStatus();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to run Live Photo pairing.");
      await loadLivePhotoPairingStatus();
    } finally {
      setIsLivePhotoPairingActionLoading(false);
    }
  }, [loadLivePhotoPairingStatus]);

  useEffect(() => {
    const isActive = duplicateStatus && ["running", "stop_requested"].includes(duplicateStatus.current.status);
    if (!isActive) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadDuplicateStatus();
    }, 3000);
    return () => window.clearInterval(timer);
  }, [duplicateStatus?.current.status, loadDuplicateStatus]);

  useEffect(() => {
    const isActive = placeGeocodingStatus && ["running", "stop_requested"].includes(placeGeocodingStatus.current.status);
    if (!isActive) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadPlaceGeocodingStatus();
    }, 3000);
    return () => window.clearInterval(timer);
  }, [placeGeocodingStatus?.current.status, loadPlaceGeocodingStatus]);

  useEffect(() => {
    const isActive = faceProcessingStatus && ["running", "stop_requested"].includes(faceProcessingStatus.current.status);
    if (!isActive) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadFaceProcessingStatus();
    }, 3000);
    return () => window.clearInterval(timer);
  }, [faceProcessingStatus?.current.status, loadFaceProcessingStatus]);

  useEffect(() => {
    const isActive = heicPreviewStatus && ["running", "stop_requested"].includes(heicPreviewStatus.current.status);
    if (!isActive) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadHeicPreviewStatus();
    }, 3000);
    return () => window.clearInterval(timer);
  }, [heicPreviewStatus?.current.status, loadHeicPreviewStatus]);

  useEffect(() => {
    const isActive = livePhotoPairingStatus && livePhotoPairingStatus.current.status === "running";
    if (!isActive) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadLivePhotoPairingStatus();
    }, 1000);
    return () => window.clearInterval(timer);
  }, [livePhotoPairingStatus?.current.status, loadLivePhotoPairingStatus]);

  const duplicateRunState = duplicateStatus?.current.status ?? "idle";
  const isDuplicateRunActive = duplicateRunState === "running" || duplicateRunState === "stop_requested";

  const placeGeocodingRunState = placeGeocodingStatus?.current.status ?? "idle";
  const isPlaceGeocodingRunActive = placeGeocodingRunState === "running" || placeGeocodingRunState === "stop_requested";

  const faceProcessingRunState = faceProcessingStatus?.current.status ?? "idle";
  const isFaceProcessingStatusKnown = faceProcessingStatus !== null;
  const isFaceProcessingRunActive = faceProcessingRunState === "running" || faceProcessingRunState === "stop_requested";

  const heicPreviewRunState = heicPreviewStatus?.current.status ?? "idle";
  const isHeicPreviewRunActive = heicPreviewRunState === "running" || heicPreviewRunState === "stop_requested";
  const livePhotoPairingRunState = livePhotoPairingStatus?.current.status ?? "idle";
  const isLivePhotoPairingRunActive = livePhotoPairingRunState === "running";
  const livePhotoPairingReportName = livePhotoPairingStatus?.current.last_report_path?.split(/[\\/]/).pop() ?? null;

  return (
    <section className={styles.adminRoot}>
      <header className={styles.header}>
        <div>
          <p className={styles.kicker}>Milestone 12.20</p>
          <h2 className={styles.title}>Admin Operations</h2>
          <p className={styles.subtitle}>
            Operational summary and manual controls for background duplicate lineage processing.
          </p>
        </div>
        <button type="button" className={styles.refreshButton} onClick={() => void loadAll()} disabled={isLoading}>
          {isLoading ? "Refreshing..." : "Refresh"}
        </button>
      </header>

      {errorMessage && <div className={styles.errorBanner}>{errorMessage}</div>}

      <div className={styles.grid}>
        <article className={styles.card}>
          <h3 className={styles.cardTitle}>Assets</h3>
          <p className={styles.metric}>{summary?.assets.total ?? 0}</p>
          <p className={styles.meta}>Visible: {summary?.assets.visible ?? 0}</p>
          <p className={styles.meta}>Demoted: {summary?.assets.demoted ?? 0}</p>
        </article>

        <article className={styles.card}>
          <h3 className={styles.cardTitle}>Duplicate Groups</h3>
          <p className={styles.metric}>{summary?.duplicates.total_groups ?? 0}</p>
          <div className={styles.breakdownList}>
            {(summary?.duplicates.by_type ?? []).length === 0 ? (
              <p className={styles.meta}>No typed groups yet.</p>
            ) : (
              (summary?.duplicates.by_type ?? []).map((entry) => (
                <p key={entry.group_type} className={styles.meta}>
                  {entry.group_type}: {entry.count}
                </p>
              ))
            )}
          </div>
        </article>

        <article className={styles.card}>
          <h3 className={styles.cardTitle}>Faces</h3>
          <p className={styles.metric}>{summary?.faces.total ?? 0}</p>
          <p className={styles.meta}>Unassigned: {summary?.faces.unassigned ?? 0}</p>
        </article>

        <article className={styles.card}>
          <h3 className={styles.cardTitle}>Places</h3>
          <p className={styles.metric}>{summary?.places.total ?? 0}</p>
          <p className={styles.meta}>With user label: {summary?.places.with_user_label ?? 0}</p>
          <p className={styles.meta}>Without user label: {summary?.places.without_user_label ?? 0}</p>
          <p className={styles.meta}>Linked to assets: {summary?.places.linked_to_assets ?? 0}</p>
          <p className={styles.meta}>Empty places: {summary?.places.empty ?? 0}</p>
        </article>

        <article className={`${styles.card} ${styles.duplicateCard}`.trim()}>
          <h3 className={styles.cardTitle}>Duplicate Processing</h3>
          <p className={styles.meta}>Status: {duplicateStatus?.current.status ?? "idle"}</p>
          <p className={styles.meta}>Pending assets: {duplicateStatus?.pending_items ?? 0}</p>
          <p className={styles.meta}>
            Progress: {duplicateStatus?.current.processed_items ?? 0}/{duplicateStatus?.current.total_items ?? 0}
          </p>
          <p className={styles.meta}>Started: {duplicateStatus?.current.started_at ? new Date(duplicateStatus.current.started_at).toLocaleString() : "-"}</p>
          <p className={styles.meta}>Finished: {duplicateStatus?.current.finished_at ? new Date(duplicateStatus.current.finished_at).toLocaleString() : "-"}</p>
          <p className={styles.meta}>Elapsed: {duplicateStatus?.current.elapsed_seconds ? `${duplicateStatus.current.elapsed_seconds.toFixed(1)}s` : "-"}</p>
          {duplicateStatus?.current.error_message && (
            <p className={styles.errorText}>Error: {duplicateStatus.current.error_message}</p>
          )}
          <div className={styles.actionRow}>
            <button
              type="button"
              className={styles.actionButton}
              onClick={() => void runDuplicateJob()}
              disabled={isDuplicateActionLoading || isDuplicateRunActive}
            >
              {isDuplicateActionLoading && !isDuplicateRunActive ? "Starting..." : "Run"}
            </button>
            <button
              type="button"
              className={styles.actionButtonSecondary}
              onClick={() => void stopDuplicateJob()}
              disabled={isDuplicateActionLoading || !isDuplicateRunActive}
            >
              {isDuplicateActionLoading && isDuplicateRunActive ? "Stopping..." : "Stop"}
            </button>
          </div>
        </article>

        <article className={`${styles.card} ${styles.duplicateCard}`.trim()}>
          <h3 className={styles.cardTitle}>Place Geocoding</h3>
          <p className={styles.meta}>Status: {placeGeocodingStatus?.current.status ?? "idle"}</p>
          <p className={styles.meta}>Pending places: {placeGeocodingStatus?.pending_places ?? 0}</p>
          <p className={styles.meta}>
            Progress: {placeGeocodingStatus?.current.processed_places ?? 0}/{placeGeocodingStatus?.current.total_places ?? 0}
          </p>
          <p className={styles.meta}>Succeeded: {placeGeocodingStatus?.current.succeeded_places ?? 0}</p>
          <p className={styles.meta}>Failed: {placeGeocodingStatus?.current.failed_places ?? 0}</p>
          <p className={styles.meta}>Started: {placeGeocodingStatus?.current.started_at ? new Date(placeGeocodingStatus.current.started_at).toLocaleString() : "-"}</p>
          <p className={styles.meta}>Finished: {placeGeocodingStatus?.current.finished_at ? new Date(placeGeocodingStatus.current.finished_at).toLocaleString() : "-"}</p>
          <p className={styles.meta}>Elapsed: {placeGeocodingStatus?.current.elapsed_seconds ? `${placeGeocodingStatus.current.elapsed_seconds.toFixed(1)}s` : "-"}</p>
          {placeGeocodingStatus?.current.last_error && (
            <p className={styles.errorText}>Error: {placeGeocodingStatus.current.last_error}</p>
          )}
          <div className={styles.actionRow}>
            <button
              type="button"
              className={styles.actionButton}
              onClick={() => void runPlaceGeocodingJob()}
              disabled={isPlaceGeocodingActionLoading || isPlaceGeocodingRunActive}
            >
              {isPlaceGeocodingActionLoading && !isPlaceGeocodingRunActive ? "Starting..." : "Run"}
            </button>
            <button
              type="button"
              className={styles.actionButtonSecondary}
              onClick={() => void stopPlaceGeocodingJob()}
              disabled={isPlaceGeocodingActionLoading || !isPlaceGeocodingRunActive}
            >
              {isPlaceGeocodingActionLoading && isPlaceGeocodingRunActive ? "Stopping..." : "Stop"}
            </button>
          </div>
        </article>

        <article className={`${styles.card} ${styles.duplicateCard}`.trim()}>
          <h3 className={styles.cardTitle}>Face Processing</h3>
          <p className={styles.meta}>Status: {faceProcessingStatus?.current.status ?? "loading"}</p>
          <p className={styles.meta}>Stage: {faceProcessingStatus?.current.current_stage ?? "-"}</p>
          <p className={styles.meta}>Pending detection: {faceProcessingStatus?.pending_detection ?? 0}</p>
          <p className={styles.meta}>Pending embedding: {faceProcessingStatus?.pending_embedding ?? 0}</p>
          <p className={styles.meta}>Pending clustering: {faceProcessingStatus?.pending_clustering ?? 0}</p>
          <p className={styles.meta}>Pending crops: {faceProcessingStatus?.pending_crops ?? 0}</p>
          <p className={styles.meta}>
            Detection: {faceProcessingStatus?.current.assets_processed_detection ?? 0}/{faceProcessingStatus?.current.assets_pending_detection ?? 0}
          </p>
          <p className={styles.meta}>
            Embedding: {faceProcessingStatus?.current.faces_processed_embedding ?? 0}/{faceProcessingStatus?.current.faces_pending_embedding ?? 0}
          </p>
          <p className={styles.meta}>
            Clustering: {faceProcessingStatus?.current.faces_processed_clustering ?? 0}/{faceProcessingStatus?.current.faces_pending_clustering ?? 0}
          </p>
          <p className={styles.meta}>
            Crops: {faceProcessingStatus?.current.crops_generated ?? 0}/{faceProcessingStatus?.current.crops_pending ?? 0}
          </p>
          <p className={styles.meta}>Started: {faceProcessingStatus?.current.started_at ? new Date(faceProcessingStatus.current.started_at).toLocaleString() : "-"}</p>
          <p className={styles.meta}>Finished: {faceProcessingStatus?.current.finished_at ? new Date(faceProcessingStatus.current.finished_at).toLocaleString() : "-"}</p>
          <p className={styles.meta}>Elapsed: {faceProcessingStatus?.current.elapsed_seconds ? `${faceProcessingStatus.current.elapsed_seconds.toFixed(1)}s` : "-"}</p>
          {faceProcessingStatus?.current.last_error && (
            <p className={styles.errorText}>Error: {faceProcessingStatus.current.last_error}</p>
          )}
          <div className={styles.actionRow}>
            <button
              type="button"
              className={styles.actionButton}
              onClick={() => void runFaceProcessingJob()}
              disabled={isFaceProcessingActionLoading || !isFaceProcessingStatusKnown || isFaceProcessingRunActive}
            >
              {isFaceProcessingActionLoading && !isFaceProcessingRunActive ? "Starting..." : "Run"}
            </button>
            <button
              type="button"
              className={styles.actionButtonSecondary}
              onClick={() => void stopFaceProcessingJob()}
              disabled={isFaceProcessingActionLoading || !isFaceProcessingRunActive}
            >
              {isFaceProcessingActionLoading && isFaceProcessingRunActive ? "Stopping..." : "Stop"}
            </button>
          </div>
        </article>

        <article className={`${styles.card} ${styles.duplicateCard}`.trim()}>
          <h3 className={styles.cardTitle}>Display Preview Generation</h3>
          <p className={styles.meta}>Generate browser-safe previews for HEIC / HEIF, TIFF / TIF, and mislabeled TIFF-content images.</p>
          <p className={styles.meta}>Status: {heicPreviewStatus?.current.status ?? "idle"}</p>
          <p className={styles.meta}>Pending previews: {heicPreviewStatus?.pending_previews ?? 0}</p>
          <p className={styles.meta}>
            Progress: {heicPreviewStatus?.current.assets_processed ?? 0}/{heicPreviewStatus?.current.assets_pending ?? 0}
          </p>
          <p className={styles.meta}>Succeeded: {heicPreviewStatus?.current.assets_succeeded ?? 0}</p>
          <p className={styles.meta}>Failed: {heicPreviewStatus?.current.assets_failed ?? 0}</p>
          {heicPreviewSummary && (
            <>
              <p className={styles.meta}>HEIC generated: {heicPreviewSummary.heicGenerated ?? 0}</p>
              <p className={styles.meta}>TIFF generated: {heicPreviewSummary.tiffGenerated ?? 0}</p>
              <p className={styles.meta}>Mismatch generated: {heicPreviewSummary.mismatchGenerated ?? 0}</p>
            </>
          )}
          <p className={styles.meta}>Started: {heicPreviewStatus?.current.started_at ? new Date(heicPreviewStatus.current.started_at).toLocaleString() : "-"}</p>
          <p className={styles.meta}>Finished: {heicPreviewStatus?.current.finished_at ? new Date(heicPreviewStatus.current.finished_at).toLocaleString() : "-"}</p>
          <p className={styles.meta}>Elapsed: {heicPreviewStatus?.current.elapsed_seconds ? `${heicPreviewStatus.current.elapsed_seconds.toFixed(1)}s` : "-"}</p>
          {heicPreviewStatus?.current.last_error && (
            <p className={styles.errorText}>Error: {heicPreviewStatus.current.last_error}</p>
          )}
          <div className={styles.actionRow}>
            <button
              type="button"
              className={styles.actionButton}
              onClick={() => void runHeicPreviewJob()}
              disabled={isHeicPreviewActionLoading || isHeicPreviewRunActive}
            >
              {isHeicPreviewActionLoading && !isHeicPreviewRunActive ? "Starting..." : "Run"}
            </button>
            <button
              type="button"
              className={styles.actionButtonSecondary}
              onClick={() => void stopHeicPreviewJob()}
              disabled={isHeicPreviewActionLoading || !isHeicPreviewRunActive}
            >
              {isHeicPreviewActionLoading && isHeicPreviewRunActive ? "Stopping..." : "Stop"}
            </button>
          </div>
        </article>

        <article className={`${styles.card} ${styles.duplicateCard}`.trim()}>
          <h3 className={styles.cardTitle}>Live Photo Pairing</h3>
          <p className={styles.meta}>Status: {livePhotoPairingStatus?.current.status ?? "idle"}</p>
          <p className={styles.meta}>Last run: {livePhotoPairingStatus?.current.finished_at ? new Date(livePhotoPairingStatus.current.finished_at).toLocaleString() : "-"}</p>
          <p className={styles.meta}>Created: {livePhotoPairingStatus?.current.pairs_created ?? 0}</p>
          <p className={styles.meta}>Already paired: {livePhotoPairingStatus?.current.already_paired ?? 0}</p>
          <p className={styles.meta}>Updated: {livePhotoPairingStatus?.current.updated ?? 0}</p>
          <p className={styles.meta}>Ambiguous skipped: {livePhotoPairingStatus?.current.skipped_ambiguous ?? 0}</p>
          <p className={styles.meta}>Suspicious skipped: {livePhotoPairingStatus?.current.skipped_suspicious_delta ?? 0}</p>
          <p className={styles.meta}>Missing source skipped: {livePhotoPairingStatus?.current.skipped_missing_source ?? 0}</p>
          <p className={styles.meta}>Scanned rows: {livePhotoPairingStatus?.current.scanned_rows ?? 0}</p>
          <p className={styles.meta}>Candidate groups: {livePhotoPairingStatus?.current.candidate_groups ?? 0}</p>
          <p className={styles.meta}>Removed stale: {livePhotoPairingStatus?.current.removed_stale ?? 0}</p>
          <p className={styles.meta}>Elapsed: {livePhotoPairingStatus?.current.elapsed_seconds ? `${livePhotoPairingStatus.current.elapsed_seconds.toFixed(1)}s` : "-"}</p>
          <p className={styles.meta}>Report: {livePhotoPairingReportName ?? "-"}</p>
          {livePhotoPairingStatus?.current.last_report_path && (
            <p className={styles.metaSmall}>{livePhotoPairingStatus.current.last_report_path}</p>
          )}
          {livePhotoPairingStatus?.current.last_error && (
            <p className={styles.errorText}>Error: {livePhotoPairingStatus.current.last_error}</p>
          )}
          <div className={styles.actionRow}>
            <button
              type="button"
              className={styles.actionButton}
              onClick={() => void runLivePhotoPairingJob()}
              disabled={isLivePhotoPairingActionLoading || isLivePhotoPairingRunActive}
            >
              {isLivePhotoPairingActionLoading ? "Running..." : "Run"}
            </button>
          </div>
        </article>

        <article className={`${styles.card} ${styles.placeholderCard}`.trim()}>
          <h3 className={styles.cardTitle}>Settings</h3>
          <p className={styles.placeholderText}>
            Configurable thresholds and runtime preferences will be introduced in future milestones.
          </p>
          <button type="button" className={styles.placeholderButton} disabled>
            Edit Settings (Coming Soon)
          </button>
        </article>
      </div>

      <p className={styles.generatedAt}>
        Snapshot time: {summary?.generated_at ? new Date(summary.generated_at).toLocaleString() : "-"}
      </p>
    </section>
  );
}

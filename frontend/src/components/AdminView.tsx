"use client";

import { useCallback, useEffect, useState } from "react";

import {
  getAdminSummary,
  getDuplicateProcessingStatus,
  runDuplicateProcessing,
  stopDuplicateProcessing,
  getPlaceGeocodingStatus,
  runPlaceGeocoding,
  stopPlaceGeocoding,
  getFaceProcessingStatus,
  runFaceProcessing,
  stopFaceProcessing
} from "@/lib/api";
import type {
  AdminDuplicateProcessingStatusResponse,
  AdminFaceProcessingStatusResponse,
  AdminPlaceGeocodingStatusResponse,
  AdminSummaryResponse
} from "@/types/ui-api";

import styles from "./admin-view.module.css";

export default function AdminView() {
  const [summary, setSummary] = useState<AdminSummaryResponse | null>(null);
  const [duplicateStatus, setDuplicateStatus] = useState<AdminDuplicateProcessingStatusResponse | null>(null);
  const [placeGeocodingStatus, setPlaceGeocodingStatus] = useState<AdminPlaceGeocodingStatusResponse | null>(null);
  const [faceProcessingStatus, setFaceProcessingStatus] = useState<AdminFaceProcessingStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isDuplicateActionLoading, setIsDuplicateActionLoading] = useState(false);
  const [isPlaceGeocodingActionLoading, setIsPlaceGeocodingActionLoading] = useState(false);
  const [isFaceProcessingActionLoading, setIsFaceProcessingActionLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

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

  const loadFaceProcessingStatus = useCallback(async () => {
    try {
      const response = await getFaceProcessingStatus();
      setFaceProcessingStatus(response);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to load face processing status.");
    }
  }, []);

  const runFaceProcessingJob = useCallback(async () => {
    setIsFaceProcessingActionLoading(true);
    setErrorMessage("");
    try {
      await runFaceProcessing();
      await loadFaceProcessingStatus();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to start face processing.");
    } finally {
      setIsFaceProcessingActionLoading(false);
    }
  }, [loadFaceProcessingStatus]);

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

  const loadAll = useCallback(async () => {
    await Promise.all([loadSummary(), loadDuplicateStatus(), loadPlaceGeocodingStatus(), loadFaceProcessingStatus()]);
  }, [loadDuplicateStatus, loadFaceProcessingStatus, loadPlaceGeocodingStatus, loadSummary]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  useEffect(() => {
    // Start polling if status is running or stop requested
    const isActive = duplicateStatus && ["running", "stop_requested"].includes(duplicateStatus.current.status);
    
    if (!isActive) {
      return;
    }

    const timer = window.setInterval(() => {
      void loadDuplicateStatus();
    }, 3000);

    return () => {
      window.clearInterval(timer);
    };
  }, [duplicateStatus?.current.status, loadDuplicateStatus]);

  useEffect(() => {
    // Start polling if status is running or stop requested
    const isActive = placeGeocodingStatus && ["running", "stop_requested"].includes(placeGeocodingStatus.current.status);
    
    if (!isActive) {
      return;
    }

    const timer = window.setInterval(() => {
      void loadPlaceGeocodingStatus();
    }, 3000);

    return () => {
      window.clearInterval(timer);
    };
  }, [placeGeocodingStatus?.current.status, loadPlaceGeocodingStatus]);

  useEffect(() => {
    // Poll if face processing is running or stop requested
    const isActive = faceProcessingStatus && ["running", "stop_requested"].includes(faceProcessingStatus.current.status);

    if (!isActive) {
      return;
    }

    const timer = window.setInterval(() => {
      void loadFaceProcessingStatus();
    }, 3000);

    return () => {
      window.clearInterval(timer);
    };
  }, [faceProcessingStatus?.current.status, loadFaceProcessingStatus]);

  const duplicateRunState = duplicateStatus?.current.status ?? "idle";
  const isDuplicateRunActive = duplicateRunState === "running" || duplicateRunState === "stop_requested";

  const placeGeocodingRunState = placeGeocodingStatus?.current.status ?? "idle";
  const isPlaceGeocodingRunActive = placeGeocodingRunState === "running" || placeGeocodingRunState === "stop_requested";

  const faceProcessingRunState = faceProcessingStatus?.current.status ?? "idle";
  const isFaceProcessingRunActive = faceProcessingRunState === "running" || faceProcessingRunState === "stop_requested";

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
          <p className={styles.meta}>Status: {faceProcessingStatus?.current.status ?? "idle"}</p>
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
              disabled={isFaceProcessingActionLoading || isFaceProcessingRunActive}
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

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
  stopFaceProcessing,
  getHeicPreviewStatus,
  runHeicPreviewGeneration,
  stopHeicPreviewGeneration,
  getSourceIntakeSources,
  getSourceIntakeReports,
  getSourceIntakeReportDetail,
} from "@/lib/api";
import type {
  AdminDuplicateProcessingStatusResponse,
  AdminFaceProcessingStatusResponse,
  AdminHeicPreviewStatusResponse,
  AdminPlaceGeocodingStatusResponse,
  AdminSummaryResponse,
  SourceIntakeReportDetail,
  SourceIntakeReportsResponse,
  SourceIntakeSourcesResponse,
} from "@/types/ui-api";

import styles from "./admin-view.module.css";

export default function AdminView() {
  const [summary, setSummary] = useState<AdminSummaryResponse | null>(null);
  const [duplicateStatus, setDuplicateStatus] = useState<AdminDuplicateProcessingStatusResponse | null>(null);
  const [placeGeocodingStatus, setPlaceGeocodingStatus] = useState<AdminPlaceGeocodingStatusResponse | null>(null);
  const [faceProcessingStatus, setFaceProcessingStatus] = useState<AdminFaceProcessingStatusResponse | null>(null);
  const [heicPreviewStatus, setHeicPreviewStatus] = useState<AdminHeicPreviewStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isDuplicateActionLoading, setIsDuplicateActionLoading] = useState(false);
  const [isPlaceGeocodingActionLoading, setIsPlaceGeocodingActionLoading] = useState(false);
  const [isFaceProcessingActionLoading, setIsFaceProcessingActionLoading] = useState(false);
  const [isHeicPreviewActionLoading, setIsHeicPreviewActionLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [sourceIntakeSources, setSourceIntakeSources] = useState<SourceIntakeSourcesResponse | null>(null);
  const [sourceIntakeReports, setSourceIntakeReports] = useState<SourceIntakeReportsResponse | null>(null);
  const [expandedReportFilename, setExpandedReportFilename] = useState<string | null>(null);
  const [reportDetail, setReportDetail] = useState<SourceIntakeReportDetail | null>(null);
  const [isSourceIntakeLoading, setIsSourceIntakeLoading] = useState(false);
  const [isReportDetailLoading, setIsReportDetailLoading] = useState(false);

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

  const loadHeicPreviewStatus = useCallback(async () => {
    try {
      const response = await getHeicPreviewStatus();
      setHeicPreviewStatus(response);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to load HEIC preview status.");
    }
  }, []);

  const loadSourceIntake = useCallback(async () => {
    setIsSourceIntakeLoading(true);
    try {
      const [sourcesRes, reportsRes] = await Promise.all([
        getSourceIntakeSources(),
        getSourceIntakeReports(),
      ]);
      setSourceIntakeSources(sourcesRes);
      setSourceIntakeReports(reportsRes);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to load source intake data.");
    } finally {
      setIsSourceIntakeLoading(false);
    }
  }, []);

  const toggleReportDetail = useCallback(async (filename: string) => {
    if (expandedReportFilename === filename) {
      setExpandedReportFilename(null);
      setReportDetail(null);
      return;
    }
    setExpandedReportFilename(filename);
    setReportDetail(null);
    setIsReportDetailLoading(true);
    try {
      const detail = await getSourceIntakeReportDetail(filename);
      setReportDetail(detail);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to load report detail.");
      setExpandedReportFilename(null);
    } finally {
      setIsReportDetailLoading(false);
    }
  }, [expandedReportFilename]);

  const runHeicPreviewJob = useCallback(async () => {
    setIsHeicPreviewActionLoading(true);
    setErrorMessage("");
    try {
      await runHeicPreviewGeneration();
      await loadHeicPreviewStatus();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to start HEIC preview generation.");
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
      setErrorMessage(error instanceof Error ? error.message : "Failed to request HEIC preview stop.");
    } finally {
      setIsHeicPreviewActionLoading(false);
    }
  }, [loadHeicPreviewStatus]);

  const loadAll = useCallback(async () => {
    await Promise.all([loadSummary(), loadDuplicateStatus(), loadPlaceGeocodingStatus(), loadFaceProcessingStatus(), loadHeicPreviewStatus(), loadSourceIntake()]);
  }, [loadDuplicateStatus, loadFaceProcessingStatus, loadHeicPreviewStatus, loadPlaceGeocodingStatus, loadSourceIntake, loadSummary]);

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

  useEffect(() => {
    const isActive = heicPreviewStatus && ["running", "stop_requested"].includes(heicPreviewStatus.current.status);

    if (!isActive) {
      return;
    }

    const timer = window.setInterval(() => {
      void loadHeicPreviewStatus();
    }, 3000);

    return () => {
      window.clearInterval(timer);
    };
  }, [heicPreviewStatus?.current.status, loadHeicPreviewStatus]);

  const duplicateRunState = duplicateStatus?.current.status ?? "idle";
  const isDuplicateRunActive = duplicateRunState === "running" || duplicateRunState === "stop_requested";

  const placeGeocodingRunState = placeGeocodingStatus?.current.status ?? "idle";
  const isPlaceGeocodingRunActive = placeGeocodingRunState === "running" || placeGeocodingRunState === "stop_requested";

  const faceProcessingRunState = faceProcessingStatus?.current.status ?? "idle";
  const isFaceProcessingRunActive = faceProcessingRunState === "running" || faceProcessingRunState === "stop_requested";

  const heicPreviewRunState = heicPreviewStatus?.current.status ?? "idle";
  const isHeicPreviewRunActive = heicPreviewRunState === "running" || heicPreviewRunState === "stop_requested";

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

        <article className={`${styles.card} ${styles.duplicateCard}`.trim()}>
          <h3 className={styles.cardTitle}>HEIC Preview Generation</h3>
          <p className={styles.meta}>Status: {heicPreviewStatus?.current.status ?? "idle"}</p>
          <p className={styles.meta}>Pending previews: {heicPreviewStatus?.pending_previews ?? 0}</p>
          <p className={styles.meta}>
            Progress: {heicPreviewStatus?.current.assets_processed ?? 0}/{heicPreviewStatus?.current.assets_pending ?? 0}
          </p>
          <p className={styles.meta}>Succeeded: {heicPreviewStatus?.current.assets_succeeded ?? 0}</p>
          <p className={styles.meta}>Failed: {heicPreviewStatus?.current.assets_failed ?? 0}</p>
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

      <section className={styles.sourceIntakeSection}>
        <div className={styles.sectionHeader}>
          <h3 className={styles.sectionTitle}>Source Intake</h3>
          <button
            type="button"
            className={styles.refreshButton}
            onClick={() => void loadSourceIntake()}
            disabled={isSourceIntakeLoading}
          >
            {isSourceIntakeLoading ? "Loading..." : "Refresh"}
          </button>
        </div>

        <div className={styles.sourceIntakeBlock}>
          <h4 className={styles.blockTitle}>Recent Intake Reports</h4>
          {!sourceIntakeReports || sourceIntakeReports.reports.length === 0 ? (
            <p className={styles.emptyState}>
              {isSourceIntakeLoading ? "Loading..." : "No source intake reports found."}
            </p>
          ) : (
            <div className={styles.tableWrapper}>
              <table className={styles.intakeTable}>
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Source Label</th>
                    <th>Scanned</th>
                    <th>Skipped</th>
                    <th>Selected</th>
                    <th>Failed</th>
                    <th>Remaining</th>
                    <th>Complete?</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {sourceIntakeReports.reports.map((report) => (
                    <>
                      <tr key={report.report_filename}>
                        <td>{report.generated_at_utc ? new Date(report.generated_at_utc).toLocaleString() : "-"}</td>
                        <td>{report.source_label ?? "-"}</td>
                        <td>{report.counts?.total_files_scanned ?? "-"}</td>
                        <td>{report.counts?.skipped_already_known ?? "-"}</td>
                        <td>{report.counts?.selected_for_session ?? "-"}</td>
                        <td>{report.counts?.failed_or_rejected ?? "-"}</td>
                        <td>{report.counts?.remaining_unknown_eligible ?? "-"}</td>
                        <td>{report.source_complete === null ? "-" : report.source_complete ? "Yes" : "No"}</td>
                        <td>
                          <button
                            type="button"
                            className={styles.detailToggle}
                            onClick={() => void toggleReportDetail(report.report_filename)}
                          >
                            {expandedReportFilename === report.report_filename ? "Close" : "Details"}
                          </button>
                        </td>
                      </tr>
                      {expandedReportFilename === report.report_filename && (
                        <tr key={`${report.report_filename}-detail`}>
                          <td colSpan={9} className={styles.detailCell}>
                            {isReportDetailLoading ? (
                              <p className={styles.meta}>Loading...</p>
                            ) : reportDetail ? (
                              <div className={styles.detailPanel}>
                                <p className={styles.meta}><strong>File:</strong> {reportDetail.report_filename}</p>
                                <p className={styles.meta}><strong>Source path:</strong> {(reportDetail.raw.source_path as string) ?? "-"}</p>
                                <p className={styles.meta}><strong>Run ID:</strong> {(reportDetail.raw.ingestion_run_id as number) ?? "-"} &nbsp; <strong>Source ID:</strong> {(reportDetail.raw.ingestion_source_id as number) ?? "-"}</p>
                                <p className={styles.meta}><strong>Limit:</strong> {((reportDetail.raw.config as Record<string, unknown>)?.ingest_source_limit as number) ?? "none"} &nbsp; <strong>Batch:</strong> {((reportDetail.raw.config as Record<string, unknown>)?.ingest_batch_size as number) ?? "-"}</p>
                                {reportDetail.raw.counts && (
                                  <div className={styles.detailCounts}>
                                    {Object.entries(reportDetail.raw.counts as Record<string, number>).map(([k, v]) => (
                                      <p key={k} className={styles.meta}>{k.replace(/_/g, " ")}: {v}</p>
                                    ))}
                                  </div>
                                )}
                                {Array.isArray(reportDetail.raw.selected_files) && (reportDetail.raw.selected_files as string[]).length > 0 && (
                                  <details className={styles.fileSample}>
                                    <summary className={styles.meta}>
                                      Sample files ({(reportDetail.raw.selected_files as string[]).length} shown{reportDetail.raw._selected_files_truncated ? ", truncated" : ""})
                                    </summary>
                                    <ul className={styles.fileList}>
                                      {(reportDetail.raw.selected_files as string[]).map((f, i) => (
                                        <li key={i} className={styles.meta}>{f}</li>
                                      ))}
                                    </ul>
                                  </details>
                                )}
                              </div>
                            ) : null}
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className={styles.sourceIntakeBlock}>
          <h4 className={styles.blockTitle}>Known Sources</h4>
          {!sourceIntakeSources || sourceIntakeSources.sources.length === 0 ? (
            <p className={styles.emptyState}>
              {isSourceIntakeLoading ? "Loading..." : "No ingestion sources found."}
            </p>
          ) : (
            <div className={styles.tableWrapper}>
              <table className={styles.intakeTable}>
                <thead>
                  <tr>
                    <th>Label</th>
                    <th>Type</th>
                    <th>Root Path</th>
                    <th>First Seen</th>
                    <th>Last Intake</th>
                    <th>Selected</th>
                    <th>Skipped Known</th>
                    <th>Remaining</th>
                    <th>Complete?</th>
                  </tr>
                </thead>
                <tbody>
                  {sourceIntakeSources.sources.map((src) => (
                    <tr key={src.source_id}>
                      <td>{src.source_label}</td>
                      <td>{src.source_type}</td>
                      <td className={styles.pathCell}>{src.source_root_path ?? "-"}</td>
                      <td>{src.first_seen_at ? new Date(src.first_seen_at).toLocaleDateString() : "-"}</td>
                      <td>{src.last_run_at ? new Date(src.last_run_at).toLocaleString() : "-"}</td>
                      <td>{src.latest_counts?.selected_for_session ?? "-"}</td>
                      <td>{src.latest_counts?.skipped_already_known ?? "-"}</td>
                      <td>{src.latest_counts?.remaining_unknown_eligible ?? "-"}</td>
                      <td>{src.source_complete === null ? "-" : src.source_complete ? "Yes" : "No"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </section>
  );
}

"use client";

import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  getAdminSummary,
  getDuplicateProcessingStatus,
  runDuplicateProcessing,
  stopDuplicateProcessing,
  getLivePhotoPairingStatus,
  runLivePhotoPairing,
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
  createOrGetIntakeSource,
  startSourceIntake,
  getSourceIntakeRunStatus,
  stopSourceIntake,
} from "@/lib/api";
import type {
  AdminDuplicateProcessingStatusResponse,
  AdminFaceProcessingStatusResponse,
  AdminHeicPreviewStatusResponse,
  AdminLivePhotoPairingStatusResponse,
  AdminPlaceGeocodingStatusResponse,
  AdminSummaryResponse,
  SourceIntakeReportDetail,
  SourceIntakeReportsResponse,
  SourceIntakeSourcesResponse,
  SourceCreateResponse,
  SourceIntakeStatusSnapshot,
} from "@/types/ui-api";

import styles from "./admin-view.module.css";
import IcloudAcquisitionCard, { type IcloudAcquisitionSourceIntakeHandoff } from "./IcloudAcquisitionCard";

function normalizeSourceLabelForMatch(value: string | null | undefined): string {
  return (value ?? "").trim().toLowerCase();
}

function normalizeSourcePathForMatch(value: string | null | undefined): string {
  return (value ?? "").trim().replaceAll("\\", "/").toLowerCase();
}

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
  const [sourceIntakeSources, setSourceIntakeSources] = useState<SourceIntakeSourcesResponse | null>(null);
  const [sourceIntakeReports, setSourceIntakeReports] = useState<SourceIntakeReportsResponse | null>(null);
  const [expandedReportFilename, setExpandedReportFilename] = useState<string | null>(null);
  const [reportDetail, setReportDetail] = useState<SourceIntakeReportDetail | null>(null);
  const [isSourceIntakeLoading, setIsSourceIntakeLoading] = useState(false);
  const [isReportDetailLoading, setIsReportDetailLoading] = useState(false);
  const [sourceIntakePreparedNotice, setSourceIntakePreparedNotice] = useState<string | null>(null);
  const [sourceIntakePrepHighlighted, setSourceIntakePrepHighlighted] = useState(false);
  const sourceIntakeFormRef = useRef<HTMLDivElement | null>(null);

  // Source Registry
  const [regLabelMode, setRegLabelMode] = useState<"existing" | "new">("existing");
  const [regExistingLabel, setRegExistingLabel] = useState("");
  const [regNewLabel, setRegNewLabel] = useState("");
  const [regType, setRegType] = useState("local_folder");
  const [regPath, setRegPath] = useState("");
  const [regResult, setRegResult] = useState<SourceCreateResponse | null>(null);
  const [regError, setRegError] = useState("");
  const [isRegLoading, setIsRegLoading] = useState(false);

  // Admin-launched Intake
  const [intakeSourceId, setIntakeSourceId] = useState<number | "">("");
  const [intakeLimit, setIntakeLimit] = useState("");
  const [intakeBatchSize, setIntakeBatchSize] = useState("500");
  const [intakeStatus, setIntakeStatus] = useState<SourceIntakeStatusSnapshot | null>(null);
  const [intakeError, setIntakeError] = useState("");
  const [isIntakeActionLoading, setIsIntakeActionLoading] = useState(false);

  const existingLabelOptions = useMemo(() => {
    const optionsByNormalized = new Map<string, { normalized: string; label: string; sourceCount: number; firstSeen: number }>();

    for (const source of sourceIntakeSources?.sources ?? []) {
      const rawLabel = source.source_label?.trim() ?? "";
      if (!rawLabel) {
        continue;
      }
      const normalized = rawLabel.toLowerCase();
      const firstSeen = source.first_seen_at ? Date.parse(source.first_seen_at) : Number.POSITIVE_INFINITY;
      const existing = optionsByNormalized.get(normalized);

      if (!existing) {
        optionsByNormalized.set(normalized, {
          normalized,
          label: rawLabel,
          sourceCount: 1,
          firstSeen,
        });
      } else {
        existing.sourceCount += 1;
        if (firstSeen < existing.firstSeen) {
          existing.firstSeen = firstSeen;
          existing.label = rawLabel;
        }
      }
    }

    return Array.from(optionsByNormalized.values()).sort((a, b) => a.label.localeCompare(b.label));
  }, [sourceIntakeSources?.sources]);

  const existingLabelSet = useMemo(() => {
    return new Set(existingLabelOptions.map((opt) => opt.normalized));
  }, [existingLabelOptions]);

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

  const loadLivePhotoPairingStatus = useCallback(async () => {
    try {
      const response = await getLivePhotoPairingStatus();
      setLivePhotoPairingStatus(response);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to load Live Photo pairing status.");
    }
  }, []);

  const loadSourceIntake = useCallback(async (): Promise<SourceIntakeSourcesResponse | null> => {
    setIsSourceIntakeLoading(true);
    try {
      const [sourcesRes, reportsRes] = await Promise.all([
        getSourceIntakeSources(),
        getSourceIntakeReports(),
      ]);
      setSourceIntakeSources(sourcesRes);
      setSourceIntakeReports(reportsRes);
      return sourcesRes;
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to load source intake data.");
      return null;
    } finally {
      setIsSourceIntakeLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!sourceIntakePrepHighlighted) {
      return;
    }

    const timer = setTimeout(() => setSourceIntakePrepHighlighted(false), 2000);
    return () => clearTimeout(timer);
  }, [sourceIntakePrepHighlighted]);

  const handlePrepareSourceIntake = useCallback(
    async (handoff: IcloudAcquisitionSourceIntakeHandoff) => {
      setIntakeError("");
      setSourceIntakePreparedNotice(null);

      const refreshedSources = await loadSourceIntake();
      if (!refreshedSources) {
        setIntakeError("Unable to refresh the source registry before preparing Source Intake.");
        sourceIntakeFormRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        setSourceIntakePrepHighlighted(true);
        return;
      }

      const currentSources = refreshedSources.sources;
      const normalizedSourceLabel = normalizeSourceLabelForMatch(handoff.sourceLabel);
      const normalizedSourceRootPath = normalizeSourcePathForMatch(handoff.sourceRootPath);

      const matchedSource = currentSources.find(
        (source) =>
          normalizeSourceLabelForMatch(source.source_label) === normalizedSourceLabel &&
          normalizeSourcePathForMatch(source.source_root_path) === normalizedSourceRootPath,
      );

      if (!matchedSource) {
        setIntakeError(
          "The acquisition source is no longer registered or its path no longer matches. Please review the Source Registry before running Source Intake.",
        );
        sourceIntakeFormRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        setSourceIntakePrepHighlighted(true);
        return;
      }

      setIntakeSourceId(matchedSource.source_id);

      const stagedCount = handoff.fileInventoryCount != null && handoff.fileInventoryCount > 0 ? handoff.fileInventoryCount : null;
      const recentCount = handoff.recentCount != null && handoff.recentCount > 0 ? handoff.recentCount : null;
      const sourceLimit = stagedCount ?? recentCount;
      const cappedSourceLimit = sourceLimit !== null ? Math.min(sourceLimit, 500) : null;

      if (cappedSourceLimit !== null) {
        setIntakeLimit(String(cappedSourceLimit));
      }

      const parsedBatchSize = Number(intakeBatchSize);
      if (!Number.isFinite(parsedBatchSize) || parsedBatchSize < 1) {
        setIntakeBatchSize("500");
      }

      if (handoff.fileInventoryCount === 0) {
        setSourceIntakePreparedNotice(
          `Warning: no staged files are currently available for intake. Prepared ${matchedSource.source_label} and used the recent count fallback for Source Intake.`,
        );
      } else if (cappedSourceLimit !== null) {
        setSourceIntakePreparedNotice(
          `Prepared Source Intake for ${matchedSource.source_label}. Source limit set to ${cappedSourceLimit}. Batch size preserved.`,
        );
      } else {
        setSourceIntakePreparedNotice(`Prepared Source Intake for ${matchedSource.source_label}. Batch size preserved.`);
      }

      sourceIntakeFormRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      setSourceIntakePrepHighlighted(true);
    },
    [intakeBatchSize, loadSourceIntake, sourceIntakeSources?.sources],
  );

  const loadIntakeStatus = useCallback(async () => {
    try {
      const response = await getSourceIntakeRunStatus();
      setIntakeStatus(response);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to load intake status.");
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

  const loadAll = useCallback(async () => {
    await Promise.all([loadSummary(), loadDuplicateStatus(), loadPlaceGeocodingStatus(), loadFaceProcessingStatus(), loadHeicPreviewStatus(), loadLivePhotoPairingStatus(), loadSourceIntake(), loadIntakeStatus()]);
  }, [loadDuplicateStatus, loadFaceProcessingStatus, loadHeicPreviewStatus, loadLivePhotoPairingStatus, loadPlaceGeocodingStatus, loadSourceIntake, loadSummary, loadIntakeStatus]);

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

  useEffect(() => {
    const isActive = livePhotoPairingStatus && livePhotoPairingStatus.current.status === "running";

    if (!isActive) {
      return;
    }

    const timer = window.setInterval(() => {
      void loadLivePhotoPairingStatus();
    }, 1000);

    return () => {
      window.clearInterval(timer);
    };
  }, [livePhotoPairingStatus?.current.status, loadLivePhotoPairingStatus]);

  useEffect(() => {
    // Start polling if intake status is running or stop requested
    const isActive = intakeStatus && ["running", "stop_requested"].includes(intakeStatus.status);

    if (!isActive) {
      return;
    }

    const timer = window.setInterval(() => {
      void loadIntakeStatus();
    }, 1000);

    return () => {
      window.clearInterval(timer);
    };
  }, [intakeStatus?.status, loadIntakeStatus]);

  useEffect(() => {
    // Keep Source Intake tables fresh while an intake run is active.
    const isActive = intakeStatus && ["running", "stop_requested"].includes(intakeStatus.status);

    if (!isActive) {
      return;
    }

    const timer = window.setInterval(() => {
      void loadSourceIntake();
    }, 3000);

    return () => {
      window.clearInterval(timer);
    };
  }, [intakeStatus?.status, loadSourceIntake]);

  useEffect(() => {
    // Run one final refresh when the run reaches a terminal state.
    const isTerminal = intakeStatus && ["completed", "failed", "stopped"].includes(intakeStatus.status);

    if (!isTerminal) {
      return;
    }

    void loadSourceIntake();
  }, [intakeStatus?.run_id, intakeStatus?.status, loadSourceIntake]);

  useEffect(() => {
    if (existingLabelOptions.length === 0) {
      setRegLabelMode("new");
      setRegExistingLabel("");
      return;
    }

    if (regLabelMode === "existing") {
      const hasSelected = existingLabelOptions.some((opt) => opt.label === regExistingLabel);
      if (!hasSelected) {
        setRegExistingLabel(existingLabelOptions[0].label);
      }
    }
  }, [existingLabelOptions, regExistingLabel, regLabelMode]);

  const duplicateRunState = duplicateStatus?.current.status ?? "idle";
  const isDuplicateRunActive = duplicateRunState === "running" || duplicateRunState === "stop_requested";

  const placeGeocodingRunState = placeGeocodingStatus?.current.status ?? "idle";
  const isPlaceGeocodingRunActive = placeGeocodingRunState === "running" || placeGeocodingRunState === "stop_requested";

  const faceProcessingRunState = faceProcessingStatus?.current.status ?? "idle";
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

      <IcloudAcquisitionCard onPrepareSourceIntake={handlePrepareSourceIntake} />

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
                    <th>Deferred</th>
                    <th>Failed</th>
                    <th>Remaining</th>
                    <th>Complete?</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {sourceIntakeReports.reports.map((report) => (
                    <Fragment key={report.report_filename}>
                      <tr>
                        <td>{report.generated_at_utc ? new Date(report.generated_at_utc).toLocaleString() : "-"}</td>
                        <td>{report.source_label ?? "-"}</td>
                        <td>{report.counts?.total_files_scanned ?? "-"}</td>
                        <td>{report.counts?.skipped_already_known ?? "-"}</td>
                        <td>{report.counts?.selected_for_session ?? "-"}</td>
                        <td>{report.counts?.deferred_unready_count ?? "-"}</td>
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
                        <tr>
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
                                {reportDetail.raw.deferred_unready_reasons && (
                                  <div className={styles.detailCounts}>
                                    <p className={styles.meta}><strong>Deferred / Unready reasons</strong></p>
                                    {Object.entries(reportDetail.raw.deferred_unready_reasons as Record<string, number>).map(([k, v]) => (
                                      <p key={k} className={styles.meta}>{k.replace(/_/g, " ")}: {v}</p>
                                    ))}
                                  </div>
                                )}
                                {Array.isArray(reportDetail.raw.deferred_unready_sample) && (reportDetail.raw.deferred_unready_sample as string[]).length > 0 ? (
                                  <details className={styles.fileSample}>
                                    <summary className={styles.meta}>
                                      Deferred / Unready sample ({(reportDetail.raw.deferred_unready_sample as string[]).length} shown)
                                    </summary>
                                    <ul className={styles.fileList}>
                                      {(reportDetail.raw.deferred_unready_sample as string[]).map((f, i) => (
                                        <li key={i} className={styles.meta}>{f}</li>
                                      ))}
                                    </ul>
                                  </details>
                                ) : (
                                  <p className={styles.meta}><strong>Deferred / Unready sample:</strong> none</p>
                                )}
                                {Array.isArray(reportDetail.raw.selected_files) && (reportDetail.raw.selected_files as string[]).length > 0 && (
                                  <details className={styles.fileSample}>
                                    <summary className={styles.meta}>
                                      Selected for intake (not deferred) ({(reportDetail.raw.selected_files as string[]).length} shown{reportDetail.raw._selected_files_truncated ? ", truncated" : ""})
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
                    </Fragment>
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

      <section className={styles.sourceIntakeSection}>
        <div className={styles.sectionHeader}>
          <h3 className={styles.sectionTitle}>Source Registry</h3>
        </div>
        <div className={styles.sourceIntakeBlock}>
          <h4 className={styles.blockTitle}>Register New Source</h4>
          <div className={styles.registryForm}>
            <label className={styles.formLabel}>
              Source Label
              <select
                className={styles.formInput}
                value={regLabelMode === "existing" ? regExistingLabel : "__new__"}
                onChange={e => {
                  const selected = e.target.value;
                  setRegError("");
                  setRegResult(null);
                  if (selected === "__new__") {
                    setRegLabelMode("new");
                  } else {
                    setRegLabelMode("existing");
                    setRegExistingLabel(selected);
                  }
                }}
              >
                {existingLabelOptions.length === 0 ? (
                  <option value="__new__">No existing labels</option>
                ) : (
                  existingLabelOptions.map((opt) => (
                    <option key={opt.normalized} value={opt.label}>
                      {opt.label}{opt.sourceCount > 1 ? ` (${opt.sourceCount})` : ""}
                    </option>
                  ))
                )}
                <option value="__new__">+ Create New Label</option>
              </select>
            </label>
            {regLabelMode === "new" && (
              <label className={styles.formLabel}>
                New Source Label
                <input
                  className={styles.formInput}
                  type="text"
                  value={regNewLabel}
                  onChange={e => setRegNewLabel(e.target.value)}
                  placeholder="e.g. My iPhone Photos 2023"
                />
              </label>
            )}
            <label className={styles.formLabel}>
              Source Type
              <select
                className={styles.formInput}
                value={regType}
                onChange={e => setRegType(e.target.value)}
              >
                <option value="local_folder">local_folder</option>
                <option value="external_drive">external_drive</option>
                <option value="cloud_export">cloud_export</option>
                <option value="scan_batch">scan_batch</option>
                <option value="other">other</option>
              </select>
            </label>
            <label className={styles.formLabel}>
              Source Root Path
              <input
                className={styles.formInput}
                type="text"
                value={regPath}
                onChange={e => setRegPath(e.target.value)}
                placeholder="/absolute/path/to/source"
              />
            </label>
            <button
              type="button"
              className={styles.actionButton}
              disabled={
                isRegLoading
                || !(regLabelMode === "new" ? regNewLabel.trim() : regExistingLabel.trim())
                || !regPath.trim()
              }
              onClick={() => {
                setRegError("");
                setRegResult(null);

                const selectedLabel = (regLabelMode === "new" ? regNewLabel : regExistingLabel).trim();
                if (!selectedLabel) {
                  setRegError("Source label is required.");
                  return;
                }

                if (regLabelMode === "new" && existingLabelSet.has(selectedLabel.toLowerCase())) {
                  setRegError("This label already exists. Please select it from the existing label dropdown.");
                  return;
                }

                setIsRegLoading(true);
                createOrGetIntakeSource({
                  source_label: selectedLabel,
                  source_type: regType,
                  source_root_path: regPath,
                  create_new_label: regLabelMode === "new",
                })
                  .then(res => {
                    setRegResult(res);
                    setRegExistingLabel(res.source_label);
                    if (regLabelMode === "new") {
                      setRegNewLabel("");
                      setRegLabelMode("existing");
                    }
                    void loadSourceIntake();
                  })
                  .catch(err => setRegError(err instanceof Error ? err.message : "Failed to register source."))
                  .finally(() => setIsRegLoading(false));
              }}
            >
              {isRegLoading ? "Registering..." : "Register Source"}
            </button>
            {regError && <p className={styles.errorText}>{regError}</p>}
            {regResult && (
              <p className={styles.successText}>
                {regResult.was_existing ? "Source already exists" : "Source registered"}: #{regResult.ingestion_source_id} — {regResult.source_label}
              </p>
            )}
          </div>
        </div>
      </section>

      <section className={styles.sourceIntakeSection}>
        <div className={styles.sectionHeader}>
          <h3 className={styles.sectionTitle}>Run Source Intake</h3>
          <button
            type="button"
            className={styles.refreshButton}
            onClick={() => {
              setIntakeError("");
              setIsIntakeActionLoading(true);
              getSourceIntakeRunStatus()
                .then(snap => setIntakeStatus(snap))
                .catch(err => setIntakeError(err instanceof Error ? err.message : "Failed to fetch status."))
                .finally(() => setIsIntakeActionLoading(false));
            }}
            disabled={isIntakeActionLoading}
          >
            Refresh Status
          </button>
        </div>
        <div
          ref={sourceIntakeFormRef}
          className={`${styles.sourceIntakeBlock} ${sourceIntakePrepHighlighted ? styles.sourceIntakeBlockHighlighted : ""}`.trim()}
        >
          {sourceIntakePreparedNotice && <p className={styles.metaSmall}>{sourceIntakePreparedNotice}</p>}
          <p className={styles.metaSmall}>
            Staged iCloud files are retained after Source Intake for now. Cleanup will be handled separately in 12.44.1.
          </p>
          <div className={styles.registryForm}>
            <label className={styles.formLabel}>
              Ingestion Source
              <select
                className={styles.formInput}
                value={intakeSourceId}
                onChange={e => setIntakeSourceId(e.target.value === "" ? "" : Number(e.target.value))}
              >
                <option value="">— select a source —</option>
                {(sourceIntakeSources?.sources ?? []).sort((a, b) => (b.last_run_at || "").localeCompare(a.last_run_at || "")).map(src => {
                  const folderName = src.source_root_path ? src.source_root_path.split(/[\\\/]/).filter(Boolean).pop() : "(no path)";
                  return (
                    <option key={src.source_id} value={src.source_id}>
                      {src.source_label} • {src.source_type} • {folderName}
                    </option>
                  );
                })}
              </select>
            </label>
            {intakeSourceId && (sourceIntakeSources?.sources ?? []).find(src => src.source_id === intakeSourceId) && (
              <div className={styles.selectedSourceDetail}>
                <p className={styles.meta}><strong>Selected path:</strong> <code>{((sourceIntakeSources?.sources ?? []).find(src => src.source_id === intakeSourceId))?.source_root_path || "(none)"}</code></p>
              </div>
            )}
            <label className={styles.formLabel}>
              Intake Limit (optional)
              <input
                className={styles.formInput}
                type="number"
                min={1}
                value={intakeLimit}
                onChange={e => setIntakeLimit(e.target.value)}
                placeholder="leave blank for no limit"
              />
            </label>
            <label className={styles.formLabel}>
              Batch Size
              <input
                className={styles.formInput}
                type="number"
                min={1}
                value={intakeBatchSize}
                onChange={e => setIntakeBatchSize(e.target.value)}
              />
            </label>
            <div className={styles.intakeActions}>
              <button
                type="button"
                className={styles.actionButton}
                disabled={isIntakeActionLoading || intakeSourceId === ""}
                onClick={() => {
                  setIntakeError("");
                  setIsIntakeActionLoading(true);
                  startSourceIntake({
                    ingestion_source_id: intakeSourceId as number,
                    source_intake_limit: intakeLimit ? Number(intakeLimit) : null,
                    ingest_batch_size: Number(intakeBatchSize) || 500,
                  })
                    .then(res => setIntakeStatus(res.current))
                    .catch(err => setIntakeError(err instanceof Error ? err.message : "Failed to start intake."))
                    .finally(() => setIsIntakeActionLoading(false));
                }}
              >
                {isIntakeActionLoading ? "Working..." : "Run Intake"}
              </button>
              <button
                type="button"
                className={styles.stopButton}
                disabled={isIntakeActionLoading || !intakeStatus || !(["running", "stop_requested"].includes(intakeStatus.status))}
                onClick={() => {
                  setIntakeError("");
                  setIsIntakeActionLoading(true);
                  stopSourceIntake()
                    .then(res => setIntakeStatus(res.current))
                    .catch(err => setIntakeError(err instanceof Error ? err.message : "Failed to stop."))
                    .finally(() => setIsIntakeActionLoading(false));
                }}
              >
                Stop
              </button>
            </div>
            {intakeError && <p className={styles.errorText}>{intakeError}</p>}
          </div>
          {intakeStatus && (
            <div className={styles.intakeStatusPanel}>
              <p className={styles.meta}><strong>Status:</strong> <span className={styles[`status_${intakeStatus.status}`] ?? styles.statusBadge}>{intakeStatus.status}</span></p>
              {intakeStatus.ingestion_run_id && <p className={styles.meta}><strong>Ingestion run:</strong> #{intakeStatus.ingestion_run_id}</p>}
              {intakeStatus.source_label && (
                <>
                  <p className={styles.meta}><strong>Source:</strong> {intakeStatus.source_label} ({intakeStatus.source_type})</p>
                  {intakeStatus.source_root_path && <p className={styles.meta}><strong>Path:</strong> <code>{intakeStatus.source_root_path}</code></p>}
                </>
              )}
              {intakeStatus.elapsed_seconds !== null && <p className={styles.meta}><strong>Elapsed:</strong> {intakeStatus.elapsed_seconds.toFixed(1)}s</p>}
              <p className={styles.meta}><strong>Scanned:</strong> {intakeStatus.files_scanned} &nbsp; <strong>Skipped known:</strong> {intakeStatus.skipped_known} &nbsp; <strong>Selected:</strong> {intakeStatus.selected}</p>
              <p className={styles.meta}><strong>New unique:</strong> {intakeStatus.processed_new_unique} &nbsp; <strong>Remaining:</strong> {intakeStatus.remaining_unknown}</p>
              {intakeStatus.error_message && <p className={styles.errorText}>{intakeStatus.error_message}</p>}
            </div>
          )}
        </div>
      </section>
    </section>
  );
}

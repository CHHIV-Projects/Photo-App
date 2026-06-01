"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  createSourceProfile,
  createSourceProfileStagingFolder,
  getSourceProfileDetail,
  getSourceIntakeReportDetail,
  getSourceIntakeReports,
  getSourceIntakeRunStatus,
  getSourceProfiles,
  startSourceIntake,
  stopSourceIntake,
  updateSourceProfileMetadata,
  verifySourceProfilePath,
} from "@/lib/api";
import type {
  SourceAcquisitionMethod,
  SourceCloudProvider,
  SourceProfileCreateRequest,
  SourceProfileDetail,
  SourceProfileMetadataUpdateRequest,
  SourceProfilePathCheckResponse,
  SourceIntakeReportDetail,
  SourceIntakeReportSummary,
  SourceProfileStagingFolderCreateResponse,
  SourceProfileStatus,
  SourceProfileSummary,
  SourceProfileType,
  SourceIntakeStatusSnapshot,
} from "@/types/ui-api";

import styles from "./ingestion-view.module.css";

type StatusFilter = SourceProfileStatus | "all";
type EditorMode = "create" | "edit";

type LoadProfilesOptions = {
  refreshOnly?: boolean;
  clearRowErrors?: boolean;
  resetBanner?: boolean;
};

type BannerState = {
  kind: "success" | "error";
  message: string;
} | null;

type EditorFormState = {
  sourceLabel: string;
  sourceType: SourceProfileType;
  profileStatus: SourceProfileStatus;
  sourceRootPath: string;
  cloudProvider: SourceCloudProvider;
  accountUsername: string;
  acquisitionMethod: SourceAcquisitionMethod;
  managedStagingPath: string;
};

const STATUS_OPTIONS: Array<{ value: StatusFilter; label: string }> = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
  { value: "archived", label: "Archived" },
  { value: "test", label: "Test" },
  { value: "deprecated", label: "Deprecated" },
  { value: "all", label: "All" },
];

const EDITABLE_STATUS_OPTIONS: SourceProfileStatus[] = [
  "active",
  "inactive",
  "archived",
  "test",
  "deprecated",
];

const SOURCE_TYPE_OPTIONS: Array<{ value: SourceProfileType; label: string }> = [
  { value: "local_folder", label: "Local Folder" },
  { value: "external_drive", label: "External Drive" },
  { value: "cloud_export", label: "Cloud Export / iCloud" },
  { value: "scan_batch", label: "Scan Batch" },
  { value: "other", label: "Other" },
];

const CLOUD_PROVIDER_OPTIONS: Array<{ value: SourceCloudProvider; label: string }> = [
  { value: "icloud", label: "iCloud" },
  { value: "onedrive", label: "OneDrive" },
  { value: "google_photos", label: "Google Photos" },
  { value: "dropbox", label: "Dropbox" },
  { value: "other", label: "Other" },
];

const ACQUISITION_METHOD_OPTIONS: Array<{ value: SourceAcquisitionMethod; label: string }> = [
  { value: "icloudpd", label: "icloudpd" },
  { value: "folder_scan", label: "folder_scan" },
  { value: "manual_export", label: "manual_export" },
  { value: "none", label: "none" },
];

function initialFormState(): EditorFormState {
  return {
    sourceLabel: "",
    sourceType: "local_folder",
    profileStatus: "active",
    sourceRootPath: "",
    cloudProvider: "icloud",
    accountUsername: "",
    acquisitionMethod: "icloudpd",
    managedStagingPath: "",
  };
}

function computeManagedStagingPreview(sourceLabel: string): string {
  const slug = sourceLabel
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "unnamed-source";
  return `storage/exports/icloud/${slug}`;
}

function toDisplayDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "-";
}

function isIcloudCloudExport(form: EditorFormState): boolean {
  return form.sourceType === "cloud_export" && form.cloudProvider === "icloud";
}

function isIcloudProfile(
  profile: Pick<SourceProfileSummary, "source_type" | "cloud_provider"> | Pick<SourceProfileDetail, "source_type" | "cloud_provider"> | null,
): boolean {
  return profile?.source_type === "cloud_export" && profile.cloud_provider === "icloud";
}

function hasHistoricalReferences(
  profile: Pick<
    SourceProfileSummary,
    "provenance_count" | "ingestion_runs_count" | "source_intake_runs_count" | "icloud_acquisition_runs_count"
  >,
): boolean {
  return (
    (profile.provenance_count ?? 0) > 0
    || (profile.ingestion_runs_count ?? 0) > 0
    || (profile.source_intake_runs_count ?? 0) > 0
    || (profile.icloud_acquisition_runs_count ?? 0) > 0
  );
}

function formatPathStatus(result: SourceProfilePathCheckResponse | null): string {
  if (!result) {
    return "Not checked";
  }
  if (result.exists && result.is_directory) {
    return "Exists";
  }
  return "Missing";
}

function isTransientFetchError(error: unknown): boolean {
  if (!(error instanceof Error)) {
    return false;
  }

  return error.message === "Failed to fetch" || error.name === "TypeError";
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function isLocalOrExternalSource(sourceType: SourceProfileType): boolean {
  return sourceType === "local_folder" || sourceType === "external_drive";
}

function getRunDisabledReason(profile: SourceProfileSummary): string | null {
  if (!isLocalOrExternalSource(profile.source_type)) {
    if (profile.source_type === "cloud_export") {
      return "iCloud/cloud workflows will be added later.";
    }
    return "Run Intake from Ingestion is available for local and external profiles only in this milestone.";
  }

  if (profile.profile_status !== "active") {
    return "Only active profiles can run intake from this tab.";
  }

  return null;
}

function extractReportFilename(reportPath: string | null): string | null {
  if (!reportPath) {
    return null;
  }
  const pieces = reportPath.split(/[\\/]/).filter(Boolean);
  return pieces.length > 0 ? pieces[pieces.length - 1] : null;
}

function mapRunStartError(error: unknown): { message: string; raw: string | null } {
  const raw = error instanceof Error ? error.message : "";
  const normalized = raw.toLowerCase();

  if (normalized.includes("already active")) {
    return {
      message: "Another Source Intake run is already active. Wait for it to finish or request stop.",
      raw,
    };
  }
  if (normalized.includes("no root path configured")) {
    return {
      message: "This Source Profile does not have a valid source path.",
      raw,
    };
  }
  if (normalized.includes("does not exist") || normalized.includes("not a directory")) {
    return {
      message: "The source path is missing or is not a directory.",
      raw,
    };
  }
  if (normalized.includes("drop zone is not empty")) {
    return {
      message: "Cannot start Source Intake because the Drop Zone is not empty. Resolve or clear the current Drop Zone state before starting a new intake.",
      raw,
    };
  }

  return {
    message: "Source Intake could not be started. See details below.",
    raw: raw || null,
  };
}

function calculateExactDuplicateCount(
  selectedForSession: number | null | undefined,
  processedNewUnique: number | null | undefined,
  failedOrRejected: number | null | undefined,
): number | null {
  if (selectedForSession == null || processedNewUnique == null || failedOrRejected == null) {
    return null;
  }

  return Math.max(0, selectedForSession - processedNewUnique - failedOrRejected);
}

export default function IngestionView() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("active");
  const [profiles, setProfiles] = useState<SourceProfileSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [banner, setBanner] = useState<BannerState>(null);

  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editorMode, setEditorMode] = useState<EditorMode>("create");
  const [editingProfile, setEditingProfile] = useState<SourceProfileSummary | null>(null);
  const [editorForm, setEditorForm] = useState<EditorFormState>(initialFormState());
  const [editorError, setEditorError] = useState<string | null>(null);
  const [isSavingEditor, setIsSavingEditor] = useState(false);

  const [isDetailsOpen, setIsDetailsOpen] = useState(false);
  const [detailSourceId, setDetailSourceId] = useState<number | null>(null);
  const [detailProfile, setDetailProfile] = useState<SourceProfileDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailBanner, setDetailBanner] = useState<BannerState>(null);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [isVerifyingPath, setIsVerifyingPath] = useState(false);
  const [pathCheckResult, setPathCheckResult] = useState<SourceProfilePathCheckResponse | null>(null);
  const [stagingCreateResult, setStagingCreateResult] = useState<SourceProfileStagingFolderCreateResponse | null>(null);
  const [isCreatingStagingFolder, setIsCreatingStagingFolder] = useState(false);
  const [sourceIntakeStatus, setSourceIntakeStatus] = useState<SourceIntakeStatusSnapshot | null>(null);
  const [sourceIntakeReports, setSourceIntakeReports] = useState<SourceIntakeReportSummary[]>([]);
  const [isRunActionLoading, setIsRunActionLoading] = useState(false);
  const [runPreflightSourceId, setRunPreflightSourceId] = useState<number | null>(null);
  const [rowRunErrors, setRowRunErrors] = useState<Record<number, string>>({});
  const [runErrorDetails, setRunErrorDetails] = useState<string | null>(null);
  const [isRunConfirmOpen, setIsRunConfirmOpen] = useState(false);
  const [runCandidateProfile, setRunCandidateProfile] = useState<SourceProfileSummary | null>(null);
  const [runCandidatePathCheck, setRunCandidatePathCheck] = useState<SourceProfilePathCheckResponse | null>(null);
  const [isAdvancedRunOptionsOpen, setIsAdvancedRunOptionsOpen] = useState(false);
  const [runLimitInput, setRunLimitInput] = useState("");
  const [runBatchSizeInput, setRunBatchSizeInput] = useState("500");
  const [runOptionsError, setRunOptionsError] = useState<string | null>(null);
  const [dismissedTerminalRunKey, setDismissedTerminalRunKey] = useState<string | null>(null);
  const [selectedReportFilename, setSelectedReportFilename] = useState<string | null>(null);
  const [selectedReportDetail, setSelectedReportDetail] = useState<SourceIntakeReportDetail | null>(null);
  const [isReportDetailLoading, setIsReportDetailLoading] = useState(false);
  const [reportDetailError, setReportDetailError] = useState<string | null>(null);

  const normalizedRunLimitInput = useMemo(() => runLimitInput.trim(), [runLimitInput]);
  const normalizedRunBatchSizeInput = useMemo(() => runBatchSizeInput.trim(), [runBatchSizeInput]);

  const runLimitValidationError = useMemo(() => {
    if (!normalizedRunLimitInput) {
      return null;
    }

    const parsed = Number(normalizedRunLimitInput);
    if (!Number.isInteger(parsed) || parsed <= 0) {
      return "Total Limit must be a positive integer or blank for no limit.";
    }

    return null;
  }, [normalizedRunLimitInput]);

  const runBatchSizeValidationError = useMemo(() => {
    const parsed = Number(normalizedRunBatchSizeInput);
    if (!normalizedRunBatchSizeInput || !Number.isInteger(parsed) || parsed <= 0) {
      return "Batch Size must be a positive integer.";
    }

    return null;
  }, [normalizedRunBatchSizeInput]);

  const runOptionSummaryText = useMemo(() => {
    const limitSummary = normalizedRunLimitInput || "unlimited";
    const batchSummary = normalizedRunBatchSizeInput || "500";
    return `Options: Total Limit = ${limitSummary}, Batch Size = ${batchSummary}`;
  }, [normalizedRunBatchSizeInput, normalizedRunLimitInput]);

  const loadProfiles = useCallback(async (options: LoadProfilesOptions = {}) => {
    const { refreshOnly = false, clearRowErrors = false, resetBanner = true } = options;

    if (refreshOnly) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }

    if (resetBanner) {
      setBanner(null);
    }
    if (clearRowErrors) {
      setRowRunErrors({});
      setRunErrorDetails(null);
    }

    try {
      let response;
      try {
        response = await getSourceProfiles({ status: statusFilter });
      } catch (error) {
        if (!isTransientFetchError(error)) {
          throw error;
        }
        await delay(350);
        response = await getSourceProfiles({ status: statusFilter });
      }
      setProfiles(response.profiles);
    } catch (error) {
      setProfiles([]);
      if (resetBanner) {
        setBanner({
          kind: "error",
          message: error instanceof Error ? error.message : "Failed to load source profiles.",
        });
      }
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    void loadProfiles({ clearRowErrors: true });
  }, [loadProfiles]);

  const loadSourceIntakeStatus = useCallback(async () => {
    try {
      const response = await getSourceIntakeRunStatus();
      setSourceIntakeStatus(response);
    } catch (error) {
      setBanner({
        kind: "error",
        message: error instanceof Error ? error.message : "Failed to load source intake status.",
      });
    }
  }, []);

  const loadSourceIntakeReports = useCallback(async () => {
    try {
      const response = await getSourceIntakeReports();
      setSourceIntakeReports(response.reports);
    } catch {
      // Keep run/report polling resilient and avoid replacing current table state on intermittent report errors.
    }
  }, []);

  useEffect(() => {
    void loadSourceIntakeStatus();
    void loadSourceIntakeReports();
  }, [loadSourceIntakeReports, loadSourceIntakeStatus]);

  const isSourceIntakeActive = sourceIntakeStatus
    ? ["running", "stop_requested"].includes(sourceIntakeStatus.status)
    : false;

  useEffect(() => {
    if (isSourceIntakeActive) {
      setDismissedTerminalRunKey(null);
    }
  }, [isSourceIntakeActive]);

  useEffect(() => {
    if (!isSourceIntakeActive) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadSourceIntakeStatus();
    }, 1000);
    return () => window.clearInterval(timer);
  }, [isSourceIntakeActive, loadSourceIntakeStatus]);

  useEffect(() => {
    if (!isSourceIntakeActive) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadProfiles({ refreshOnly: true, resetBanner: false });
      void loadSourceIntakeReports();
    }, 3000);
    return () => window.clearInterval(timer);
  }, [isSourceIntakeActive, loadProfiles, loadSourceIntakeReports]);

  useEffect(() => {
    if (!sourceIntakeStatus || !["completed", "failed", "stopped"].includes(sourceIntakeStatus.status)) {
      return;
    }
    void loadProfiles({ refreshOnly: true, resetBanner: false });
    void loadSourceIntakeReports();
  }, [sourceIntakeStatus?.run_id, sourceIntakeStatus?.status, loadProfiles, loadSourceIntakeReports]);

  const countsSummary = useMemo(() => {
    const counts: Record<SourceProfileStatus, number> = {
      active: 0,
      inactive: 0,
      archived: 0,
      test: 0,
      deprecated: 0,
    };

    for (const profile of profiles) {
      counts[profile.profile_status] += 1;
    }

    return {
      active: counts.active,
      nonActive: counts.archived + counts.test + counts.deprecated,
    };
  }, [profiles]);

  const managedStagingPreview = useMemo(() => {
    return computeManagedStagingPreview(editorForm.sourceLabel);
  }, [editorForm.sourceLabel]);

  const editingProfileIsReferenced = useMemo(() => {
    return editingProfile ? hasHistoricalReferences(editingProfile) : false;
  }, [editingProfile]);

  const isManagedStagingLocked = useMemo(() => {
    return editorMode === "edit" && editingProfileIsReferenced && isIcloudProfile(editingProfile);
  }, [editingProfile, editingProfileIsReferenced, editorMode]);

  const loadDetail = useCallback(async (sourceId: number) => {
    setIsLoadingDetails(true);
    setDetailError(null);
    try {
      const detail = await getSourceProfileDetail(sourceId);
      setDetailProfile(detail);
    } catch (error) {
      setDetailProfile(null);
      setDetailError(error instanceof Error ? error.message : "Failed to load source profile details.");
    } finally {
      setIsLoadingDetails(false);
    }
  }, []);

  const openCreateDrawer = useCallback(() => {
    setIsDetailsOpen(false);
    setEditorMode("create");
    setEditingProfile(null);
    setEditorError(null);
    setEditorForm(initialFormState());
    setIsEditorOpen(true);
  }, []);

  const openEditDrawer = useCallback((profile: SourceProfileSummary) => {
    setIsDetailsOpen(false);
    setEditorMode("edit");
    setEditingProfile(profile);
    setEditorError(null);
    setEditorForm({
      sourceLabel: profile.source_label,
      sourceType: profile.source_type,
      profileStatus: profile.profile_status,
      sourceRootPath: profile.source_root_path ?? "",
      cloudProvider: profile.cloud_provider ?? "icloud",
      accountUsername: profile.account_username ?? "",
      acquisitionMethod: profile.acquisition_method ?? "icloudpd",
      managedStagingPath: profile.managed_staging_path ?? "",
    });
    setIsEditorOpen(true);
  }, []);

  const openDetailsDrawer = useCallback((profile: SourceProfileSummary) => {
    setIsEditorOpen(false);
    setIsDetailsOpen(true);
    setDetailSourceId(profile.source_id);
    setDetailProfile(null);
    setDetailError(null);
    setDetailBanner(null);
    setPathCheckResult(null);
    setStagingCreateResult(null);
    void loadDetail(profile.source_id);
  }, [loadDetail]);

  const closeEditor = useCallback(() => {
    setIsEditorOpen(false);
    setEditorError(null);
  }, []);

  const closeDetails = useCallback(() => {
    setIsDetailsOpen(false);
    setDetailSourceId(null);
    setDetailProfile(null);
    setDetailError(null);
    setDetailBanner(null);
    setPathCheckResult(null);
    setStagingCreateResult(null);
  }, []);

  const handleVerifyPath = useCallback(async () => {
    if (!detailSourceId) {
      return;
    }
    setIsVerifyingPath(true);
    setDetailBanner(null);
    try {
      const result = await verifySourceProfilePath(detailSourceId);
      setPathCheckResult(result);
    } catch (error) {
      setDetailBanner({
        kind: "error",
        message: error instanceof Error ? error.message : "Failed to verify the configured path.",
      });
    } finally {
      setIsVerifyingPath(false);
    }
  }, [detailSourceId]);

  const handleCreateStagingFolder = useCallback(async () => {
    if (!detailSourceId) {
      return;
    }
    setIsCreatingStagingFolder(true);
    setDetailBanner(null);
    try {
      const result = await createSourceProfileStagingFolder(detailSourceId);
      setStagingCreateResult(result);
      setDetailBanner({
        kind: "success",
        message: result.created ? "Managed staging folder created." : "Managed staging folder already exists.",
      });
      const refreshedPath = await verifySourceProfilePath(detailSourceId);
      setPathCheckResult(refreshedPath);
      await loadProfiles({ refreshOnly: true });
      await loadDetail(detailSourceId);
    } catch (error) {
      setDetailBanner({
        kind: "error",
        message: error instanceof Error ? error.message : "Failed to create the managed staging folder.",
      });
    } finally {
      setIsCreatingStagingFolder(false);
    }
  }, [detailSourceId, loadDetail, loadProfiles]);

  const saveEditor = useCallback(async () => {
    setEditorError(null);

    const trimmedLabel = editorForm.sourceLabel.trim();
    if (!trimmedLabel) {
      setEditorError("Source label is required.");
      return;
    }

    if (editorMode === "create") {
      if (!isIcloudCloudExport(editorForm) && !editorForm.sourceRootPath.trim()) {
        setEditorError("Source root path is required for this source type.");
        return;
      }

      if (isIcloudCloudExport(editorForm) && !editorForm.accountUsername.trim()) {
        setEditorError("Account username is required for iCloud source profiles.");
        return;
      }
    }

    setIsSavingEditor(true);
    try {
      if (editorMode === "create") {
        const payload: SourceProfileCreateRequest = {
          source_label: trimmedLabel,
          source_type: editorForm.sourceType,
          profile_status: editorForm.profileStatus,
          source_root_path: isIcloudCloudExport(editorForm)
            ? null
            : editorForm.sourceRootPath.trim(),
          cloud_provider: editorForm.sourceType === "cloud_export" ? editorForm.cloudProvider : null,
          account_username: editorForm.accountUsername.trim() || null,
          acquisition_method: editorForm.sourceType === "cloud_export" ? editorForm.acquisitionMethod : null,
          managed_staging_path: editorForm.sourceType === "cloud_export"
            ? (editorForm.managedStagingPath.trim() || managedStagingPreview)
            : null,
        };

        const response = await createSourceProfile(payload);
        await loadProfiles({ refreshOnly: true });
        closeEditor();
        setBanner({
          kind: "success",
          message: response.already_exists
            ? `Source profile already exists: ${response.profile.source_label}`
            : `Source profile created: ${response.profile.source_label}`,
        });
        return;
      }

      if (!editingProfile) {
        setEditorError("Unable to save source profile.");
        return;
      }

      const payload: SourceProfileMetadataUpdateRequest = {
        source_label: trimmedLabel,
        profile_status: editorForm.profileStatus,
        cloud_provider: editorForm.sourceType === "cloud_export" ? editorForm.cloudProvider : null,
        account_username: editorForm.accountUsername.trim() || null,
        acquisition_method: editorForm.sourceType === "cloud_export" ? editorForm.acquisitionMethod : null,
        ...(editorForm.sourceType === "cloud_export" && !isManagedStagingLocked
          ? { managed_staging_path: editorForm.managedStagingPath.trim() || null }
          : {}),
      };

      const updated = await updateSourceProfileMetadata(editingProfile.source_id, payload);
      await loadProfiles({ refreshOnly: true });
      closeEditor();
      if (statusFilter !== "all" && updated.profile_status !== statusFilter) {
        setBanner({
          kind: "success",
          message: `Source profile updated. It is now hidden by the ${statusFilter} filter.`,
        });
      } else {
        setBanner({
          kind: "success",
          message: `Source profile updated: ${updated.source_label}`,
        });
      }
    } catch (error) {
      setEditorError(error instanceof Error ? error.message : "Failed to save source profile.");
    } finally {
      setIsSavingEditor(false);
    }
  }, [
    closeEditor,
    editorForm,
    editorMode,
    editingProfile,
    isManagedStagingLocked,
    loadProfiles,
    managedStagingPreview,
    statusFilter,
  ]);

  const detailPathLabel = detailProfile && isIcloudProfile(detailProfile) ? "Staging status" : "Path status";
  const detailVerifyButtonLabel = detailProfile && isIcloudProfile(detailProfile) ? "Verify Staging" : "Verify Path";

  const activeRunReport = useMemo(() => {
    if (!sourceIntakeStatus) {
      return null;
    }

    const reportFilenameFromStatus = extractReportFilename(sourceIntakeStatus.report_path);
    if (reportFilenameFromStatus) {
      const byName = sourceIntakeReports.find((report) => report.report_filename === reportFilenameFromStatus);
      if (byName) {
        return byName;
      }
    }

    if (sourceIntakeStatus.ingestion_run_id != null) {
      const byRun = sourceIntakeReports.find((report) => report.ingestion_run_id === sourceIntakeStatus.ingestion_run_id);
      if (byRun) {
        return byRun;
      }
    }

    return sourceIntakeReports.length > 0 ? sourceIntakeReports[0] : null;
  }, [sourceIntakeReports, sourceIntakeStatus]);

  const isTerminalRun = sourceIntakeStatus
    ? ["completed", "failed", "stopped"].includes(sourceIntakeStatus.status)
    : false;

  const currentTerminalRunKey = useMemo(() => terminalSummaryKey(sourceIntakeStatus), [sourceIntakeStatus]);
  const showTerminalSummary = Boolean(
    sourceIntakeStatus
    && isTerminalRun
    && currentTerminalRunKey
    && currentTerminalRunKey !== dismissedTerminalRunKey,
  );

  const terminalReportFilename =
    extractReportFilename(sourceIntakeStatus?.report_path ?? null)
    || activeRunReport?.report_filename
    || null;

  const latestReportBySourceId = useMemo(() => {
    const bySource = new Map<number, SourceIntakeReportSummary>();
    for (const report of sourceIntakeReports) {
      if (report.ingestion_source_id == null || bySource.has(report.ingestion_source_id)) {
        continue;
      }
      bySource.set(report.ingestion_source_id, report);
    }
    return bySource;
  }, [sourceIntakeReports]);

  const recentReportsBySourceId = useMemo(() => {
    const bySource = new Map<number, SourceIntakeReportSummary[]>();
    for (const report of sourceIntakeReports) {
      if (report.ingestion_source_id == null) {
        continue;
      }
      const list = bySource.get(report.ingestion_source_id) ?? [];
      if (list.length < 5) {
        list.push(report);
      }
      bySource.set(report.ingestion_source_id, list);
    }
    return bySource;
  }, [sourceIntakeReports]);

  const selectedReportSummary = useMemo(() => {
    if (!selectedReportFilename) {
      return null;
    }
    return sourceIntakeReports.find((report) => report.report_filename === selectedReportFilename) ?? null;
  }, [selectedReportFilename, sourceIntakeReports]);

  const terminalExactDuplicates = useMemo(() => {
    if (!sourceIntakeStatus) {
      return null;
    }

    return calculateExactDuplicateCount(
      sourceIntakeStatus.selected,
      sourceIntakeStatus.processed_new_unique,
      sourceIntakeStatus.failed_or_rejected,
    );
  }, [sourceIntakeStatus]);

  const reportSummaryExactDuplicates = useMemo(() => {
    return calculateExactDuplicateCount(
      selectedReportSummary?.counts?.selected_for_session,
      selectedReportSummary?.counts?.processed_new_unique,
      selectedReportSummary?.counts?.failed_or_rejected,
    );
  }, [selectedReportSummary]);

  const selectedReportPath = useMemo(() => {
    if (!selectedReportFilename) {
      return null;
    }

    const rawPath = selectedReportDetail?.raw?.report_path;
    if (sourceIntakeStatus?.report_path && extractReportFilename(sourceIntakeStatus.report_path) === selectedReportFilename) {
      return sourceIntakeStatus.report_path;
    }

    return buildReportReferencePath(selectedReportFilename, rawPath);
  }, [selectedReportDetail, selectedReportFilename, sourceIntakeStatus?.report_path]);

  const loadReportDetail = useCallback(async (reportFilename: string) => {
    setIsReportDetailLoading(true);
    setReportDetailError(null);
    setSelectedReportDetail(null);
    try {
      const detail = await getSourceIntakeReportDetail(reportFilename);
      setSelectedReportDetail(detail);
    } catch (error) {
      setReportDetailError(error instanceof Error ? error.message : "Failed to load report detail.");
    } finally {
      setIsReportDetailLoading(false);
    }
  }, []);

  const handleToggleReportSummary = useCallback((reportFilename: string) => {
    if (selectedReportFilename === reportFilename) {
      setSelectedReportFilename(null);
      setSelectedReportDetail(null);
      setReportDetailError(null);
      return;
    }
    setSelectedReportFilename(reportFilename);
    void loadReportDetail(reportFilename);
  }, [loadReportDetail, selectedReportFilename]);

  const handleRefreshReportSummary = useCallback(() => {
    if (!selectedReportFilename) {
      return;
    }
    void loadReportDetail(selectedReportFilename);
  }, [loadReportDetail, selectedReportFilename]);

  const closeRunConfirmation = useCallback(() => {
    setIsRunConfirmOpen(false);
    setRunCandidateProfile(null);
    setRunCandidatePathCheck(null);
    setIsAdvancedRunOptionsOpen(false);
    setRunLimitInput("");
    setRunBatchSizeInput("500");
    setRunOptionsError(null);
  }, []);

  const setRowRunError = useCallback((sourceId: number, message: string) => {
    setRowRunErrors((prev) => ({ ...prev, [sourceId]: message }));
  }, []);

  const clearRowRunError = useCallback((sourceId: number) => {
    setRowRunErrors((prev) => {
      const next = { ...prev };
      delete next[sourceId];
      return next;
    });
  }, []);

  const handleRunIntakeClick = useCallback(async (profile: SourceProfileSummary) => {
    clearRowRunError(profile.source_id);
    setRunErrorDetails(null);
    setBanner(null);

    const disabledReason = getRunDisabledReason(profile);
    if (disabledReason) {
      setRowRunError(profile.source_id, disabledReason);
      return;
    }

    if (isSourceIntakeActive) {
      const message = "Another Source Intake run is already active. Wait for it to finish or request stop.";
      setRowRunError(profile.source_id, message);
      setBanner({ kind: "error", message });
      return;
    }

    setRunPreflightSourceId(profile.source_id);
    try {
      const pathCheck = await verifySourceProfilePath(profile.source_id);
      if (!pathCheck.exists || !pathCheck.is_directory) {
        const message = "Cannot run intake. Source path does not exist or is not a directory.";
        setRowRunError(profile.source_id, message);
        setBanner({ kind: "error", message });
        return;
      }

      setRunCandidateProfile(profile);
      setRunCandidatePathCheck(pathCheck);
      setRunLimitInput("");
      setRunBatchSizeInput("500");
      setIsAdvancedRunOptionsOpen(false);
      setRunOptionsError(null);
      setIsRunConfirmOpen(true);
    } catch (error) {
      const mapped = mapRunStartError(error);
      setRowRunError(profile.source_id, mapped.message);
      setBanner({ kind: "error", message: mapped.message });
      setRunErrorDetails(mapped.raw);
    } finally {
      setRunPreflightSourceId(null);
    }
  }, [clearRowRunError, isSourceIntakeActive, setRowRunError]);

  const handleConfirmRunIntake = useCallback(async () => {
    if (!runCandidateProfile) {
      return;
    }

    if (runLimitValidationError || runBatchSizeValidationError) {
      setIsAdvancedRunOptionsOpen(true);
      setRunOptionsError("Fix run option values before starting Source Intake.");
      return;
    }

    setIsRunActionLoading(true);
    clearRowRunError(runCandidateProfile.source_id);
    setRunErrorDetails(null);
    setRunOptionsError(null);
    setBanner(null);

    const parsedLimit = Number(normalizedRunLimitInput);
    const parsedBatchSize = Number(normalizedRunBatchSizeInput);

    try {
      const response = await startSourceIntake({
        ingestion_source_id: runCandidateProfile.source_id,
        source_intake_limit: normalizedRunLimitInput ? parsedLimit : null,
        ingest_batch_size: parsedBatchSize,
      });

      setSourceIntakeStatus(response.current);
      setDismissedTerminalRunKey(null);
      setBanner({ kind: "success", message: `Source Intake started for ${runCandidateProfile.source_label}.` });
      closeRunConfirmation();
      await loadSourceIntakeReports();
      await loadProfiles({ refreshOnly: true, resetBanner: false });
    } catch (error) {
      const mapped = mapRunStartError(error);
      setRowRunError(runCandidateProfile.source_id, mapped.message);
      setBanner({ kind: "error", message: mapped.message });
      setRunErrorDetails(mapped.raw);
    } finally {
      setIsRunActionLoading(false);
    }
  }, [
    clearRowRunError,
    closeRunConfirmation,
    loadProfiles,
    loadSourceIntakeReports,
    normalizedRunBatchSizeInput,
    normalizedRunLimitInput,
    runCandidateProfile,
    runBatchSizeValidationError,
    runLimitValidationError,
    setRowRunError,
  ]);

  const handleRequestStop = useCallback(async () => {
    setIsRunActionLoading(true);
    setBanner(null);
    try {
      const response = await stopSourceIntake();
      setSourceIntakeStatus(response.current);
      setBanner({ kind: "success", message: "Stop requested. Current batch will finish before exit." });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to request stop.";
      setBanner({ kind: "error", message });
      setRunErrorDetails(message);
    } finally {
      setIsRunActionLoading(false);
    }
  }, []);

  return (
    <section className={styles.root}>
      <header className={styles.header}>
        <div>
          <h2 className={styles.title}>Ingestion</h2>
          <p className={styles.subtitle}>
            Source profile lifecycle management foundation. Existing Source Intake operational tools remain in Admin.
          </p>
        </div>
        <div className={styles.toolbar}>
          <button type="button" className={styles.button} onClick={openCreateDrawer}>
            Create Source Profile
          </button>
          <label>
            <span className={styles.subtitle}>Status filter</span>
            <br />
            <select
              className={styles.select}
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className={styles.button}
            onClick={() => void loadProfiles({ refreshOnly: true, clearRowErrors: true })}
            disabled={isLoading || isRefreshing}
          >
            {isRefreshing ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </header>

      {banner && (
        <p className={banner.kind === "success" ? styles.bannerSuccess : styles.bannerError}>
          {banner.message}
        </p>
      )}

      <p className={styles.note}>
        Source profiles define where files come from. Run Intake from this tab supports active local and external profiles.
      </p>
      <p className={styles.note}>
        Lifecycle status does not delete files, sources, or provenance. Archived, test, and deprecated sources are retained for history and remain visible through the status filter.
      </p>
      <p className={styles.note}>
        Source Profile status changes are non-destructive and do not rewrite prior provenance.
      </p>
      <p className={styles.note}>
        Source labels are not globally unique. Source identity is based on label + type + effective path. For iCloud, managed staging path is the effective operational path when present.
      </p>
      <p className={styles.note}>
        iCloud authentication is handled by icloudpd outside Photo Organizer. Do not enter Apple ID passwords here.
      </p>
      <p className={styles.placeholder}>Full Source Intake reports remain available in Admin.</p>
      <p className={styles.subtitle}>
        Active shown: {countsSummary.active} | Archived/Test/Deprecated shown: {countsSummary.nonActive}
      </p>

      {sourceIntakeStatus && isSourceIntakeActive && (
        <section className={styles.runPanel}>
          <div className={styles.runPanelHeader}>
            <h3 className={styles.runPanelTitle}>Source Intake is currently running</h3>
            <button
              type="button"
              className={styles.stopButton}
              onClick={() => void handleRequestStop()}
              disabled={isRunActionLoading || sourceIntakeStatus.status === "stop_requested"}
            >
              {sourceIntakeStatus.status === "stop_requested"
                ? "Stop Requested"
                : (isRunActionLoading ? "Requesting..." : "Request Stop")}
            </button>
          </div>
          <p className={styles.helperText}>Only one Source Intake run can run at a time.</p>
          <div className={styles.runMetrics}>
            <span>
              <strong>Status:</strong>{" "}
              <span className={`${styles.runStatusBadge} ${statusClassName(sourceIntakeStatus.status)}`}>
                {toStatusLabel(sourceIntakeStatus.status)}
              </span>
            </span>
            {sourceIntakeStatus.source_label && (
              <span><strong>Source:</strong> {sourceIntakeStatus.source_label} ({sourceIntakeStatus.source_type})</span>
            )}
            {sourceIntakeStatus.started_at && <span><strong>Started:</strong> {toDisplayDate(sourceIntakeStatus.started_at)}</span>}
            {sourceIntakeStatus.stop_requested && <span><strong>Stop Requested:</strong> Yes</span>}
            <span><strong>Scanned:</strong> {sourceIntakeStatus.files_scanned}</span>
            <span><strong>Eligible Unknown:</strong> {sourceIntakeStatus.selected + sourceIntakeStatus.remaining_unknown}</span>
            <span><strong>Selected for Session:</strong> {sourceIntakeStatus.selected}</span>
            <span><strong>Staged to Drop Zone:</strong> {sourceIntakeStatus.staged}</span>
            <span><strong>Processed New:</strong> {sourceIntakeStatus.processed_new_unique}</span>
          </div>
        </section>
      )}

      {sourceIntakeStatus && showTerminalSummary && (
        <section className={styles.runPanel}>
          <div className={styles.runPanelHeader}>
            <h3 className={styles.runPanelTitle}>Last Source Intake Summary</h3>
            <div className={styles.rowActions}>
              {terminalReportFilename && (
                <button
                  type="button"
                  className={styles.updateButton}
                  onClick={() => handleToggleReportSummary(terminalReportFilename)}
                >
                  {selectedReportFilename === terminalReportFilename ? "Hide Report Summary" : "View Report Summary"}
                </button>
              )}
              <button
                type="button"
                className={styles.button}
                onClick={() => setDismissedTerminalRunKey(currentTerminalRunKey)}
              >
                Dismiss
              </button>
            </div>
          </div>
          <div className={styles.runMetrics}>
            <span>
              <strong>Final Status:</strong>{" "}
              <span className={`${styles.runStatusBadge} ${statusClassName(sourceIntakeStatus.status)}`}>
                {toStatusLabel(sourceIntakeStatus.status)}
              </span>
            </span>
            {sourceIntakeStatus.source_label && (
              <span><strong>Source:</strong> {sourceIntakeStatus.source_label} ({sourceIntakeStatus.source_type})</span>
            )}
            <span><strong>Started:</strong> {toDisplayDate(sourceIntakeStatus.started_at)}</span>
            <span><strong>Finished:</strong> {toDisplayDate(sourceIntakeStatus.finished_at)}</span>
            <span><strong>Scanned:</strong> {sourceIntakeStatus.files_scanned}</span>
            <span><strong>Skipped Known:</strong> {sourceIntakeStatus.skipped_known}</span>
            <span><strong>Eligible Unknown:</strong> {sourceIntakeStatus.selected + sourceIntakeStatus.remaining_unknown}</span>
            <span><strong>Selected for Session:</strong> {sourceIntakeStatus.selected}</span>
            <span><strong>Staged to Drop Zone:</strong> {sourceIntakeStatus.staged}</span>
            <span><strong>Processed New:</strong> {sourceIntakeStatus.processed_new_unique}</span>
            <span><strong>Remaining Unknown Eligible:</strong> {sourceIntakeStatus.remaining_unknown}</span>
            {activeRunReport?.counts?.failed_or_rejected != null && (
              <span><strong>Failed/Rejected:</strong> {activeRunReport.counts.failed_or_rejected}</span>
            )}
            {terminalExactDuplicates != null && (
              <span><strong>Exact Duplicates (Vault):</strong> {terminalExactDuplicates}</span>
            )}
            {activeRunReport?.counts?.deferred_unready_count != null && (
              <span><strong>Deferred/Unready:</strong> {activeRunReport.counts.deferred_unready_count}</span>
            )}
            {activeRunReport?.source_complete != null && (
              <span><strong>Source Complete:</strong> {activeRunReport.source_complete ? "Yes" : "No"}</span>
            )}
            {terminalReportFilename && (
              <span>
                <strong>Report:</strong> {terminalReportFilename}
              </span>
            )}
            {sourceIntakeStatus.report_path && <span><strong>Path:</strong> {sourceIntakeStatus.report_path}</span>}
          </div>
        </section>
      )}

      {selectedReportFilename && (
        <section className={styles.runPanel}>
          <div className={styles.runPanelHeader}>
            <h3 className={styles.runPanelTitle}>Report Summary</h3>
            <div className={styles.rowActions}>
              <button
                type="button"
                className={styles.button}
                onClick={() => void handleRefreshReportSummary()}
                disabled={isReportDetailLoading}
              >
                {isReportDetailLoading ? "Refreshing..." : "Refresh Report"}
              </button>
              <button
                type="button"
                className={styles.button}
                onClick={() => {
                  setSelectedReportFilename(null);
                  setSelectedReportDetail(null);
                  setReportDetailError(null);
                }}
              >
                Close
              </button>
            </div>
          </div>

          {reportDetailError ? (
            <p className={styles.bannerError}>{reportDetailError}</p>
          ) : isReportDetailLoading ? (
            <p className={styles.helperText}>Loading report summary...</p>
          ) : (
            <>
              <div className={styles.runMetrics}>
                <span><strong>Report Filename:</strong> {selectedReportFilename}</span>
                <span><strong>Report Path:</strong> {selectedReportPath ?? "-"}</span>
                <span><strong>Source Label:</strong> {selectedReportSummary?.source_label ?? "-"}</span>
                <span><strong>Source ID:</strong> {selectedReportSummary?.ingestion_source_id ?? "-"}</span>
                <span><strong>Generated:</strong> {toDisplayDate(selectedReportSummary?.generated_at_utc ?? null)}</span>
                <span><strong>Ingestion Run ID:</strong> {selectedReportSummary?.ingestion_run_id ?? "-"}</span>
                <span><strong>Source Intake Limit:</strong> {selectedReportSummary?.ingest_source_limit ?? "none"}</span>
                <span><strong>Ingest Batch Size:</strong> {selectedReportSummary?.ingest_batch_size ?? "-"}</span>
                <span><strong>Scanned:</strong> {selectedReportSummary?.counts?.total_files_scanned ?? "-"}</span>
                <span><strong>Skipped Known:</strong> {selectedReportSummary?.counts?.skipped_already_known ?? "-"}</span>
                <span><strong>Eligible Unknown:</strong> {selectedReportSummary?.counts?.eligible_unknown_files ?? "-"}</span>
                <span><strong>Selected for Session:</strong> {selectedReportSummary?.counts?.selected_for_session ?? "-"}</span>
                <span><strong>Staged to Drop Zone:</strong> {selectedReportSummary?.counts?.staged_to_dropzone ?? "-"}</span>
                <span><strong>Processed New Unique:</strong> {selectedReportSummary?.counts?.processed_new_unique ?? "-"}</span>
                <span><strong>Failed/Rejected:</strong> {selectedReportSummary?.counts?.failed_or_rejected ?? "-"}</span>
                <span><strong>Exact Duplicates (Vault):</strong> {reportSummaryExactDuplicates ?? "-"}</span>
                <span><strong>Deferred/Unready:</strong> {selectedReportSummary?.counts?.deferred_unready_count ?? "-"}</span>
                <span><strong>Remaining Unknown Eligible:</strong> {selectedReportSummary?.counts?.remaining_unknown_eligible ?? "-"}</span>
                <span><strong>Source Complete:</strong> {selectedReportSummary?.source_complete == null ? "-" : selectedReportSummary.source_complete ? "Yes" : "No"}</span>
              </div>

              <p className={styles.placeholder}>Full Source Intake report details remain available in Admin.</p>

              {selectedReportDetail && (
                <details className={styles.errorDetails}>
                  <summary>Show raw report details</summary>
                  <pre className={styles.errorDetailsText}>{JSON.stringify(selectedReportDetail.raw, null, 2)}</pre>
                </details>
              )}
            </>
          )}
        </section>
      )}

      {runErrorDetails && (
        <details className={styles.errorDetails}>
          <summary>Details</summary>
          <pre className={styles.errorDetailsText}>{runErrorDetails}</pre>
        </details>
      )}

      {isLoading ? (
        <p className={styles.empty}>Loading source profiles...</p>
      ) : profiles.length === 0 ? (
        <p className={styles.empty}>No source profiles match the selected status filter.</p>
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Source Label</th>
                <th>Type</th>
                <th>Status</th>
                <th>Root Path</th>
                <th>Cloud Provider</th>
                <th>Acquisition Method</th>
                <th>Managed Staging Path</th>
                <th>Account Username (Masked)</th>
                <th>First Seen</th>
                <th>Last Run</th>
                <th>Reference Counts</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {profiles.map((profile) => {
                const isReferenced = hasHistoricalReferences(profile);
                return (
                  <tr key={profile.source_id}>
                    <td>
                      <div className={styles.labelCell}>
                        <span>{profile.source_label}</span>
                        <span className={isReferenced ? styles.referenceBadge : styles.unreferencedBadge}>
                          {isReferenced ? "Referenced" : "Unreferenced"}
                        </span>
                      </div>
                    </td>
                    <td>{profile.source_type}</td>
                    <td>
                      <span className={styles.statusBadge}>{profile.profile_status}</span>
                    </td>
                    <td className={styles.pathCell}>{profile.source_root_path ?? "-"}</td>
                    <td>{profile.cloud_provider ?? "-"}</td>
                    <td>{profile.acquisition_method ?? "-"}</td>
                    <td className={styles.pathCell}>{profile.managed_staging_path ?? "-"}</td>
                    <td>{profile.account_username_masked ?? "-"}</td>
                    <td>{toDisplayDate(profile.first_seen_at)}</td>
                    <td>
                      {(() => {
                        const latestReport = latestReportBySourceId.get(profile.source_id);
                        if (!latestReport) {
                          return (
                            <span className={styles.lastRunSummary}>
                              {(profile.source_intake_runs_count ?? 0) > 0
                                ? "No recent run found in available report history."
                                : "Last run: no run found"}
                            </span>
                          );
                        }
                        return (
                          <span className={styles.lastRunSummary}>
                            {buildLastRunSummaryText(latestReport, profile, sourceIntakeStatus)}
                          </span>
                        );
                      })()}
                    </td>
                    <td>
                      <div className={styles.counts}>
                        <span>Provenance: {profile.provenance_count ?? 0}</span>
                        <span>Ingestion: {profile.ingestion_runs_count ?? 0}</span>
                        <span>Source Intake: {profile.source_intake_runs_count ?? 0}</span>
                        <span>iCloud Runs: {profile.icloud_acquisition_runs_count ?? 0}</span>
                      </div>
                    </td>
                    <td>
                      <div className={styles.rowActions}>
                        {(() => {
                          const disabledReason = getRunDisabledReason(profile);
                          const isDisabledForActiveRun = isSourceIntakeActive && disabledReason == null;
                          const effectiveReason = isDisabledForActiveRun
                            ? "Another Source Intake run is already active."
                            : disabledReason;
                          const rowRunError = rowRunErrors[profile.source_id];
                          const isChecking = runPreflightSourceId === profile.source_id;

                          return (
                            <>
                              <button
                                type="button"
                                className={styles.runButton}
                                onClick={() => void handleRunIntakeClick(profile)}
                                disabled={Boolean(effectiveReason) || isChecking || isRunActionLoading}
                              >
                                {isChecking ? "Checking..." : "Run Intake"}
                              </button>
                              {effectiveReason && <span className={styles.disabledReason}>{effectiveReason}</span>}
                              {rowRunError && <span className={styles.rowError}>{rowRunError}</span>}
                            </>
                          );
                        })()}
                        <button type="button" className={styles.updateButton} onClick={() => openDetailsDrawer(profile)}>
                          Details
                        </button>
                        <button type="button" className={styles.updateButton} onClick={() => openEditDrawer(profile)}>
                          Manage
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {isEditorOpen && (
        <div className={styles.drawerBackdrop} role="dialog" aria-modal="true">
          <div className={styles.drawerPanel}>
            <div className={styles.drawerHeader}>
              <div>
                <h3 className={styles.drawerTitle}>
                  {editorMode === "create" ? "Create Source Profile" : "Manage Source Profile Status and Metadata"}
                </h3>
                <p className={styles.drawerSubtitle}>
                  {editorMode === "create"
                    ? "Create a safe metadata profile without starting ingestion."
                    : "Manage lifecycle status and safe metadata only. Source type and source root path stay locked."}
                </p>
              </div>
              <button type="button" className={styles.closeButton} onClick={closeEditor} disabled={isSavingEditor}>
                Close
              </button>
            </div>

            {editorMode === "edit" && (
              <p className={styles.inlineWarning}>
                Source Profile changes are not retroactive. They do not rewrite prior provenance records, prior source paths, prior intake reports, or prior asset history. If a profile is wrong, archive/deprecate/test it and create a corrected profile.
              </p>
            )}

            <div className={styles.formGrid}>
              <label className={styles.formLabel}>
                Source Label
                <input
                  className={styles.formInput}
                  value={editorForm.sourceLabel}
                  onChange={(event) => setEditorForm((prev) => ({ ...prev, sourceLabel: event.target.value }))}
                  placeholder="Chuck PC"
                />
              </label>

              <label className={styles.formLabel}>
                Source Type
                {editorMode === "create" ? (
                  <select
                    className={styles.formInput}
                    value={editorForm.sourceType}
                    onChange={(event) => {
                      const sourceType = event.target.value as SourceProfileType;
                      setEditorForm((prev) => ({
                        ...prev,
                        sourceType,
                        cloudProvider: sourceType === "cloud_export" ? prev.cloudProvider : "icloud",
                        acquisitionMethod: sourceType === "cloud_export" ? prev.acquisitionMethod : "icloudpd",
                      }));
                    }}
                  >
                    {SOURCE_TYPE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input className={styles.formInput} value={editorForm.sourceType} readOnly />
                )}
              </label>

              <label className={styles.formLabel}>
                Profile Status
                <select
                  className={styles.formInput}
                  value={editorForm.profileStatus}
                  onChange={(event) => setEditorForm((prev) => ({
                    ...prev,
                    profileStatus: event.target.value as SourceProfileStatus,
                  }))}
                >
                  {EDITABLE_STATUS_OPTIONS.map((statusValue) => (
                    <option key={statusValue} value={statusValue}>
                      {statusValue}
                    </option>
                  ))}
                </select>
              </label>

              {!isIcloudCloudExport(editorForm) && (
                <label className={styles.formLabel}>
                  Source Root Path
                  {editorMode === "create" ? (
                    <input
                      className={styles.formInput}
                      value={editorForm.sourceRootPath}
                      onChange={(event) => setEditorForm((prev) => ({
                        ...prev,
                        sourceRootPath: event.target.value,
                      }))}
                      placeholder="C:\\Users\\chhen\\Pictures"
                    />
                  ) : (
                    <input className={styles.formInput} value={editorForm.sourceRootPath || "(locked)"} readOnly />
                  )}
                </label>
              )}

              {editorForm.sourceType === "cloud_export" && (
                <>
                  <label className={styles.formLabel}>
                    Cloud Provider
                    <select
                      className={styles.formInput}
                      value={editorForm.cloudProvider}
                      onChange={(event) => setEditorForm((prev) => ({
                        ...prev,
                        cloudProvider: event.target.value as SourceCloudProvider,
                      }))}
                    >
                      {CLOUD_PROVIDER_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className={styles.formLabel}>
                    Acquisition Method
                    <select
                      className={styles.formInput}
                      value={editorForm.acquisitionMethod}
                      onChange={(event) => setEditorForm((prev) => ({
                        ...prev,
                        acquisitionMethod: event.target.value as SourceAcquisitionMethod,
                      }))}
                    >
                      {ACQUISITION_METHOD_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className={styles.formLabel}>
                    Account Username
                    <input
                      className={styles.formInput}
                      value={editorForm.accountUsername}
                      onChange={(event) => setEditorForm((prev) => ({
                        ...prev,
                        accountUsername: event.target.value,
                      }))}
                      placeholder="chhendersoniv@gmail.com"
                    />
                  </label>

                  <label className={styles.formLabel}>
                    Managed Staging Path
                    <input
                      className={styles.formInput}
                      value={editorForm.managedStagingPath || managedStagingPreview}
                      onChange={(event) => setEditorForm((prev) => ({
                        ...prev,
                        managedStagingPath: event.target.value,
                      }))}
                      placeholder={managedStagingPreview}
                      readOnly={isManagedStagingLocked}
                    />
                  </label>
                </>
              )}
            </div>

            {editorMode === "edit" && editingProfileIsReferenced && (
              <p className={styles.inlineWarning}>
                This source profile has historical references. Edits should preserve provenance meaning.
              </p>
            )}

            {!isIcloudCloudExport(editorForm) ? (
              <p className={styles.helperText}>
                Root path is the folder that will be scanned in a future intake run. Root path cannot be edited after creation in this milestone.
              </p>
            ) : (
              <div className={styles.pathPreviewBlock}>
                <p className={styles.helperText}>
                  Photo Organizer stores only the iCloud account username and managed staging path. Apple ID password and 2FA are handled outside Photo Organizer by icloudpd.
                </p>
                <p className={styles.pathPreviewLine}>
                  <strong>Preview path:</strong> {managedStagingPreview}
                </p>
                <p className={styles.pathPreviewLine}>
                  <strong>Resolved path:</strong> {editorMode === "edit" && editingProfile?.managed_staging_path
                    ? editingProfile.managed_staging_path
                    : "Stored by the backend on save."}
                </p>
                {isManagedStagingLocked && (
                  <p className={styles.inlineWarning}>
                    Managed staging path is locked in the normal UI for referenced iCloud profiles.
                  </p>
                )}
              </div>
            )}

            {editorError && <p className={styles.bannerError}>{editorError}</p>}

            <div className={styles.drawerActions}>
              <button
                type="button"
                className={styles.updateButton}
                onClick={() => void saveEditor()}
                disabled={isSavingEditor}
              >
                {isSavingEditor ? "Saving..." : editorMode === "create" ? "Create Profile" : "Save Changes"}
              </button>
              <button type="button" className={styles.button} onClick={closeEditor} disabled={isSavingEditor}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {isRunConfirmOpen && runCandidateProfile && runCandidatePathCheck && (
        <div className={styles.drawerBackdrop} role="dialog" aria-modal="true">
          <div className={styles.drawerPanel}>
            <div className={styles.drawerHeader}>
              <div>
                <h3 className={styles.drawerTitle}>Confirm Source Intake</h3>
                <p className={styles.drawerSubtitle}>
                  Review the source and run options before starting Source Intake.
                </p>
              </div>
              <button type="button" className={styles.closeButton} onClick={closeRunConfirmation} disabled={isRunActionLoading}>
                Close
              </button>
            </div>

            <div className={styles.detailGrid}>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Source Label</span>
                <span>{runCandidateProfile.source_label}</span>
              </div>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Source Type</span>
                <span>{runCandidateProfile.source_type}</span>
              </div>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Source Path</span>
                <span>{runCandidatePathCheck.path ?? "-"}</span>
              </div>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Profile Status</span>
                <span>{runCandidateProfile.profile_status}</span>
              </div>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Path Verification Result</span>
                <span className={styles.okBadge}>{formatPathStatus(runCandidatePathCheck)}</span>
              </div>
            </div>

            <p className={styles.note}>
              This scans the selected source folder and copies eligible files into the Drop Zone for ingestion.
              It does not delete files from the source folder.
              Only one Source Intake run can run at a time.
            </p>

            <section className={styles.runOptionsBlock}>
              <h4 className={styles.runOptionsTitle}>Run Intake Options</h4>
              <p className={styles.runOptionsSummary}>{runOptionSummaryText}</p>
            </section>

            <p className={styles.helperText}>
              These options apply only to this run. They are not saved to the Source Profile.
            </p>

            {runOptionsError && <p className={styles.bannerError}>{runOptionsError}</p>}

            <button
              type="button"
              className={styles.linkButton}
              onClick={() => setIsAdvancedRunOptionsOpen((prev) => !prev)}
              disabled={isRunActionLoading}
            >
              {isAdvancedRunOptionsOpen ? "Hide Advanced Options" : "Show Advanced Options"}
            </button>

            {isAdvancedRunOptionsOpen && (
              <div className={styles.formGrid}>
                <label className={styles.formLabel}>
                  Total Limit
                  <input
                    className={styles.formInput}
                    type="number"
                    min={1}
                    value={runLimitInput}
                    onChange={(event) => setRunLimitInput(event.target.value)}
                    placeholder="leave blank for no limit"
                  />
                  <span className={styles.formHint}>
                    Total Limit controls the maximum number of eligible unknown files selected for this run. Leave blank for no total limit.
                  </span>
                  {runLimitValidationError && <span className={styles.fieldError}>{runLimitValidationError}</span>}
                </label>
                <label className={styles.formLabel}>
                  Batch Size
                  <input
                    className={styles.formInput}
                    type="number"
                    min={1}
                    value={runBatchSizeInput}
                    onChange={(event) => setRunBatchSizeInput(event.target.value)}
                  />
                  <span className={styles.formHint}>
                    Batch Size controls how many files are staged and processed per ingestion batch. Default: 500.
                  </span>
                  {runBatchSizeValidationError && <span className={styles.fieldError}>{runBatchSizeValidationError}</span>}
                </label>
              </div>
            )}

            <div className={styles.drawerActions}>
              <button
                type="button"
                className={styles.runButton}
                onClick={() => void handleConfirmRunIntake()}
                disabled={isRunActionLoading}
              >
                {isRunActionLoading ? "Starting..." : "Run Intake"}
              </button>
              <button type="button" className={styles.button} onClick={closeRunConfirmation} disabled={isRunActionLoading}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {isDetailsOpen && (
        <div className={styles.drawerBackdrop} role="dialog" aria-modal="true">
          <div className={styles.drawerPanel}>
            <div className={styles.drawerHeader}>
              <div>
                <h3 className={styles.drawerTitle}>Source Profile Details</h3>
                <p className={styles.drawerSubtitle}>
                  Read-only operational view showing source identity, effective path, references, and safe verification actions.
                </p>
              </div>
              <button type="button" className={styles.closeButton} onClick={closeDetails}>
                Close
              </button>
            </div>

            {detailBanner && (
              <p className={detailBanner.kind === "success" ? styles.bannerSuccess : styles.bannerError}>
                {detailBanner.message}
              </p>
            )}

            {detailError ? (
              <p className={styles.bannerError}>{detailError}</p>
            ) : isLoadingDetails || !detailProfile ? (
              <p className={styles.empty}>Loading source profile details...</p>
            ) : (
              <>
                <section className={styles.detailSection}>
                  <h4 className={styles.detailHeading}>Source Identity</h4>
                  <p className={styles.helperText}>
                    Source identity is based on label + type + effective path. Source labels are not globally unique.
                  </p>
                  <div className={styles.detailGrid}>
                    <div className={styles.detailCard}>
                      <span className={styles.detailLabel}>Source Label</span>
                      <span>{detailProfile.source_label}</span>
                    </div>
                    <div className={styles.detailCard}>
                      <span className={styles.detailLabel}>Normalized Label</span>
                      <span>{detailProfile.normalized_label}</span>
                    </div>
                    <div className={styles.detailCard}>
                      <span className={styles.detailLabel}>Source Type</span>
                      <span>{detailProfile.source_type}</span>
                    </div>
                    <div className={styles.detailCard}>
                      <span className={styles.detailLabel}>Lifecycle Status</span>
                      <span className={styles.statusBadge}>{detailProfile.profile_status}</span>
                    </div>
                    <div className={styles.detailCard}>
                      <span className={styles.detailLabel}>Effective Path</span>
                      <span>{detailProfile.effective_path ?? "-"}</span>
                      {detailProfile.effective_path_relative && (
                        <span className={styles.detailMeta}>Preview path: {detailProfile.effective_path_relative}</span>
                      )}
                      <span className={styles.detailMeta}>Effective path kind: {detailProfile.effective_path_kind}</span>
                    </div>
                    <div className={styles.detailCard}>
                      <span className={styles.detailLabel}>Reference Status</span>
                      <span className={detailProfile.is_referenced ? styles.referenceBadge : styles.unreferencedBadge}>
                        {detailProfile.is_referenced ? "Referenced" : "Unreferenced"}
                      </span>
                    </div>
                  </div>
                </section>

                <section className={styles.detailSection}>
                  <h4 className={styles.detailHeading}>Paths and Staging</h4>
                  <div className={styles.detailGrid}>
                    <div className={styles.detailCard}>
                      <span className={styles.detailLabel}>Source Root Path</span>
                      <span>{detailProfile.source_root_path ?? "-"}</span>
                      {detailProfile.source_root_path_relative && (
                        <span className={styles.detailMeta}>Preview path: {detailProfile.source_root_path_relative}</span>
                      )}
                    </div>
                    <div className={styles.detailCard}>
                      <span className={styles.detailLabel}>Managed Staging Path</span>
                      <span>{detailProfile.managed_staging_path ?? "-"}</span>
                      {detailProfile.managed_staging_path_relative && (
                        <span className={styles.detailMeta}>Preview path: {detailProfile.managed_staging_path_relative}</span>
                      )}
                    </div>
                    <div className={styles.detailCard}>
                      <span className={styles.detailLabel}>{detailPathLabel}</span>
                      <span className={pathCheckResult?.exists ? styles.okBadge : styles.pendingBadge}>
                        {formatPathStatus(pathCheckResult)}
                      </span>
                      {pathCheckResult && (
                        <span className={styles.detailMeta}>
                          Checked {toDisplayDate(pathCheckResult.checked_at)} via {pathCheckResult.path_kind}
                        </span>
                      )}
                      {stagingCreateResult && (
                        <span className={styles.detailMeta}>
                          Create Staging Folder: {stagingCreateResult.created ? "Created" : "Already existed"}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className={styles.drawerActions}>
                    <button
                      type="button"
                      className={styles.updateButton}
                      onClick={() => void handleVerifyPath()}
                      disabled={isVerifyingPath}
                    >
                      {isVerifyingPath ? "Checking..." : detailVerifyButtonLabel}
                    </button>
                    {isIcloudProfile(detailProfile) && detailProfile.managed_staging_path && (
                      <button
                        type="button"
                        className={styles.button}
                        onClick={() => void handleCreateStagingFolder()}
                        disabled={isCreatingStagingFolder}
                      >
                        {isCreatingStagingFolder ? "Creating..." : "Create Staging Folder"}
                      </button>
                    )}
                  </div>
                </section>

                <section className={styles.detailSection}>
                  <h4 className={styles.detailHeading}>References</h4>
                  <div className={styles.detailGrid}>
                    <div className={styles.detailCard}>
                      <span className={styles.detailLabel}>Provenance references</span>
                      <span>{detailProfile.provenance_count ?? 0}</span>
                    </div>
                    <div className={styles.detailCard}>
                      <span className={styles.detailLabel}>Ingestion runs</span>
                      <span>{detailProfile.ingestion_runs_count ?? 0}</span>
                    </div>
                    <div className={styles.detailCard}>
                      <span className={styles.detailLabel}>Source intake runs</span>
                      <span>{detailProfile.source_intake_runs_count ?? 0}</span>
                    </div>
                    <div className={styles.detailCard}>
                      <span className={styles.detailLabel}>iCloud acquisition runs</span>
                      <span>{detailProfile.icloud_acquisition_runs_count ?? 0}</span>
                    </div>
                  </div>
                </section>

                <section className={styles.detailSection}>
                  <h4 className={styles.detailHeading}>Recent Source Intake Runs</h4>
                  {(() => {
                    const sourceReports = recentReportsBySourceId.get(detailProfile.source_id) ?? [];
                    if (sourceReports.length === 0) {
                      return <p className={styles.helperText}>No recent run found in available report history.</p>;
                    }

                    return (
                      <div className={styles.warningList}>
                        {sourceReports.map((report) => (
                          <div key={report.report_filename} className={styles.detailCard}>
                            <span className={styles.detailMeta}>{toDisplayDate(report.generated_at_utc)}</span>
                            <span>{buildLastRunSummaryText(report, detailProfile, sourceIntakeStatus)}</span>
                            <span className={styles.detailMeta}>Report: {report.report_filename}</span>
                            <div className={styles.rowActions}>
                              <button
                                type="button"
                                className={styles.updateButton}
                                onClick={() => handleToggleReportSummary(report.report_filename)}
                              >
                                {selectedReportFilename === report.report_filename ? "Hide Report Summary" : "View Report Summary"}
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    );
                  })()}
                </section>

                <section className={styles.detailSection}>
                  <h4 className={styles.detailHeading}>Warnings</h4>
                  {detailProfile.warnings.length === 0 ? (
                    <p className={styles.helperText}>No additional operational warnings for this profile.</p>
                  ) : (
                    <div className={styles.warningList}>
                      {detailProfile.warnings.map((warning) => (
                        <p key={warning} className={styles.inlineWarning}>{warning}</p>
                      ))}
                    </div>
                  )}
                  <p className={styles.helperText}>
                    Password and 2FA remain outside Photo Organizer through icloudpd. This drawer does not run intake or acquisition.
                  </p>
                </section>
              </>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

function normalizeIdentityValue(value: string | null | undefined): string {
  return (value ?? "").trim().toLowerCase();
}

function normalizePathForMatch(value: string | null | undefined): string {
  return (value ?? "").trim().replaceAll("\\", "/").toLowerCase();
}

function doesStatusMatchProfile(profile: SourceProfileSummary, status: SourceIntakeStatusSnapshot | null): boolean {
  if (!status) {
    return false;
  }

  const sameType = normalizeIdentityValue(status.source_type) === normalizeIdentityValue(profile.source_type);
  const sameLabel = normalizeIdentityValue(status.source_label) === normalizeIdentityValue(profile.source_label);
  const samePath = normalizePathForMatch(status.source_root_path) === normalizePathForMatch(profile.source_root_path);

  return sameType && sameLabel && samePath;
}

function toStatusLabel(status: string): string {
  return status
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function statusClassName(status: string): string {
  const normalized = status.toLowerCase();
  if (normalized === "running") {
    return styles.runStatusRunning;
  }
  if (normalized === "stop_requested") {
    return styles.runStatusStopRequested;
  }
  if (normalized === "completed") {
    return styles.runStatusCompleted;
  }
  if (normalized === "failed") {
    return styles.runStatusFailed;
  }
  if (normalized === "stopped") {
    return styles.runStatusStopped;
  }
  return styles.runStatusNeutral;
}

function terminalSummaryKey(status: SourceIntakeStatusSnapshot | null): string | null {
  if (!status) {
    return null;
  }
  return [
    status.run_id ?? "none",
    status.status,
    status.started_at ?? "",
    status.finished_at ?? "",
  ].join("|");
}

function buildReportReferencePath(reportFilename: string, rawReportPath: unknown): string {
  if (typeof rawReportPath === "string" && rawReportPath.trim().length > 0) {
    return rawReportPath;
  }
  return `storage/logs/source_intake_reports/${reportFilename}`;
}

function buildLastRunSummaryText(
  report: SourceIntakeReportSummary,
  profile: SourceProfileSummary,
  status: SourceIntakeStatusSnapshot | null,
): string {
  const timestamp = report.generated_at_utc ? new Date(report.generated_at_utc).toLocaleString() : null;
  const statusText = doesStatusMatchProfile(profile, status) ? toStatusLabel(status?.status ?? "reported") : "Reported";
  const processedNew = report.counts?.processed_new_unique ?? 0;
  const failedOrRejected = report.counts?.failed_or_rejected ?? 0;
  const deferred = report.counts?.deferred_unready_count ?? 0;
  const failedTotal = failedOrRejected + deferred;
  const completion = report.source_complete == null
    ? "source state unknown"
    : (report.source_complete ? "source complete" : "source incomplete");

  if (timestamp) {
    return `Last run: ${timestamp} - ${statusText.toLowerCase()} - ${processedNew} new / ${failedTotal} failed - ${completion}`;
  }

  return `Last run: ${statusText.toLowerCase()} - ${processedNew} new / ${failedTotal} failed - ${completion}`;
}
"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  createSourceProfile,
  createSourceProfileStagingFolder,
  getIcloudAcquisitionStatus,
  IcloudAcquisitionStartError,
  getSourceProfileIcloudReadiness,
  getSourceProfileDetail,
  getSourceIntakeReportDetail,
  getSourceIntakeReports,
  getSourceIntakeRunStatus,
  getSourceProfiles,
  runIcloudAcquisitionWithDetails,
  startSourceIntake,
  stopIcloudAcquisition,
  stopSourceIntake,
  updateSourceProfileMetadata,
  verifySourceProfilePath,
} from "@/lib/api";
import type {
  IcloudAcquisitionRunStatus,
  SourceAcquisitionMethod,
  SourceCloudProvider,
  IcloudSourceReadiness,
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

type IcloudReadinessState = "ready" | "warning" | "not_ready" | "unknown";
type IcloudAuthState = "action_required" | "unknown";
type IcloudSourceRegistrationState = "matched" | "mismatch" | "unknown";
type IcloudAcquisitionUiState = "idle" | "loading_details" | "confirm_open" | "starting" | "running" | "stop_requested" | "terminal";
type IcloudAcquisitionMode = "standard" | "list_first_non_repeat";
type IcloudSourceIntakeLimitSuggestion = {
  value: string;
  label: string;
  note: string;
};

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

const ICLOUD_ACQUISITION_POLL_MS = 3000;
const ICLOUD_ACQUISITION_ACTIVE_STATUSES = new Set(["running", "stop_requested"]);
const ICLOUD_ACQUISITION_TERMINAL_STATUSES = new Set(["completed", "completed_with_warnings", "failed", "stopped"]);
const SOURCE_INTAKE_ACTIVE_STATUSES = new Set(["running", "stop_requested"]);
const SOURCE_INTAKE_TERMINAL_STATUSES = new Set(["completed", "failed", "stopped"]);
const ICLOUD_ACQUISITION_HARD_BLOCKING_CODES = new Set([
  "AUTH_REQUIRED",
  "SESSION_EXPIRED",
  "PATH_MISMATCH",
  "SOURCE_ROOT_MISMATCH",
  "SOURCE_REGISTRATION_MISMATCH",
  "APPROVED_ROOT_BLOCKED",
  "ACCOUNT_USERNAME_MISSING",
  "INGESTION_OPERATION_ACTIVE",
]);
const ICLOUD_ACQUISITION_BENIGN_WARNING_CODES = new Set([
  "AUTH_UNKNOWN",
  "NO_RECENT_ACQUISITION",
  "STAGING_FOLDER_MISSING",
]);

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
    .replace(/[^a-z0-9_-]+/g, "_")
    .replace(/[_-]{2,}/g, "_")
    .replace(/^[_\-\s]+|[_\-\s]+$/g, "") || "unnamed_source";
  return `storage/exports/icloud/${slug}`;
}

function toIcloudReadinessLabel(value: IcloudReadinessState): string {
  if (value === "ready") {
    return "Ready";
  }
  if (value === "warning") {
    return "Warning";
  }
  if (value === "not_ready") {
    return "Not Ready";
  }
  return "Unknown";
}

function toAuthStatusLabel(value: IcloudAuthState): string {
  return value === "action_required" ? "Action Required" : "Unknown";
}

function toRegistrationStatusLabel(value: IcloudSourceRegistrationState): string {
  if (value === "matched") {
    return "Matched";
  }
  if (value === "mismatch") {
    return "Mismatch";
  }
  return "Unknown";
}

function toDisplayDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "-";
}

function isIcloudCloudExport(form: EditorFormState): boolean {
  return form.sourceType === "cloud_export" && form.cloudProvider === "icloud";
}

function isIcloudProfile(
  profile: Pick<
    SourceProfileSummary,
    "source_type" | "cloud_provider" | "acquisition_method" | "source_root_path" | "managed_staging_path"
  >
    | Pick<
      SourceProfileDetail,
      "source_type" | "cloud_provider" | "acquisition_method" | "source_root_path" | "managed_staging_path"
    >
    | null,
): boolean {
  if (!profile || profile.source_type !== "cloud_export") {
    return false;
  }

  if (profile.cloud_provider === "icloud") {
    return true;
  }

  if (profile.acquisition_method === "icloudpd") {
    return true;
  }

  const looksLikeLegacyIcloudPath = [profile.managed_staging_path, profile.source_root_path]
    .filter((value): value is string => Boolean(value))
    .some((value) => value.replace(/\\/g, "/").toLowerCase().includes("storage/exports/icloud/"));

  return looksLikeLegacyIcloudPath;
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

function toIcloudAcquisitionModeLabel(mode: IcloudAcquisitionMode): string {
  if (mode === "list_first_non_repeat") {
    return "List first / non-repeat";
  }
  return "Standard";
}

function toIcloudAcquisitionStateLabel(value: IcloudAcquisitionUiState): string {
  if (value === "loading_details") {
    return "Loading acquisition details...";
  }
  if (value === "confirm_open") {
    return "Ready to confirm";
  }
  if (value === "starting") {
    return "Starting acquisition...";
  }
  if (value === "running") {
    return "Acquisition running";
  }
  if (value === "stop_requested") {
    return "Stop requested";
  }
  if (value === "terminal") {
    return "Last run summary";
  }
  return "Idle";
}

function getIcloudAcquisitionTerminalKey(status: IcloudAcquisitionRunStatus | null): string | null {
  if (!status || !ICLOUD_ACQUISITION_TERMINAL_STATUSES.has(status.status)) {
    return null;
  }
  return [
    status.run_id ?? "none",
    status.status,
    status.started_at ?? "",
    status.completed_at ?? "",
  ].join("|");
}

function isIcloudAcquisitionGuardrailBlocked(snapshot: IcloudSourceReadiness | null): boolean {
  if (!snapshot) {
    return true;
  }
  const conflicts = snapshot.operation_conflicts;
  return conflicts.icloud_acquisition_active || conflicts.source_intake_active || conflicts.icloud_cleanup_active;
}

function getIcloudAcquireDisabledReason(snapshot: IcloudSourceReadiness | null): string | null {
  if (!snapshot) {
    return "Readiness snapshot unavailable. Refresh readiness before acquiring.";
  }

  if (snapshot.readiness_status === "not_ready") {
    return "Readiness is not ready. Resolve blocking readiness issues first.";
  }

  if (snapshot.blocking_reasons.length > 0) {
    const first = snapshot.blocking_reasons[0];
    return `${first.code}: ${first.message}`;
  }

  if (isIcloudAcquisitionGuardrailBlocked(snapshot)) {
    return "Another ingestion-related operation is active. Wait for it to finish before starting iCloud acquisition.";
  }

  if (snapshot.auth_status === "action_required") {
    return "Authentication is required. Re-authenticate icloudpd outside Photo Organizer, then refresh readiness.";
  }

  if (snapshot.source_registration_status === "mismatch") {
    return "Source registration is mismatched. Resolve source profile readiness issues before trying again.";
  }

  if (snapshot.path_alignment_status === "mismatch" || snapshot.source_root_alignment_status === "mismatch") {
    return "Path alignment is invalid. Resolve source profile readiness issues before trying again.";
  }

  if (snapshot.approved_root_status === "blocked") {
    return "Managed staging path is outside approved iCloud root.";
  }

  if (!snapshot.account_username_masked) {
    return "Account username is required before acquisition can run.";
  }

  if (snapshot.readiness_status === "warning") {
    for (const warning of snapshot.warnings) {
      if (!ICLOUD_ACQUISITION_BENIGN_WARNING_CODES.has(warning.code)) {
        return `${warning.code}: ${warning.message}`;
      }
      if (warning.code === "STAGING_FOLDER_MISSING" && snapshot.approved_root_status !== "ok") {
        return "Staging folder warning is not safely actionable until approved root is confirmed.";
      }
    }
  }

  return null;
}

function getIcloudSourceIntakeDisabledReason(snapshot: IcloudSourceReadiness | null, profile: SourceProfileDetail | null): string | null {
  if (!snapshot) {
    return "Readiness snapshot unavailable. Refresh readiness before preparing Source Intake.";
  }

  if (!profile || !isIcloudProfile(profile)) {
    return "Source Intake handoff is available for iCloud source profiles only.";
  }

  if (profile.profile_status !== "active") {
    return "Only active profiles can run Source Intake from this tab.";
  }

  if (snapshot.readiness_status === "not_ready") {
    return "Readiness is not ready. Resolve blocking readiness issues first.";
  }

  if (snapshot.blocking_reasons.length > 0) {
    const first = snapshot.blocking_reasons[0];
    return `${first.code}: ${first.message}`;
  }

  if (isIcloudAcquisitionGuardrailBlocked(snapshot)) {
    return "Another ingestion-related operation is active. Wait for it to finish before starting Source Intake.";
  }

  if (snapshot.path_alignment_status === "mismatch" || snapshot.source_root_alignment_status === "mismatch") {
    return "Path alignment is invalid. Resolve source profile readiness issues before trying again.";
  }

  if (snapshot.source_registration_status === "mismatch") {
    return "Source registration is mismatched. Resolve source profile readiness issues before trying again.";
  }

  if (snapshot.approved_root_status === "blocked") {
    return "Managed staging path is outside approved iCloud root.";
  }

  return null;
}

function getIcloudSourceIntakeLimitSuggestion(status: IcloudAcquisitionRunStatus | null): IcloudSourceIntakeLimitSuggestion {
  if (status?.file_inventory_count != null && status.file_inventory_count > 0) {
    return {
      value: String(status.file_inventory_count),
      label: "Suggested from latest acquisition inventory.",
      note: `Using file_inventory_count from the latest acquisition summary (${status.file_inventory_count}).`,
    };
  }

  if (status?.recent_count != null && status.recent_count > 0) {
    return {
      value: String(status.recent_count),
      label: "Suggested from latest acquisition recent count.",
      note: `Using recent_count from the latest acquisition summary (${status.recent_count}).`,
    };
  }

  return {
    value: "",
    label: "No acquisition-derived suggestion available.",
    note: "Staged inventory count is unavailable. Source Intake will scan the staging folder and skip files already known for this source.",
  };
}

function doesIcloudAcquisitionStatusMatchProfile(
  profile: Pick<SourceProfileSummary, "source_label" | "source_type" | "source_root_path">,
  status: IcloudAcquisitionRunStatus | null,
): boolean {
  if (!status) {
    return false;
  }

  const sameType = normalizeIdentityValue(status.source_type) === normalizeIdentityValue(profile.source_type);
  const sameLabel = normalizeIdentityValue(status.source_label) === normalizeIdentityValue(profile.source_label);
  const samePath = normalizePathForMatch(status.source_root_path) === normalizePathForMatch(profile.source_root_path);

  return sameType && sameLabel && samePath;
}

function getMostRecentReportForSource(
  reports: SourceIntakeReportSummary[],
  sourceId: number,
): SourceIntakeReportSummary | null {
  let candidate: SourceIntakeReportSummary | null = null;
  let candidateTs = Number.NEGATIVE_INFINITY;

  for (const report of reports) {
    if (report.ingestion_source_id !== sourceId) {
      continue;
    }
    const ts = report.generated_at_utc ? Date.parse(report.generated_at_utc) : Number.NEGATIVE_INFINITY;
    if (!candidate || ts > candidateTs) {
      candidate = report;
      candidateTs = ts;
    }
  }

  return candidate;
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
  const [icloudReadinessSnapshot, setIcloudReadinessSnapshot] = useState<IcloudSourceReadiness | null>(null);
  const [isLoadingIcloudReadiness, setIsLoadingIcloudReadiness] = useState(false);
  const [icloudReadinessError, setIcloudReadinessError] = useState<string | null>(null);
  const [icloudAcquisitionStatus, setIcloudAcquisitionStatus] = useState<IcloudAcquisitionRunStatus | null>(null);
  const [icloudAcquisitionUiState, setIcloudAcquisitionUiState] = useState<IcloudAcquisitionUiState>("idle");
  const [isIcloudAcquisitionConfirmOpen, setIsIcloudAcquisitionConfirmOpen] = useState(false);
  const [isIcloudAcquisitionActionLoading, setIsIcloudAcquisitionActionLoading] = useState(false);
  const [isLoadingIcloudAcquisitionDetails, setIsLoadingIcloudAcquisitionDetails] = useState(false);
  const [icloudAcquisitionRecentCountInput, setIcloudAcquisitionRecentCountInput] = useState("25");
  const [icloudAcquisitionMode, setIcloudAcquisitionMode] = useState<IcloudAcquisitionMode>("standard");
  const [icloudAcquisitionUsernameForRun, setIcloudAcquisitionUsernameForRun] = useState<string | null>(null);
  const [icloudAcquisitionError, setIcloudAcquisitionError] = useState<string | null>(null);
  const [icloudAcquisitionErrorCode, setIcloudAcquisitionErrorCode] = useState<string | null>(null);
  const [icloudAcquisitionBlockingReasons, setIcloudAcquisitionBlockingReasons] = useState<Array<{ code: string; message: string }>>([]);
  const [icloudAcquisitionConflictSummary, setIcloudAcquisitionConflictSummary] = useState<string | null>(null);
  const [dismissedIcloudAcquisitionTerminalKey, setDismissedIcloudAcquisitionTerminalKey] = useState<string | null>(null);
  const [sourceIntakeStatus, setSourceIntakeStatus] = useState<SourceIntakeStatusSnapshot | null>(null);
  const [sourceIntakeReports, setSourceIntakeReports] = useState<SourceIntakeReportSummary[]>([]);
  const [isRunActionLoading, setIsRunActionLoading] = useState(false);
  const [runPreflightSourceId, setRunPreflightSourceId] = useState<number | null>(null);
  const [rowRunErrors, setRowRunErrors] = useState<Record<number, string>>({});
  const [runErrorDetails, setRunErrorDetails] = useState<string | null>(null);
  const [isRunConfirmOpen, setIsRunConfirmOpen] = useState(false);
  const [runCandidateProfile, setRunCandidateProfile] = useState<SourceProfileSummary | null>(null);
  const [runCandidatePathCheck, setRunCandidatePathCheck] = useState<SourceProfilePathCheckResponse | null>(null);
  const [runLimitInput, setRunLimitInput] = useState("");
  const [runBatchSizeInput, setRunBatchSizeInput] = useState("500");
  const [runOptionsError, setRunOptionsError] = useState<string | null>(null);
  const [dismissedTerminalRunKey, setDismissedTerminalRunKey] = useState<string | null>(null);
  const [selectedReportFilename, setSelectedReportFilename] = useState<string | null>(null);
  const [selectedReportDetail, setSelectedReportDetail] = useState<SourceIntakeReportDetail | null>(null);
  const [isReportDetailLoading, setIsReportDetailLoading] = useState(false);
  const [reportDetailError, setReportDetailError] = useState<string | null>(null);
  const detailLoadRequestSeqRef = useRef(0);

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

  const icloudAcquireDisabledReason = useMemo(() => {
    const detailIsIcloud = detailProfile ? isIcloudProfile(detailProfile) : false;
    if (!detailProfile || !detailIsIcloud) {
      return "Acquire from iCloud is available for iCloud source profiles only.";
    }
    return getIcloudAcquireDisabledReason(icloudReadinessSnapshot);
  }, [detailProfile, icloudReadinessSnapshot]);

  const icloudSourceIntakeDisabledReason = useMemo(() => {
    return getIcloudSourceIntakeDisabledReason(icloudReadinessSnapshot, detailProfile);
  }, [detailProfile, icloudReadinessSnapshot]);

  const icloudSourceIntakeLimitSuggestion = useMemo(() => {
    return getIcloudSourceIntakeLimitSuggestion(icloudAcquisitionStatus);
  }, [icloudAcquisitionStatus]);

  const normalizedIcloudAcquisitionRecentCountInput = useMemo(
    () => icloudAcquisitionRecentCountInput.trim(),
    [icloudAcquisitionRecentCountInput],
  );

  const icloudAcquisitionRecentCountValidationError = useMemo(() => {
    const parsed = Number(normalizedIcloudAcquisitionRecentCountInput);
    if (!normalizedIcloudAcquisitionRecentCountInput || !Number.isInteger(parsed) || parsed < 1 || parsed > 500) {
      return "Recent Count must be an integer between 1 and 500.";
    }
    return null;
  }, [normalizedIcloudAcquisitionRecentCountInput]);

  const isIcloudAcquisitionActive = useMemo(
    () => (icloudAcquisitionStatus ? ICLOUD_ACQUISITION_ACTIVE_STATUSES.has(icloudAcquisitionStatus.status) : false),
    [icloudAcquisitionStatus],
  );

  const currentIcloudAcquisitionTerminalKey = useMemo(
    () => getIcloudAcquisitionTerminalKey(icloudAcquisitionStatus),
    [icloudAcquisitionStatus],
  );

  const showIcloudAcquisitionTerminalSummary = useMemo(
    () => Boolean(currentIcloudAcquisitionTerminalKey && currentIcloudAcquisitionTerminalKey !== dismissedIcloudAcquisitionTerminalKey),
    [currentIcloudAcquisitionTerminalKey, dismissedIcloudAcquisitionTerminalKey],
  );

  const loadIcloudAcquisitionStatus = useCallback(async () => {
    try {
      const response = await getIcloudAcquisitionStatus();
      setIcloudAcquisitionStatus(response.current);

      if (response.current.status === "running") {
        setIcloudAcquisitionUiState("running");
      } else if (response.current.status === "stop_requested") {
        setIcloudAcquisitionUiState("stop_requested");
      } else if (ICLOUD_ACQUISITION_TERMINAL_STATUSES.has(response.current.status)) {
        setIcloudAcquisitionUiState("terminal");
      }
    } catch (error) {
      setIcloudAcquisitionError(error instanceof Error ? error.message : "Failed to load iCloud acquisition status.");
    }
  }, []);

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
    ? SOURCE_INTAKE_ACTIVE_STATUSES.has(sourceIntakeStatus.status)
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
    if (!sourceIntakeStatus || !SOURCE_INTAKE_TERMINAL_STATUSES.has(sourceIntakeStatus.status)) {
      return;
    }
    void loadProfiles({ refreshOnly: true, resetBanner: false });
    void loadSourceIntakeReports();
  }, [sourceIntakeStatus?.run_id, sourceIntakeStatus?.status, loadProfiles, loadSourceIntakeReports]);

  useEffect(() => {
    if (!icloudAcquisitionStatus) {
      return;
    }
    if (icloudAcquisitionStatus.status === "running") {
      setIcloudAcquisitionUiState("running");
      setDismissedIcloudAcquisitionTerminalKey(null);
      return;
    }
    if (icloudAcquisitionStatus.status === "stop_requested") {
      setIcloudAcquisitionUiState("stop_requested");
      setDismissedIcloudAcquisitionTerminalKey(null);
      return;
    }
    if (ICLOUD_ACQUISITION_TERMINAL_STATUSES.has(icloudAcquisitionStatus.status)) {
      setIcloudAcquisitionUiState("terminal");
      return;
    }
    setIcloudAcquisitionUiState("idle");
  }, [icloudAcquisitionStatus]);

  useEffect(() => {
    if (!isDetailsOpen || !detailProfile || !isIcloudProfile(detailProfile) || !isIcloudAcquisitionActive) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadIcloudAcquisitionStatus();
    }, ICLOUD_ACQUISITION_POLL_MS);
    return () => window.clearInterval(timer);
  }, [detailProfile, isDetailsOpen, isIcloudAcquisitionActive, loadIcloudAcquisitionStatus]);

  useEffect(() => {
    if (!detailSourceId || !isDetailsOpen || !detailProfile || !isIcloudProfile(detailProfile) || !icloudAcquisitionStatus) {
      return;
    }
    if (!ICLOUD_ACQUISITION_TERMINAL_STATUSES.has(icloudAcquisitionStatus.status)) {
      return;
    }
    void (async () => {
      setIsLoadingIcloudReadiness(true);
      setIcloudReadinessError(null);
      try {
        const snapshot = await getSourceProfileIcloudReadiness(detailSourceId);
        setIcloudReadinessSnapshot(snapshot);
      } catch (error) {
        setIcloudReadinessSnapshot(null);
        setIcloudReadinessError(error instanceof Error ? error.message : "Readiness unavailable.");
      } finally {
        setIsLoadingIcloudReadiness(false);
      }
    })();
    void loadIcloudAcquisitionStatus();
  }, [
    detailProfile,
    detailSourceId,
    icloudAcquisitionStatus?.run_id,
    icloudAcquisitionStatus?.status,
    isDetailsOpen,
    loadIcloudAcquisitionStatus,
  ]);

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

  const loadDetail = useCallback(async (sourceId: number) => {
    const requestSeq = ++detailLoadRequestSeqRef.current;
    setIsLoadingDetails(true);
    setDetailError(null);
    try {
      const detail = await getSourceProfileDetail(sourceId);
      if (requestSeq !== detailLoadRequestSeqRef.current) {
        return;
      }
      setDetailProfile(detail);
    } catch (error) {
      if (requestSeq !== detailLoadRequestSeqRef.current) {
        return;
      }
      setDetailProfile(null);
      setDetailError(error instanceof Error ? error.message : "Failed to load source profile details.");
    } finally {
      if (requestSeq === detailLoadRequestSeqRef.current) {
        setIsLoadingDetails(false);
      }
    }
  }, []);

  const loadIcloudReadiness = useCallback(async (sourceId: number) => {
    setIsLoadingIcloudReadiness(true);
    setIcloudReadinessError(null);
    try {
      const snapshot = await getSourceProfileIcloudReadiness(sourceId);
      setIcloudReadinessSnapshot(snapshot);
    } catch (error) {
      setIcloudReadinessSnapshot(null);
      setIcloudReadinessError(error instanceof Error ? error.message : "Readiness unavailable.");
    } finally {
      setIsLoadingIcloudReadiness(false);
    }
  }, []);

  useEffect(() => {
    if (!detailSourceId || !isDetailsOpen || !detailProfile || !isIcloudProfile(detailProfile) || !sourceIntakeStatus) {
      return;
    }
    if (!SOURCE_INTAKE_TERMINAL_STATUSES.has(sourceIntakeStatus.status)) {
      return;
    }
    if (!doesStatusMatchProfile(detailProfile, sourceIntakeStatus)) {
      return;
    }
    void loadIcloudReadiness(detailSourceId);
    void loadIcloudAcquisitionStatus();
  }, [
    detailProfile,
    detailSourceId,
    isDetailsOpen,
    loadIcloudAcquisitionStatus,
    loadIcloudReadiness,
    sourceIntakeStatus?.run_id,
    sourceIntakeStatus?.status,
  ]);

  const closeIcloudAcquisitionConfirmation = useCallback(() => {
    setIsIcloudAcquisitionConfirmOpen(false);
    setIcloudAcquisitionUiState((prev) => (prev === "loading_details" ? "idle" : prev));
    setIcloudAcquisitionErrorCode(null);
    setIcloudAcquisitionBlockingReasons([]);
    setIcloudAcquisitionConflictSummary(null);
  }, []);

  const handleAcquireFromIcloudClick = useCallback(async () => {
    if (!detailSourceId || !detailProfile || !isIcloudProfile(detailProfile)) {
      return;
    }

    if (icloudAcquireDisabledReason) {
      setIcloudAcquisitionError(icloudAcquireDisabledReason);
      return;
    }

    setIsLoadingIcloudAcquisitionDetails(true);
    setIcloudAcquisitionUiState("loading_details");
    setIcloudAcquisitionError(null);
    setIcloudAcquisitionErrorCode(null);
    setIcloudAcquisitionBlockingReasons([]);
    setIcloudAcquisitionConflictSummary(null);

    try {
      const detailWithUsername = await getSourceProfileDetail(detailSourceId, { includeUsername: true });
      const username = (detailWithUsername.account_username || "").trim();
      if (!username) {
        setIcloudAcquisitionError("Account username is required before acquisition can run.");
        setIcloudAcquisitionUiState("idle");
        return;
      }

      setIcloudAcquisitionUsernameForRun(username);
      setIcloudAcquisitionRecentCountInput("25");
      setIcloudAcquisitionMode("standard");
      setIsIcloudAcquisitionConfirmOpen(true);
      setIcloudAcquisitionUiState("confirm_open");
    } catch (error) {
      setIcloudAcquisitionError(error instanceof Error ? error.message : "Failed to load acquisition details.");
      setIcloudAcquisitionUiState("idle");
    } finally {
      setIsLoadingIcloudAcquisitionDetails(false);
    }
  }, [detailProfile, detailSourceId, icloudAcquireDisabledReason]);

  const handleConfirmAcquireFromIcloud = useCallback(async () => {
    if (!detailProfile || !isIcloudProfile(detailProfile) || !icloudAcquisitionUsernameForRun) {
      return;
    }

    if (icloudAcquisitionRecentCountValidationError) {
      setIcloudAcquisitionError(icloudAcquisitionRecentCountValidationError);
      return;
    }

    setIsIcloudAcquisitionActionLoading(true);
    setIcloudAcquisitionUiState("starting");
    setIcloudAcquisitionError(null);
    setIcloudAcquisitionErrorCode(null);
    setIcloudAcquisitionBlockingReasons([]);
    setIcloudAcquisitionConflictSummary(null);

    try {
      const response = await runIcloudAcquisitionWithDetails({
        source_label: detailProfile.source_label,
        username: icloudAcquisitionUsernameForRun,
        recent_count: Number(normalizedIcloudAcquisitionRecentCountInput),
        source_type: "cloud_export",
        acquisition_mode: icloudAcquisitionMode,
      });

      setIcloudAcquisitionStatus(response.current);
      setDismissedIcloudAcquisitionTerminalKey(null);
      setIcloudAcquisitionUiState(
        response.current.status === "stop_requested"
          ? "stop_requested"
          : ICLOUD_ACQUISITION_ACTIVE_STATUSES.has(response.current.status)
            ? "running"
            : ICLOUD_ACQUISITION_TERMINAL_STATUSES.has(response.current.status)
              ? "terminal"
              : "idle",
      );
      setIsIcloudAcquisitionConfirmOpen(false);
      setBanner({ kind: "success", message: "iCloud acquisition started." });
    } catch (error) {
      if (error instanceof IcloudAcquisitionStartError) {
        setIcloudAcquisitionError(error.message);
        setIcloudAcquisitionErrorCode(error.payload?.error_code ?? null);
        setIcloudAcquisitionBlockingReasons(error.payload?.blocking_reasons ?? []);
        if (error.payload?.operation_conflicts) {
          const conflicts = error.payload.operation_conflicts;
          setIcloudAcquisitionConflictSummary([
            `Acquisition active: ${conflicts.icloud_acquisition_active ? "Yes" : "No"}`,
            `Source Intake active: ${conflicts.source_intake_active ? "Yes" : "No"}`,
            `iCloud cleanup active: ${conflicts.icloud_cleanup_active ? "Yes" : "No"}`,
          ].join(" | "));
        }
      } else {
        setIcloudAcquisitionError(error instanceof Error ? error.message : "Failed to start iCloud acquisition.");
      }
      setIcloudAcquisitionUiState("idle");
    } finally {
      setIsIcloudAcquisitionActionLoading(false);
    }
  }, [
    detailProfile,
    icloudAcquisitionMode,
    icloudAcquisitionRecentCountValidationError,
    icloudAcquisitionUsernameForRun,
    normalizedIcloudAcquisitionRecentCountInput,
  ]);

  const handleIcloudAcquisitionRequestStop = useCallback(async () => {
    setIsIcloudAcquisitionActionLoading(true);
    setIcloudAcquisitionError(null);

    try {
      const response = await stopIcloudAcquisition();
      setIcloudAcquisitionStatus(response.current);
      setIcloudAcquisitionUiState(response.current.status === "stop_requested" ? "stop_requested" : "running");
      setBanner({ kind: "success", message: "Stop requested for iCloud acquisition." });
    } catch (error) {
      setIcloudAcquisitionError(error instanceof Error ? error.message : "Failed to request stop.");
    } finally {
      setIsIcloudAcquisitionActionLoading(false);
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
    setIcloudReadinessSnapshot(null);
    setIcloudReadinessError(null);
    setIcloudAcquisitionStatus(null);
    setIcloudAcquisitionError(null);
    setIcloudAcquisitionErrorCode(null);
    setIcloudAcquisitionBlockingReasons([]);
    setIcloudAcquisitionConflictSummary(null);
    setIsIcloudAcquisitionConfirmOpen(false);
    setIcloudAcquisitionUiState("idle");
    void loadDetail(profile.source_id);
    if (isIcloudProfile(profile)) {
      void loadIcloudReadiness(profile.source_id);
      void loadIcloudAcquisitionStatus();
    }
  }, [loadDetail, loadIcloudAcquisitionStatus, loadIcloudReadiness]);

  const closeEditor = useCallback(() => {
    setIsEditorOpen(false);
    setEditorError(null);
  }, []);

  const closeDetails = useCallback(() => {
    detailLoadRequestSeqRef.current += 1;
    setIsDetailsOpen(false);
    setDetailSourceId(null);
    setDetailProfile(null);
    setDetailError(null);
    setDetailBanner(null);
    setPathCheckResult(null);
    setStagingCreateResult(null);
    setIcloudReadinessSnapshot(null);
    setIcloudReadinessError(null);
    setIcloudAcquisitionStatus(null);
    setIcloudAcquisitionUiState("idle");
    setIcloudAcquisitionError(null);
    setIcloudAcquisitionErrorCode(null);
    setIcloudAcquisitionBlockingReasons([]);
    setIcloudAcquisitionConflictSummary(null);
    setIsIcloudAcquisitionConfirmOpen(false);
    setIsLoadingIcloudAcquisitionDetails(false);
    setIcloudAcquisitionUsernameForRun(null);
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
      if (detailProfile && isIcloudProfile(detailProfile)) {
        await loadIcloudReadiness(detailSourceId);
      }
    } catch (error) {
      setDetailBanner({
        kind: "error",
        message: error instanceof Error ? error.message : "Failed to verify the configured path.",
      });
    } finally {
      setIsVerifyingPath(false);
    }
  }, [detailProfile, detailSourceId, loadIcloudReadiness]);

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
      if (detailProfile && isIcloudProfile(detailProfile)) {
        await loadIcloudReadiness(detailSourceId);
      }
    } catch (error) {
      setDetailBanner({
        kind: "error",
        message: error instanceof Error ? error.message : "Failed to create the managed staging folder.",
      });
    } finally {
      setIsCreatingStagingFolder(false);
    }
  }, [detailProfile, detailSourceId, loadDetail, loadIcloudReadiness, loadProfiles]);

  const saveEditor = useCallback(async () => {
    setEditorError(null);
    const trimmedLabel = editorForm.sourceLabel.trim();

    if (editorMode === "create") {
      if (!trimmedLabel) {
        setEditorError("Source label is required.");
        return;
      }

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
        profile_status: editorForm.profileStatus,
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
    loadProfiles,
    managedStagingPreview,
    statusFilter,
  ]);

  const detailPathLabel = detailProfile && isIcloudProfile(detailProfile) ? "Staging status" : "Path status";
  const detailVerifyButtonLabel = detailProfile && isIcloudProfile(detailProfile) ? "Verify Staging" : "Verify Path";

  const isDetailIcloudProfile = detailProfile ? isIcloudProfile(detailProfile) : false;
  const isGuidedIcloudRunCandidate = runCandidateProfile ? isIcloudProfile(runCandidateProfile) : false;

  const expectedAcquisitionPath = useMemo(() => {
    if (!detailProfile || !isDetailIcloudProfile) {
      return null;
    }
    return icloudReadinessSnapshot?.expected_acquisition_path ?? detailProfile.expected_acquisition_path;
  }, [detailProfile, icloudReadinessSnapshot?.expected_acquisition_path, isDetailIcloudProfile]);

  const pathAlignmentStatus = useMemo(() => {
    if (!detailProfile || !isDetailIcloudProfile) {
      return "unknown";
    }
    return icloudReadinessSnapshot?.path_alignment_status === "matched"
      ? "ok"
      : icloudReadinessSnapshot?.path_alignment_status === "mismatch"
        ? "mismatch"
        : "unknown";
  }, [detailProfile, icloudReadinessSnapshot?.path_alignment_status, isDetailIcloudProfile]);

  const approvedRootStatus = useMemo(() => {
    if (!detailProfile || !isDetailIcloudProfile) {
      return "unknown";
    }
    return icloudReadinessSnapshot?.approved_root_status ?? "unknown";
  }, [detailProfile, icloudReadinessSnapshot?.approved_root_status, isDetailIcloudProfile]);

  const stagingFolderStatus = useMemo(() => {
    if (!detailProfile || !isDetailIcloudProfile) {
      return "not_checked";
    }
    if (icloudReadinessSnapshot?.staging_folder_status === "exists") {
      return "exists";
    }
    if (icloudReadinessSnapshot?.staging_folder_status === "missing") {
      return "missing";
    }
    if (icloudReadinessSnapshot?.staging_folder_status === "unsafe") {
      return "unsafe";
    }
    if (!pathCheckResult || pathCheckResult.path_kind !== "managed_staging_path") {
      return "not_checked";
    }
    return pathCheckResult.exists && pathCheckResult.is_directory ? "exists" : "missing";
  }, [detailProfile, icloudReadinessSnapshot?.staging_folder_status, isDetailIcloudProfile, pathCheckResult]);

  const sourceRegistrationStatus = useMemo<IcloudSourceRegistrationState>(() => {
    if (!detailProfile || !isDetailIcloudProfile) {
      return "unknown";
    }
    if (icloudReadinessSnapshot?.source_registration_status === "matched") {
      return "matched";
    }
    if (icloudReadinessSnapshot?.source_registration_status === "mismatch") {
      return "mismatch";
    }
    return "unknown";
  }, [detailProfile, icloudReadinessSnapshot?.source_registration_status, isDetailIcloudProfile]);

  const authStatus = useMemo<IcloudAuthState>(() => {
    if (icloudReadinessSnapshot?.auth_status === "action_required") {
      return "action_required";
    }
    return "unknown";
  }, [icloudReadinessSnapshot?.auth_status]);

  const icloudReadiness = useMemo<IcloudReadinessState>(() => {
    if (!detailProfile || !isDetailIcloudProfile) {
      return "unknown";
    }
    return icloudReadinessSnapshot?.readiness_status ?? "unknown";
  }, [detailProfile, icloudReadinessSnapshot?.readiness_status, isDetailIcloudProfile]);

  const readinessBadgeClassName = useMemo(() => {
    if (icloudReadiness === "ready") {
      return styles.readinessBadgeReady;
    }
    if (icloudReadiness === "warning") {
      return styles.readinessBadgeWarning;
    }
    if (icloudReadiness === "not_ready") {
      return styles.readinessBadgeNotReady;
    }
    return styles.readinessBadgeUnknown;
  }, [icloudReadiness]);

  const recommendedIcloudAction = useMemo(() => {
    if (!detailProfile || !isDetailIcloudProfile) {
      return null;
    }
    return icloudReadinessSnapshot?.recommended_action
      ?? "Run diagnostics or use Admin iCloud tools to confirm readiness.";
  }, [
    detailProfile,
    icloudReadinessSnapshot?.recommended_action,
    isDetailIcloudProfile,
  ]);

  const readinessBlockingReasons = useMemo(() => icloudReadinessSnapshot?.blocking_reasons ?? [], [icloudReadinessSnapshot?.blocking_reasons]);
  const readinessWarnings = useMemo(() => icloudReadinessSnapshot?.warnings ?? [], [icloudReadinessSnapshot?.warnings]);

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

  const detailSourceIntakeStatus = useMemo(() => {
    if (!detailProfile) {
      return null;
    }
    return doesStatusMatchProfile(detailProfile, sourceIntakeStatus) ? sourceIntakeStatus : null;
  }, [detailProfile, sourceIntakeStatus]);

  const latestSourceIntakeReportForDetail = useMemo(() => {
    if (!detailSourceId) {
      return null;
    }
    return getMostRecentReportForSource(sourceIntakeReports, detailSourceId);
  }, [detailSourceId, sourceIntakeReports]);

  const latestAcquisitionForDetail = useMemo(() => {
    if (!detailProfile) {
      return null;
    }
    if (doesIcloudAcquisitionStatusMatchProfile(detailProfile, icloudAcquisitionStatus)) {
      return {
        status: icloudAcquisitionStatus?.status ?? null,
        started_at: icloudAcquisitionStatus?.started_at ?? null,
        finished_at: icloudAcquisitionStatus?.completed_at ?? null,
        recent_count: icloudAcquisitionStatus?.recent_count ?? null,
        file_inventory_count: icloudAcquisitionStatus?.file_inventory_count ?? null,
        downloaded_count: icloudAcquisitionStatus?.downloaded_count ?? null,
        skipped_count: icloudAcquisitionStatus?.skipped_existing_count ?? null,
        failed_count: icloudAcquisitionStatus?.failed_count ?? null,
        acquisition_mode: icloudAcquisitionStatus?.acquisition_mode ?? null,
        report_path: icloudAcquisitionStatus?.report_path ?? null,
      };
    }

    const readinessAcq = icloudReadinessSnapshot?.last_acquisition;
    if (!readinessAcq) {
      return null;
    }
    return {
      status: readinessAcq.status,
      started_at: readinessAcq.started_at,
      finished_at: readinessAcq.finished_at,
      recent_count: null,
      file_inventory_count: null,
      downloaded_count: readinessAcq.downloaded_count,
      skipped_count: readinessAcq.skipped_count,
      failed_count: readinessAcq.failed_count,
      acquisition_mode: null,
      report_path: readinessAcq.report_path,
    };
  }, [detailProfile, icloudAcquisitionStatus, icloudReadinessSnapshot?.last_acquisition]);

  const overallIcloudWorkflowSummary = useMemo(() => {
    if (!detailProfile || !isIcloudProfile(detailProfile)) {
      return null;
    }

    const readiness = icloudReadinessSnapshot;
    const intakeStatus = detailSourceIntakeStatus;
    const intakeStatusActive = Boolean(intakeStatus && SOURCE_INTAKE_ACTIVE_STATUSES.has(intakeStatus.status));
    const intakeStatusTerminal = Boolean(intakeStatus && SOURCE_INTAKE_TERMINAL_STATUSES.has(intakeStatus.status));
    const intakeReport = latestSourceIntakeReportForDetail;
    const intakeReportHasCounts = Boolean(intakeReport?.counts);
    const acquisition = latestAcquisitionForDetail;
    const acquisitionStatus = acquisition?.status ?? null;
    const acquisitionActive = Boolean(acquisitionStatus && ICLOUD_ACQUISITION_ACTIVE_STATUSES.has(acquisitionStatus));
    const hasReadinessBlockers = Boolean(
      readiness
      && (
        readiness.readiness_status === "not_ready"
        || readiness.blocking_reasons.length > 0
        || readiness.path_alignment_status === "mismatch"
        || readiness.source_root_alignment_status === "mismatch"
        || readiness.source_registration_status === "mismatch"
        || readiness.approved_root_status === "blocked"
        || readiness.auth_status === "action_required"
      )
    );

    const sameSourceConflict = Boolean(
      (readiness?.operation_conflicts.source_intake_active_for_this_source ?? false)
      || (readiness?.operation_conflicts.icloud_cleanup_active_for_this_source ?? false)
    );

    const acquisitionActiveDifferentSource = Boolean(
      readiness?.operation_conflicts.icloud_acquisition_active
      && !acquisitionActive,
    );

    const hasOtherSourceConflict = Boolean(
      (readiness?.operation_conflicts.source_intake_active && !sameSourceConflict)
      || (readiness?.operation_conflicts.icloud_cleanup_active && !sameSourceConflict)
      || acquisitionActiveDifferentSource
    );

    const noActiveConflict = readiness
      ? !(readiness.operation_conflicts.icloud_acquisition_active || readiness.operation_conflicts.source_intake_active || readiness.operation_conflicts.icloud_cleanup_active)
      : false;

    const readyForSourceIntake = Boolean(
      detailProfile.profile_status === "active"
      && readiness
      && !hasReadinessBlockers
      && noActiveConflict
      && !acquisitionActive
    );

    const hasNoRecentAcquisition = !acquisition;
    const hasRecentIntakeEvidence = Boolean(intakeStatus || intakeReport);

    // Precedence table from milestone 12.62.8 answers:
    // 1) same-profile active operation
    // 2) hard blockers / attention needed
    // 3) active operation conflict for another source
    // 4) ready states (source intake / acquire)
    // 5) review results
    // 6) no recent activity
    if (acquisitionActive) {
      return {
        status: "Acquisition running",
        message: "iCloud acquisition is currently running for this profile.",
      };
    }
    if (intakeStatusActive) {
      return {
        status: "Source Intake running",
        message: "Source Intake is currently running for this profile.",
      };
    }
    if (hasReadinessBlockers) {
      return {
        status: "Attention needed",
        message: "Readiness blockers must be resolved before running acquisition or intake.",
      };
    }
    if (hasOtherSourceConflict) {
      return {
        status: "Attention needed",
        message: "Another ingestion-related operation is active. Wait for it to finish before starting Source Intake.",
      };
    }
    if (readyForSourceIntake) {
      return {
        status: "Ready for Source Intake",
        message: hasNoRecentAcquisition
          ? "No recent iCloud acquisition found. You may acquire from iCloud or run Source Intake if staged files already exist."
          : "Acquisition completed. Run Source Intake to process staged files.",
      };
    }
    if ((intakeStatusTerminal && intakeStatus?.status === "completed") || (intakeReportHasCounts && intakeReport?.source_complete)) {
      return {
        status: "Ready for cleanup dry run later",
        message: "Source Intake completed. Review the summary before cleanup. Cleanup will be added in a later milestone.",
      };
    }
    if (intakeStatusTerminal || intakeReportHasCounts) {
      return {
        status: "Review intake results",
        message: hasNoRecentAcquisition && hasRecentIntakeEvidence
          ? "No recent acquisition found. Recent Source Intake results are available for this profile. Review intake results or acquire again if you need newer iCloud files."
          : "Source Intake results are available for review.",
      };
    }

    return {
      status: "Ready to acquire",
      message: "No recent iCloud acquisition found for this profile.",
    };
  }, [detailProfile, detailSourceIntakeStatus, icloudReadinessSnapshot, latestAcquisitionForDetail, latestSourceIntakeReportForDetail]);

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

  const handleRefreshIcloudWorkflowSummary = useCallback(async () => {
    if (!detailSourceId || !detailProfile || !isIcloudProfile(detailProfile)) {
      return;
    }
    setDetailBanner(null);
    try {
      await Promise.all([
        loadIcloudReadiness(detailSourceId),
        loadIcloudAcquisitionStatus(),
        loadSourceIntakeStatus(),
        loadSourceIntakeReports(),
      ]);
    } catch (error) {
      setDetailBanner({
        kind: "error",
        message: error instanceof Error ? error.message : "Failed to refresh workflow summary.",
      });
    }
  }, [detailProfile, detailSourceId, loadIcloudAcquisitionStatus, loadIcloudReadiness, loadSourceIntakeReports, loadSourceIntakeStatus]);

  const closeRunConfirmation = useCallback(() => {
    setIsRunConfirmOpen(false);
    setRunCandidateProfile(null);
    setRunCandidatePathCheck(null);
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

  const handlePrepareIcloudSourceIntake = useCallback(async () => {
    if (!detailProfile || !isDetailIcloudProfile) {
      return;
    }

    if (icloudSourceIntakeDisabledReason) {
      setDetailBanner({ kind: "error", message: icloudSourceIntakeDisabledReason });
      return;
    }

    setRunPreflightSourceId(detailProfile.source_id);
    setDetailBanner(null);

    try {
      const pathCheck = await verifySourceProfilePath(detailProfile.source_id);
      if (!pathCheck.exists || !pathCheck.is_directory) {
        const message = "Cannot run Source Intake. Managed staging path does not exist or is not a directory.";
        setDetailBanner({ kind: "error", message });
        return;
      }

      setRunCandidateProfile(detailProfile);
      setRunCandidatePathCheck(pathCheck);
      setRunLimitInput(icloudSourceIntakeLimitSuggestion.value);
      setRunBatchSizeInput("500");
      setRunOptionsError(null);
      setIsRunConfirmOpen(true);
    } catch (error) {
      const mapped = mapRunStartError(error);
      setDetailBanner({ kind: "error", message: mapped.message });
      setRunErrorDetails(mapped.raw);
    } finally {
      setRunPreflightSourceId(null);
    }
  }, [detailProfile, icloudSourceIntakeDisabledReason, icloudSourceIntakeLimitSuggestion.value, isDetailIcloudProfile]);

  const handleConfirmRunIntake = useCallback(async () => {
    if (!runCandidateProfile) {
      return;
    }

    if (runLimitValidationError || runBatchSizeValidationError) {
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
                  {editorMode === "create" ? "Create Source Profile" : "Manage Source Profile Status"}
                </h3>
                <p className={styles.drawerSubtitle}>
                  {editorMode === "create"
                    ? "Create a safe metadata profile without starting ingestion."
                    : "Manage lifecycle status while preserving historical source identity."}
                </p>
              </div>
              <button type="button" className={styles.closeButton} onClick={closeEditor} disabled={isSavingEditor}>
                Close
              </button>
            </div>

            {editorMode === "edit" && (
              <>
                <p className={styles.helperText}>
                  Source identity is historical after creation. If this profile is wrong, archive/deprecate/test it and create a corrected Source Profile.
                </p>
                <p className={styles.inlineWarning}>
                  Source Profile changes are not retroactive. They do not rewrite prior provenance records, prior source paths, prior intake reports, or prior asset history.
                </p>
              </>
            )}

            <div className={styles.formGrid}>
              <label className={styles.formLabel}>
                Source Label
                {editorMode === "create" ? (
                  <input
                    className={styles.formInput}
                    value={editorForm.sourceLabel}
                    onChange={(event) => setEditorForm((prev) => ({ ...prev, sourceLabel: event.target.value }))}
                    placeholder="Chuck PC"
                  />
                ) : (
                  <input className={`${styles.formInput} ${styles.readOnlyInput}`} value={editorForm.sourceLabel || "-"} readOnly />
                )}
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
                  <input className={`${styles.formInput} ${styles.readOnlyInput}`} value={editorForm.sourceType} readOnly />
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
                    <input className={`${styles.formInput} ${styles.readOnlyInput}`} value={editorForm.sourceRootPath || "-"} readOnly />
                  )}
                </label>
              )}

              {editorForm.sourceType === "cloud_export" && (
                <>
                  <label className={styles.formLabel}>
                    Cloud Provider
                    {editorMode === "create" ? (
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
                    ) : (
                      <input className={`${styles.formInput} ${styles.readOnlyInput}`} value={editorForm.cloudProvider || "-"} readOnly />
                    )}
                  </label>

                  <label className={styles.formLabel}>
                    Acquisition Method
                    {editorMode === "create" ? (
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
                    ) : (
                      <input className={`${styles.formInput} ${styles.readOnlyInput}`} value={editorForm.acquisitionMethod || "-"} readOnly />
                    )}
                  </label>

                  <label className={styles.formLabel}>
                    Account Username
                    {editorMode === "create" ? (
                      <input
                        className={styles.formInput}
                        value={editorForm.accountUsername}
                        onChange={(event) => setEditorForm((prev) => ({
                          ...prev,
                          accountUsername: event.target.value,
                        }))}
                        placeholder="chhendersoniv@gmail.com"
                      />
                    ) : (
                      <input className={`${styles.formInput} ${styles.readOnlyInput}`} value={editorForm.accountUsername || "-"} readOnly />
                    )}
                  </label>

                  <label className={styles.formLabel}>
                    Managed Staging Path
                    {editorMode === "create" ? (
                      <input
                        className={styles.formInput}
                        value={editorForm.managedStagingPath || managedStagingPreview}
                        onChange={(event) => setEditorForm((prev) => ({
                          ...prev,
                          managedStagingPath: event.target.value,
                        }))}
                        placeholder={managedStagingPreview}
                      />
                    ) : (
                      <input className={`${styles.formInput} ${styles.readOnlyInput}`} value={editorForm.managedStagingPath || "-"} readOnly />
                    )}
                  </label>
                </>
              )}
            </div>

            {editorMode === "edit" && editingProfileIsReferenced && (
              <p className={styles.inlineWarning}>
                This source profile has historical references. Edits should preserve provenance meaning.
              </p>
            )}

            {editorMode === "create" && !isIcloudCloudExport(editorForm) ? (
              <p className={styles.helperText}>
                Root path is the folder that will be scanned in a future intake run. Root path cannot be edited after creation in this milestone.
              </p>
            ) : editorMode === "create" ? (
              <div className={styles.pathPreviewBlock}>
                <p className={styles.helperText}>
                  Managed staging path should match the canonical iCloud path for this label.
                </p>
                <p className={styles.pathPreviewLine}>
                  <strong>Preview path:</strong> {managedStagingPreview}
                </p>
                <p className={styles.pathPreviewLine}>
                  <strong>Resolved path:</strong> Stored by the backend on save.
                </p>
              </div>
            ) : null}

            {editorError && <p className={styles.bannerError}>{editorError}</p>}

            <div className={styles.drawerActions}>
              <button
                type="button"
                className={styles.updateButton}
                onClick={() => void saveEditor()}
                disabled={isSavingEditor}
              >
                {isSavingEditor ? "Saving..." : editorMode === "create" ? "Create Profile" : "Save Status"}
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
                <h3 className={styles.drawerTitle}>
                  {isGuidedIcloudRunCandidate ? "Confirm Guided iCloud Source Intake" : "Confirm Source Intake"}
                </h3>
                <p className={styles.drawerSubtitle}>
                  {isGuidedIcloudRunCandidate
                    ? "Review the staged iCloud context and run options before starting Source Intake."
                    : "Review the source and run options before starting Source Intake."}
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
                <span className={styles.detailLabel}>{isGuidedIcloudRunCandidate ? "Source Type / Provider" : "Source Type"}</span>
                <span>{isGuidedIcloudRunCandidate ? "cloud_export / icloud" : runCandidateProfile.source_type}</span>
              </div>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>{isGuidedIcloudRunCandidate ? "Managed Staging Path" : "Source Path"}</span>
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
              {isGuidedIcloudRunCandidate && (
                <div className={styles.detailCard}>
                  <span className={styles.detailLabel}>iCloud Intake Context</span>
                  <span>Source Profile ID {runCandidateProfile.source_id} maps to ingestion_source_id.</span>
                  <span className={styles.detailMeta}>{icloudSourceIntakeLimitSuggestion.label}</span>
                  <span className={styles.detailMeta}>{icloudSourceIntakeLimitSuggestion.note}</span>
                </div>
              )}
            </div>

            <p className={styles.note}>
              {isGuidedIcloudRunCandidate
                ? "This scans the managed iCloud staging folder and copies eligible files into the Drop Zone for ingestion. It does not delete files from the staging folder, and cleanup will not run automatically."
                : "This scans the selected source folder and copies eligible files into the Drop Zone for ingestion. It does not delete files from the source folder."}
              {" "}
              Only one Source Intake run can run at a time.
            </p>

            <section className={styles.runOptionsBlock}>
              <h4 className={styles.runOptionsTitle}>{isGuidedIcloudRunCandidate ? "Guided Source Intake Options" : "Run Intake Options"}</h4>
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
                    {isGuidedIcloudRunCandidate
                      ? "Leave blank for no limit. Suggested from the latest acquisition when available; otherwise Source Intake scans the staging folder and skips known files."
                      : "Leave blank for no limit. Controls the maximum number of eligible unknown files selected for this run."}
                  </span>
                  {isGuidedIcloudRunCandidate && (
                    <span className={styles.formHint}>{icloudSourceIntakeLimitSuggestion.note}</span>
                  )}
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
                    Controls how many files are staged and processed per ingestion batch. Default: 500.
                  </span>
                  {runBatchSizeValidationError && <span className={styles.fieldError}>{runBatchSizeValidationError}</span>}
                </label>
              </div>
            </section>

            <p className={styles.helperText}>
              These options apply only to this run. They are not saved to the Source Profile.
            </p>

            {runOptionsError && <p className={styles.bannerError}>{runOptionsError}</p>}

            <div className={styles.drawerActions}>
              <button
                type="button"
                className={styles.runButton}
                onClick={() => void handleConfirmRunIntake()}
                disabled={isRunActionLoading}
              >
                {isRunActionLoading ? "Starting..." : (isGuidedIcloudRunCandidate ? "Start Guided Source Intake" : "Run Intake")}
              </button>
              <button type="button" className={styles.button} onClick={closeRunConfirmation} disabled={isRunActionLoading}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {isIcloudAcquisitionConfirmOpen && detailProfile && isDetailIcloudProfile && (
        <div className={styles.drawerBackdrop} role="dialog" aria-modal="true">
          <div className={styles.drawerPanel}>
            <div className={styles.drawerHeader}>
              <div>
                <h3 className={styles.drawerTitle}>Confirm iCloud Acquisition</h3>
                <p className={styles.drawerSubtitle}>
                  Review source profile readiness and acquisition settings before starting.
                </p>
              </div>
              <button
                type="button"
                className={styles.closeButton}
                onClick={closeIcloudAcquisitionConfirmation}
                disabled={isIcloudAcquisitionActionLoading}
              >
                Close
              </button>
            </div>

            <div className={styles.detailGrid}>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Source Profile</span>
                <span>{detailProfile.source_label}</span>
              </div>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Account Username</span>
                <span>{detailProfile.account_username_masked ?? "-"}</span>
                <span className={styles.detailMeta}>Real username is used internally for API payload.</span>
              </div>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Managed Staging Path</span>
                <span>{detailProfile.managed_staging_path ?? "-"}</span>
              </div>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Expected Acquisition Path</span>
                <span>{expectedAcquisitionPath ?? "-"}</span>
              </div>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Readiness Status</span>
                <span className={`${styles.readinessBadge} ${readinessBadgeClassName}`}>{toIcloudReadinessLabel(icloudReadiness)}</span>
              </div>
            </div>

            <section className={styles.runOptionsBlock}>
              <h4 className={styles.runOptionsTitle}>Acquisition Options</h4>
              <div className={styles.formGrid}>
                <label className={styles.formLabel}>
                  Recent Count
                  <input
                    className={styles.formInput}
                    type="number"
                    min={1}
                    max={500}
                    value={icloudAcquisitionRecentCountInput}
                    onChange={(event) => setIcloudAcquisitionRecentCountInput(event.target.value)}
                  />
                  <span className={styles.formHint}>
                    Recent Count controls how many recent iCloud items icloudpd considers for acquisition.
                  </span>
                  {icloudAcquisitionRecentCountValidationError && (
                    <span className={styles.fieldError}>{icloudAcquisitionRecentCountValidationError}</span>
                  )}
                </label>

                <label className={styles.formLabel}>
                  Acquisition Mode
                  <select
                    className={styles.formInput}
                    value={icloudAcquisitionMode}
                    onChange={(event) => setIcloudAcquisitionMode(event.target.value as IcloudAcquisitionMode)}
                  >
                    <option value="standard">Standard</option>
                    <option value="list_first_non_repeat">List first / non-repeat</option>
                  </select>
                  <span className={styles.formHint}>
                    Standard downloads the requested recent items. List-first/non-repeat checks candidate filenames first and may skip download if candidates are already known.
                  </span>
                </label>
              </div>
            </section>

            <p className={styles.note}>
              Photo Organizer does not store your Apple password or 2FA code. iCloud authentication is handled outside the app by icloudpd.
              If authentication is expired, acquisition may fail and the readiness panel will show Action Required.
            </p>

            <p className={styles.note}>
              This will download recent iCloud files into the managed staging folder. It will not run Source Intake automatically.
              It will not delete files from iCloud. It will not clean up staged files.
            </p>

            {icloudAcquisitionError && <p className={styles.bannerError}>{icloudAcquisitionError}</p>}

            <div className={styles.drawerActions}>
              <button
                type="button"
                className={styles.runButton}
                onClick={() => void handleConfirmAcquireFromIcloud()}
                disabled={isIcloudAcquisitionActionLoading}
              >
                {isIcloudAcquisitionActionLoading ? "Starting..." : "Acquire from iCloud"}
              </button>
              <button
                type="button"
                className={styles.button}
                onClick={closeIcloudAcquisitionConfirmation}
                disabled={isIcloudAcquisitionActionLoading}
              >
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
                      <span className={styles.detailLabel}>Source Root Path / Compatibility Identity Path</span>
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
                        disabled={isCreatingStagingFolder || approvedRootStatus === "blocked"}
                      >
                        {isCreatingStagingFolder ? "Creating..." : "Create Staging Folder"}
                      </button>
                    )}
                    {isDetailIcloudProfile && (
                      <button
                        type="button"
                        className={styles.button}
                        onClick={() => {
                          if (detailSourceId) {
                            void loadIcloudReadiness(detailSourceId);
                          }
                        }}
                        disabled={isLoadingIcloudReadiness || !detailSourceId}
                      >
                        {isLoadingIcloudReadiness ? "Refreshing..." : "Refresh Readiness"}
                      </button>
                    )}
                  </div>
                </section>

                {isDetailIcloudProfile && (
                  <section className={styles.detailSection}>
                    <h4 className={styles.detailHeading}>iCloud Readiness</h4>
                    <div className={styles.detailGrid}>
                      <div className={styles.detailCard}>
                        <span className={styles.detailLabel}>Readiness</span>
                        <span className={`${styles.readinessBadge} ${readinessBadgeClassName}`}>
                          {toIcloudReadinessLabel(icloudReadiness)}
                        </span>
                        {icloudReadinessError && (
                          <p className={styles.inlineWarning}>Readiness unavailable: {icloudReadinessError}</p>
                        )}
                        <span className={styles.detailMeta}>Acquisition flow state: {toIcloudAcquisitionStateLabel(icloudAcquisitionUiState)}</span>
                        {isLoadingIcloudAcquisitionDetails && (
                          <span className={styles.detailMeta}>Loading acquisition details...</span>
                        )}
                      </div>
                      <div className={styles.detailCard}>
                        <span className={styles.detailLabel}>Managed Staging Path</span>
                        <span>{detailProfile.managed_staging_path ?? "-"}</span>
                        <span className={styles.detailMeta}>
                          Approved root: {approvedRootStatus === "ok" ? "OK" : approvedRootStatus === "blocked" ? "Blocked" : "Unknown"}
                        </span>
                        <span className={styles.detailMeta}>
                          Staging folder: {
                            stagingFolderStatus === "exists"
                              ? "Exists"
                              : stagingFolderStatus === "missing"
                                ? "Missing"
                                : stagingFolderStatus === "unsafe"
                                  ? "Unsafe"
                                  : "Not checked"
                          }
                        </span>
                      </div>
                      <div className={styles.detailCard}>
                        <span className={styles.detailLabel}>Expected Acquisition Path</span>
                        <span>{expectedAcquisitionPath ?? "-"}</span>
                        <span className={styles.detailMeta}>
                          Path alignment: {
                            pathAlignmentStatus === "ok"
                              ? "OK"
                              : pathAlignmentStatus === "mismatch"
                                ? "Mismatch"
                                : "Unknown"
                          }
                        </span>
                        {pathAlignmentStatus === "mismatch" && (
                          <p className={styles.inlineWarning}>
                            The managed staging path does not match the expected iCloud acquisition path. Acquisition should not run until this profile is aligned.
                          </p>
                        )}
                        {pathAlignmentStatus === "mismatch" && (
                          <span className={styles.detailMeta}>
                            Creating the staging folder does not repair source path alignment. Resolve path mismatch before acquisition.
                          </span>
                        )}
                      </div>
                      <div className={styles.detailCard}>
                        <span className={styles.detailLabel}>Source Registration</span>
                        <span>{toRegistrationStatusLabel(sourceRegistrationStatus)}</span>
                        {sourceRegistrationStatus === "mismatch" ? (
                          <span className={styles.detailMeta}>
                            Current acquisition expects the source root path to match the acquisition staging path. This profile may need path alignment before acquisition can run from Ingestion.
                          </span>
                        ) : (
                          <span className={styles.detailMeta}>
                            Current acquisition requires source label/type/path alignment. Exact launch validation will occur when acquisition is implemented.
                          </span>
                        )}
                      </div>
                      <div className={styles.detailCard}>
                        <span className={styles.detailLabel}>iCloud Authentication</span>
                        <span>{toAuthStatusLabel(authStatus)}</span>
                        {authStatus === "action_required" && (
                          <p className={styles.inlineWarning}>
                            iCloud authentication is required. Re-authenticate icloudpd outside Photo Organizer, then refresh readiness.
                          </p>
                        )}
                        <span className={styles.detailMeta}>
                          Photo Organizer does not store your Apple password or 2FA code. iCloud authentication is handled outside the app by icloudpd.
                        </span>
                      </div>
                      <div className={styles.detailCard}>
                        <span className={styles.detailLabel}>Acquire from iCloud</span>
                        <span>
                          {icloudAcquireDisabledReason
                            ? "Blocked"
                            : "Ready"}
                        </span>
                        <span className={styles.detailMeta}>
                          Use this to download recent iCloud files into the managed staging folder.
                        </span>
                        <span className={styles.detailMeta}>
                          This does not run Source Intake automatically and does not run cleanup.
                        </span>
                        {icloudAcquireDisabledReason && (
                          <p className={styles.inlineWarning}>{icloudAcquireDisabledReason}</p>
                        )}
                        <div className={styles.rowActions}>
                          <button
                            type="button"
                            className={styles.runButton}
                            onClick={() => void handleAcquireFromIcloudClick()}
                            disabled={Boolean(icloudAcquireDisabledReason) || isIcloudAcquisitionActionLoading || isLoadingIcloudAcquisitionDetails}
                          >
                            {isLoadingIcloudAcquisitionDetails
                              ? "Loading..."
                              : "Acquire from iCloud"}
                          </button>
                          <button
                            type="button"
                            className={styles.button}
                            onClick={() => void loadIcloudAcquisitionStatus()}
                            disabled={isIcloudAcquisitionActionLoading}
                          >
                            Refresh Acquisition Status
                          </button>
                          {isIcloudAcquisitionActive && (
                            <button
                              type="button"
                              className={styles.stopButton}
                              onClick={() => void handleIcloudAcquisitionRequestStop()}
                              disabled={isIcloudAcquisitionActionLoading || icloudAcquisitionStatus?.status === "stop_requested"}
                            >
                              {icloudAcquisitionStatus?.status === "stop_requested"
                                ? "Stop Requested"
                                : (isIcloudAcquisitionActionLoading ? "Requesting..." : "Request Stop")}
                            </button>
                          )}
                        </div>
                      </div>
                      <div className={styles.detailCard}>
                        <span className={styles.detailLabel}>Last Acquisition Status</span>
                        {isLoadingIcloudReadiness ? (
                          <span>Loading...</span>
                        ) : icloudReadinessSnapshot?.last_acquisition ? (
                          <>
                            <span>{toStatusLabel(icloudReadinessSnapshot.last_acquisition.status)}</span>
                            <span className={styles.detailMeta}>Started: {toDisplayDate(icloudReadinessSnapshot.last_acquisition.started_at)}</span>
                            <span className={styles.detailMeta}>Finished: {toDisplayDate(icloudReadinessSnapshot.last_acquisition.finished_at)}</span>
                            <span className={styles.detailMeta}>Downloaded: {icloudReadinessSnapshot.last_acquisition.downloaded_count}</span>
                            <span className={styles.detailMeta}>Skipped: {icloudReadinessSnapshot.last_acquisition.skipped_count}</span>
                            <span className={styles.detailMeta}>Failed: {icloudReadinessSnapshot.last_acquisition.failed_count}</span>
                            <span className={styles.detailMeta}>Error Code: {icloudReadinessSnapshot.last_acquisition.error_code ?? "-"}</span>
                            <span className={styles.detailMeta}>Report: {icloudReadinessSnapshot.last_acquisition.report_path ?? "-"}</span>
                          </>
                        ) : (
                          <span>No matching recent acquisition status found.</span>
                        )}
                      </div>
                      <div className={styles.detailCard}>
                        <span className={styles.detailLabel}>Operation Conflicts</span>
                        <span>
                          {(icloudReadinessSnapshot?.operation_conflicts.icloud_acquisition_active
                            || icloudReadinessSnapshot?.operation_conflicts.source_intake_active
                            || icloudReadinessSnapshot?.operation_conflicts.icloud_cleanup_active)
                            ? "Active"
                            : "None detected"}
                        </span>
                        <span className={styles.detailMeta}>iCloud acquisition active: {icloudReadinessSnapshot?.operation_conflicts.icloud_acquisition_active ? "Yes" : "No"}</span>
                        <span className={styles.detailMeta}>Source intake active: {icloudReadinessSnapshot?.operation_conflicts.source_intake_active ? "Yes" : "No"}</span>
                        <span className={styles.detailMeta}>iCloud cleanup active: {icloudReadinessSnapshot?.operation_conflicts.icloud_cleanup_active ? "Yes" : "No"}</span>
                      </div>
                      <div className={styles.detailCard}>
                        <span className={styles.detailLabel}>Blocking Reasons</span>
                        {readinessBlockingReasons.length > 0 ? (
                          readinessBlockingReasons.map((reason) => (
                            <span key={reason.code} className={styles.detailMeta}>{reason.code}: {reason.message}</span>
                          ))
                        ) : (
                          <span className={styles.detailMeta}>None</span>
                        )}
                      </div>
                      <div className={styles.detailCard}>
                        <span className={styles.detailLabel}>Warnings</span>
                        {readinessWarnings.length > 0 ? (
                          readinessWarnings.map((reason) => (
                            <span key={reason.code} className={styles.detailMeta}>{reason.code}: {reason.message}</span>
                          ))
                        ) : (
                          <span className={styles.detailMeta}>None</span>
                        )}
                      </div>
                      <div className={styles.detailCard}>
                        <span className={styles.detailLabel}>Recommended Next Action</span>
                        <span>{recommendedIcloudAction ?? "Run diagnostics or use Admin iCloud tools to confirm readiness."}</span>
                        <span className={styles.detailMeta}>Guided Source Intake stays manual and runs from this iCloud detail view.</span>
                      </div>
                      <div className={styles.detailCard}>
                        <span className={styles.detailLabel}>Source Intake Handoff</span>
                        <span>{icloudSourceIntakeLimitSuggestion.label}</span>
                        <span className={styles.detailMeta}>Source Profile ID {detailProfile.source_id} will be sent as ingestion_source_id.</span>
                        <span className={styles.detailMeta}>Cleanup will not run automatically.</span>
                        <span className={styles.detailMeta}>{icloudSourceIntakeLimitSuggestion.note}</span>
                        <div className={styles.rowActions}>
                          <button
                            type="button"
                            className={styles.runButton}
                            onClick={() => void handlePrepareIcloudSourceIntake()}
                            disabled={Boolean(icloudSourceIntakeDisabledReason) || isRunActionLoading || isIcloudAcquisitionActionLoading}
                          >
                            Run Source Intake for Staged iCloud Files
                          </button>
                        </div>
                        <span className={styles.detailMeta}>You will confirm Total Limit and Batch Size before the run starts.</span>
                        {icloudSourceIntakeDisabledReason && (
                          <span className={styles.detailMeta}>{icloudSourceIntakeDisabledReason}</span>
                        )}
                      </div>
                    </div>

                    {icloudAcquisitionError && (
                      <p className={styles.bannerError}>{icloudAcquisitionError}</p>
                    )}
                    {icloudAcquisitionErrorCode && (
                      <p className={styles.helperText}>Error code: {icloudAcquisitionErrorCode}</p>
                    )}
                    {icloudAcquisitionBlockingReasons.length > 0 && (
                      <div className={styles.warningList}>
                        {icloudAcquisitionBlockingReasons.map((reason) => (
                          <p key={`${reason.code}:${reason.message}`} className={styles.inlineWarning}>
                            {reason.code}: {reason.message}
                          </p>
                        ))}
                      </div>
                    )}
                    {icloudAcquisitionConflictSummary && (
                      <p className={styles.helperText}>{icloudAcquisitionConflictSummary}</p>
                    )}

                    {icloudAcquisitionStatus && (
                      <section className={styles.runPanel}>
                        <div className={styles.runPanelHeader}>
                          <h3 className={styles.runPanelTitle}>iCloud Acquisition Status</h3>
                          {showIcloudAcquisitionTerminalSummary && currentIcloudAcquisitionTerminalKey && (
                            <button
                              type="button"
                              className={styles.button}
                              onClick={() => setDismissedIcloudAcquisitionTerminalKey(currentIcloudAcquisitionTerminalKey)}
                            >
                              Dismiss
                            </button>
                          )}
                        </div>
                        <div className={styles.runMetrics}>
                          <span><strong>Status:</strong> <span className={`${styles.runStatusBadge} ${statusClassName(icloudAcquisitionStatus.status)}`}>{toStatusLabel(icloudAcquisitionStatus.status)}</span></span>
                          <span><strong>Source:</strong> {icloudAcquisitionStatus.source_label ?? "-"}</span>
                          <span><strong>Recent Count:</strong> {icloudAcquisitionStatus.recent_count ?? "-"}</span>
                          <span><strong>Acquisition Mode:</strong> {toIcloudAcquisitionModeLabel((icloudAcquisitionStatus.acquisition_mode ?? "standard") as IcloudAcquisitionMode)}</span>
                          <span><strong>Started:</strong> {toDisplayDate(icloudAcquisitionStatus.started_at)}</span>
                          <span><strong>Finished:</strong> {toDisplayDate(icloudAcquisitionStatus.completed_at)}</span>
                          <span><strong>Downloaded:</strong> {icloudAcquisitionStatus.downloaded_count}</span>
                          <span><strong>Skipped:</strong> {icloudAcquisitionStatus.skipped_existing_count}</span>
                          <span><strong>Failed:</strong> {icloudAcquisitionStatus.failed_count}</span>
                          <span><strong>File inventory count:</strong> {icloudAcquisitionStatus.file_inventory_count ?? "-"}</span>
                          <span><strong>Error code:</strong> {icloudAcquisitionStatus.error_code ?? "-"}</span>
                          <span><strong>Error message:</strong> {icloudAcquisitionStatus.error_message ?? "-"}</span>
                          <span><strong>Report path:</strong> {icloudAcquisitionStatus.report_path ?? "-"}</span>
                        </div>

                        {(icloudAcquisitionStatus.status === "completed" || icloudAcquisitionStatus.status === "completed_with_warnings") && (
                          <p className={styles.bannerSuccess}>
                            Acquisition completed. The next step is Source Intake for staged iCloud files. Use the Source Intake Handoff section above to continue.
                          </p>
                        )}
                        {(icloudAcquisitionStatus.error_code === "AUTH_REQUIRED" || icloudAcquisitionStatus.error_code === "SESSION_EXPIRED") && (
                          <p className={styles.inlineWarning}>
                            Authentication is required. Re-authenticate icloudpd outside Photo Organizer, then refresh readiness.
                          </p>
                        )}
                        {(icloudAcquisitionStatus.error_code === "SOURCE_NOT_REGISTERED"
                          || icloudAcquisitionStatus.error_code === "INVALID_PATH"
                          || icloudAcquisitionStatus.error_code === "APPROVED_ROOT_BLOCKED") && (
                          <p className={styles.inlineWarning}>
                            Resolve Source Profile readiness issues before trying again.
                          </p>
                        )}
                      </section>
                    )}

                    <section className={styles.runPanel}>
                      <div className={styles.runPanelHeader}>
                        <h3 className={styles.runPanelTitle}>iCloud Workflow Summary</h3>
                        <button
                          type="button"
                          className={styles.button}
                          onClick={() => void handleRefreshIcloudWorkflowSummary()}
                        >
                          Refresh Summary
                        </button>
                      </div>

                      <div className={styles.detailGrid}>
                        <div className={styles.detailCard}>
                          <span className={styles.detailLabel}>Acquisition</span>
                          {latestAcquisitionForDetail ? (
                            <>
                              <span><strong>Status:</strong> <span className={`${styles.runStatusBadge} ${statusClassName(latestAcquisitionForDetail.status ?? "idle")}`}>{toStatusLabel(latestAcquisitionForDetail.status ?? "unknown")}</span></span>
                              <span className={styles.detailMeta}>Started: {toDisplayDate(latestAcquisitionForDetail.started_at)}</span>
                              <span className={styles.detailMeta}>Finished: {toDisplayDate(latestAcquisitionForDetail.finished_at)}</span>
                              <span className={styles.detailMeta}>Requested recent count: {latestAcquisitionForDetail.recent_count ?? "-"}</span>
                              <span className={styles.detailMeta}>File inventory count: {latestAcquisitionForDetail.file_inventory_count ?? "-"}</span>
                              <span className={styles.detailMeta}>Downloaded: {latestAcquisitionForDetail.downloaded_count ?? "-"}</span>
                              <span className={styles.detailMeta}>Skipped: {latestAcquisitionForDetail.skipped_count ?? "-"}</span>
                              <span className={styles.detailMeta}>Failed: {latestAcquisitionForDetail.failed_count ?? "-"}</span>
                              <span className={styles.detailMeta}>Acquisition mode: {latestAcquisitionForDetail.acquisition_mode ?? "-"}</span>
                              <span className={styles.detailMeta}>Report: {latestAcquisitionForDetail.report_path ?? "-"}</span>
                            </>
                          ) : (
                            <span>No recent iCloud acquisition found for this profile.</span>
                          )}
                        </div>

                        <div className={styles.detailCard}>
                          <span className={styles.detailLabel}>Source Intake</span>
                          {detailSourceIntakeStatus ? (
                            <>
                              <span><strong>Status:</strong> <span className={`${styles.runStatusBadge} ${statusClassName(detailSourceIntakeStatus.status)}`}>{toStatusLabel(detailSourceIntakeStatus.status)}</span></span>
                              <span className={styles.detailMeta}>Started: {toDisplayDate(detailSourceIntakeStatus.started_at)}</span>
                              <span className={styles.detailMeta}>Finished: {toDisplayDate(detailSourceIntakeStatus.finished_at)}</span>
                              <span className={styles.detailMeta}>Scanned: {detailSourceIntakeStatus.files_scanned}</span>
                              <span className={styles.detailMeta}>Skipped known: {detailSourceIntakeStatus.skipped_known}</span>
                              <span className={styles.detailMeta}>Selected: {detailSourceIntakeStatus.selected}</span>
                              <span className={styles.detailMeta}>Staged to Drop Zone: {detailSourceIntakeStatus.staged}</span>
                              <span className={styles.detailMeta}>Processed new unique: {detailSourceIntakeStatus.processed_new_unique}</span>
                              <span className={styles.detailMeta}>Failed/rejected: {detailSourceIntakeStatus.failed_or_rejected}</span>
                              <span className={styles.detailMeta}>Deferred/unready: {latestSourceIntakeReportForDetail?.counts?.deferred_unready_count ?? "-"}</span>
                              <span className={styles.detailMeta}>Remaining unknown eligible: {detailSourceIntakeStatus.remaining_unknown}</span>
                              <span className={styles.detailMeta}>Source complete: {latestSourceIntakeReportForDetail?.source_complete == null ? "-" : latestSourceIntakeReportForDetail.source_complete ? "Yes" : "No"}</span>
                              <span className={styles.detailMeta}>Report: {detailSourceIntakeStatus.report_path ?? latestSourceIntakeReportForDetail?.report_filename ?? "-"}</span>
                            </>
                          ) : latestSourceIntakeReportForDetail ? (
                            <>
                              <span><strong>Status:</strong> Reported</span>
                              <span className={styles.detailMeta}>Finished: {toDisplayDate(latestSourceIntakeReportForDetail.generated_at_utc)}</span>
                              <span className={styles.detailMeta}>Scanned: {latestSourceIntakeReportForDetail.counts?.total_files_scanned ?? "-"}</span>
                              <span className={styles.detailMeta}>Skipped known: {latestSourceIntakeReportForDetail.counts?.skipped_already_known ?? "-"}</span>
                              <span className={styles.detailMeta}>Selected: {latestSourceIntakeReportForDetail.counts?.selected_for_session ?? "-"}</span>
                              <span className={styles.detailMeta}>Staged to Drop Zone: {latestSourceIntakeReportForDetail.counts?.staged_to_dropzone ?? "-"}</span>
                              <span className={styles.detailMeta}>Processed new unique: {latestSourceIntakeReportForDetail.counts?.processed_new_unique ?? "-"}</span>
                              <span className={styles.detailMeta}>Failed/rejected: {latestSourceIntakeReportForDetail.counts?.failed_or_rejected ?? "-"}</span>
                              <span className={styles.detailMeta}>Deferred/unready: {latestSourceIntakeReportForDetail.counts?.deferred_unready_count ?? "-"}</span>
                              <span className={styles.detailMeta}>Remaining unknown eligible: {latestSourceIntakeReportForDetail.counts?.remaining_unknown_eligible ?? "-"}</span>
                              <span className={styles.detailMeta}>Source complete: {latestSourceIntakeReportForDetail.source_complete == null ? "-" : latestSourceIntakeReportForDetail.source_complete ? "Yes" : "No"}</span>
                              <span className={styles.detailMeta}>Report: {latestSourceIntakeReportForDetail.report_filename}</span>
                            </>
                          ) : (
                            <span>Source Intake has not been run for this iCloud profile yet.</span>
                          )}
                        </div>

                        <div className={styles.detailCard}>
                          <span className={styles.detailLabel}>Overall Result / Next Step</span>
                          <span>
                            <strong>Status:</strong>{" "}
                            <span className={`${styles.runStatusBadge} ${statusClassName(overallIcloudWorkflowSummary?.status ?? "idle")}`}>
                              {overallIcloudWorkflowSummary?.status ?? "Unknown"}
                            </span>
                          </span>
                          <span className={styles.detailMeta}>{overallIcloudWorkflowSummary?.message ?? "No iCloud workflow summary available."}</span>
                          {overallIcloudWorkflowSummary?.status === "Attention needed" && readinessBlockingReasons.length > 0 && (
                            <div className={styles.warningList}>
                              {readinessBlockingReasons.map((reason) => (
                                <span key={`summary-${reason.code}`} className={styles.detailMeta}>{reason.code}: {reason.message}</span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </section>
                  </section>
                )}

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

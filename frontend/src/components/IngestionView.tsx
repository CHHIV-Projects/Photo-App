"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  checkSourceProfileReadiness,
  createSourceProfile,
  createSourceProfileStagingFolder,
  confirmSourceEndpointEnrollment,
  getIcloudAcquisitionStatus,
  getIcloudStagingCleanupStatus,
  getIcloudStagingCleanupReadiness,
  executeIcloudStagingCleanup,
  IcloudAcquisitionStartError,
  getSourceProfileIcloudReadiness,
  getSourceProfileDetail,
  getSourceIntakeReportDetail,
  getSourceIntakeReports,
  getSourceIntakeRunStatus,
  getSourceProfiles,
  planSourceEndpointEnrollment,
  probeSourceIdentity,
  runIcloudAcquisitionWithDetails,
  runIcloudStagingCleanupDryRun,
  SourceIntakeStartError,
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
  SourceEndpointEnrollmentConfirmResponse,
  SourceEndpointEnrollmentPlanResponse,
  SourceIdentityProbeRequest,
  SourceIdentityProbeSourceType,
  SourceProfileCreateRequest,
  SourceProfileDetail,
  SourceProfileMetadataUpdateRequest,
  SourceProfilePathCheckResponse,
  SourceProfileReadinessResponse,
  SourceProfileReadinessStatus,
  SourceIntakeReportDetail,
  SourceIntakeReportSummary,
  SourceIntakeReadinessRejectionPayload,
  SourceDurableIdentityStatus,
  SourceProfileStagingFolderCreateResponse,
  SourceProfileStatus,
  SourceProfileSummary,
  SourceProfileType,
  SourceIntakeStatusSnapshot,
  IcloudStagingCleanupRunStatus,
  IcloudStagingCleanupReadinessResponse,
} from "@/types/ui-api";

import IcloudRunWorkflowPanel from "./IcloudRunWorkflowPanel";
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
type IcloudCleanupUiState = "idle" | "loading" | "confirm_open" | "running" | "terminal";
type IcloudAcquisitionMode = "standard" | "list_first_non_repeat";
type IcloudSourceIntakeLimitSuggestion = {
  value: string;
  label: string;
  note: string;
};

type EditorFormState = {
  sourceLabel: string;
  operatorSourceType: OperatorSourceType;
  sourceType: SourceProfileType;
  profileStatus: SourceProfileStatus;
  sourceRootPath: string;
  cloudProvider: SourceCloudProvider;
  accountUsername: string;
  acquisitionMethod: SourceAcquisitionMethod;
  managedStagingPath: string;
};

type SourceIdentityEnrollmentPhase = "idle" | "planning" | "review" | "confirming" | "complete";

type SourceIdentityPlanOutcome = {
  plan: SourceEndpointEnrollmentPlanResponse;
  autoLinked: boolean;
};

type SourceIdentityEnrollmentSupport = {
  supported: boolean;
  probeSourceType: SourceIdentityProbeSourceType | null;
  reason: string | null;
  note: string;
};

type OperatorSourceType = "local" | "external" | "nas" | "removable" | "icloud" | "advanced";

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

const ADVANCED_SOURCE_TYPE_OPTIONS: Array<{ value: SourceProfileType; label: string }> = [
  { value: "scan_batch", label: "Scan Batch" },
  { value: "other", label: "Other" },
  { value: "cloud_export", label: "Other Cloud Export" },
];

const OPERATOR_SOURCE_TYPE_OPTIONS: Array<{ value: OperatorSourceType; label: string; disabled?: boolean }> = [
  { value: "local", label: "Local" },
  { value: "nas", label: "NAS" },
  { value: "external", label: "External" },
  { value: "removable", label: "Removable", disabled: true },
  { value: "icloud", label: "iCloud" },
  { value: "advanced", label: "Advanced / Legacy" },
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
const ICLOUD_CLEANUP_POLL_MS = 3000;
const ICLOUD_CLEANUP_ACTIVE_STATUSES = new Set(["pending", "running", "stop_requested"]);
const ICLOUD_CLEANUP_TERMINAL_STATUSES = new Set(["completed", "completed_with_errors", "failed", "stopped"]);
const ICLOUD_CLEANUP_CONFIRMATION_PHRASE = "DELETE LOCAL STAGING COPIES";
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
    operatorSourceType: "local",
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
  const slug = sanitizeIcloudLabelForMatch(sourceLabel);
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

function toSourceProfileReadinessLabel(value: SourceProfileReadinessStatus | null | undefined): string {
  if (value === "ready") {
    return "Ready";
  }
  if (value === "path_only") {
    return "Path-only";
  }
  if (value === "needs_review") {
    return "Needs Review";
  }
  if (value === "blocked") {
    return "Blocked";
  }
  if (value === "provider_specific") {
    return "Provider-specific";
  }
  return "Unknown";
}

function sourceProfileReadinessBadgeClassName(value: SourceProfileReadinessStatus | null | undefined): string {
  if (value === "ready") {
    return styles.readinessBadgeReady;
  }
  if (value === "blocked") {
    return styles.readinessBadgeNotReady;
  }
  if (value === "path_only" || value === "needs_review") {
    return styles.readinessBadgeWarning;
  }
  return styles.readinessBadgeUnknown;
}

function toDurableIdentityLabel(value: SourceDurableIdentityStatus | null | undefined): string {
  if (value === "verified") {
    return "Verified";
  }
  if (value === "not_verified") {
    return "Not verified";
  }
  if (value === "provider_specific") {
    return "Provider-specific";
  }
  return "Unknown";
}

function durableIdentityBadgeClassName(value: SourceDurableIdentityStatus | null | undefined): string {
  if (value === "verified" || value === "provider_specific") {
    return styles.okBadge;
  }
  if (value === "not_verified") {
    return styles.pendingBadge;
  }
  return styles.pendingBadge;
}

function buildSourceReadinessAdvancedDetails(result: SourceProfileReadinessResponse): Record<string, unknown> {
  return {
    identity_match_status: result.identity_match_status,
    endpoint_id: result.endpoint_id,
    endpoint_alias: result.endpoint_alias,
    endpoint_source_type: result.endpoint_source_type,
    durable_identity_identifier_type: result.durable_identity_identifier_type,
    durable_identity_identifier: result.durable_identity_identifier,
    checked_at: result.checked_at,
    probe_summary: result.probe_summary,
    observed_path_summary: result.observed_path_summary,
    access_node_summary: result.access_node_summary,
    advanced_details: result.advanced_details,
  };
}

function sourceReadinessObservedPath(result: SourceProfileReadinessResponse | null, fallbackPath: string | null | undefined): string {
  const observedPath = result?.observed_path_summary?.observed_path;
  if (typeof observedPath === "string" && observedPath.trim()) {
    return observedPath;
  }
  const sourceRootCandidatePath = result?.observed_path_summary?.source_root_candidate_path;
  if (typeof sourceRootCandidatePath === "string" && sourceRootCandidatePath.trim()) {
    return sourceRootCandidatePath;
  }
  return fallbackPath || "-";
}

function sourceReadinessLaunchBlockMessage(result: SourceProfileReadinessResponse): string {
  if (result.readiness_status === "provider_specific") {
    return "This source uses a provider-specific workflow. Use iCloud Intake.";
  }
  if (result.readiness_status === "unknown") {
    return "Readiness could not be determined. Check readiness again before running intake.";
  }
  return result.operator_message || "Source Profile readiness blocks Source Intake launch.";
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

function cleanupSourceLabel(status: IcloudStagingCleanupRunStatus | null): string {
  if (!status) {
    return "-";
  }

  return status.source_label ?? `Source ID ${status.source_id ?? "-"}`;
}

function cleanupSourcePath(status: IcloudStagingCleanupRunStatus | null): string {
  if (!status) {
    return "-";
  }

  return status.source_root_path ?? "-";
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

function isUncPath(pathValue: string | null | undefined): boolean {
  const normalized = (pathValue ?? "").trim().replace(/\//g, "\\");
  return normalized.startsWith("\\\\");
}

function isDriveLetterPath(pathValue: string | null | undefined): boolean {
  return /^[a-zA-Z]:[\\/]/.test((pathValue ?? "").trim());
}

function persistedSourceTypeForOperator(value: OperatorSourceType): SourceProfileType {
  if (value === "external") {
    return "external_drive";
  }
  if (value === "icloud") {
    return "cloud_export";
  }
  if (value === "advanced") {
    return "other";
  }
  return "local_folder";
}

function probeSourceTypeForOperator(value: OperatorSourceType): SourceIdentityProbeSourceType | null {
  if (value === "local") {
    return "local";
  }
  if (value === "nas") {
    return "nas";
  }
  if (value === "external") {
    return "external_device";
  }
  return null;
}

function getCreateSourceIdentitySupport(value: OperatorSourceType): SourceIdentityEnrollmentSupport {
  const probeSourceType = probeSourceTypeForOperator(value);
  if (probeSourceType) {
    return {
      supported: true,
      probeSourceType,
      reason: null,
      note: value === "nas"
        ? "NAS identity uses the canonical UNC server/share while the selected folder remains the Source Root."
        : `${getOperatorSourceTypeLabel(value)} durable identity is checked when the source is created.`,
    };
  }
  if (value === "icloud") {
    return {
      supported: false,
      probeSourceType: null,
      reason: "iCloud uses provider-specific identity and the iCloud Intake workflow.",
      note: "iCloud uses provider-specific identity.",
    };
  }
  return {
    supported: false,
    probeSourceType: null,
    reason: value === "removable"
      ? "Removable sources are coming later."
      : "Source Identity Check is not available for this Advanced / Legacy source type.",
    note: "Generic durable identity is unavailable for this source type.",
  };
}

function sourceNamePart(value: string): string {
  return value
    .split(/[\s_-]+/)
    .filter(Boolean)
    .map((part) => part.toLowerCase() === "nas"
      ? "NAS"
      : part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function suggestSourceName(sourceType: OperatorSourceType, pathValue: string): string | null {
  const normalized = pathValue.trim().replace(/\//g, "\\").replace(/\\+$/, "");
  const parts = normalized.split("\\").filter(Boolean);
  const leaf = parts.length > 0 ? sourceNamePart(parts[parts.length - 1]) : "";
  if (sourceType === "nas") {
    const server = isUncPath(normalized) && parts.length > 0 ? sourceNamePart(parts[0]) : "NAS";
    const endpointName = server.toLowerCase().endsWith(" nas") ? server : `${server} NAS`;
    return leaf && leaf !== server ? `${endpointName} - ${leaf}` : endpointName;
  }
  if (sourceType === "external") {
    return leaf ? `External - ${leaf}` : "External Source";
  }
  if (sourceType === "local") {
    return leaf ? `Local - ${leaf}` : "Local Source";
  }
  return null;
}

function getSourceIdentityEnrollmentSupport(
  sourceType: SourceProfileType,
  pathValue: string | null | undefined,
  endpointSourceType: SourceIdentityProbeSourceType | null = null,
): SourceIdentityEnrollmentSupport {
  if (sourceType === "cloud_export") {
    return {
      supported: false,
      probeSourceType: null,
      reason: "Cloud sources use provider-specific identity and staging. Generic filesystem Source Identity Check is not available for this source type yet.",
      note: "Cloud sources use provider-specific identity and staging.",
    };
  }
  if (sourceType === "scan_batch") {
    return {
      supported: false,
      probeSourceType: null,
      reason: "Source Identity Check is not available for scan batch profiles yet.",
      note: "Source Identity Check is not available for scan batch profiles yet.",
    };
  }
  if (sourceType === "other") {
    return {
      supported: false,
      probeSourceType: null,
      reason: "Source Identity Check is not available for this source type yet.",
      note: "Source Identity Check is not available for this source type yet.",
    };
  }
  if (endpointSourceType === "nas") {
    return {
      supported: true,
      probeSourceType: "nas",
      reason: null,
      note: "NAS durable identity uses the canonical UNC server/share.",
    };
  }
  if (sourceType === "external_drive") {
    return {
      supported: true,
      probeSourceType: "external_device",
      reason: null,
      note: "External durable identity can be checked after the profile is created.",
    };
  }
  if (sourceType === "local_folder" && isUncPath(pathValue)) {
    return {
      supported: true,
      probeSourceType: "nas",
      reason: null,
      note: "UNC paths are treated as NAS source identity for the check.",
    };
  }
  return {
    supported: true,
    probeSourceType: "local",
    reason: null,
    note: "Local durable identity can be checked after the profile is created.",
  };
}

function buildSourceIdentityProbeRequest(profile: SourceProfileSummary): SourceIdentityProbeRequest | null {
  const support = getSourceIdentityEnrollmentSupport(
    profile.source_type,
    profile.source_root_path,
    profile.endpoint_source_type,
  );
  if (!support.supported || !support.probeSourceType || !profile.source_root_path) {
    return null;
  }
  return {
    source_type: support.probeSourceType,
    observed_path: profile.source_root_path,
    probe_mode: "setup_probe",
    intended_use: "source_profile_endpoint_enrollment",
    os_family: "windows",
  };
}

function buildCreateSourceProbeRequest(
  sourceType: OperatorSourceType,
  observedPath: string,
): SourceIdentityProbeRequest | null {
  const probeSourceType = probeSourceTypeForOperator(sourceType);
  if (!probeSourceType || !observedPath.trim()) {
    return null;
  }
  return {
    source_type: probeSourceType,
    observed_path: observedPath.trim(),
    probe_mode: "setup_probe",
    intended_use: "source_profile_endpoint_enrollment",
    os_family: "windows",
  };
}

function formatEnrollmentAction(value: string): string {
  if (value === "create_new_endpoint") {
    return "Create new endpoint";
  }
  if (value === "link_existing_endpoint") {
    return "Link existing endpoint";
  }
  return "No endpoint change";
}

function formatPlanStatus(value: string): string {
  return value
    .split("_")
    .map((piece) => piece.charAt(0).toUpperCase() + piece.slice(1))
    .join(" ");
}

function formatEnrollmentPlanStatus(plan: SourceEndpointEnrollmentPlanResponse): string {
  if (plan.plan_status === "duplicate_match") {
    return plan.candidate?.source_type === "nas"
      ? "Existing NAS share endpoint found"
      : "Existing durable source identity found";
  }
  return formatPlanStatus(plan.plan_status);
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

function getOperatorSourceType(profile: SourceProfileSummary): OperatorSourceType {
  if (isIcloudProfile(profile)) {
    return "icloud";
  }
  if (profile.endpoint_source_type === "nas" || (profile.source_type === "local_folder" && isUncPath(profile.source_root_path))) {
    return "nas";
  }
  if (profile.endpoint_source_type === "removable_media") {
    return "removable";
  }
  if (profile.source_type === "local_folder") {
    return "local";
  }
  if (profile.source_type === "external_drive") {
    return "external";
  }
  return "advanced";
}

function getOperatorSourceTypeLabel(value: OperatorSourceType): string {
  const option = OPERATOR_SOURCE_TYPE_OPTIONS.find((item) => item.value === value);
  return option?.label ?? "Advanced / Legacy";
}

function formatSourceProvider(value: SourceCloudProvider | null | undefined): string {
  if (value === "icloud") {
    return "iCloud";
  }
  if (value === "google_photos") {
    return "Google Photos";
  }
  if (value === "onedrive") {
    return "OneDrive";
  }
  if (value === "dropbox") {
    return "Dropbox";
  }
  if (value === "other") {
    return "Other cloud";
  }
  return "No provider";
}

function getSourcePathOrProviderHint(profile: SourceProfileSummary): string {
  if (isIcloudProfile(profile)) {
    const accountHint = profile.account_username_masked ? `Account: ${profile.account_username_masked}` : "Account: not shown";
    const stagingHint = profile.managed_staging_path ? `Staging: ${profile.managed_staging_path}` : "Staging: not configured";
    return `${accountHint}; ${stagingHint}`;
  }
  if (profile.source_root_path) {
    return profile.source_root_path;
  }
  if (profile.managed_staging_path) {
    return profile.managed_staging_path;
  }
  return formatSourceProvider(profile.cloud_provider);
}

function getSourceIdentityDisplay(
  profile: SourceProfileSummary,
  readinessResult: SourceProfileReadinessResponse | null,
): string {
  if (readinessResult && readinessResult.source_profile_id === profile.source_id) {
    return toDurableIdentityLabel(readinessResult.durable_identity_status);
  }
  if (isIcloudProfile(profile)) {
    return "Provider-specific";
  }
  return "Not checked";
}

function getSourceIdentityBadgeClassName(
  profile: SourceProfileSummary,
  readinessResult: SourceProfileReadinessResponse | null,
): string {
  if (readinessResult && readinessResult.source_profile_id === profile.source_id) {
    return durableIdentityBadgeClassName(readinessResult.durable_identity_status);
  }
  if (isIcloudProfile(profile)) {
    return durableIdentityBadgeClassName("provider_specific");
  }
  return durableIdentityBadgeClassName("unknown");
}

function getSourceIdentityMeta(
  profile: SourceProfileSummary,
  readinessResult: SourceProfileReadinessResponse | null,
): string {
  if (readinessResult && readinessResult.source_profile_id === profile.source_id) {
    return readinessResult.durable_identity_reason ?? "Durable identity checked.";
  }
  if (profile.endpoint_id) {
    return "Endpoint link present. Run Check Readiness to verify current durable identity.";
  }
  if (isIcloudProfile(profile)) {
    return "Use iCloud Intake for provider-specific identity.";
  }
  return "Run Check Readiness to verify durable identity.";
}

function getSourceWorkflowDisplay(profile: SourceProfileSummary): string {
  const sourceType = getOperatorSourceType(profile);
  if (sourceType === "icloud") {
    return "iCloud Intake";
  }
  if (sourceType === "advanced") {
    return "Advanced / legacy";
  }
  return "Filesystem Source Intake";
}

function getSourceWorkflowPlaceholder(profile: SourceProfileSummary): string {
  const sourceType = getOperatorSourceType(profile);
  if (sourceType === "icloud") {
    return "iCloud workflow actions remain in the iCloud Intake panel for now: Refresh / Prepare and Import / Resume.";
  }
  if (sourceType === "advanced") {
    return "These sources are retained for history, diagnostics, or unsupported workflows.";
  }
  return "Filesystem workflow actions will move here next: Check Readiness and Run Intake.";
}

function normalizeWorkbenchSearch(value: string | null | undefined): string {
  return (value ?? "").trim().toLowerCase();
}

function matchesSourceSearch(profile: SourceProfileSummary, query: string): boolean {
  const normalizedQuery = normalizeWorkbenchSearch(query);
  if (!normalizedQuery) {
    return true;
  }
  const searchValues = [
    profile.source_label,
    profile.source_root_path,
    profile.managed_staging_path,
    profile.cloud_provider,
    profile.acquisition_method,
    profile.account_username_masked,
    getSourcePathOrProviderHint(profile),
  ];
  return searchValues.some((value) => normalizeWorkbenchSearch(value).includes(normalizedQuery));
}

function extractReportFilename(reportPath: string | null): string | null {
  if (!reportPath) {
    return null;
  }
  const pieces = reportPath.split(/[\\/]/).filter(Boolean);
  return pieces.length > 0 ? pieces[pieces.length - 1] : null;
}

function formatSourceIntakeReadinessRejection(payload: SourceIntakeReadinessRejectionPayload): string {
  const lines: string[] = [];
  if (payload.readiness_status) {
    lines.push(`Readiness: ${toSourceProfileReadinessLabel(payload.readiness_status)}`);
  }
  if (payload.identity_match_status) {
    lines.push(`Identity match: ${toStatusLabel(payload.identity_match_status)}`);
  }
  if (payload.recommended_next_action) {
    lines.push(`Recommended next action: ${payload.recommended_next_action}`);
  }
  for (const blocker of payload.blockers ?? []) {
    lines.push(`Blocker - ${blocker.code}: ${blocker.message}`);
  }
  for (const warning of payload.warnings ?? []) {
    lines.push(`Warning - ${warning.code}: ${warning.message}`);
  }
  return lines.join("\n");
}

function mapRunStartError(error: unknown): { message: string; raw: string | null } {
  if (error instanceof SourceIntakeStartError && error.payload) {
    const payload = error.payload;
    return {
      message: payload.operator_message || payload.detail || error.message,
      raw: formatSourceIntakeReadinessRejection(payload) || error.message,
    };
  }

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
  if (profile && isIcloudProfile(profile)) {
    return "Legacy guided Source Intake handoff is retired. Use the iCloud Intake workflow for this source.";
  }

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
  profile: Pick<
    SourceProfileSummary,
    "source_id" | "source_label" | "source_type" | "source_root_path" | "managed_staging_path"
  > & {
    expected_acquisition_path?: string | null;
  },
  status: IcloudAcquisitionRunStatus | null,
): boolean {
  if (!status) {
    return false;
  }

  const statusWithIds = status as IcloudAcquisitionRunStatus & {
    source_id?: number | null;
    ingestion_source_id?: number | null;
  };
  const statusSourceId = statusWithIds.source_id ?? statusWithIds.ingestion_source_id ?? null;
  if (statusSourceId != null && statusSourceId === profile.source_id) {
    return true;
  }

  const sameType = normalizeIdentityValue(status.source_type) === normalizeIdentityValue(profile.source_type);
  if (!sameType) {
    return false;
  }

  const profilePaths = [
    profile.managed_staging_path,
    profile.expected_acquisition_path,
    profile.source_root_path,
  ]
    .map(normalizePathForMatch)
    .filter((value) => value.length > 0);
  const statusPaths = [status.staging_path, status.source_root_path]
    .map(normalizePathForMatch)
    .filter((value) => value.length > 0);
  if (statusPaths.some((statusPath) => profilePaths.includes(statusPath))) {
    return true;
  }

  const sameSlug = sanitizeIcloudLabelForMatch(status.source_label) === sanitizeIcloudLabelForMatch(profile.source_label);
  if (sameSlug) {
    return true;
  }

  const sameLabel = normalizeIdentityValue(status.source_label) === normalizeIdentityValue(profile.source_label);
  if (sameLabel) {
    return true;
  }

  return false;
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
  const [workbenchSourceType, setWorkbenchSourceType] = useState<OperatorSourceType>("local");
  const [workbenchSearch, setWorkbenchSearch] = useState("");
  const [showInactiveWorkbenchSources, setShowInactiveWorkbenchSources] = useState(false);
  const [selectedWorkbenchSourceId, setSelectedWorkbenchSourceId] = useState<number | null>(null);
  const [isCreateSourceExpanded, setIsCreateSourceExpanded] = useState(false);

  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editorMode, setEditorMode] = useState<EditorMode>("create");
  const [editingProfile, setEditingProfile] = useState<SourceProfileSummary | null>(null);
  const [editorForm, setEditorForm] = useState<EditorFormState>(initialFormState());
  const [editorError, setEditorError] = useState<string | null>(null);
  const [isSavingEditor, setIsSavingEditor] = useState(false);
  const [sourceIdentityEnrollRequested, setSourceIdentityEnrollRequested] = useState(false);
  const [sourceIdentityAlias, setSourceIdentityAlias] = useState("");
  const [sourceIdentityPhase, setSourceIdentityPhase] = useState<SourceIdentityEnrollmentPhase>("idle");
  const [sourceIdentityCreatedProfile, setSourceIdentityCreatedProfile] = useState<SourceProfileSummary | null>(null);
  const [sourceIdentityPlan, setSourceIdentityPlan] = useState<SourceEndpointEnrollmentPlanResponse | null>(null);
  const [sourceIdentityConfirmResult, setSourceIdentityConfirmResult] = useState<SourceEndpointEnrollmentConfirmResponse | null>(null);
  const [sourceIdentityReviewAcknowledged, setSourceIdentityReviewAcknowledged] = useState(false);
  const [sourceIdentitySelectedEndpointId, setSourceIdentitySelectedEndpointId] = useState<number | null>(null);
  const [sourceIdentityProbeRequest, setSourceIdentityProbeRequest] = useState<SourceIdentityProbeRequest | null>(null);

  const [isDetailsOpen, setIsDetailsOpen] = useState(false);
  const [detailSourceId, setDetailSourceId] = useState<number | null>(null);
  const [detailProfile, setDetailProfile] = useState<SourceProfileDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailBanner, setDetailBanner] = useState<BannerState>(null);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [isVerifyingPath, setIsVerifyingPath] = useState(false);
  const [pathCheckResult, setPathCheckResult] = useState<SourceProfilePathCheckResponse | null>(null);
  const [sourceReadinessResult, setSourceReadinessResult] = useState<SourceProfileReadinessResponse | null>(null);
  const [isCheckingSourceReadiness, setIsCheckingSourceReadiness] = useState(false);
  const [sourceReadinessError, setSourceReadinessError] = useState<string | null>(null);
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
  const [icloudCleanupStatus, setIcloudCleanupStatus] = useState<IcloudStagingCleanupRunStatus | null>(null);
  const [icloudCleanupReadiness, setIcloudCleanupReadiness] = useState<IcloudStagingCleanupReadinessResponse | null>(null);
  const [icloudCleanupUiState, setIcloudCleanupUiState] = useState<IcloudCleanupUiState>("idle");
  const [isIcloudCleanupConfirmOpen, setIsIcloudCleanupConfirmOpen] = useState(false);
  const [isIcloudCleanupActionLoading, setIsIcloudCleanupActionLoading] = useState(false);
  const [isLoadingIcloudCleanupStatus, setIsLoadingIcloudCleanupStatus] = useState(false);
  const [icloudCleanupError, setIcloudCleanupError] = useState<string | null>(null);
  const [isIcloudCleanupExecutionConfirmOpen, setIsIcloudCleanupExecutionConfirmOpen] = useState(false);
  const [icloudCleanupExecutionAcknowledged, setIcloudCleanupExecutionAcknowledged] = useState(false);
  const [icloudCleanupExecutionPhrase, setIcloudCleanupExecutionPhrase] = useState("");
  const [icloudCleanupFreshnessNow, setIcloudCleanupFreshnessNow] = useState(() => Date.now());
  const [sourceIntakeStatus, setSourceIntakeStatus] = useState<SourceIntakeStatusSnapshot | null>(null);
  const [sourceIntakeReports, setSourceIntakeReports] = useState<SourceIntakeReportSummary[]>([]);
  const [isRunActionLoading, setIsRunActionLoading] = useState(false);
  const [runPreflightSourceId, setRunPreflightSourceId] = useState<number | null>(null);
  const [rowRunErrors, setRowRunErrors] = useState<Record<number, string>>({});
  const [runErrorDetails, setRunErrorDetails] = useState<string | null>(null);
  const [isRunConfirmOpen, setIsRunConfirmOpen] = useState(false);
  const [runCandidateProfile, setRunCandidateProfile] = useState<SourceProfileSummary | null>(null);
  const [runCandidateReadiness, setRunCandidateReadiness] = useState<SourceProfileReadinessResponse | null>(null);
  const [runReadinessAcknowledged, setRunReadinessAcknowledged] = useState(false);
  const [runLimitInput, setRunLimitInput] = useState("");
  const [runBatchSizeInput, setRunBatchSizeInput] = useState("500");
  const [runOptionsError, setRunOptionsError] = useState<string | null>(null);
  const [dismissedTerminalRunKey, setDismissedTerminalRunKey] = useState<string | null>(null);
  const [selectedReportFilename, setSelectedReportFilename] = useState<string | null>(null);
  const [selectedReportDetail, setSelectedReportDetail] = useState<SourceIntakeReportDetail | null>(null);
  const [isReportDetailLoading, setIsReportDetailLoading] = useState(false);
  const [reportDetailError, setReportDetailError] = useState<string | null>(null);
  const detailLoadRequestSeqRef = useRef(0);
  const sourceReadinessRequestSeqRef = useRef(0);

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

  const cleanupStatusForDetail = useMemo(() => {
    if (!detailProfile || !isIcloudProfile(detailProfile) || !icloudCleanupStatus) {
      return null;
    }

    if (icloudCleanupStatus.status === "idle") {
      return icloudCleanupStatus;
    }

    return icloudCleanupStatus.source_id === detailProfile.source_id ? icloudCleanupStatus : null;
  }, [detailProfile, icloudCleanupStatus]);

  const isIcloudCleanupActive = useMemo(
    () => (cleanupStatusForDetail ? ICLOUD_CLEANUP_ACTIVE_STATUSES.has(cleanupStatusForDetail.status) : false),
    [cleanupStatusForDetail],
  );

  const isIcloudCleanupTerminal = useMemo(
    () => (cleanupStatusForDetail ? ICLOUD_CLEANUP_TERMINAL_STATUSES.has(cleanupStatusForDetail.status) : false),
    [cleanupStatusForDetail],
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

  const loadIcloudCleanupStatus = useCallback(async (sourceId?: number) => {
    setIsLoadingIcloudCleanupStatus(true);
    setIcloudCleanupError(null);
    try {
      if (sourceId == null) {
        const response = await getIcloudStagingCleanupStatus();
        setIcloudCleanupStatus(response.current);
        setIcloudCleanupReadiness(null);
      } else {
        const [statusResponse, readinessResponse] = await Promise.all([
          getIcloudStagingCleanupStatus(sourceId),
          getIcloudStagingCleanupReadiness(sourceId),
        ]);
        setIcloudCleanupStatus(statusResponse.current);
        setIcloudCleanupReadiness(readinessResponse);
      }
    } catch (error) {
      setIcloudCleanupError(error instanceof Error ? error.message : "Failed to load iCloud cleanup status.");
    } finally {
      setIsLoadingIcloudCleanupStatus(false);
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
        response = await getSourceProfiles({ status: "all" });
      } catch (error) {
        if (!isTransientFetchError(error)) {
          throw error;
        }
        await delay(350);
        response = await getSourceProfiles({ status: "all" });
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
  }, []);

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
    if (!isDetailsOpen || !detailProfile || !isIcloudProfile(detailProfile) || !isIcloudCleanupActive) {
      return;
    }

    const timer = window.setInterval(() => {
      void loadIcloudCleanupStatus(detailProfile.source_id);
    }, ICLOUD_CLEANUP_POLL_MS);

    return () => window.clearInterval(timer);
  }, [detailProfile, isDetailsOpen, isIcloudCleanupActive, loadIcloudCleanupStatus]);

  useEffect(() => {
    const expiresAt = cleanupStatusForDetail?.preview_expires_at
      ? Date.parse(cleanupStatusForDetail.preview_expires_at)
      : Number.NaN;
    setIcloudCleanupFreshnessNow(Date.now());
    if (!Number.isFinite(expiresAt) || expiresAt <= Date.now()) {
      return;
    }
    const timer = window.setTimeout(
      () => setIcloudCleanupFreshnessNow(Date.now()),
      Math.min(expiresAt - Date.now() + 50, 2_147_000_000),
    );
    return () => window.clearTimeout(timer);
  }, [cleanupStatusForDetail?.preview_expires_at]);

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

  const registryProfiles = useMemo(() => {
    if (statusFilter === "all") {
      return profiles;
    }
    return profiles.filter((profile) => profile.profile_status === statusFilter);
  }, [profiles, statusFilter]);

  const countsSummary = useMemo(() => {
    const counts: Record<SourceProfileStatus, number> = {
      active: 0,
      inactive: 0,
      archived: 0,
      test: 0,
      deprecated: 0,
    };

    for (const profile of registryProfiles) {
      counts[profile.profile_status] += 1;
    }

    return {
      active: counts.active,
      nonActive: counts.archived + counts.test + counts.deprecated,
    };
  }, [registryProfiles]);

  const workbenchProfiles = useMemo(() => {
    return profiles.filter((profile) => {
      const operatorSourceType = getOperatorSourceType(profile);
      const isNonActive = profile.profile_status !== "active";
      const matchesSourceType = workbenchSourceType === "advanced"
        ? operatorSourceType === "advanced" || (showInactiveWorkbenchSources && isNonActive)
        : operatorSourceType === workbenchSourceType;

      if (!matchesSourceType) {
        return false;
      }
      if (!showInactiveWorkbenchSources && isNonActive) {
        return false;
      }
      return matchesSourceSearch(profile, workbenchSearch);
    });
  }, [profiles, showInactiveWorkbenchSources, workbenchSearch, workbenchSourceType]);

  const selectedWorkbenchProfile = useMemo(() => {
    if (selectedWorkbenchSourceId == null) {
      return null;
    }
    return workbenchProfiles.find((profile) => profile.source_id === selectedWorkbenchSourceId) ?? null;
  }, [selectedWorkbenchSourceId, workbenchProfiles]);

  useEffect(() => {
    if (
      selectedWorkbenchSourceId != null
      && workbenchProfiles.some((profile) => profile.source_id === selectedWorkbenchSourceId)
    ) {
      return;
    }
    setSelectedWorkbenchSourceId(workbenchProfiles[0]?.source_id ?? null);
  }, [selectedWorkbenchSourceId, workbenchProfiles]);

  const managedStagingPreview = useMemo(() => {
    return computeManagedStagingPreview(editorForm.sourceLabel);
  }, [editorForm.sourceLabel]);

  const editorSourceIdentitySupport = useMemo(() => (
    editorMode === "create"
      ? getCreateSourceIdentitySupport(editorForm.operatorSourceType)
      : getSourceIdentityEnrollmentSupport(editorForm.sourceType, editorForm.sourceRootPath)
  ), [editorForm.operatorSourceType, editorForm.sourceRootPath, editorForm.sourceType, editorMode]);

  const sourceIdentityConfirmDisabledReason = useMemo(() => {
    if (!sourceIdentityPlan) {
      return "Plan enrollment before confirming.";
    }
    if (sourceIdentityPlan.blockers.length > 0) {
      return "Resolve plan blockers before confirming.";
    }
    if (
      sourceIdentityPlan.plan_status !== "ready"
      && sourceIdentityPlan.plan_status !== "source_profile_already_linked"
      && sourceIdentityPlan.plan_status !== "needs_review"
    ) {
      return "The enrollment plan is not ready to confirm.";
    }
    if (sourceIdentityPlan.endpoint_action === "create_new_endpoint") {
      if (!sourceIdentityAlias.trim()) {
        return "Endpoint alias is required.";
      }
      if ((sourceIdentityPlan.proposed_alias ?? "") !== sourceIdentityAlias.trim()) {
        return "Run the plan again after changing the endpoint alias.";
      }
    }
    if (sourceIdentityPlan.endpoint_action === "link_existing_endpoint" && sourceIdentitySelectedEndpointId == null) {
      return "Select the existing endpoint before confirming.";
    }
    if (sourceIdentityPlan.required_confirmations.length > 0 && !sourceIdentityReviewAcknowledged) {
      return "Review acknowledgment is required.";
    }
    return null;
  }, [
    sourceIdentityAlias,
    sourceIdentityPlan,
    sourceIdentityReviewAcknowledged,
    sourceIdentitySelectedEndpointId,
  ]);

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
    setIsIcloudAcquisitionConfirmOpen(true);
    setIcloudAcquisitionUsernameForRun((prev) => prev ?? "");
    setIcloudAcquisitionRecentCountInput((prev) => prev || "25");
    setIcloudAcquisitionMode("standard");

    try {
      let detailWithUsername;
      try {
        detailWithUsername = await getSourceProfileDetail(detailSourceId, { includeUsername: true });
      } catch (error) {
        if (!isTransientFetchError(error)) {
          throw error;
        }
        await delay(350);
        detailWithUsername = await getSourceProfileDetail(detailSourceId, { includeUsername: true });
      }
      const username = (detailWithUsername.account_username || "").trim();
      if (!username) {
        setIcloudAcquisitionError("Account username is required before acquisition can run. Enter Apple ID username in the modal.");
        setIcloudAcquisitionUiState("confirm_open");
        return;
      }

      setIcloudAcquisitionUsernameForRun(username);
      setIcloudAcquisitionUiState("confirm_open");
    } catch (error) {
      setIcloudAcquisitionError(
        error instanceof Error
          ? `${error.message} Enter Apple ID username in the modal and try again.`
          : "Failed to load acquisition details. Enter Apple ID username in the modal and try again.",
      );
      setIcloudAcquisitionUiState("confirm_open");
    } finally {
      setIsLoadingIcloudAcquisitionDetails(false);
    }
  }, [detailProfile, detailSourceId, icloudAcquireDisabledReason]);

  const handleConfirmAcquireFromIcloud = useCallback(async () => {
    const username = (icloudAcquisitionUsernameForRun || "").trim();
    if (!detailProfile || !isIcloudProfile(detailProfile) || !username) {
      setIcloudAcquisitionError("Account username is required before acquisition can run.");
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
        username,
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

  const resetSourceIdentityEnrollmentState = useCallback(() => {
    setSourceIdentityEnrollRequested(false);
    setSourceIdentityAlias("");
    setSourceIdentityPhase("idle");
    setSourceIdentityCreatedProfile(null);
    setSourceIdentityPlan(null);
    setSourceIdentityConfirmResult(null);
    setSourceIdentityReviewAcknowledged(false);
    setSourceIdentitySelectedEndpointId(null);
    setSourceIdentityProbeRequest(null);
  }, []);

  const openCreateDrawer = useCallback(() => {
    setIsDetailsOpen(false);
    setEditorMode("create");
    setEditingProfile(null);
    setEditorError(null);
    setEditorForm(initialFormState());
    resetSourceIdentityEnrollmentState();
    setSourceIdentityEnrollRequested(true);
    setIsEditorOpen(true);
  }, [resetSourceIdentityEnrollmentState]);

  const openEditDrawer = useCallback((profile: SourceProfileSummary) => {
    setIsDetailsOpen(false);
    setEditorMode("edit");
    setEditingProfile(profile);
    setEditorError(null);
    resetSourceIdentityEnrollmentState();
    setEditorForm({
      sourceLabel: profile.source_label,
      operatorSourceType: getOperatorSourceType(profile),
      sourceType: profile.source_type,
      profileStatus: profile.profile_status,
      sourceRootPath: profile.source_root_path ?? "",
      cloudProvider: profile.cloud_provider ?? "icloud",
      accountUsername: profile.account_username ?? "",
      acquisitionMethod: profile.acquisition_method ?? "icloudpd",
      managedStagingPath: profile.managed_staging_path ?? "",
    });
    setIsEditorOpen(true);
  }, [resetSourceIdentityEnrollmentState]);

  const openDetailsDrawer = useCallback((profile: SourceProfileSummary) => {
    sourceReadinessRequestSeqRef.current += 1;
    setIsEditorOpen(false);
    setIsDetailsOpen(true);
    setDetailSourceId(profile.source_id);
    setDetailProfile(null);
    setDetailError(null);
    setDetailBanner(null);
    setPathCheckResult(null);
    setSourceReadinessResult(null);
    setSourceReadinessError(null);
    setIsCheckingSourceReadiness(false);
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
    setIcloudCleanupStatus(null);
    setIcloudCleanupReadiness(null);
    setIcloudCleanupUiState("idle");
    setIsIcloudCleanupConfirmOpen(false);
    setIcloudCleanupError(null);
    setIsIcloudCleanupExecutionConfirmOpen(false);
    setIcloudCleanupExecutionAcknowledged(false);
    setIcloudCleanupExecutionPhrase("");
    void loadDetail(profile.source_id);
    if (isIcloudProfile(profile)) {
      void loadIcloudReadiness(profile.source_id);
      void loadIcloudAcquisitionStatus();
      void loadIcloudCleanupStatus(profile.source_id);
    }
  }, [loadDetail, loadIcloudAcquisitionStatus, loadIcloudCleanupStatus, loadIcloudReadiness]);

  const closeEditor = useCallback(() => {
    setIsEditorOpen(false);
    setEditorError(null);
    resetSourceIdentityEnrollmentState();
  }, [resetSourceIdentityEnrollmentState]);

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
    setIcloudCleanupStatus(null);
    setIcloudCleanupReadiness(null);
    setIcloudCleanupUiState("idle");
    setIsIcloudCleanupConfirmOpen(false);
    setIcloudCleanupError(null);
    setIsIcloudCleanupExecutionConfirmOpen(false);
    setIcloudCleanupExecutionAcknowledged(false);
    setIcloudCleanupExecutionPhrase("");
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

  const handleCheckSourceReadiness = useCallback(async () => {
    if (!detailSourceId) {
      return;
    }
    const sourceId = detailSourceId;
    const requestSeq = sourceReadinessRequestSeqRef.current + 1;
    sourceReadinessRequestSeqRef.current = requestSeq;
    setIsCheckingSourceReadiness(true);
    setSourceReadinessError(null);
    try {
      const result = await checkSourceProfileReadiness(sourceId);
      if (sourceReadinessRequestSeqRef.current === requestSeq && result.source_profile_id === sourceId) {
        setSourceReadinessResult(result);
      }
    } catch (error) {
      if (sourceReadinessRequestSeqRef.current === requestSeq) {
        setSourceReadinessError(error instanceof Error ? error.message : "Failed to check Source Profile readiness.");
      }
    } finally {
      if (sourceReadinessRequestSeqRef.current === requestSeq) {
        setIsCheckingSourceReadiness(false);
      }
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

  const runSourceIdentityEnrollmentPlan = useCallback(async (
    profile: SourceProfileSummary,
    selectedExistingEndpointId: number | null = sourceIdentitySelectedEndpointId,
    probeRequestOverride: SourceIdentityProbeRequest | null = null,
  ): Promise<SourceIdentityPlanOutcome | null> => {
    const probeRequest = probeRequestOverride ?? buildSourceIdentityProbeRequest(profile);
    if (!probeRequest) {
      setEditorError("Source Identity Check is not available for this Source Profile.");
      return null;
    }

    setSourceIdentityProbeRequest(probeRequest);
    setSourceIdentityPhase("planning");
    setEditorError(null);
    setSourceIdentityPlan(null);
    setSourceIdentityConfirmResult(null);

    try {
      let plan = await planSourceEndpointEnrollment({
        source_profile_id: profile.source_id,
        probe_request: probeRequest,
        proposed_alias: sourceIdentityAlias.trim() || null,
        selected_existing_endpoint_id: selectedExistingEndpointId,
        operator_review_acknowledged: sourceIdentityReviewAcknowledged,
      });

      const strongMatches = plan.possible_matches.filter((match) => match.match_strength === "strong");
      const shouldAutoLink = (
        selectedExistingEndpointId == null
        && plan.durable_identity_status === "verified"
        && plan.blockers.length === 0
        && strongMatches.length === 1
      );

      if (shouldAutoLink) {
        const matchedEndpointId = strongMatches[0].source_endpoint_id;
        setSourceIdentitySelectedEndpointId(matchedEndpointId);
        setSourceIdentityReviewAcknowledged(true);
        plan = await planSourceEndpointEnrollment({
          source_profile_id: profile.source_id,
          probe_request: probeRequest,
          proposed_alias: sourceIdentityAlias.trim() || null,
          selected_existing_endpoint_id: matchedEndpointId,
          operator_review_acknowledged: true,
        });
        setSourceIdentityPlan(plan);

        if (
          plan.plan_status === "ready"
          && plan.endpoint_action === "link_existing_endpoint"
          && plan.durable_identity_status === "verified"
          && plan.blockers.length === 0
        ) {
          setSourceIdentityPhase("confirming");
          const response = await confirmSourceEndpointEnrollment({
            source_profile_id: profile.source_id,
            probe_request: probeRequest,
            plan_fingerprint: plan.plan_fingerprint,
            confirmed_alias: null,
            selected_existing_endpoint_id: matchedEndpointId,
            operator_confirmed: true,
            operator_review_acknowledged: true,
          });
          setSourceIdentityConfirmResult(response);
          setSourceIdentityPhase(response.enrollment_status === "completed" ? "complete" : "review");
          await loadProfiles({ refreshOnly: true });
          return { plan, autoLinked: response.enrollment_status === "completed" };
        }
      }

      setSourceIdentityPlan(plan);
      setSourceIdentityPhase("review");
      return { plan, autoLinked: false };
    } catch (error) {
      setSourceIdentityPhase("review");
      setEditorError(error instanceof Error ? error.message : "Failed to plan endpoint enrollment.");
      return null;
    }
  }, [loadProfiles, sourceIdentityAlias, sourceIdentityReviewAcknowledged, sourceIdentitySelectedEndpointId]);

  const confirmSourceIdentityEnrollment = useCallback(async () => {
    if (!sourceIdentityCreatedProfile || !sourceIdentityPlan) {
      setEditorError("Create and plan enrollment before confirming.");
      return;
    }

    const probeRequest = sourceIdentityProbeRequest ?? buildSourceIdentityProbeRequest(sourceIdentityCreatedProfile);
    if (!probeRequest) {
      setEditorError("Source Identity Check is not available for this Source Profile.");
      return;
    }

    const confirmedAlias = sourceIdentityAlias.trim();
    if (sourceIdentityPlan.endpoint_action === "create_new_endpoint" && !confirmedAlias) {
      setEditorError("Endpoint alias is required before confirming durable identity.");
      return;
    }

    if (sourceIdentityPlan.required_confirmations.length > 0 && !sourceIdentityReviewAcknowledged) {
      setEditorError("Review acknowledgment is required before confirming enrollment.");
      return;
    }

    if (sourceIdentityPlan.endpoint_action === "link_existing_endpoint" && sourceIdentitySelectedEndpointId == null) {
      setEditorError("Select the existing endpoint before confirming enrollment.");
      return;
    }

    setSourceIdentityPhase("confirming");
    setEditorError(null);
    setSourceIdentityConfirmResult(null);

    try {
      const response = await confirmSourceEndpointEnrollment({
        source_profile_id: sourceIdentityCreatedProfile.source_id,
        probe_request: probeRequest,
        plan_fingerprint: sourceIdentityPlan.plan_fingerprint,
        confirmed_alias: sourceIdentityPlan.endpoint_action === "create_new_endpoint" ? confirmedAlias : null,
        selected_existing_endpoint_id: sourceIdentitySelectedEndpointId,
        operator_confirmed: true,
        operator_review_acknowledged: sourceIdentityReviewAcknowledged || sourceIdentityPlan.required_confirmations.length === 0,
      });
      setSourceIdentityConfirmResult(response);
      setSourceIdentityPhase(response.enrollment_status === "completed" ? "complete" : "review");
      await loadProfiles({ refreshOnly: true });
      setBanner({
        kind: response.enrollment_status === "completed" ? "success" : "error",
        message: response.enrollment_status === "completed"
          ? "Endpoint enrolled. Source Intake behavior is unchanged."
          : response.blockers[0]?.message ?? "Endpoint enrollment did not complete.",
      });
    } catch (error) {
      setSourceIdentityPhase("review");
      setEditorError(error instanceof Error ? error.message : "Failed to confirm endpoint enrollment.");
    }
  }, [
    loadProfiles,
    sourceIdentityAlias,
    sourceIdentityCreatedProfile,
    sourceIdentityPlan,
    sourceIdentityProbeRequest,
    sourceIdentityReviewAcknowledged,
    sourceIdentitySelectedEndpointId,
  ]);

  const saveEditor = useCallback(async () => {
    setEditorError(null);
    const trimmedLabel = editorForm.sourceLabel.trim();

    if (editorMode === "create") {
      if (!trimmedLabel) {
        setEditorError("Source Name is required.");
        return;
      }

      if (editorForm.operatorSourceType === "removable") {
        setEditorError("Removable sources are coming later and cannot be created yet.");
        return;
      }

      if (!isIcloudCloudExport(editorForm) && !editorForm.sourceRootPath.trim()) {
        setEditorError("Source root path is required for this source type.");
        return;
      }

      if (isIcloudCloudExport(editorForm) && !editorForm.accountUsername.trim()) {
        setEditorError("Account username is required for iCloud sources.");
        return;
      }

      if (
        (editorForm.operatorSourceType === "local" || editorForm.operatorSourceType === "external")
        && isUncPath(editorForm.sourceRootPath)
      ) {
        setEditorError("This looks like a NAS path. Choose source type NAS.");
        return;
      }

      if (
        (editorForm.operatorSourceType === "local" || editorForm.operatorSourceType === "external")
        && !isDriveLetterPath(editorForm.sourceRootPath)
      ) {
        setEditorError("Enter an absolute Windows drive path, such as C:\\Photos.");
        return;
      }

      if (sourceIdentityEnrollRequested) {
        if (!editorSourceIdentitySupport.supported) {
          setEditorError(editorSourceIdentitySupport.reason ?? "Source Identity Check is not available for this source type.");
          return;
        }
        if (!sourceIdentityAlias.trim()) {
          setEditorError("Endpoint alias is required when recording a new durable source identity.");
          return;
        }
      }
    }

    setIsSavingEditor(true);
    try {
      if (editorMode === "create") {
        let sourceRootPath = editorForm.sourceRootPath.trim();
        const createProbeRequest = buildCreateSourceProbeRequest(
          editorForm.operatorSourceType,
          sourceRootPath,
        );
        const drivePathProbe = createProbeRequest && isDriveLetterPath(sourceRootPath)
          ? await probeSourceIdentity(createProbeRequest)
          : null;
        const mappedNetworkBlocker = drivePathProbe?.blockers.find(
          (item) => item.code === "mapped_network_path_requires_nas",
        );
        if (mappedNetworkBlocker) {
          setEditorError(mappedNetworkBlocker.message);
          return;
        }

        if (editorForm.operatorSourceType === "nas") {
          if (!isUncPath(sourceRootPath) && !isDriveLetterPath(sourceRootPath)) {
            setEditorError("Enter a UNC path or an existing mapped NAS drive path.");
            return;
          }
          if (!createProbeRequest) {
            setEditorError("Unable to check this NAS location.");
            return;
          }
          const probe = drivePathProbe ?? await probeSourceIdentity(createProbeRequest);
          const canonicalRoot = probe.source_root_candidate.path;
          const boundary = probe.source_root_candidate.filesystem_boundary_type;
          const resolutionBlocker = probe.blockers.find((item) => (
            item.code === "mapped_nas_unc_resolution_failed"
            || item.code === "nas_server_not_runnable"
          ));
          if (resolutionBlocker || !canonicalRoot || !isUncPath(canonicalRoot) || boundary === "nas_server_only" || boundary === "unknown") {
            setEditorError(
              resolutionBlocker?.message
              ?? probe.next_safe_actions[0]
              ?? "The NAS location could not be resolved to a UNC share and folder.",
            );
            return;
          }
          sourceRootPath = canonicalRoot;
        }

        const payload: SourceProfileCreateRequest = {
          source_label: trimmedLabel,
          source_type: editorForm.sourceType,
          profile_status: editorForm.profileStatus,
          source_root_path: isIcloudCloudExport(editorForm)
            ? null
            : sourceRootPath,
          cloud_provider: editorForm.sourceType === "cloud_export" ? editorForm.cloudProvider : null,
          account_username: editorForm.accountUsername.trim() || null,
          acquisition_method: editorForm.sourceType === "cloud_export" ? editorForm.acquisitionMethod : null,
          managed_staging_path: editorForm.sourceType === "cloud_export"
            ? (editorForm.managedStagingPath.trim() || managedStagingPreview)
            : null,
        };

        const response = await createSourceProfile(payload);
        await loadProfiles({ refreshOnly: true });
        setWorkbenchSourceType(editorForm.operatorSourceType);
        setSelectedWorkbenchSourceId(response.profile.source_id);
        if (sourceIdentityEnrollRequested) {
          setSourceIdentityCreatedProfile(response.profile);
          setSourceIdentityAlias((current) => current.trim() || response.profile.source_label);
          const planOutcome = await runSourceIdentityEnrollmentPlan(
            response.profile,
            null,
            createProbeRequest,
          );
          if (planOutcome?.autoLinked) {
            closeEditor();
            setBanner({
              kind: "success",
              message: response.already_exists
                ? `Source already exists and is linked: ${response.profile.source_label}`
                : `Source created and linked: ${response.profile.source_label}`,
            });
            return;
          }
          setBanner({
            kind: "success",
            message: response.already_exists
              ? `Source already exists: ${response.profile.source_label}`
              : `Source created: ${response.profile.source_label}. Review the identity result to finish enrollment.`,
          });
          return;
        }
        closeEditor();
        setBanner({
          kind: "success",
          message: response.already_exists
            ? `Source already exists: ${response.profile.source_label}`
            : `Source created: ${response.profile.source_label}`,
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
    editorSourceIdentitySupport,
    editorForm,
    editorMode,
    editingProfile,
    loadProfiles,
    managedStagingPreview,
    runSourceIdentityEnrollmentPlan,
    statusFilter,
    sourceIdentityAlias,
    sourceIdentityEnrollRequested,
  ]);

  const detailPathLabel = detailProfile && isIcloudProfile(detailProfile) ? "Staging status" : "Path status";
  const detailVerifyButtonLabel = detailProfile && isIcloudProfile(detailProfile) ? "Verify Staging" : "Verify Path";

  const isDetailIcloudProfile = detailProfile ? isIcloudProfile(detailProfile) : false;
  const isGuidedIcloudRunCandidate = runCandidateProfile ? isIcloudProfile(runCandidateProfile) : false;
  const runReadinessRequiresAcknowledgment = Boolean(
    runCandidateReadiness?.requires_operator_acknowledgment
      && (runCandidateReadiness.readiness_status === "path_only" || runCandidateReadiness.readiness_status === "needs_review"),
  );
  const canConfirmRunIntake = !isRunActionLoading && (!runReadinessRequiresAcknowledgment || runReadinessAcknowledged);

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

  const detailReadinessResult = detailSourceId != null && sourceReadinessResult?.source_profile_id === detailSourceId
    ? sourceReadinessResult
    : null;
  const selectedWorkbenchReadinessResult = selectedWorkbenchProfile && sourceReadinessResult?.source_profile_id === selectedWorkbenchProfile.source_id
    ? sourceReadinessResult
    : null;
  const sourceReadinessStatus = detailReadinessResult?.readiness_status ?? "unknown";
  const sourceReadinessBadgeClassName = sourceProfileReadinessBadgeClassName(sourceReadinessStatus);
  const sourceReadinessWarnings = detailReadinessResult?.warnings ?? [];
  const sourceReadinessBlockers = detailReadinessResult?.blockers ?? [];
  const sourceReadinessAdvancedDetails = useMemo(
    () => detailReadinessResult ? buildSourceReadinessAdvancedDetails(detailReadinessResult) : null,
    [detailReadinessResult],
  );

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

  const acquisitionStatusMatchesDetailProfile = useMemo(() => {
    if (!detailProfile || !icloudAcquisitionStatus) {
      return false;
    }

    return doesIcloudAcquisitionStatusMatchProfile(detailProfile, icloudAcquisitionStatus);
  }, [detailProfile, icloudAcquisitionStatus]);

  const icloudCleanupDryRunViewModel = useMemo(() => {
    if (!detailProfile || !isIcloudProfile(detailProfile)) {
      return null;
    }

    const hasRecentAcquisition = Boolean(latestAcquisitionForDetail);
    const hasSourceIntakeEvidence = Boolean(detailSourceIntakeStatus || latestSourceIntakeReportForDetail);
    const evidenceMessage = !hasRecentAcquisition || !hasSourceIntakeEvidence
      ? "Evidence is incomplete. The dry run will still inspect the managed staging folder and report what would be eligible, protected, or skipped."
      : "Ready to review staged cleanup candidates.";

    if (cleanupStatusForDetail && cleanupStatusForDetail.status !== "idle") {
      if (isIcloudCleanupActive) {
        return {
          statusLabel: cleanupStatusForDetail.dry_run ? "Dry run running" : "Cleanup running",
          badgeClassName: styles.readinessBadgeWarning,
          helperMessage: `${cleanupStatusForDetail.dry_run ? "Cleanup dry run" : "Verified cleanup"} is currently running for ${cleanupSourceLabel(cleanupStatusForDetail)}.`,
          buttonDisabledReason: "A cleanup operation is already active for this profile.",
        };
      }

      if (cleanupStatusForDetail.status === "failed") {
        return {
          statusLabel: "Dry run needs attention",
          badgeClassName: styles.readinessBadgeNotReady,
          helperMessage: cleanupStatusForDetail.error_message ?? "The most recent cleanup dry run failed.",
          buttonDisabledReason: null,
        };
      }

      if (isIcloudCleanupTerminal) {
        return {
          statusLabel: cleanupStatusForDetail.dry_run ? "Dry run complete" : "Cleanup complete",
          badgeClassName: styles.readinessBadgeReady,
          helperMessage: cleanupStatusForDetail.dry_run
            ? `Cleanup dry run completed for ${cleanupSourceLabel(cleanupStatusForDetail)}.`
            : `Cleanup run completed for ${cleanupSourceLabel(cleanupStatusForDetail)}.`,
          buttonDisabledReason: null,
        };
      }
    }

    if (!icloudCleanupReadiness) {
      return {
        statusLabel: "Blocked",
        badgeClassName: styles.readinessBadgeNotReady,
        helperMessage: "Cleanup readiness is unavailable. Refresh cleanup status before continuing.",
        buttonDisabledReason: "Cleanup readiness is unavailable.",
      };
    }

    if (icloudCleanupReadiness.readiness_status === "blocked") {
      const firstReason = icloudCleanupReadiness.blocking_reasons[0];
      const message = firstReason ? `${firstReason.code}: ${firstReason.message}` : "Cleanup readiness is blocked.";
      return {
        statusLabel: "Blocked",
        badgeClassName: styles.readinessBadgeNotReady,
        helperMessage: message,
        buttonDisabledReason: message,
      };
    }

    return {
      statusLabel: evidenceMessage === "Ready to review staged cleanup candidates." ? "Ready for dry run" : "Ready with warning",
      badgeClassName: evidenceMessage === "Ready to review staged cleanup candidates." ? styles.readinessBadgeReady : styles.readinessBadgeWarning,
      helperMessage: evidenceMessage,
      buttonDisabledReason: null,
    };
  }, [cleanupStatusForDetail, detailProfile, detailSourceIntakeStatus, icloudCleanupReadiness, isIcloudCleanupActive, isIcloudCleanupTerminal, latestAcquisitionForDetail, latestSourceIntakeReportForDetail]);

  const cleanupExecutionPreview = useMemo(() => {
    if (!cleanupStatusForDetail || cleanupStatusForDetail.status !== "completed" || !cleanupStatusForDetail.dry_run) {
      return null;
    }
    if (
      cleanupStatusForDetail.run_id == null
      || cleanupStatusForDetail.eligible_count <= 0
      || !cleanupStatusForDetail.manifest_fingerprint
      || cleanupStatusForDetail.authorization_consumed_at
      || !cleanupStatusForDetail.preview_expires_at
    ) {
      return null;
    }
    const expiresAt = Date.parse(cleanupStatusForDetail.preview_expires_at);
    if (!Number.isFinite(expiresAt) || expiresAt <= icloudCleanupFreshnessNow) {
      return null;
    }
    return cleanupStatusForDetail;
  }, [cleanupStatusForDetail, icloudCleanupFreshnessNow]);

  const overallIcloudWorkflowSummary = useMemo(() => {
    if (!detailProfile || !isIcloudProfile(detailProfile)) {
      return null;
    }

    if (cleanupStatusForDetail && cleanupStatusForDetail.status !== "idle") {
      if (isIcloudCleanupActive) {
        return {
          status: cleanupStatusForDetail.dry_run ? "Cleanup dry run running" : "Cleanup execution running",
          message: cleanupStatusForDetail.dry_run
            ? `Cleanup dry run is currently running for ${cleanupSourceLabel(cleanupStatusForDetail)}. No files will be deleted.`
            : `Verified local staging cleanup is running for ${cleanupSourceLabel(cleanupStatusForDetail)}.`,
        };
      }

      if (cleanupStatusForDetail.status === "failed") {
        return {
          status: "Cleanup dry run needs attention",
          message: cleanupStatusForDetail.error_message ?? "The most recent cleanup dry run failed. Review the cleanup status section for details.",
        };
      }

      if (isIcloudCleanupTerminal) {
        return {
          status: cleanupStatusForDetail.dry_run ? "Cleanup dry run complete" : "Cleanup execution complete",
          message: cleanupStatusForDetail.dry_run
            ? `Cleanup dry run completed for ${cleanupSourceLabel(cleanupStatusForDetail)}. Review eligible, skipped, and protected counts before execution.`
            : `Cleanup run finished for ${cleanupSourceLabel(cleanupStatusForDetail)}. Review deleted and protected/error counts.`,
        };
      }
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
  }, [cleanupStatusForDetail, detailProfile, detailSourceIntakeStatus, icloudReadinessSnapshot, isIcloudCleanupActive, isIcloudCleanupTerminal, latestAcquisitionForDetail, latestSourceIntakeReportForDetail]);

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
        loadIcloudCleanupStatus(detailSourceId),
        loadSourceIntakeStatus(),
        loadSourceIntakeReports(),
      ]);
    } catch (error) {
      setDetailBanner({
        kind: "error",
        message: error instanceof Error ? error.message : "Failed to refresh workflow summary.",
      });
    }
  }, [detailProfile, detailSourceId, loadIcloudAcquisitionStatus, loadIcloudCleanupStatus, loadIcloudReadiness, loadSourceIntakeReports, loadSourceIntakeStatus]);

  const closeIcloudCleanupConfirmation = useCallback(() => {
    setIsIcloudCleanupConfirmOpen(false);
    setIcloudCleanupUiState((prev) => (prev === "running" ? prev : "idle"));
  }, []);

  const handleOpenIcloudCleanupDryRunConfirmation = useCallback(() => {
    if (!detailProfile || !isDetailIcloudProfile) {
      return;
    }

    setIcloudCleanupError(null);

    if (isIcloudCleanupActive) {
      setDetailBanner({ kind: "error", message: "A cleanup dry run is already active for this profile." });
      return;
    }

    if (icloudCleanupDryRunViewModel?.buttonDisabledReason) {
      setDetailBanner({ kind: "error", message: icloudCleanupDryRunViewModel.buttonDisabledReason });
      return;
    }

    setIsIcloudCleanupConfirmOpen(true);
    setIcloudCleanupUiState("confirm_open");
  }, [detailProfile, icloudCleanupDryRunViewModel, isDetailIcloudProfile, isIcloudCleanupActive]);

  const handleConfirmIcloudCleanupDryRun = useCallback(async () => {
    if (!detailProfile || !isDetailIcloudProfile) {
      return;
    }

    setIsIcloudCleanupActionLoading(true);
    setIcloudCleanupError(null);
    setDetailBanner(null);
    setIcloudCleanupUiState("running");

    try {
      const response = await runIcloudStagingCleanupDryRun(detailProfile.source_id);
      setIcloudCleanupStatus(response.current);
      setIcloudCleanupUiState(ICLOUD_CLEANUP_TERMINAL_STATUSES.has(response.current.status) ? "terminal" : "running");
      setDetailBanner({ kind: "success", message: response.message });
      closeIcloudCleanupConfirmation();
      await handleRefreshIcloudWorkflowSummary();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to start iCloud cleanup dry run.";
      setIcloudCleanupError(message);
      setDetailBanner({ kind: "error", message });
      setIcloudCleanupUiState("idle");
    } finally {
      setIsIcloudCleanupActionLoading(false);
    }
  }, [closeIcloudCleanupConfirmation, detailProfile, handleRefreshIcloudWorkflowSummary, isDetailIcloudProfile]);

  const closeIcloudCleanupExecutionConfirmation = useCallback(() => {
    setIsIcloudCleanupExecutionConfirmOpen(false);
    setIcloudCleanupExecutionAcknowledged(false);
    setIcloudCleanupExecutionPhrase("");
  }, []);

  const handleOpenIcloudCleanupExecutionConfirmation = useCallback(() => {
    if (!detailProfile || !isDetailIcloudProfile || !cleanupExecutionPreview) {
      setDetailBanner({ kind: "error", message: "Run a fresh successful cleanup dry run before execution." });
      return;
    }
    setIcloudCleanupError(null);
    setIcloudCleanupExecutionAcknowledged(false);
    setIcloudCleanupExecutionPhrase("");
    setIsIcloudCleanupExecutionConfirmOpen(true);
  }, [cleanupExecutionPreview, detailProfile, isDetailIcloudProfile]);

  const handleConfirmIcloudCleanupExecution = useCallback(async () => {
    if (!detailProfile || !cleanupExecutionPreview?.run_id) {
      return;
    }
    if (!icloudCleanupExecutionAcknowledged || icloudCleanupExecutionPhrase !== ICLOUD_CLEANUP_CONFIRMATION_PHRASE) {
      setIcloudCleanupError("Acknowledge the local deletion and type the confirmation phrase exactly.");
      return;
    }

    setIsIcloudCleanupActionLoading(true);
    setIcloudCleanupError(null);
    setDetailBanner(null);
    setIcloudCleanupUiState("running");
    try {
      const response = await executeIcloudStagingCleanup({
        source_id: detailProfile.source_id,
        dry_run_run_id: cleanupExecutionPreview.run_id,
        explicit_confirmation: icloudCleanupExecutionPhrase,
      });
      setIcloudCleanupStatus(response.current);
      setDetailBanner({ kind: "success", message: response.message });
      closeIcloudCleanupExecutionConfirmation();
      await handleRefreshIcloudWorkflowSummary();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to start verified local staging cleanup.";
      setIcloudCleanupError(message);
      setDetailBanner({ kind: "error", message });
      setIcloudCleanupUiState("idle");
    } finally {
      setIsIcloudCleanupActionLoading(false);
    }
  }, [cleanupExecutionPreview, closeIcloudCleanupExecutionConfirmation, detailProfile, handleRefreshIcloudWorkflowSummary, icloudCleanupExecutionAcknowledged, icloudCleanupExecutionPhrase]);

  const closeRunConfirmation = useCallback(() => {
    setIsRunConfirmOpen(false);
    setRunCandidateProfile(null);
    setRunCandidateReadiness(null);
    setRunReadinessAcknowledged(false);
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
      const readiness = await checkSourceProfileReadiness(profile.source_id);
      if (detailSourceId === profile.source_id) {
        setSourceReadinessResult(readiness);
        setSourceReadinessError(null);
      }

      const isAllowedReadiness =
        readiness.readiness_status === "ready"
        || readiness.readiness_status === "path_only"
        || readiness.readiness_status === "needs_review";
      if (!isAllowedReadiness || !readiness.can_run_source_intake) {
        const message = sourceReadinessLaunchBlockMessage(readiness);
        setRowRunError(profile.source_id, message);
        setBanner({ kind: "error", message });
        return;
      }

      setRunCandidateProfile(profile);
      setRunCandidateReadiness(readiness);
      setRunReadinessAcknowledged(false);
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
  }, [clearRowRunError, detailSourceId, isSourceIntakeActive, setRowRunError]);

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
      setRunCandidateReadiness(null);
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

    if (runReadinessRequiresAcknowledgment && !runReadinessAcknowledged) {
      setRunOptionsError("Acknowledge the readiness warning before starting Source Intake.");
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
        readiness_acknowledged: runReadinessRequiresAcknowledgment && runReadinessAcknowledged,
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
      setRunOptionsError(mapped.message);
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
    runReadinessAcknowledged,
    runReadinessRequiresAcknowledgment,
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

      <section className={styles.workbenchPanel} aria-labelledby="create-source-title">
        <div className={styles.workbenchHeader}>
          <h3 id="create-source-title" className={styles.runPanelTitle}>Create Source</h3>
          <button
            type="button"
            className={styles.button}
            onClick={() => setIsCreateSourceExpanded((current) => !current)}
            aria-expanded={isCreateSourceExpanded}
          >
            {isCreateSourceExpanded ? "Collapse" : "Expand"}
          </button>
        </div>
        {isCreateSourceExpanded && (
          <div className={styles.rowActions}>
            <button type="button" className={styles.updateButton} onClick={openCreateDrawer}>
              Create Source
            </button>
          </div>
        )}
      </section>

      <section className={styles.workbenchPanel} aria-labelledby="source-selector-title">
        <div className={styles.workbenchHeader}>
          <div>
            <h3 id="source-selector-title" className={styles.runPanelTitle}>Source Selector</h3>
          </div>
          <div className={styles.rowActions}>
            <button
              type="button"
              className={styles.button}
              onClick={() => void loadProfiles({ refreshOnly: true, clearRowErrors: true })}
              disabled={isLoading || isRefreshing}
            >
              {isRefreshing ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </div>

        <div className={styles.workbenchControls}>
          <div className={styles.workbenchControlGroup}>
            <span className={styles.detailLabel}>Source Type</span>
            <div className={styles.segmentedControl} role="group" aria-label="Source type">
              {OPERATOR_SOURCE_TYPE_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className={`${styles.segmentButton} ${workbenchSourceType === option.value ? styles.segmentButtonActive : ""}`}
                  onClick={() => setWorkbenchSourceType(option.value)}
                  aria-pressed={workbenchSourceType === option.value}
                  disabled={option.disabled}
                  title={option.disabled ? "Coming later" : undefined}
                >
                  {option.label}{option.disabled ? " - coming later" : ""}
                </button>
              ))}
            </div>
          </div>

          <label className={styles.formLabel}>
            Search Sources
            <input
              className={styles.formInput}
              value={workbenchSearch}
              onChange={(event) => setWorkbenchSearch(event.target.value)}
              placeholder="Search label, path, provider, or masked account"
            />
          </label>

          <label className={styles.formLabel}>
            Source
            <select
              className={styles.formInput}
              value={selectedWorkbenchSourceId ?? ""}
              onChange={(event) => setSelectedWorkbenchSourceId(event.target.value ? Number(event.target.value) : null)}
              disabled={workbenchProfiles.length === 0}
            >
              {workbenchProfiles.length === 0 ? (
                <option value="">No matching sources</option>
              ) : (
                workbenchProfiles.map((profile) => (
                  <option key={profile.source_id} value={profile.source_id}>
                    {profile.source_label} - {getSourcePathOrProviderHint(profile)}
                  </option>
                ))
              )}
            </select>
          </label>

          <label className={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={showInactiveWorkbenchSources}
              onChange={(event) => setShowInactiveWorkbenchSources(event.target.checked)}
            />
            Show inactive / legacy sources
          </label>
        </div>

        {workbenchProfiles.length === 0 ? (
          <p className={styles.empty}>
            No {showInactiveWorkbenchSources ? "" : "active "}
            {getOperatorSourceTypeLabel(workbenchSourceType)} sources found. Create a Source, adjust search, or show inactive / legacy sources.
          </p>
        ) : selectedWorkbenchProfile ? (
          <div className={styles.workbenchSummary}>
            <div className={styles.workbenchSummaryHeader}>
              <div className={styles.labelCell}>
                <span>{selectedWorkbenchProfile.source_label}</span>
                <span className={styles.statusBadge}>{selectedWorkbenchProfile.profile_status}</span>
              </div>
              <div className={styles.rowActions}>
                <button type="button" className={styles.updateButton} onClick={() => openDetailsDrawer(selectedWorkbenchProfile)}>
                  Details
                </button>
                <button type="button" className={styles.updateButton} onClick={() => openEditDrawer(selectedWorkbenchProfile)}>
                  Manage
                </button>
              </div>
            </div>

            <div className={styles.detailGrid}>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Type</span>
                <span>{getOperatorSourceTypeLabel(getOperatorSourceType(selectedWorkbenchProfile))}</span>
                <span className={styles.detailMeta}>Stored type: {selectedWorkbenchProfile.source_type}</span>
              </div>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Path / Provider</span>
                <span>{getSourcePathOrProviderHint(selectedWorkbenchProfile)}</span>
                {selectedWorkbenchProfile.cloud_provider && (
                  <span className={styles.detailMeta}>Provider: {formatSourceProvider(selectedWorkbenchProfile.cloud_provider)}</span>
                )}
              </div>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Durable Identity</span>
                <span className={getSourceIdentityBadgeClassName(selectedWorkbenchProfile, selectedWorkbenchReadinessResult)}>
                  {getSourceIdentityDisplay(selectedWorkbenchProfile, selectedWorkbenchReadinessResult)}
                </span>
                <span className={styles.detailMeta}>
                  {getSourceIdentityMeta(selectedWorkbenchProfile, selectedWorkbenchReadinessResult)}
                </span>
              </div>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Readiness</span>
                <span>
                  {selectedWorkbenchReadinessResult
                    ? toSourceProfileReadinessLabel(selectedWorkbenchReadinessResult.readiness_status)
                    : "Not checked in this view"}
                </span>
                <span className={styles.detailMeta}>
                  {selectedWorkbenchReadinessResult?.operator_message ?? "Open Details to run the manual readiness check."}
                </span>
              </div>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Workflow</span>
                <span>{getSourceWorkflowDisplay(selectedWorkbenchProfile)}</span>
                <span className={styles.detailMeta}>{getSourceWorkflowPlaceholder(selectedWorkbenchProfile)}</span>
              </div>
            </div>
          </div>
        ) : null}
      </section>

      <IcloudRunWorkflowPanel />

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
        <p className={styles.empty}>No source profiles found.</p>
      ) : registryProfiles.length === 0 ? (
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
              {registryProfiles.map((profile) => {
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
                  {editorMode === "create" ? "Create Source" : "Manage Source Status"}
                </h3>
                <p className={styles.drawerSubtitle}>
                  {editorMode === "create"
                    ? "Create a source without starting ingestion."
                    : "Manage lifecycle status while preserving historical source identity."}
                </p>
              </div>
              <button
                type="button"
                className={styles.closeButton}
                onClick={closeEditor}
                disabled={isSavingEditor || sourceIdentityPhase === "planning" || sourceIdentityPhase === "confirming"}
              >
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
                Source Name
                {editorMode === "create" ? (
                  <input
                    className={styles.formInput}
                    autoComplete="off"
                    value={editorForm.sourceLabel}
                    disabled={sourceIdentityPhase !== "idle"}
                    onChange={(event) => {
                      const nextLabel = event.target.value;
                      const previousLabel = editorForm.sourceLabel.trim();
                      setEditorForm((prev) => ({ ...prev, sourceLabel: nextLabel }));
                      if (sourceIdentityEnrollRequested) {
                        setSourceIdentityAlias((prevAlias) => {
                          const trimmedAlias = prevAlias.trim();
                          if (!trimmedAlias || trimmedAlias === previousLabel) {
                            return nextLabel.trim();
                          }
                          return prevAlias;
                        });
                      }
                    }}
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
                    value={editorForm.operatorSourceType}
                    disabled={sourceIdentityPhase !== "idle"}
                    onChange={(event) => {
                      const operatorSourceType = event.target.value as OperatorSourceType;
                      const sourceType = persistedSourceTypeForOperator(operatorSourceType);
                      resetSourceIdentityEnrollmentState();
                      setSourceIdentityEnrollRequested(probeSourceTypeForOperator(operatorSourceType) != null);
                      setEditorForm((prev) => ({
                        ...prev,
                        operatorSourceType,
                        sourceType,
                        cloudProvider: operatorSourceType === "icloud" ? "icloud" : prev.cloudProvider,
                        acquisitionMethod: operatorSourceType === "icloud" ? "icloudpd" : prev.acquisitionMethod,
                      }));
                    }}
                  >
                    {OPERATOR_SOURCE_TYPE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value} disabled={option.disabled}>
                        {option.label}{option.disabled ? " - coming later" : ""}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    className={`${styles.formInput} ${styles.readOnlyInput}`}
                    value={getOperatorSourceTypeLabel(editorForm.operatorSourceType)}
                    readOnly
                  />
                )}
              </label>

              {editorMode === "create" && editorForm.operatorSourceType === "advanced" && (
                <label className={styles.formLabel}>
                  Legacy Type
                  <select
                    className={styles.formInput}
                    value={editorForm.sourceType}
                    disabled={sourceIdentityPhase !== "idle"}
                    onChange={(event) => {
                      const sourceType = event.target.value as SourceProfileType;
                      setEditorForm((prev) => ({
                        ...prev,
                        sourceType,
                        cloudProvider: sourceType === "cloud_export" ? "other" : prev.cloudProvider,
                      }));
                    }}
                  >
                    {ADVANCED_SOURCE_TYPE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </label>
              )}

              {editorMode === "edit" && (
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
                      <option key={statusValue} value={statusValue}>{statusValue}</option>
                    ))}
                  </select>
                </label>
              )}

              {!isIcloudCloudExport(editorForm) && (
                <label className={styles.formLabel}>
                  Location / Root Path
                  {editorMode === "create" ? (
                    <input
                      className={styles.formInput}
                      autoComplete="off"
                      value={editorForm.sourceRootPath}
                      disabled={sourceIdentityPhase !== "idle"}
                      onChange={(event) => setEditorForm((prev) => ({
                        ...prev,
                        sourceRootPath: event.target.value,
                      }))}
                      onBlur={() => {
                        setSourceIdentityPlan(null);
                        setSourceIdentityConfirmResult(null);
                        setSourceIdentityPhase("idle");
                        setSourceIdentitySelectedEndpointId(null);
                        setSourceIdentityReviewAcknowledged(false);
                        setSourceIdentityProbeRequest(null);
                        if (!editorForm.sourceLabel.trim()) {
                          const suggestion = suggestSourceName(editorForm.operatorSourceType, editorForm.sourceRootPath);
                          if (suggestion) {
                            setEditorForm((prev) => ({ ...prev, sourceLabel: suggestion }));
                            setSourceIdentityAlias(suggestion);
                          }
                        }
                      }}
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
                        disabled={sourceIdentityPhase !== "idle"}
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
                        disabled={sourceIdentityPhase !== "idle"}
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
                        disabled={sourceIdentityPhase !== "idle"}
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
                        disabled={sourceIdentityPhase !== "idle"}
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

            {editorMode === "create" && (
              <section className={styles.detailSection}>
                <h4 className={styles.detailHeading}>Source Identity</h4>
                {editorSourceIdentitySupport.supported ? (
                  <>
                    <p className={styles.helperText}>{editorSourceIdentitySupport.note}</p>
                    <details className={styles.advancedDetails}>
                      <summary>Advanced Details</summary>
                      <div className={styles.advancedDetailsText}>
                        <label className={styles.formLabel}>
                          Endpoint Alias
                          <input
                            className={styles.formInput}
                            value={sourceIdentityAlias}
                            disabled={sourceIdentityPhase === "planning" || sourceIdentityPhase === "confirming" || sourceIdentityPhase === "complete"}
                            onChange={(event) => setSourceIdentityAlias(event.target.value)}
                            placeholder={editorForm.sourceLabel.trim() || "Chuck PC Pictures"}
                          />
                        </label>
                      </div>
                    </details>
                  </>
                ) : (
                  <p className={styles.helperText}>{editorSourceIdentitySupport.reason}</p>
                )}

                {sourceIdentityPhase === "planning" && (
                  <p className={styles.note}>Creating source and checking durable identity...</p>
                )}

                {sourceIdentityPlan && (
                  <div className={styles.readOnlyBlock}>
                    <div className={styles.runPanelHeader}>
                      <div>
                        <h5 className={styles.runOptionsTitle}>Enrollment Plan</h5>
                        <p className={styles.runOptionsSummary}>
                          {formatEnrollmentPlanStatus(sourceIdentityPlan)} | {formatEnrollmentAction(sourceIdentityPlan.endpoint_action)}
                        </p>
                      </div>
                      <span className={styles.statusBadge}>{formatEnrollmentPlanStatus(sourceIdentityPlan)}</span>
                    </div>

                    <div className={styles.detailGrid}>
                      <div className={styles.detailCard}>
                        <span className={styles.detailLabel}>Source Root</span>
                        <span>{sourceIdentityPlan.candidate?.source_root_candidate_path ?? "-"}</span>
                      </div>
                      <div className={styles.detailCard}>
                        <span className={styles.detailLabel}>Durable Identity</span>
                        <span className={durableIdentityBadgeClassName(sourceIdentityPlan.durable_identity_status)}>
                          {toDurableIdentityLabel(sourceIdentityPlan.durable_identity_status)}
                        </span>
                        <span className={styles.detailMeta}>
                          {sourceIdentityPlan.durable_identity_reason ?? "Durable identity was not checked."}
                        </span>
                      </div>
                      <div className={styles.detailCard}>
                        <span className={styles.detailLabel}>Identifier Type</span>
                        <span>{sourceIdentityPlan.durable_identity_identifier_type ?? "-"}</span>
                      </div>
                      <div className={styles.detailCard}>
                        <span className={styles.detailLabel}>Identifier</span>
                        <span>{sourceIdentityPlan.durable_identity_identifier ?? "-"}</span>
                      </div>
                    </div>

                    {sourceIdentityPlan.candidate?.source_type === "nas" && (
                      <p className={styles.helperText}>
                        NAS endpoint identity is server + share. The full configured folder remains this Source Profile root.
                      </p>
                    )}

                    {sourceIdentityPlan.possible_matches.length > 0 && (
                      <label className={styles.formLabel}>
                        {sourceIdentityPlan.candidate?.source_type === "nas"
                          ? "Existing NAS Share"
                          : "Existing Durable Identity"}
                        <select
                          className={styles.formInput}
                          value={sourceIdentitySelectedEndpointId ?? ""}
                          onChange={(event) => {
                            const parsed = Number(event.target.value);
                            setSourceIdentitySelectedEndpointId(Number.isFinite(parsed) && parsed > 0 ? parsed : null);
                          }}
                        >
                          <option value="">Select endpoint...</option>
                          {sourceIdentityPlan.possible_matches.map((match) => (
                            <option key={match.source_endpoint_id} value={match.source_endpoint_id}>
                              {match.alias} ({match.match_strength})
                            </option>
                          ))}
                        </select>
                        <button
                          type="button"
                          className={styles.button}
                          disabled={!sourceIdentityCreatedProfile || sourceIdentitySelectedEndpointId == null || sourceIdentityPhase === "planning"}
                          onClick={() => {
                            if (sourceIdentityCreatedProfile) {
                              void runSourceIdentityEnrollmentPlan(sourceIdentityCreatedProfile, sourceIdentitySelectedEndpointId);
                            }
                          }}
                        >
                          Review Selected Identity
                        </button>
                      </label>
                    )}

                    {sourceIdentityPlan.blockers.length > 0 && (
                      <div className={styles.warningList}>
                        {sourceIdentityPlan.blockers.map((blocker) => (
                          <p className={styles.bannerError} key={blocker.code}>
                            {blocker.code}: {blocker.message}
                          </p>
                        ))}
                      </div>
                    )}

                    {sourceIdentityPlan.warnings.length > 0 && (
                      <div className={styles.warningList}>
                        {sourceIdentityPlan.warnings.map((warning) => (
                          <p className={styles.inlineWarning} key={warning.code}>
                            {warning.code}: {warning.message}
                          </p>
                        ))}
                      </div>
                    )}

                    {sourceIdentityPlan.required_confirmations.length > 0 && (
                      <>
                        <div className={styles.warningList}>
                          {sourceIdentityPlan.required_confirmations.map((confirmation) => (
                            <p className={styles.inlineWarning} key={confirmation.code}>
                              {confirmation.code}: {confirmation.message}
                            </p>
                          ))}
                        </div>
                        <label className={styles.checkboxLabel}>
                          <input
                            type="checkbox"
                            checked={sourceIdentityReviewAcknowledged}
                            onChange={(event) => setSourceIdentityReviewAcknowledged(event.target.checked)}
                          />
                          I reviewed the warnings and want to enroll this source endpoint.
                        </label>
                      </>
                    )}

                    {sourceIdentityConfirmResult && (
                      <p className={sourceIdentityConfirmResult.enrollment_status === "completed" ? styles.bannerSuccess : styles.bannerError}>
                        {sourceIdentityConfirmResult.enrollment_status === "completed"
                          ? `Endpoint enrolled. Durable identity: ${toDurableIdentityLabel(sourceIdentityConfirmResult.durable_identity_status)}. Source Intake behavior is unchanged.`
                          : sourceIdentityConfirmResult.blockers[0]?.message ?? "Endpoint enrollment did not complete."}
                      </p>
                    )}

                    {sourceIdentityConfirmResult?.blockers.length ? (
                      <div className={styles.warningList}>
                        {sourceIdentityConfirmResult.blockers.map((blocker) => (
                          <p className={styles.bannerError} key={`confirm-blocker:${blocker.code}`}>
                            {blocker.code}: {blocker.message}
                          </p>
                        ))}
                      </div>
                    ) : null}

                    {sourceIdentityConfirmResult?.warnings.length ? (
                      <div className={styles.warningList}>
                        {sourceIdentityConfirmResult.warnings.map((warning) => (
                          <p className={styles.inlineWarning} key={`confirm-warning:${warning.code}`}>
                            {warning.code}: {warning.message}
                          </p>
                        ))}
                      </div>
                    ) : null}

                    <details className={styles.errorDetails}>
                      <summary>Advanced Details</summary>
                      <p className={styles.errorDetailsText}>
                        Plan fingerprint: {sourceIdentityPlan.plan_fingerprint}
                        {"\n"}Candidate type: {sourceIdentityPlan.candidate?.source_type ?? "-"}
                        {"\n"}Boundary: {sourceIdentityPlan.candidate?.filesystem_boundary_type ?? "-"}
                        {"\n"}Observed access path: {sourceIdentityPlan.candidate?.observed_path ?? "-"}
                        {"\n"}Endpoint alias: {sourceIdentityPlan.proposed_alias ?? (sourceIdentityAlias.trim() || "-")}
                        {"\n"}Normalized alias: {sourceIdentityPlan.alias_normalized ?? "-"}
                        {"\n"}Provider: {sourceIdentityPlan.candidate?.provider_name ?? "-"} {sourceIdentityPlan.candidate?.provider_version ?? ""}
                        {"\n"}Identity confidence: {sourceIdentityPlan.candidate?.confidence_tier ?? "-"}
                        {"\n"}Fingerprint evidence: {sourceIdentityPlan.candidate?.identity_fingerprint_strength ?? "-"}
                        {"\n"}Durable identity evidence: {sourceIdentityPlan.durable_identity_evidence.join(" | ") || "-"}
                        {"\n"}Possible endpoint IDs: {sourceIdentityPlan.possible_matches.map((match) => match.source_endpoint_id).join(", ") || "-"}
                        {"\n"}Blocker codes: {sourceIdentityPlan.blockers.map((item) => item.code).join(", ") || "-"}
                        {"\n"}Warning codes: {sourceIdentityPlan.warnings.map((item) => item.code).join(", ") || "-"}
                      </p>
                    </details>

                    <div className={styles.drawerActions}>
                      {sourceIdentityConfirmDisabledReason && sourceIdentityPhase !== "complete" && (
                        <span className={styles.disabledReason}>{sourceIdentityConfirmDisabledReason}</span>
                      )}
                      <button
                        type="button"
                        className={styles.button}
                        disabled={!sourceIdentityCreatedProfile || sourceIdentityPhase === "planning" || sourceIdentityPhase === "confirming" || sourceIdentityPhase === "complete"}
                        onClick={() => {
                          if (sourceIdentityCreatedProfile) {
                            void runSourceIdentityEnrollmentPlan(sourceIdentityCreatedProfile, sourceIdentitySelectedEndpointId);
                          }
                        }}
                      >
                        Refresh Plan
                      </button>
                      <button
                        type="button"
                        className={styles.updateButton}
                        disabled={Boolean(sourceIdentityConfirmDisabledReason) || sourceIdentityPhase === "confirming" || sourceIdentityPhase === "complete"}
                        onClick={() => void confirmSourceIdentityEnrollment()}
                      >
                        {sourceIdentityPhase === "confirming" ? "Confirming..." : "Confirm Enrollment"}
                      </button>
                      {sourceIdentityPhase === "complete" && (
                        <button type="button" className={styles.button} onClick={closeEditor}>
                          Done
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </section>
            )}

            {editorError && <p className={styles.bannerError}>{editorError}</p>}

            <div className={styles.drawerActions}>
              <button
                type="button"
                className={styles.updateButton}
                onClick={() => void saveEditor()}
                disabled={isSavingEditor || sourceIdentityPhase !== "idle"}
              >
                {isSavingEditor || sourceIdentityPhase === "planning"
                  ? "Saving..."
                  : editorMode === "create"
                    ? "Create Source"
                    : "Save Status"}
              </button>
              <button
                type="button"
                className={styles.button}
                onClick={closeEditor}
                disabled={isSavingEditor || sourceIdentityPhase === "planning" || sourceIdentityPhase === "confirming"}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {isRunConfirmOpen && runCandidateProfile && runCandidateReadiness && (
        <div className={styles.modalBackdrop} role="dialog" aria-modal="true">
          <div className={styles.modalPanel}>
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
                <span>{sourceReadinessObservedPath(runCandidateReadiness, runCandidateProfile.source_root_path)}</span>
              </div>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Profile Status</span>
                <span>{runCandidateProfile.profile_status}</span>
              </div>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Readiness Result</span>
                <span className={`${styles.readinessBadge} ${sourceProfileReadinessBadgeClassName(runCandidateReadiness.readiness_status)}`}>
                  {toSourceProfileReadinessLabel(runCandidateReadiness.readiness_status)}
                </span>
                <span className={styles.detailMeta}>Identity match: {toStatusLabel(runCandidateReadiness.identity_match_status)}</span>
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

            {runReadinessRequiresAcknowledgment && (
              <section className={styles.runOptionsBlock}>
                <h4 className={styles.runOptionsTitle}>Readiness Acknowledgment</h4>
                <p className={styles.inlineWarning}>
                  {runCandidateReadiness.readiness_status === "path_only"
                    ? "Path-only source. This can run, but durable source identity enrollment is recommended."
                    : "This source needs review before relying on durable source identity. You may run Source Intake after acknowledging this warning."}
                </p>
                <p className={styles.helperText}>{runCandidateReadiness.operator_message}</p>
                <label className={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={runReadinessAcknowledged}
                    onChange={(event) => setRunReadinessAcknowledged(event.target.checked)}
                    disabled={isRunActionLoading}
                  />
                  I reviewed this readiness warning and want to run Source Intake for this source now.
                </label>
              </section>
            )}

            <div className={styles.drawerActions}>
              <button
                type="button"
                className={styles.runButton}
                onClick={() => void handleConfirmRunIntake()}
                disabled={!canConfirmRunIntake}
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
        <div className={styles.modalBackdrop} role="dialog" aria-modal="true">
          <div className={styles.modalPanel}>
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
                <label className={styles.formLabel}>
                  Apple ID Username
                  <input
                    className={styles.formInput}
                    type="text"
                    value={icloudAcquisitionUsernameForRun ?? ""}
                    onChange={(event) => setIcloudAcquisitionUsernameForRun(event.target.value)}
                    placeholder="name@example.com"
                  />
                  <span className={styles.formHint}>Used for icloudpd launch. Password/2FA are not stored here.</span>
                </label>
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
                    Standard downloads the requested recent items. List-first/non-repeat checks only the requested recent window.
                    It skips downloading only when every listed candidate is already known; mixed windows download the full window.
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
                disabled={isIcloudAcquisitionActionLoading || !(icloudAcquisitionUsernameForRun || "").trim()}
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

      {isIcloudCleanupConfirmOpen && detailProfile && isDetailIcloudProfile && (
        <div className={styles.modalBackdrop} role="dialog" aria-modal="true">
          <div className={styles.modalPanel}>
            <div className={styles.drawerHeader}>
              <div>
                <h3 className={styles.drawerTitle}>Confirm iCloud Cleanup Dry Run</h3>
                <p className={styles.drawerSubtitle}>
                  Review the source context before starting a dry run. This will not delete any files.
                </p>
              </div>
              <button
                type="button"
                className={styles.closeButton}
                onClick={closeIcloudCleanupConfirmation}
                disabled={isIcloudCleanupActionLoading}
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
                <span className={styles.detailLabel}>Managed Staging Path</span>
                <span>{detailProfile.managed_staging_path ?? "-"}</span>
              </div>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Dry Run Mode</span>
                <span className={`${styles.readinessBadge} ${styles.readinessBadgeReady}`}>Enabled</span>
                <span className={styles.detailMeta}>No file deletion will occur from the Ingestion tab.</span>
              </div>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Latest Acquisition Summary</span>
                {latestAcquisitionForDetail ? (
                  <>
                    <span>{toStatusLabel(latestAcquisitionForDetail.status ?? "unknown")}</span>
                    <span className={styles.detailMeta}>Started: {toDisplayDate(latestAcquisitionForDetail.started_at)}</span>
                    <span className={styles.detailMeta}>Finished: {toDisplayDate(latestAcquisitionForDetail.finished_at)}</span>
                    <span className={styles.detailMeta}>Downloaded: {latestAcquisitionForDetail.downloaded_count ?? "-"}</span>
                    <span className={styles.detailMeta}>Skipped: {latestAcquisitionForDetail.skipped_count ?? "-"}</span>
                    <span className={styles.detailMeta}>Report: {latestAcquisitionForDetail.report_path ?? "-"}</span>
                  </>
                ) : (
                  <span className={styles.detailMeta}>No cached acquisition summary available for this profile.</span>
                )}
              </div>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Latest Source Intake Summary</span>
                {detailSourceIntakeStatus ? (
                  <>
                    <span>{toStatusLabel(detailSourceIntakeStatus.status)}</span>
                    <span className={styles.detailMeta}>Started: {toDisplayDate(detailSourceIntakeStatus.started_at)}</span>
                    <span className={styles.detailMeta}>Finished: {toDisplayDate(detailSourceIntakeStatus.finished_at)}</span>
                    <span className={styles.detailMeta}>Selected: {detailSourceIntakeStatus.selected}</span>
                    <span className={styles.detailMeta}>Staged: {detailSourceIntakeStatus.staged}</span>
                    <span className={styles.detailMeta}>Report: {detailSourceIntakeStatus.report_path ?? "-"}</span>
                  </>
                ) : latestSourceIntakeReportForDetail ? (
                  <>
                    <span>Reported</span>
                    <span className={styles.detailMeta}>Generated: {toDisplayDate(latestSourceIntakeReportForDetail.generated_at_utc)}</span>
                    <span className={styles.detailMeta}>Selected: {latestSourceIntakeReportForDetail.counts?.selected_for_session ?? "-"}</span>
                    <span className={styles.detailMeta}>Staged: {latestSourceIntakeReportForDetail.counts?.staged_to_dropzone ?? "-"}</span>
                    <span className={styles.detailMeta}>Report: {latestSourceIntakeReportForDetail.report_filename}</span>
                  </>
                ) : (
                  <span className={styles.detailMeta}>No cached Source Intake summary available for this profile.</span>
                )}
              </div>
            </div>

            {icloudCleanupError && <p className={styles.bannerError}>{icloudCleanupError}</p>}

            <p className={styles.note}>
              This is a dry run only. It reports eligible, skipped, and protected items for the selected iCloud staging folder and does not delete files.
            </p>

            <div className={styles.drawerActions}>
              <button
                type="button"
                className={styles.runButton}
                onClick={() => void handleConfirmIcloudCleanupDryRun()}
                disabled={Boolean(icloudCleanupDryRunViewModel?.buttonDisabledReason) || isIcloudCleanupActionLoading}
              >
                {isIcloudCleanupActionLoading ? "Starting..." : "Run Cleanup Dry Run"}
              </button>
              <button type="button" className={styles.button} onClick={closeIcloudCleanupConfirmation} disabled={isIcloudCleanupActionLoading}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {isIcloudCleanupExecutionConfirmOpen && detailProfile && cleanupExecutionPreview && (
        <div className={styles.modalBackdrop} role="dialog" aria-modal="true">
          <div className={styles.modalPanel}>
            <div className={styles.drawerHeader}>
              <div>
                <h3 className={styles.drawerTitle}>Confirm Local iCloud Staging Cleanup</h3>
                <p className={styles.drawerSubtitle}>
                  This removes only the verified local staging copies shown by dry run #{cleanupExecutionPreview.run_id}.
                </p>
              </div>
              <button type="button" className={styles.closeButton} onClick={closeIcloudCleanupExecutionConfirmation} disabled={isIcloudCleanupActionLoading}>
                Close
              </button>
            </div>

            <div className={styles.detailGrid}>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Source Profile</span>
                <span>{detailProfile.source_label}</span>
                <span className={styles.detailMeta}>Source ID: {detailProfile.source_id}</span>
              </div>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Canonical Local Staging Path</span>
                <span>{icloudCleanupReadiness?.canonical_staging_path ?? cleanupExecutionPreview.source_root_path ?? "-"}</span>
              </div>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Approved Dry Run</span>
                <span>Run #{cleanupExecutionPreview.run_id}</span>
                <span className={styles.detailMeta}>Finished: {toDisplayDate(cleanupExecutionPreview.finished_at)}</span>
                <span className={styles.detailMeta}>Expires: {toDisplayDate(cleanupExecutionPreview.preview_expires_at)}</span>
                <span className={styles.detailMeta}>Report: {cleanupExecutionPreview.report_path ?? "-"}</span>
              </div>
              <div className={styles.detailCard}>
                <span className={styles.detailLabel}>Verified Impact</span>
                <span>{cleanupExecutionPreview.eligible_count} local files ({cleanupExecutionPreview.total_bytes_eligible} bytes)</span>
                <span className={styles.detailMeta}>Skipped / protected: {cleanupExecutionPreview.skipped_count}</span>
              </div>
            </div>

            <p className={styles.note}>
              This does not delete anything from iCloud or the Vault. It does not delete DB, provenance, Source Profile, or source registry records.
            </p>

            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={icloudCleanupExecutionAcknowledged}
                onChange={(event) => setIcloudCleanupExecutionAcknowledged(event.target.checked)}
                disabled={isIcloudCleanupActionLoading}
              />
              I understand that verified local staging copies will be permanently removed.
            </label>
            <label className={styles.fieldLabel}>
              Type <strong>{ICLOUD_CLEANUP_CONFIRMATION_PHRASE}</strong> to confirm
              <input
                className={styles.textInput}
                value={icloudCleanupExecutionPhrase}
                onChange={(event) => setIcloudCleanupExecutionPhrase(event.target.value)}
                autoComplete="off"
                disabled={isIcloudCleanupActionLoading}
              />
            </label>
            {icloudCleanupError && <p className={styles.bannerError}>{icloudCleanupError}</p>}

            <div className={styles.drawerActions}>
              <button
                type="button"
                className={styles.stopButton}
                onClick={() => void handleConfirmIcloudCleanupExecution()}
                disabled={
                  !icloudCleanupExecutionAcknowledged
                  || icloudCleanupExecutionPhrase !== ICLOUD_CLEANUP_CONFIRMATION_PHRASE
                  || isIcloudCleanupActionLoading
                }
              >
                {isIcloudCleanupActionLoading ? "Starting..." : "Delete Verified Local Staging Copies"}
              </button>
              <button type="button" className={styles.button} onClick={closeIcloudCleanupExecutionConfirmation} disabled={isIcloudCleanupActionLoading}>
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
                    Source labels are not globally unique. Durable identity verification uses safe provider evidence from Check Readiness.
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
                      <span className={styles.detailLabel}>Durable Source Identity</span>
                      <span className={durableIdentityBadgeClassName(
                        detailReadinessResult?.durable_identity_status
                          ?? (isIcloudProfile(detailProfile) ? "provider_specific" : "unknown"),
                      )}>
                        {detailReadinessResult
                          ? toDurableIdentityLabel(detailReadinessResult.durable_identity_status)
                          : isIcloudProfile(detailProfile)
                            ? "Provider-specific"
                            : "Unknown"}
                      </span>
                      <span className={styles.detailMeta}>
                        {detailReadinessResult?.durable_identity_reason
                          ?? (detailProfile.endpoint_id
                            ? "Endpoint link present. Run Check Readiness to verify current durable identity."
                            : "Run Check Readiness to verify durable identity.")}
                      </span>
                      {detailReadinessResult?.durable_identity_identifier_type && (
                        <span className={styles.detailMeta}>
                          {detailReadinessResult.durable_identity_identifier_type}: {detailReadinessResult.durable_identity_identifier ?? "-"}
                        </span>
                      )}
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
                  <h4 className={styles.detailHeading}>Source Readiness</h4>
                  <p className={styles.helperText}>
                    Manual read-only check. Source Intake launch behavior is unchanged.
                  </p>
                  <div className={styles.detailGrid}>
                    <div className={styles.detailCard}>
                      <span className={styles.detailLabel}>Status</span>
                      <span className={`${styles.readinessBadge} ${sourceReadinessBadgeClassName}`}>
                        {toSourceProfileReadinessLabel(sourceReadinessStatus)}
                      </span>
                      <span className={styles.detailMeta}>
                        Identity match: {detailReadinessResult ? toStatusLabel(detailReadinessResult.identity_match_status) : "Not checked"}
                      </span>
                      <span className={styles.detailMeta}>
                        Checked: {detailReadinessResult ? toDisplayDate(detailReadinessResult.checked_at) : "Not checked"}
                      </span>
                    </div>
                    <div className={styles.detailCard}>
                      <span className={styles.detailLabel}>Message</span>
                      <span>{detailReadinessResult?.operator_message ?? "Readiness has not been checked."}</span>
                      <span className={styles.detailMeta}>
                        Recommended next action: {detailReadinessResult?.recommended_next_action ?? "Check readiness before running intake."}
                      </span>
                      {detailReadinessResult?.readiness_status === "provider_specific" && (
                        <span className={styles.detailMeta}>
                          Use iCloud Intake or the provider-specific workflow for this source.
                        </span>
                      )}
                    </div>
                    <div className={styles.detailCard}>
                      <span className={styles.detailLabel}>Source Intake</span>
                      <span className={detailReadinessResult?.can_run_source_intake ? styles.okBadge : styles.pendingBadge}>
                        Can run: {detailReadinessResult ? (detailReadinessResult.can_run_source_intake ? "Yes" : "No") : "Unknown"}
                      </span>
                      <span className={styles.detailMeta}>
                        Run acknowledgment needed later: {detailReadinessResult ? (detailReadinessResult.requires_operator_acknowledgment ? "Yes" : "No") : "Unknown"}
                      </span>
                      <span className={styles.detailMeta}>
                        Hard block: {detailReadinessResult ? (detailReadinessResult.hard_block ? "Yes" : "No") : "Unknown"}
                      </span>
                    </div>
                    <div className={styles.detailCard}>
                      <span className={styles.detailLabel}>Durable Identity</span>
                      <span className={durableIdentityBadgeClassName(detailReadinessResult?.durable_identity_status)}>
                        {toDurableIdentityLabel(detailReadinessResult?.durable_identity_status)}
                      </span>
                      <span className={styles.detailMeta}>
                        {detailReadinessResult?.durable_identity_reason ?? "Check readiness to verify durable identity."}
                      </span>
                      {detailReadinessResult?.durable_identity_identifier_type && (
                        <span className={styles.detailMeta}>
                          {detailReadinessResult.durable_identity_identifier_type}: {detailReadinessResult.durable_identity_identifier ?? "-"}
                        </span>
                      )}
                    </div>
                  </div>
                  {sourceReadinessError && (
                    <p className={styles.bannerError}>{sourceReadinessError}</p>
                  )}
                  {detailReadinessResult && detailReadinessResult.durable_identity_evidence.length > 0 && (
                    <div className={styles.warningList}>
                      {detailReadinessResult.durable_identity_evidence.map((evidence, index) => (
                        <p key={`durable-identity-evidence:${index}:${evidence}`} className={styles.helperText}>
                          Evidence - {evidence}
                        </p>
                      ))}
                    </div>
                  )}
                  {sourceReadinessBlockers.length > 0 && (
                    <div className={styles.warningList}>
                      {sourceReadinessBlockers.map((message) => (
                        <p key={`blocker:${message.code}:${message.message}`} className={styles.inlineWarning}>
                          Blocker - {message.code}: {message.message}
                        </p>
                      ))}
                    </div>
                  )}
                  {sourceReadinessWarnings.length > 0 && (
                    <div className={styles.warningList}>
                      {sourceReadinessWarnings.map((message) => (
                        <p key={`warning:${message.code}:${message.message}`} className={styles.inlineWarning}>
                          Warning - {message.code}: {message.message}
                        </p>
                      ))}
                    </div>
                  )}
                  {sourceReadinessAdvancedDetails && (
                    <details className={styles.advancedDetails}>
                      <summary>Advanced Details</summary>
                      <pre className={styles.advancedDetailsText}>
                        {JSON.stringify(sourceReadinessAdvancedDetails, null, 2)}
                      </pre>
                    </details>
                  )}
                  <div className={styles.drawerActions}>
                    <button
                      type="button"
                      className={styles.updateButton}
                      onClick={() => void handleCheckSourceReadiness()}
                      disabled={isCheckingSourceReadiness || !detailSourceId}
                    >
                      {isCheckingSourceReadiness
                        ? "Checking readiness..."
                        : detailReadinessResult
                          ? "Recheck Readiness"
                          : "Check Readiness"}
                    </button>
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
                        {icloudAcquisitionError && (
                          <p className={styles.inlineWarning}>{icloudAcquisitionError}</p>
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
                        {!acquisitionStatusMatchesDetailProfile && (
                          <p className={styles.helperText}>
                            This acquisition status belongs to another source profile and is shown here as the latest global iCloud acquisition run.
                          </p>
                        )}

                        {(icloudAcquisitionStatus.status === "completed" || icloudAcquisitionStatus.status === "completed_with_warnings") && (
                          <p className={styles.bannerSuccess}>
                            {acquisitionStatusMatchesDetailProfile
                              ? "Acquisition completed. The next step is Source Intake for staged iCloud files. Use the Source Intake Handoff section above to continue."
                              : "A global acquisition run completed for a different source profile. Run acquisition or intake for this profile using the controls above when ready."}
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
                            <>
                              <span>No recent iCloud acquisition found for this profile.</span>
                              {icloudAcquisitionStatus && !acquisitionStatusMatchesDetailProfile && (
                                <span className={styles.detailMeta}>
                                  Latest global acquisition status is for source {icloudAcquisitionStatus.source_label ?? "-"}.
                                </span>
                              )}
                            </>
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

                    {icloudCleanupDryRunViewModel && (
                      <section className={styles.detailSection}>
                        <h4 className={styles.detailHeading}>iCloud Cleanup Readiness</h4>
                        <div className={styles.detailGrid}>
                          <div className={styles.detailCard}>
                            <span className={styles.detailLabel}>Dry Run Readiness</span>
                            <span className={`${styles.readinessBadge} ${icloudCleanupDryRunViewModel.badgeClassName}`}>
                              {icloudCleanupDryRunViewModel.statusLabel}
                            </span>
                            <span className={styles.detailMeta}>{icloudCleanupDryRunViewModel.helperMessage}</span>
                            {isLoadingIcloudCleanupStatus && <span className={styles.detailMeta}>Refreshing cleanup status...</span>}
                            {icloudCleanupError && <p className={styles.inlineWarning}>Cleanup status unavailable: {icloudCleanupError}</p>}
                          </div>

                          <div className={styles.detailCard}>
                             <span className={styles.detailLabel}>Current Cleanup Context</span>
                             <span>{cleanupSourceLabel(cleanupStatusForDetail)}</span>
                             <span className={styles.detailMeta}>Managed path: {icloudCleanupReadiness?.canonical_staging_path ?? cleanupSourcePath(cleanupStatusForDetail)}</span>
                             <span className={styles.detailMeta}>Execution requires a fresh matching dry run and explicit confirmation.</span>
                          </div>

                          <div className={styles.detailCard}>
                            <span className={styles.detailLabel}>Dry Run Action</span>
                            <span className={styles.detailMeta}>
                              This launches a dry run only. It reports eligible, skipped, and protected items without deleting any files.
                            </span>
                            {icloudCleanupDryRunViewModel.buttonDisabledReason && (
                              <p className={styles.inlineWarning}>{icloudCleanupDryRunViewModel.buttonDisabledReason}</p>
                            )}
                            <div className={styles.rowActions}>
                              <button
                                type="button"
                                className={styles.runButton}
                                onClick={() => void handleOpenIcloudCleanupDryRunConfirmation()}
                                disabled={Boolean(icloudCleanupDryRunViewModel.buttonDisabledReason) || isIcloudCleanupActionLoading || isLoadingIcloudCleanupStatus}
                              >
                                Run Cleanup Dry Run
                              </button>
                              <button
                                type="button"
                                className={styles.button}
                                onClick={() => void loadIcloudCleanupStatus(detailSourceId ?? undefined)}
                                disabled={isIcloudCleanupActionLoading || isLoadingIcloudCleanupStatus}
                              >
                                Refresh Cleanup Status
                              </button>
                            </div>
                          </div>
                        </div>

                        {cleanupStatusForDetail && cleanupStatusForDetail.status !== "idle" && (
                          <section className={styles.runPanel}>
                            <div className={styles.runPanelHeader}>
                              <h3 className={styles.runPanelTitle}>{cleanupStatusForDetail.dry_run ? "Cleanup Dry Run Status" : "Cleanup Execution Status"}</h3>
                              <span className={`${styles.runStatusBadge} ${statusClassName(cleanupStatusForDetail.status)}`}>
                                {toStatusLabel(cleanupStatusForDetail.status)}
                              </span>
                            </div>
                            <div className={styles.runMetrics}>
                              <span><strong>Source:</strong> {cleanupSourceLabel(cleanupStatusForDetail)}</span>
                              <span><strong>Path:</strong> {cleanupSourcePath(cleanupStatusForDetail)}</span>
                              <span><strong>Dry Run:</strong> {cleanupStatusForDetail.dry_run ? "Yes" : "No"}</span>
                              <span><strong>Started:</strong> {toDisplayDate(cleanupStatusForDetail.started_at)}</span>
                              <span><strong>Finished:</strong> {toDisplayDate(cleanupStatusForDetail.finished_at)}</span>
                              <span><strong>Eligible:</strong> {cleanupStatusForDetail.eligible_count}</span>
                              <span><strong>Skipped / Protected:</strong> {cleanupStatusForDetail.skipped_count}</span>
                              <span><strong>Deleted:</strong> {cleanupStatusForDetail.deleted_count}</span>
                              <span><strong>Bytes Eligible:</strong> {cleanupStatusForDetail.total_bytes_eligible}</span>
                              <span><strong>Bytes Deleted:</strong> {cleanupStatusForDetail.total_bytes_deleted}</span>
                              <span><strong>Progress:</strong> {cleanupStatusForDetail.processed_files} / {cleanupStatusForDetail.total_files}</span>
                              <span><strong>Stage:</strong> {cleanupStatusForDetail.current_stage ?? "-"}</span>
                              <span><strong>Protected:</strong> {cleanupStatusForDetail.protected_count}</span>
                              <span><strong>Verification Failed:</strong> {cleanupStatusForDetail.verification_failed_count}</span>
                              <span><strong>File Missing:</strong> {cleanupStatusForDetail.file_missing_count}</span>
                              <span><strong>Delete Failed:</strong> {cleanupStatusForDetail.delete_failed_count}</span>
                              {cleanupStatusForDetail.dry_run && (
                                <span><strong>Preview Expires:</strong> {toDisplayDate(cleanupStatusForDetail.preview_expires_at)}</span>
                              )}
                              <span><strong>Report:</strong> {cleanupStatusForDetail.report_path ?? "-"}</span>
                              {cleanupStatusForDetail.error_message && (
                                <span><strong>Error:</strong> {cleanupStatusForDetail.error_message}</span>
                              )}
                            </div>
                            {cleanupExecutionPreview && (
                              <div className={styles.rowActions}>
                                <button
                                  type="button"
                                  className={styles.stopButton}
                                  onClick={handleOpenIcloudCleanupExecutionConfirmation}
                                  disabled={isIcloudCleanupActionLoading || isLoadingIcloudCleanupStatus}
                                >
                                  Execute Verified Local Cleanup
                                </button>
                              </div>
                            )}
                            {Object.keys(cleanupStatusForDetail.skipped_reasons).length > 0 && (
                              <div className={styles.detailGrid}>
                                <div className={styles.detailCard}>
                                  <span className={styles.detailLabel}>Skipped Reasons</span>
                                  {Object.entries(cleanupStatusForDetail.skipped_reasons).map(([reason, count]) => (
                                    <span key={reason} className={styles.detailMeta}>{reason}: {count}</span>
                                  ))}
                                </div>
                                <div className={styles.detailCard}>
                                  <span className={styles.detailLabel}>Skipped Samples</span>
                                  {Object.entries(cleanupStatusForDetail.skipped_samples).map(([reason, samples]) => (
                                    <span key={reason} className={styles.detailMeta}>
                                      {reason}: {samples.length > 0 ? samples.join(", ") : "-"}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </section>
                        )}
                      </section>
                    )}
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

function sanitizeIcloudLabelForMatch(value: string | null | undefined): string {
  return (value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "_")
    .replace(/[_-]{2,}/g, "_")
    .replace(/^[_\-\s]+|[_\-\s]+$/g, "") || "unnamed_source";
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

function toStatusLabel(status: string | null | undefined): string {
  const normalized = (status ?? "unknown").trim();
  if (!normalized) {
    return "Unknown";
  }

  return normalized
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function statusClassName(status: string): string {
  const normalized = status.toLowerCase();
  if (normalized === "pending" || normalized === "running") {
    return styles.runStatusRunning;
  }
  if (normalized === "stop_requested") {
    return styles.runStatusStopRequested;
  }
  if (normalized === "completed") {
    return styles.runStatusCompleted;
  }
  if (normalized === "completed_with_errors") {
    return styles.runStatusWarning;
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

"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  createSourceProfile,
  getSourceProfiles,
  updateSourceProfileMetadata,
} from "@/lib/api";
import type {
  SourceAcquisitionMethod,
  SourceCloudProvider,
  SourceProfileCreateRequest,
  SourceProfileMetadataUpdateRequest,
  SourceProfileStatus,
  SourceProfileSummary,
  SourceProfileType,
} from "@/types/ui-api";

import styles from "./ingestion-view.module.css";

type StatusFilter = SourceProfileStatus | "all";
type EditorMode = "create" | "edit";

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

  const loadProfiles = useCallback(async (refreshOnly = false) => {
    if (refreshOnly) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }

    setBanner(null);
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
      setBanner({
        kind: "error",
        message: error instanceof Error ? error.message : "Failed to load source profiles.",
      });
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    void loadProfiles();
  }, [loadProfiles]);

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

  const openCreateDrawer = useCallback(() => {
    setEditorMode("create");
    setEditingProfile(null);
    setEditorError(null);
    setEditorForm(initialFormState());
    setIsEditorOpen(true);
  }, []);

  const openEditDrawer = useCallback((profile: SourceProfileSummary) => {
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

  const closeEditor = useCallback(() => {
    setIsEditorOpen(false);
    setEditorError(null);
  }, []);

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
          source_root_path: editorForm.sourceType === "cloud_export"
            ? undefined
            : editorForm.sourceRootPath.trim(),
          cloud_provider: editorForm.sourceType === "cloud_export" ? editorForm.cloudProvider : null,
          account_username: editorForm.accountUsername.trim() || null,
          acquisition_method: editorForm.sourceType === "cloud_export" ? editorForm.acquisitionMethod : null,
          managed_staging_path: editorForm.sourceType === "cloud_export"
            ? (editorForm.managedStagingPath.trim() || managedStagingPreview)
            : null,
        };

        const response = await createSourceProfile(payload);
        await loadProfiles(true);
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
        managed_staging_path: editorForm.sourceType === "cloud_export"
          ? (editorForm.managedStagingPath.trim() || null)
          : null,
      };

      const updated = await updateSourceProfileMetadata(editingProfile.source_id, payload);
      await loadProfiles(true);
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
          <button
            type="button"
            className={styles.button}
            onClick={openCreateDrawer}
          >
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
            onClick={() => void loadProfiles(true)}
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
        Source profiles define where files come from. Running intake from this tab will be added later.
      </p>
      <p className={styles.note}>
        Lifecycle status does not delete files, sources, or provenance. Archived, test, and deprecated sources are retained for history and remain visible through the status filter.
      </p>
      <p className={styles.note}>
        Source labels are not globally unique. Source identity is based on label + type + path. For iCloud, managed staging path is part of source identity.
      </p>
      <p className={styles.note}>
        iCloud authentication is handled by icloudpd outside Photo Organizer. Do not enter Apple ID passwords here.
      </p>
      <p className={styles.placeholder}>
        Run Intake from this tab will be added in a later milestone. Existing Source Intake tools remain in Admin.
      </p>
      <p className={styles.subtitle}>
        Active shown: {countsSummary.active} | Archived/Test/Deprecated shown: {countsSummary.nonActive}
      </p>

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
              {profiles.map((profile) => (
                <tr key={profile.source_id}>
                  <td>{profile.source_label}</td>
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
                  <td>{toDisplayDate(profile.last_run_at)}</td>
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
                      <button
                        type="button"
                        className={styles.updateButton}
                        onClick={() => openEditDrawer(profile)}
                      >
                        Edit
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
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
                  {editorMode === "create" ? "Create Source Profile" : "Edit Source Profile"}
                </h3>
                <p className={styles.drawerSubtitle}>
                  {editorMode === "create"
                    ? "Create a safe metadata profile without starting ingestion."
                    : "Edit non-destructive metadata only. Source type and source root path stay locked."}
                </p>
              </div>
              <button
                type="button"
                className={styles.closeButton}
                onClick={closeEditor}
                disabled={isSavingEditor}
              >
                Close
              </button>
            </div>

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
                        cloudProvider: sourceType === "cloud_export" ? "icloud" : prev.cloudProvider,
                        acquisitionMethod: sourceType === "cloud_export" ? "icloudpd" : prev.acquisitionMethod,
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

              {!isIcloudCloudExport(editorForm) ? (
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
              ) : null}

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
                    />
                  </label>
                </>
              )}
            </div>

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
              <button
                type="button"
                className={styles.button}
                onClick={closeEditor}
                disabled={isSavingEditor}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getSourceProfiles,
  updateSourceProfileStatus,
} from "@/lib/api";
import type {
  SourceProfileStatus,
  SourceProfileSummary,
} from "@/types/ui-api";

import styles from "./ingestion-view.module.css";

type StatusFilter = SourceProfileStatus | "all";

type BannerState = {
  kind: "success" | "error";
  message: string;
} | null;

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

function toDisplayDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "-";
}

export default function IngestionView() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("active");
  const [profiles, setProfiles] = useState<SourceProfileSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [banner, setBanner] = useState<BannerState>(null);
  const [pendingStatusById, setPendingStatusById] = useState<Record<number, SourceProfileStatus>>({});
  const [updatingSourceId, setUpdatingSourceId] = useState<number | null>(null);

  const loadProfiles = useCallback(async (refreshOnly = false) => {
    if (refreshOnly) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }

    try {
      const response = await getSourceProfiles({ status: statusFilter });
      setProfiles(response.profiles);
      setPendingStatusById((prev) => {
        const next: Record<number, SourceProfileStatus> = {};
        for (const profile of response.profiles) {
          next[profile.source_id] = prev[profile.source_id] ?? profile.profile_status;
        }
        return next;
      });
    } catch (error) {
      setBanner({
        kind: "error",
        message: error instanceof Error ? error.message : "Failed to load source profiles.",
      });
      setProfiles([]);
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

    const nonActive = counts.archived + counts.test + counts.deprecated;
    return { active: counts.active, nonActive };
  }, [profiles]);

  const handleUpdateStatus = useCallback(async (profile: SourceProfileSummary) => {
    const nextStatus = pendingStatusById[profile.source_id] ?? profile.profile_status;
    if (nextStatus === profile.profile_status) {
      setBanner({ kind: "success", message: `No change for ${profile.source_label}.` });
      return;
    }

    setUpdatingSourceId(profile.source_id);
    setBanner(null);

    try {
      await updateSourceProfileStatus(profile.source_id, nextStatus);
      await loadProfiles(true);

      if (statusFilter !== "all" && nextStatus !== statusFilter) {
        setBanner({
          kind: "success",
          message: `Source profile marked ${nextStatus}. It is now hidden by the ${statusFilter} filter.`,
        });
      } else {
        setBanner({
          kind: "success",
          message: `Source profile updated: ${profile.source_label} -> ${nextStatus}`,
        });
      }
    } catch (error) {
      setBanner({
        kind: "error",
        message: error instanceof Error ? error.message : "Failed to update source profile status.",
      });
    } finally {
      setUpdatingSourceId(null);
    }
  }, [loadProfiles, pendingStatusById, statusFilter]);

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
        Lifecycle status does not delete files, sources, or provenance. Archived, test, and deprecated sources are retained for history and remain visible through the status filter.
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
              {profiles.map((profile) => {
                const pendingStatus = pendingStatusById[profile.source_id] ?? profile.profile_status;
                const isUpdating = updatingSourceId === profile.source_id;
                return (
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
                        <select
                          className={styles.select}
                          value={pendingStatus}
                          onChange={(event) => {
                            const nextStatus = event.target.value as SourceProfileStatus;
                            setPendingStatusById((prev) => ({
                              ...prev,
                              [profile.source_id]: nextStatus,
                            }));
                          }}
                          disabled={isUpdating}
                        >
                          {EDITABLE_STATUS_OPTIONS.map((statusValue) => (
                            <option key={statusValue} value={statusValue}>
                              {statusValue}
                            </option>
                          ))}
                        </select>
                        <button
                          type="button"
                          className={styles.updateButton}
                          onClick={() => void handleUpdateStatus(profile)}
                          disabled={isUpdating}
                        >
                          {isUpdating ? "Updating..." : "Update"}
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
    </section>
  );
}

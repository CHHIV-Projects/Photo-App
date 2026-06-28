"use client";

import { useEffect, useMemo, useState } from "react";

import { getInternalIcloudRunStatus, getSourceProfiles, startInternalIcloudRun } from "@/lib/api";
import type {
  InternalIcloudMediaScope,
  InternalIcloudRunStatus,
  SourceProfileSummary,
} from "@/types/ui-api";

import styles from "./IcloudInternalRunCard.module.css";

const MEDIA_SCOPE_OPTIONS: Array<{ value: InternalIcloudMediaScope; label: string }> = [
  { value: "ordinary_stills", label: "ordinary_stills" },
  { value: "stills_with_live_photo_pairs", label: "stills_with_live_photo_pairs" },
  { value: "videos_only", label: "videos_only" },
  { value: "all_supported_media", label: "all_supported_media" },
];

export default function IcloudInternalRunCard() {
  const [profiles, setProfiles] = useState<SourceProfileSummary[]>([]);
  const [sourceId, setSourceId] = useState<number | "">(66);
  const [batchSize, setBatchSize] = useState("5");
  const [totalLimit, setTotalLimit] = useState("10");
  const [candidateSearchCap, setCandidateSearchCap] = useState("50");
  const [mediaScope, setMediaScope] = useState<InternalIcloudMediaScope>("ordinary_stills");
  const [autoCleanupIfSafe, setAutoCleanupIfSafe] = useState(true);
  const [isStarting, setIsStarting] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [current, setCurrent] = useState<InternalIcloudRunStatus | null>(null);

  const currentRunId = current?.run_id ?? null;

  const loadProfiles = async () => {
    const response = await getSourceProfiles({ status: "active", includeUsername: false });
    const icloudProfiles = response.profiles.filter((profile) => profile.cloud_provider === "icloud");
    setProfiles(icloudProfiles);
    if (sourceId === "" && icloudProfiles.length > 0) {
      setSourceId(icloudProfiles[0].source_id);
    }
  };

  const refreshRun = async (runId: number) => {
    const response = await getInternalIcloudRunStatus(runId);
    setCurrent(response.current);
  };

  useEffect(() => {
    void loadProfiles().catch((error) => {
      setErrorMessage(error instanceof Error ? error.message : "Failed to load source profiles.");
    });
  }, []);

  useEffect(() => {
    if (currentRunId == null) {
      return;
    }
    if (!["running", "paused_for_cleanup"].includes(current?.status ?? "")) {
      return;
    }

    const timer = setInterval(() => {
      void refreshRun(currentRunId).catch(() => {
        // Keep polling resilient; surface errors only on manual refresh.
      });
    }, 5000);

    return () => clearInterval(timer);
  }, [currentRunId, current?.status]);

  const selectedProfile = useMemo(() => {
    if (sourceId === "") {
      return null;
    }
    return profiles.find((profile) => profile.source_id === sourceId) ?? null;
  }, [profiles, sourceId]);

  const handleStart = async () => {
    if (sourceId === "") {
      setErrorMessage("Please select a Source Profile.");
      return;
    }
    setIsStarting(true);
    setErrorMessage("");
    setSuccessMessage("");

    try {
      const response = await startInternalIcloudRun({
        source_id: sourceId,
        batch_size: Number(batchSize),
        total_limit: Number(totalLimit),
        candidate_search_cap: Number(candidateSearchCap),
        media_scope: mediaScope,
        auto_cleanup_if_safe: autoCleanupIfSafe,
      });
      setCurrent(response.current);
      setSuccessMessage(response.message);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to start internal iCloud run.");
    } finally {
      setIsStarting(false);
    }
  };

  const handleRefresh = async () => {
    if (currentRunId == null) {
      return;
    }
    setIsRefreshing(true);
    setErrorMessage("");
    try {
      await refreshRun(currentRunId);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to refresh run status.");
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <section className={styles.card}>
      <h3 className={styles.title}>iCloud Internal Run</h3>
      <p className={styles.meta}>
        Internal/admin single-flow wrapper over the bounded orchestration pipeline. Non-ordinary media scopes may be exposed but can stop safely if execution support is not available.
      </p>

      <div className={styles.grid}>
        <label className={styles.label}>
          Source Profile
          <select
            className={styles.select}
            value={sourceId}
            onChange={(event) => setSourceId(event.target.value === "" ? "" : Number(event.target.value))}
          >
            <option value="">-- select --</option>
            {profiles.map((profile) => (
              <option key={profile.source_id} value={profile.source_id}>
                #{profile.source_id} {profile.source_label}
              </option>
            ))}
          </select>
        </label>

        <label className={styles.label}>
          batch_size
          <input className={styles.input} type="number" min={1} value={batchSize} onChange={(event) => setBatchSize(event.target.value)} />
        </label>

        <label className={styles.label}>
          total_limit
          <input className={styles.input} type="number" min={1} value={totalLimit} onChange={(event) => setTotalLimit(event.target.value)} />
        </label>

        <label className={styles.label}>
          Candidate Search Cap
          <input
            className={styles.input}
            type="number"
            min={1}
            value={candidateSearchCap}
            onChange={(event) => setCandidateSearchCap(event.target.value)}
          />
        </label>

        <label className={styles.label}>
          Media Scope
          <select className={styles.select} value={mediaScope} onChange={(event) => setMediaScope(event.target.value as InternalIcloudMediaScope)}>
            {MEDIA_SCOPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className={styles.checkboxRow}>
        <input type="checkbox" checked={autoCleanupIfSafe} onChange={(event) => setAutoCleanupIfSafe(event.target.checked)} />
        Auto-cleanup when safe
      </label>

      <div className={styles.actions}>
        <button type="button" className={styles.button} onClick={() => void handleStart()} disabled={isStarting || sourceId === ""}>
          {isStarting ? "Starting..." : "Start Run"}
        </button>
        <button
          type="button"
          className={styles.buttonSecondary}
          onClick={() => void handleRefresh()}
          disabled={isRefreshing || currentRunId == null}
        >
          {isRefreshing ? "Refreshing..." : "Refresh Status"}
        </button>
      </div>

      {selectedProfile && (
        <p className={styles.meta}>Selected: #{selectedProfile.source_id} {selectedProfile.source_label} ({selectedProfile.profile_status})</p>
      )}

      {errorMessage && <p className={styles.error}>{errorMessage}</p>}
      {successMessage && <p className={styles.success}>{successMessage}</p>}

      {current && (
        <div className={styles.statusPanel}>
          <p className={styles.kv}><strong>Run ID:</strong> {current.run_id ?? "(none)"}</p>
          <p className={styles.kv}><strong>Status:</strong> {current.status}</p>
          <p className={styles.kv}><strong>Phase:</strong> {current.current_phase ?? "-"}</p>
          <p className={styles.kv}><strong>Stop Reason:</strong> {current.stop_reason ?? "-"}</p>
          <p className={styles.kv}><strong>Failure Reason:</strong> {current.failure_reason ?? "-"}</p>
          <p className={styles.kv}><strong>Requested Scope:</strong> {current.requested_media_scope}</p>
          <p className={styles.kv}><strong>Effective Scope:</strong> {current.effective_media_scope ?? "not_executed"}</p>
          <p className={styles.kv}><strong>Dry Run Performed:</strong> {current.dry_run_performed ? "yes" : "no"}</p>
          <p className={styles.kv}><strong>Execution Performed:</strong> {current.execution_performed ? "yes" : "no"}</p>
          <p className={styles.kv}><strong>Cleanup Performed:</strong> {current.cleanup_performed ? "yes" : "no"}</p>
          <p className={styles.kv}><strong>Final Verification Passed:</strong> {current.final_verification_passed ? "yes" : "no"}</p>
          <p className={styles.kv}><strong>Logical Selected:</strong> {String(current.logical_assets_selected)}</p>
          <p className={styles.kv}><strong>Resources Selected:</strong> {String(current.resources_selected)}</p>
          <p className={styles.kv}><strong>Video Count:</strong> {String(current.video_count)}</p>
          <p className={styles.kv}><strong>Live Photo Logical Count:</strong> {String(current.live_photo_logical_count)}</p>
          <p className={styles.kv}><strong>Final staging clean:</strong> {current.final_staging_clean == null ? "unknown" : current.final_staging_clean ? "yes" : "no"}</p>
          <p className={styles.kv}><strong>Drop Zone clean:</strong> {current.drop_zone_clean == null ? "unknown" : current.drop_zone_clean ? "yes" : "no"}</p>
          <p className={styles.kv}><strong>.partial clean:</strong> {current.partial_workspace_clean == null ? "unknown" : current.partial_workspace_clean ? "yes" : "no"}</p>
          <p className={styles.kv}><strong>Cloud deletion occurred:</strong> {current.cloud_deletion_occurred ? "yes" : "no"}</p>
          <p className={styles.kv}><strong>Next Safe Action:</strong> {current.next_safe_action ?? "-"}</p>
          {current.report_path && <p className={`${styles.kv} ${styles.path}`}><strong>Report:</strong> {current.report_path}</p>}
        </div>
      )}
    </section>
  );
}

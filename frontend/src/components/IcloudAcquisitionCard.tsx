"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  getIcloudAcquisitionStatus,
  getSourceIntakeSources,
  runIcloudAcquisition,
  stopIcloudAcquisition,
} from "@/lib/api";
import type {
  IcloudAcquisitionRunStatus,
  SourceIntakeSourceSummary,
} from "@/types/ui-api";

import styles from "./admin-view.module.css";

const POLL_INTERVAL_MS = 3000;
const ACTIVE_STATUSES = new Set(["running", "stop_requested"]);
const AUTH_ERROR_CODES = new Set(["AUTH_REQUIRED", "SESSION_EXPIRED"]);

export interface IcloudAcquisitionSourceIntakeHandoff {
  sourceLabel: string;
  sourceRootPath: string | null;
  fileInventoryCount: number | null;
  recentCount: number | null;
  recommendedSourceIntakeCommand: string | null;
}

interface IcloudAcquisitionCardProps {
  onPrepareSourceIntake?: (handoff: IcloudAcquisitionSourceIntakeHandoff) => void;
}

function StatusBadge({ status }: { status: string }) {
  const cls = styles[`status_${status}` as keyof typeof styles] ?? "";
  return (
    <span className={`${styles.statusBadge} ${cls}`.trim()}>
      {status}
    </span>
  );
}

function elapsed(seconds: number | null): string {
  if (seconds === null) return "-";
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

export default function IcloudAcquisitionCard({ onPrepareSourceIntake }: IcloudAcquisitionCardProps) {
  // ── State ──────────────────────────────────────────────────────────────────
  const [status, setStatus] = useState<IcloudAcquisitionRunStatus | null>(null);
  const [sources, setSources] = useState<SourceIntakeSourceSummary[]>([]);
  const [sourceLabel, setSourceLabel] = useState("");
  const [username, setUsername] = useState("");
  const [recentCount, setRecentCount] = useState<number>(25);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [showIntakeCommand, setShowIntakeCommand] = useState(false);
  const [usernameOverrideEnabled, setUsernameOverrideEnabled] = useState(false);
  const [usernameDiffersFromSource, setUsernameDiffersFromSource] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Derived ────────────────────────────────────────────────────────────────
  const isActive = status ? ACTIVE_STATUSES.has(status.status) : false;
  const isAuthError = status?.error_code ? AUTH_ERROR_CODES.has(status.error_code) : false;
  const selectedSource = sources.find(s => s.source_label === sourceLabel) ?? null;
  const sourceAccountUsername = selectedSource?.account_username?.trim() ?? "";
  const hasSourceAccountUsername = sourceAccountUsername.length > 0;
  const effectiveUsername = hasSourceAccountUsername && !usernameOverrideEnabled
    ? sourceAccountUsername
    : username.trim();
  const cloudExportSources = sources.filter(s => s.source_type === "cloud_export");

  // ── Data loading ───────────────────────────────────────────────────────────
  const loadStatus = useCallback(async () => {
    try {
      const res = await getIcloudAcquisitionStatus();
      setStatus(res.current);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load iCloud acquisition status.");
    }
  }, []);

  const loadSources = useCallback(async () => {
    try {
      const res = await getSourceIntakeSources();
      setSources(res.sources);
    } catch {
      // Non-fatal — source list is optional UI sugar.
    }
  }, []);

  useEffect(() => {
    void loadStatus();
    void loadSources();
  }, [loadStatus, loadSources]);

  // ── Prefill username when source changes ────────────────────────────────────
  useEffect(() => {
    if (hasSourceAccountUsername) {
      setUsername(sourceAccountUsername);
      setUsernameDiffersFromSource(false);
      setUsernameOverrideEnabled(false);
    } else {
      setUsername("");
      setUsernameDiffersFromSource(false);
      setUsernameOverrideEnabled(false);
    }
  }, [hasSourceAccountUsername, sourceAccountUsername, selectedSource]);

  // ── Polling ────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!isActive) return;
    pollRef.current = setInterval(() => void loadStatus(), POLL_INTERVAL_MS);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [isActive, loadStatus]);

  // ── Actions ────────────────────────────────────────────────────────────────
  async function handleRun() {
    if (!sourceLabel.trim()) { setError("Select a source first."); return; }
    if (!effectiveUsername) { setError("Enter an Apple ID username."); return; }
    if (recentCount < 1 || recentCount > 500) { setError("Recent count must be between 1 and 500."); return; }
    setError("");
    setIsActionLoading(true);
    try {
      const res = await runIcloudAcquisition({ source_label: sourceLabel, username: effectiveUsername, recent_count: recentCount });
      setStatus(res.current);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start iCloud acquisition.");
    } finally {
      setIsActionLoading(false);
    }
  }

  async function handleStop() {
    setError("");
    setIsActionLoading(true);
    try {
      const res = await stopIcloudAcquisition();
      setStatus(res.current);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to stop iCloud acquisition.");
    } finally {
      setIsActionLoading(false);
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <section className={styles.sourceIntakeSection}>
      {/* Header */}
      <div className={styles.sectionHeader}>
        <h3 className={styles.sectionTitle}>iCloud Acquisition</h3>
        <button
          type="button"
          className={styles.refreshButton}
          onClick={() => {
            void loadStatus();
            void loadSources();
          }}
          disabled={isActionLoading}
        >
          Refresh Status
        </button>
      </div>

      {/* Safety and workflow notice */}
      <div className={styles.sourceIntakeBlock}>
        <p className={styles.metaSmall}>
          <strong>Workflow:</strong> Use one stable iCloud source per iCloud account. Create/manage sources in Source Registry before running acquisition.
        </p>
        <p className={styles.metaSmall}>
          <strong>Staging:</strong> Downloads from iCloud into the exports staging folder. Does not ingest directly into Vault. Run Source Intake after acquisition to import staged files.
        </p>
        <p className={styles.metaSmall}>
          <strong>Security:</strong> Does not delete or modify iCloud content. Does not store your Apple ID password. Password and 2FA are handled by icloudpd outside Photo Organizer.
        </p>
      </div>

      {/* Form */}
      <div className={styles.sourceIntakeBlock}>
        <div className={styles.registryForm}>

          {/* Source selector */}
          <label className={styles.formLabel}>
            iCloud Source
            {cloudExportSources.length === 0 ? (
              <p className={styles.errorText}>
                No cloud_export source registered. Register a source before running acquisition.
              </p>
            ) : (
              <select
                className={styles.formInput}
                value={sourceLabel}
                onChange={e => setSourceLabel(e.target.value)}
                disabled={isActive}
              >
                <option value="">— select a registered iCloud source —</option>
                {cloudExportSources.map(src => (
                  <option key={src.source_id} value={src.source_label}>
                    {src.source_label} • {src.source_root_path ?? "(no path)"}
                  </option>
                ))}
              </select>
            )}
          </label>

          {/* Selected source detail */}
          {selectedSource && (
            <div className={styles.selectedSourceDetail}>
              <p className={styles.meta}><strong>Type:</strong> {selectedSource.source_type}</p>
              <p className={styles.meta}><strong>Path:</strong> <code>{selectedSource.source_root_path ?? "(none)"}</code></p>
              <p className={styles.meta}><strong>Registration:</strong> registered</p>
            </div>
          )}

          {/* Username */}
          <label className={styles.formLabel}>
            Apple ID (username)
            <input
              className={styles.formInput}
              type="email"
              autoComplete="off"
              placeholder="your@icloud.com"
              value={username}
              onChange={e => {
                setUsername(e.target.value);
                if (
                  hasSourceAccountUsername
                  && e.target.value.trim().toLowerCase() !== sourceAccountUsername.toLowerCase()
                ) {
                  setUsernameDiffersFromSource(true);
                } else {
                  setUsernameDiffersFromSource(false);
                }
              }}
              disabled={isActive || (hasSourceAccountUsername && !usernameOverrideEnabled)}
            />
          </label>
          {hasSourceAccountUsername && (
            <div className={styles.inlineToggleRow}>
              <p className={styles.metaSmall}>
                Using source-associated account by default: <strong>{sourceAccountUsername}</strong>
              </p>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={usernameOverrideEnabled}
                  onChange={e => {
                    const enabled = e.target.checked;
                    setUsernameOverrideEnabled(enabled);
                    if (!enabled) {
                      setUsername(sourceAccountUsername);
                      setUsernameDiffersFromSource(false);
                    }
                  }}
                  disabled={isActive}
                />
                Override for this run
              </label>
            </div>
          )}
          {usernameOverrideEnabled && usernameDiffersFromSource && (
            <p className={styles.warningText}>
              ⚠ This username differs from the account associated with the selected source. Make sure you are not downloading from the wrong iCloud account into this source.
            </p>
          )}
          <p className={styles.metaSmall}>
            Password and 2FA are handled by icloudpd outside Photo Organizer. This app does not store your Apple ID password.
          </p>

          {/* Recent count */}
          <label className={styles.formLabel}>
            Recent Count
            <input
              className={styles.formInput}
              type="number"
              min={1}
              max={500}
              value={recentCount}
              onChange={e => setRecentCount(Number(e.target.value))}
              disabled={isActive}
            />
          </label>
          <p className={styles.metaSmall}>
            Number of recent iCloud items to acquire. This checks the N most recent items in your iCloud library but does not prove the entire library is caught up.
            Start with 25 for small updates; use 100–500 for catch-up after travel or a long interval.
          </p>

          {/* Action buttons */}
          <div className={styles.actionRow}>
            <button
              type="button"
              className={styles.actionButton}
              onClick={() => void handleRun()}
              disabled={isActionLoading || isActive || !sourceLabel || !effectiveUsername}
            >
              {isActionLoading && !isActive ? "Starting…" : "Run iCloud Acquisition"}
            </button>
            {isActive && (
              <button
                type="button"
                className={styles.actionButtonSecondary}
                onClick={() => void handleStop()}
                disabled={isActionLoading}
              >
                {isActionLoading ? "Stopping…" : "Stop"}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Errors */}
      {error && <p className={styles.errorText}>{error}</p>}

      {/* Auth error guidance */}
      {isAuthError && (
        <div className={styles.sourceIntakeBlock}>
          <p className={styles.errorText}>
            <strong>iCloud authentication required.</strong> Photo Organizer does not store your Apple password.
            Re-authenticate using the icloudpd setup command, then try again.
          </p>
          <p className={styles.metaSmall}>
            Run: <code>.tools/icloudpd/Scripts/icloudpd.exe --username your@icloud.com --cookie-directory .tools/icloud_session --auth-only</code>
          </p>
        </div>
      )}

      {/* Status panel */}
      {status && status.status !== "idle" && (
        <div className={styles.sourceIntakeBlock}>
          <p className={styles.blockTitle}>Run Status</p>
          <p className={styles.meta}>Status: <StatusBadge status={status.status} /></p>
          {status.run_id !== null && <p className={styles.meta}>Run ID: {status.run_id}</p>}
          {status.source_label && <p className={styles.meta}>Source: {status.source_label}</p>}
          {status.username && <p className={styles.meta}>Apple ID: {status.username}</p>}
          {status.recent_count !== null && <p className={styles.meta}>Recent count: {status.recent_count}</p>}
          {status.staging_path && <p className={styles.meta}>Staging path: <code>{status.staging_path}</code></p>}
          {status.started_at && (
            <p className={styles.meta}>Started: {new Date(status.started_at).toLocaleString()}</p>
          )}
          {status.completed_at && (
            <p className={styles.meta}>Completed: {new Date(status.completed_at).toLocaleString()}</p>
          )}
          <p className={styles.meta}>Elapsed: {elapsed(status.elapsed_seconds)}</p>

          {/* Counts */}
          <p className={styles.meta}>icloudpd reported downloads: {status.downloaded_count}</p>
          <p className={styles.meta}>Skipped existing: {status.skipped_existing_count}</p>
          <p className={styles.meta}>Failed: {status.failed_count}</p>
          {status.file_inventory_count !== null && status.file_inventory_count !== undefined && (
            <p className={styles.meta}><strong>Files currently staged: {status.file_inventory_count}</strong></p>
          )}

          {/* Completeness note */}
          {status.recent_count !== null && status.recent_count !== undefined && (
            <p className={styles.metaSmall} style={{ fontStyle: "italic", marginTop: "0.5rem" }}>
              <strong>Completeness:</strong> This run checked the most recent {status.recent_count} iCloud item(s). It does not prove the entire iCloud library is caught up.
            </p>
          )}

          {/* Report path */}
          {status.report_path && (
            <p className={styles.meta}>Report: <code>{status.report_path}</code></p>
          )}

          {/* Error */}
          {status.error_code && !isAuthError && (
            <p className={styles.errorText}>Error [{status.error_code}]: {status.error_message}</p>
          )}

          {/* Next step: Source Intake */}
          {(status.status === "completed" || status.status === "completed_with_warnings") && (
            <div className={styles.intakeStatusPanel}>
              <p className={styles.successText}>
                Acquisition complete. Next step: Run Source Intake for this same registered source using the Source Intake section below.
              </p>
              <p className={styles.metaSmall}>
                Staged files remain after Source Intake for now. Cleanup will be handled separately in 12.44.1.
              </p>
              {onPrepareSourceIntake && (
                <button
                  type="button"
                  className={styles.detailToggle}
                  onClick={() =>
                    onPrepareSourceIntake({
                      sourceLabel: status.source_label ?? sourceLabel,
                      sourceRootPath: status.source_root_path ?? selectedSource?.source_root_path ?? null,
                      fileInventoryCount: status.file_inventory_count ?? null,
                      recentCount: status.recent_count ?? null,
                      recommendedSourceIntakeCommand: status.recommended_source_intake_command ?? null,
                    })
                  }
                >
                  Prepare Source Intake
                </button>
              )}
              {status.recommended_source_intake_command && (
                <>
                  <button
                    type="button"
                    className={styles.detailToggle}
                    onClick={() => setShowIntakeCommand(v => !v)}
                  >
                    {showIntakeCommand ? "Hide" : "Show"} recommended command
                  </button>
                  {showIntakeCommand && (
                    <pre className={styles.fileSample}>{status.recommended_source_intake_command}</pre>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

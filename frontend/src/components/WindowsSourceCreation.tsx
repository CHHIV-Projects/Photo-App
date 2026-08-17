"use client";

import { useCallback, useMemo, useState } from "react";

import {
  confirmWindowsSourceUiCreation,
  getWindowsSourceUiOperation,
  planWindowsSourceUiCreation,
  startWindowsSourceUiCreationProbe,
} from "@/lib/api";
import type {
  WindowsSourceUiCreateFields,
  WindowsSourceUiCreatePlan,
  WindowsSourceUiCreateResult,
} from "@/types/ui-api";

import styles from "./ingestion-view.module.css";


const START_URI = "photoorganizer-helper://start";

function invokeWindowsAccess(): void {
  window.location.href = START_URI;
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

const PROFILE_ACTION_LABELS: Record<string, string> = {
  create_new_source: "Create new Profile",
  reuse_existing_source: "Reuse existing Profile",
  reactivate_existing_source: "Reactivate existing Profile",
  adopt_legacy_source: "Adopt legacy Profile",
  adopt_and_reactivate_source: "Adopt and reactivate Profile",
  canonicalize_existing_source: "Use canonical existing Profile",
  canonicalize_and_reactivate_source: "Use and reactivate canonical Profile",
  none: "No Profile change",
};

function profileActionLabel(action: string): string {
  return PROFILE_ACTION_LABELS[action] ?? "Review required";
}

type Props = {
  deviceAliases: string[];
  onComplete: () => void;
  launchWindowsAccess?: () => void;
};

export default function WindowsSourceCreation({
  deviceAliases,
  onComplete,
  launchWindowsAccess = invokeWindowsAccess,
}: Props) {
  const [fields, setFields] = useState<WindowsSourceUiCreateFields>({
    device_alias: deviceAliases[0] ?? "",
    windows_root: "",
    profile_name: "",
  });
  const [probeToken, setProbeToken] = useState<string | null>(null);
  const [plan, setPlan] = useState<WindowsSourceUiCreatePlan | null>(null);
  const [result, setResult] = useState<WindowsSourceUiCreateResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pathError = useMemo(() => {
    const root = fields.windows_root.trim();
    return /^[A-Za-z]:\\/.test(root) || /^\\\\[^\\]+\\[^\\]+/.test(root)
      ? null
      : "Enter an absolute Windows folder path.";
  }, [fields.windows_root]);

  const update = (key: keyof WindowsSourceUiCreateFields, value: string) => {
    setFields((current) => ({ ...current, [key]: value }));
    setProbeToken(null);
    setPlan(null);
    setResult(null);
    setError(null);
  };

  const identify = useCallback(() => {
    if (!fields.device_alias.trim() || !fields.profile_name.trim() || pathError) {
      setError(pathError ?? "Device and Profile name are required.");
      return;
    }
    // Synchronous user gesture: a healthy existing instance safely reuses its OS mutex.
    launchWindowsAccess();
    setBusy(true);
    setError(null);
    void (async () => {
      const probe = await startWindowsSourceUiCreationProbe(fields);
      const deadline = Date.now() + 120_000;
      while (Date.now() < deadline) {
        const status = await getWindowsSourceUiOperation(probe.operation_token);
        if (status.stage === "failed") throw new Error(status.safe_message);
        if (status.stage === "ready") {
          const reviewed = await planWindowsSourceUiCreation(fields, probe.operation_token);
          setProbeToken(probe.operation_token);
          setPlan(reviewed);
          return;
        }
        await delay(1000);
      }
      throw new Error("The Windows folder check timed out safely.");
    })().catch((caught: unknown) => {
      setError(caught instanceof Error ? caught.message : "The Windows folder could not be checked.");
    }).finally(() => setBusy(false));
  }, [fields, launchWindowsAccess, pathError]);

  const confirm = useCallback(async () => {
    if (!probeToken || !plan) return;
    setBusy(true);
    setError(null);
    try {
      const created = await confirmWindowsSourceUiCreation(fields, probeToken);
      setResult(created);
      if (created.status === "completed") onComplete();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The Source was not saved.");
    } finally {
      setBusy(false);
    }
  }, [fields, onComplete, plan, probeToken]);

  return (
    <section aria-label="Create Windows Local Source">
      <div className={styles.createSourceControls}>
        <label className={styles.formLabel}>
          Windows device
          <select className={styles.formInput} value={fields.device_alias} onChange={(event) => update("device_alias", event.target.value)} disabled={busy}>
            {deviceAliases.length === 0 ? <option value="">No paired Windows devices</option> : deviceAliases.map((alias) => <option key={alias} value={alias}>{alias}</option>)}
          </select>
        </label>
        <label className={styles.formLabel}>
          Exact Windows Local folder
          <input className={styles.formInput} value={fields.windows_root} onChange={(event) => update("windows_root", event.target.value)} placeholder="C:\\Users\\name\\Pictures" disabled={busy} />
        </label>
        <label className={styles.formLabel}>
          Source Profile name
          <input className={styles.formInput} value={fields.profile_name} onChange={(event) => update("profile_name", event.target.value)} placeholder="Family photos" disabled={busy} />
        </label>
        <button type="button" className={styles.updateButton} onClick={identify} disabled={busy || deviceAliases.length === 0}>{busy && !plan ? "Checking..." : "Review Source"}</button>
      </div>
      {pathError && fields.windows_root && <p className={styles.helperText}>{pathError}</p>}
      {plan && !result && (
        <section className={styles.creationReview} aria-label="Windows Local Source review">
          <h4 className={styles.detailHeading}>Review Windows Local Source</h4>
          <div className={styles.creationResultGrid}>
            <div><span className={styles.detailLabel}>Device</span><span>{plan.device_alias}</span></div>
            <div><span className={styles.detailLabel}>Source type</span><span>Local</span></div>
            <div><span className={styles.detailLabel}>Folder</span><span>{plan.windows_root}</span></div>
            <div><span className={styles.detailLabel}>Profile name</span><span>{plan.profile_name}</span></div>
            <div><span className={styles.detailLabel}>Device</span><span>{plan.device_action.includes("reuse") ? "Existing device" : plan.device_action}</span></div>
            <div><span className={styles.detailLabel}>Source Profile</span><span>{profileActionLabel(plan.profile_action)}</span></div>
          </div>
          {plan.warnings.map((warning) => <p key={warning} className={styles.inlineWarning}>{warning}</p>)}
          {plan.blockers.map((blocker) => <p key={blocker} className={styles.bannerError}>{blocker}</p>)}
          <button type="button" className={styles.runButton} onClick={() => void confirm()} disabled={busy || plan.blockers.length > 0 || !["ready", "source_exists"].includes(plan.plan_status)}>Create Source</button>
        </section>
      )}
      {result && <p className={result.status === "completed" ? styles.bannerSuccess : styles.bannerError}>{result.safe_message}</p>}
      {error && <p className={styles.bannerError}>{error}</p>}
    </section>
  );
}

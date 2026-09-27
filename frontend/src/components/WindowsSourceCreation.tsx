"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  confirmWindowsSourceUiCreation,
  getWindowsSourceUiComputers,
  getWindowsSourceUiOperation,
  planWindowsSourceUiCreation,
  resolveWindowsPortableDiscovery,
  startWindowsSourceUiCreationProbe,
  startWindowsPortableDiscovery,
} from "@/lib/api";
import type {
  WindowsSourceUiComputer,
  WindowsSourceUiCreateFields,
  WindowsSourceUiCreatePlan,
  WindowsSourceUiCreateResult,
  WindowsSourceUiPortableCandidate,
  WindowsSourceUiPortableDiscovery,
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
  computers: WindowsSourceUiComputer[];
  sourceType: "local" | "external" | "removable";
  onComplete: () => void;
  launchWindowsAccess?: () => void;
};

export default function WindowsSourceCreation({
  computers,
  sourceType,
  onComplete,
  launchWindowsAccess = invokeWindowsAccess,
}: Props) {
  const [fields, setFields] = useState<WindowsSourceUiCreateFields>({
    access_node_id: computers[0]?.access_node_id ?? "",
    source_type: sourceType,
    device_alias: sourceType === "local" ? computers[0]?.computer_alias ?? "" : "",
    windows_root: "",
    profile_name: "",
  });
  const [discovery, setDiscovery] = useState<WindowsSourceUiPortableDiscovery | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<WindowsSourceUiPortableCandidate | null>(null);
  const [portableFolder, setPortableFolder] = useState("");
  const [probeToken, setProbeToken] = useState<string | null>(null);
  const [plan, setPlan] = useState<WindowsSourceUiCreatePlan | null>(null);
  const [result, setResult] = useState<WindowsSourceUiCreateResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setFields((current) => {
      if (computers.some((computer) => computer.access_node_id === current.access_node_id)) {
        return current;
      }
      const first = computers[0];
      return {
        ...current,
        access_node_id: first?.access_node_id ?? "",
        device_alias: sourceType === "local" ? first?.computer_alias ?? "" : current.device_alias,
      };
    });
  }, [computers, sourceType]);

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

  const waitForAvailableComputer = useCallback(async (accessNodeId?: string) => {
    const deadline = Date.now() + 120_000;
    while (Date.now() < deadline) {
      const current = await getWindowsSourceUiComputers();
      if (current.computers.some((computer) => (
        computer.paired
        && computer.online
        && (!accessNodeId || computer.access_node_id === accessNodeId)
      ))) {
        return;
      }
      await delay(1000);
    }
    throw new Error("The registered Windows Helper did not become available in time.");
  }, []);

  const discover = useCallback(() => {
    if (sourceType === "local") return;
    if (!computers.some((computer) => computer.paired)) {
      setError("Register a Windows computer before detecting Source devices.");
      return;
    }
    launchWindowsAccess();
    setBusy(true);
    setError(null);
    setSelectedCandidate(null);
    void (async () => {
      await waitForAvailableComputer();
      let current = await startWindowsPortableDiscovery(sourceType);
      const deadline = Date.now() + 120_000;
      while (current.stage === "checking_devices" && Date.now() < deadline) {
        await delay(1000);
        current = await resolveWindowsPortableDiscovery(sourceType, current.observation_tokens);
      }
      setDiscovery(current);
      if (current.stage !== "ready") setError(current.safe_message);
    })().catch((caught: unknown) => {
      setError(caught instanceof Error ? caught.message : "Connected devices could not be detected.");
    }).finally(() => setBusy(false));
  }, [computers, launchWindowsAccess, sourceType, waitForAvailableComputer]);

  const chooseCandidate = (candidateToken: string) => {
    const candidate = discovery?.candidates.find((item) => item.candidate_token === candidateToken) ?? null;
    setSelectedCandidate(candidate);
    setPortableFolder("");
    setFields((current) => ({
      ...current,
      access_node_id: "",
      discovery_candidate_token: candidate?.candidate_token ?? null,
      device_alias: candidate?.device_alias ?? "",
      windows_root: candidate?.current_root ?? "",
    }));
    setProbeToken(null);
    setPlan(null);
    setResult(null);
    setError(null);
  };

  const updatePortableFolder = (value: string) => {
    setPortableFolder(value);
    const relative = value.trim().replace(/^[/\\]+/, "");
    setFields((current) => ({
      ...current,
      windows_root: selectedCandidate
        ? `${selectedCandidate.current_root}${relative}`
        : current.windows_root,
    }));
    setProbeToken(null);
    setPlan(null);
    setResult(null);
    setError(null);
  };

  const identify = useCallback(() => {
    const missingRoute = sourceType === "local" ? !fields.access_node_id : !fields.discovery_candidate_token;
    if (missingRoute || !fields.device_alias.trim() || !fields.profile_name.trim() || pathError) {
      setError(pathError ?? "Select the Source device and enter a Profile name.");
      return;
    }
    // Synchronous user gesture: a healthy existing instance safely reuses its OS mutex.
    launchWindowsAccess();
    setBusy(true);
    setError(null);
    void (async () => {
      if (sourceType === "local") {
        await waitForAvailableComputer(fields.access_node_id);
      }
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
  }, [fields, launchWindowsAccess, pathError, sourceType, waitForAvailableComputer]);

  const selectedComputer = computers.find((item) => item.access_node_id === fields.access_node_id);
  const sourceTypeLabel = sourceType === "external" ? "External" : sourceType === "removable" ? "Removable" : "Local";

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
    <section aria-label={`Create Windows ${sourceTypeLabel} Source`}>
      <div className={styles.createSourceControls}>
        {sourceType === "local" && computers.length > 1 && (
          <label className={styles.formLabel}>
            Computer
            <select className={styles.formInput} value={fields.access_node_id} onChange={(event) => {
              const computer = computers.find((item) => item.access_node_id === event.target.value);
              update("access_node_id", event.target.value);
              if (computer) update("device_alias", computer.computer_alias);
            }} disabled={busy}>
              {computers.map((computer) => <option key={computer.access_node_id} value={computer.access_node_id}>{computer.computer_alias}</option>)}
            </select>
          </label>
        )}
        {sourceType === "local" && computers.length === 1 && (
          <div className={styles.detailCard}><span className={styles.detailLabel}>Computer</span><span>{computers[0].computer_alias}</span></div>
        )}
        {sourceType === "local" && computers.length === 0 && (
          <p className={styles.inlineWarning}>Register a Windows computer before adding a Local Source.</p>
        )}
        {sourceType !== "local" && (
          <>
            <button type="button" className={styles.updateButton} onClick={discover} disabled={busy}>{busy && !discovery ? "Detecting..." : `Detect connected ${sourceTypeLabel} devices`}</button>
            {discovery?.stage === "ready" && (
              <label className={styles.formLabel}>
                {`Detected ${sourceTypeLabel} device`}
                <select className={styles.formInput} value={selectedCandidate?.candidate_token ?? ""} onChange={(event) => chooseCandidate(event.target.value)} disabled={busy}>
                  <option value="">Select device...</option>
                  {discovery.candidates.map((candidate) => (
                    <option key={candidate.candidate_token} value={candidate.candidate_token}>
                      {candidate.device_alias ?? `New ${sourceTypeLabel} device`} ({candidate.current_root})
                    </option>
                  ))}
                </select>
              </label>
            )}
            {selectedCandidate && !selectedCandidate.known_device && (
              <label className={styles.formLabel}>
                Device name
                <input className={styles.formInput} value={fields.device_alias} onChange={(event) => update("device_alias", event.target.value)} placeholder="Family Archive Drive" disabled={busy} />
              </label>
            )}
          </>
        )}
        {sourceType === "local" ? (
          <label className={styles.formLabel}>
            Folder
            <input className={styles.formInput} value={fields.windows_root} onChange={(event) => update("windows_root", event.target.value)} placeholder="C:\\Users\\name\\Pictures" disabled={busy} />
          </label>
        ) : selectedCandidate && (
          <label className={styles.formLabel}>
            Folder within device (optional)
            <input className={styles.formInput} value={portableFolder} onChange={(event) => updatePortableFolder(event.target.value)} placeholder="Family Photos" disabled={busy} />
            <span className={styles.helperText}>Current access: {selectedCandidate.current_root}</span>
          </label>
        )}
        <label className={styles.formLabel}>
          Source Profile name
          <input className={styles.formInput} value={fields.profile_name} onChange={(event) => update("profile_name", event.target.value)} placeholder="Family photos" disabled={busy} />
        </label>
        <button type="button" className={styles.updateButton} onClick={identify} disabled={busy || (sourceType === "local" ? computers.length === 0 : !selectedCandidate)}>{busy && !plan ? "Checking..." : "Review Source"}</button>
      </div>
      {pathError && fields.windows_root && <p className={styles.helperText}>{pathError}</p>}
      {plan && !result && (
        <section className={styles.creationReview} aria-label={`Windows ${sourceTypeLabel} Source review`}>
          <h4 className={styles.detailHeading}>{`Review Windows ${sourceTypeLabel} Source`}</h4>
          <div className={styles.creationResultGrid}>
            {sourceType === "local" && <div><span className={styles.detailLabel}>Computer</span><span>{selectedComputer?.computer_alias ?? "-"}</span></div>}
            <div><span className={styles.detailLabel}>Source device</span><span>{plan.device_alias}</span></div>
            <div><span className={styles.detailLabel}>Source type</span><span>{sourceTypeLabel}</span></div>
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

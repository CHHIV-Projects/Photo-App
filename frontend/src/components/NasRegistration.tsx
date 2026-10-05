"use client";

import { useCallback, useEffect, useState } from "react";

import {
  createNasPendingRegistration,
  discoverNasAppliances,
  getNasRegistrations,
} from "@/lib/api";
import type {
  NasDiscoveryCandidate,
  NasPendingRegistrationResponse,
  NasRegistrationSummary,
} from "@/types/ui-api";

import styles from "./ingestion-view.module.css";

interface NasRegistrationProps {
  onLocationsChanged: (preferredLocationId?: string) => void | Promise<void>;
  onInteraction?: () => void;
}

export default function NasRegistration({ onLocationsChanged, onInteraction }: NasRegistrationProps) {
  const [registrations, setRegistrations] = useState<NasRegistrationSummary[]>([]);
  const [candidates, setCandidates] = useState<NasDiscoveryCandidate[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [networkHost, setNetworkHost] = useState("");
  const [shareName, setShareName] = useState("");
  const [applianceName, setApplianceName] = useState("");
  const [pending, setPending] = useState<NasPendingRegistrationResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const response = await getNasRegistrations();
      setRegistrations(response.registrations);
      const preferredLocationId = pending
        ? response.registrations.find((item) => (
          item.share_name.toLocaleLowerCase() === pending.share_name.toLocaleLowerCase()
          && item.location_name === pending.location_name
          && item.registration_status === "registered"
        ))?.location_id
        : undefined;
      void onLocationsChanged(preferredLocationId);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not load registered NAS locations.");
    }
  }, [onLocationsChanged, pending]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function discover() {
    onInteraction?.();
    setBusy(true);
    setMessage(null);
    try {
      const response = await discoverNasAppliances();
      setCandidates(response.candidates);
      setShowForm(true);
      setMessage(
        response.candidates.length > 0
          ? "Choose a discovered NAS or enter its hostname manually. Discovery does not register access."
          : "No NAS was discovered. Enter its hostname manually.",
      );
    } catch (error) {
      setShowForm(true);
      setMessage(error instanceof Error ? error.message : "NAS discovery is unavailable; enter its hostname manually.");
    } finally {
      setBusy(false);
    }
  }

  async function prepare() {
    onInteraction?.();
    setBusy(true);
    setMessage(null);
    setPending(null);
    const generatedLocationName = `${applianceName.trim()} — ${shareName.trim()}`;
    try {
      const response = await createNasPendingRegistration({
        network_host: networkHost.trim(),
        share_name: shareName.trim(),
        appliance_name: applianceName.trim(),
        location_name: generatedLocationName,
      });
      setPending(response);
      setMessage("Registration prepared. Run the exact command on the Photo Organizer Server; credentials are entered only in that terminal.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not prepare NAS registration.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className={styles.detailCard} aria-label="Registered NAS locations">
      <div className={styles.workbenchHeader}>
        <div>
          <span className={styles.detailLabel}>Registered NAS locations</span>
          <p className={styles.helperText}>Each share is registered separately. Credentials never pass through the browser.</p>
        </div>
        <button type="button" className={styles.button} disabled={busy} onClick={() => void refresh()}>
          Refresh status
        </button>
      </div>

      {registrations.map((item) => (
        <div key={item.share_id} className={styles.detailCard}>
          <span>{item.appliance_name} — \\{item.share_name}</span>
          <span className={styles.detailMeta}>Registered share: {item.location_name}</span>
          <span className={styles.detailMeta}>{item.availability.replace("_", " ")} · {item.status_message}</span>
        </div>
      ))}
      {registrations.length === 0 && <p className={styles.helperText}>No NAS location is registered yet.</p>}

      <div className={styles.workbenchControls}>
        <button type="button" className={styles.button} disabled={busy} onClick={() => { onInteraction?.(); setShowForm(true); setPending(null); }}>
          Register NAS manually
        </button>
        <button type="button" className={styles.button} disabled={busy} onClick={() => void discover()}>
          Discover NAS
        </button>
      </div>

      {showForm && (
        <div className={styles.createSourceControls}>
          {candidates.length > 0 && (
            <label className={styles.formLabel}>
              Discovered NAS (optional)
              <select
                className={styles.formInput}
                value=""
                onChange={(event) => {
                  const candidate = candidates.find((item) => item.candidate_id === event.target.value);
                  if (candidate) {
                    onInteraction?.();
                    setNetworkHost(candidate.address_hint);
                    setApplianceName(candidate.suggested_name);
                  }
                }}
              >
                <option value="">Choose a discovery result</option>
                {candidates.map((candidate) => (
                  <option key={candidate.candidate_id} value={candidate.candidate_id}>
                    {candidate.suggested_name} — {candidate.network_host} — {candidate.address_hint}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label className={styles.formLabel}>
            NAS hostname or IP address
            <input className={styles.formInput} autoComplete="off" value={networkHost} onChange={(event) => setNetworkHost(event.target.value)} />
          </label>
          <label className={styles.formLabel}>
            NAS name
            <input className={styles.formInput} autoComplete="off" value={applianceName} onChange={(event) => setApplianceName(event.target.value)} />
          </label>
          <label className={styles.formLabel}>
            SMB share name
            <input className={styles.formInput} autoComplete="off" value={shareName} onChange={(event) => setShareName(event.target.value)} />
          </label>
          {applianceName.trim() && shareName.trim() && (
            <div className={styles.detailCard}>
              <span className={styles.detailLabel}>Registered share name</span>
              <span>{applianceName.trim()} — {shareName.trim()}</span>
              <span className={styles.helperText}>Generated automatically from the NAS and SMB share.</span>
            </div>
          )}
          <button
            type="button"
            className={styles.updateButton}
            disabled={busy || !networkHost.trim() || !applianceName.trim() || !shareName.trim()}
            onClick={() => void prepare()}
          >
            Prepare registration
          </button>
        </div>
      )}

      {pending && (
        <div className={styles.detailCard}>
          <span className={styles.detailLabel}>Run on the Photo Organizer Server</span>
          <code>{pending.operator_command}</code>
          <p className={styles.helperText}>This request expires at {new Date(pending.expires_at).toLocaleString()}.</p>
          <button type="button" className={styles.button} onClick={() => void navigator.clipboard.writeText(pending.operator_command)}>
            Copy command
          </button>
        </div>
      )}
      {message && <p className={styles.helperText} role="status">{message}</p>}
    </section>
  );
}

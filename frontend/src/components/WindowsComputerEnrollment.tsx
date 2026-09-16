"use client";

import { useMemo, useState } from "react";

import { createWindowsHelperPairing, getWindowsHelperStatuses } from "@/lib/api";
import type { WindowsHelperPairingAuthorization } from "@/types/ui-api";

import styles from "./ingestion-view.module.css";


type Props = {
  onPaired: () => void;
};

const HELPER_EXE = "$env:LOCALAPPDATA\\PhotoOrganizer\\WindowsHelper\\bin\\0.5.1\\PhotoOrganizerWindowsHelper.exe";

export default function WindowsComputerEnrollment({ onPaired }: Props) {
  const [open, setOpen] = useState(false);
  const [computerAlias, setComputerAlias] = useState("");
  const [authorization, setAuthorization] = useState<WindowsHelperPairingAuthorization | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paired, setPaired] = useState(false);

  const command = useMemo(() => {
    if (!authorization) return "";
    return `& "${HELPER_EXE}" pair --access-node-id "${authorization.access_node_id}"; if ($LASTEXITCODE -eq 0) { & "${HELPER_EXE}" heartbeat }`;
  }, [authorization]);

  const beginPairing = async () => {
    if (!computerAlias.trim()) {
      setError("Enter a friendly name for the Windows computer.");
      return;
    }
    setBusy(true);
    setError(null);
    setPaired(false);
    try {
      setAuthorization(await createWindowsHelperPairing(computerAlias.trim()));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Pairing could not be prepared.");
    } finally {
      setBusy(false);
    }
  };

  const checkPairing = async () => {
    if (!authorization) return;
    setBusy(true);
    setError(null);
    try {
      const statuses = await getWindowsHelperStatuses();
      const current = statuses.helpers.find((item) => item.access_node_id === authorization.access_node_id);
      if (current?.credential_status !== "active" || !current.last_seen_at) {
        setError("Pairing or the first authenticated heartbeat has not completed yet.");
        return;
      }
      setPaired(true);
      onPaired();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Pairing status could not be checked.");
    } finally {
      setBusy(false);
    }
  };

  if (!open) {
    return <button type="button" className={styles.updateButton} onClick={() => setOpen(true)}>Add / Pair Windows Device</button>;
  }

  return (
    <section className={styles.creationReview} aria-label="Pair Windows computer">
      <div className={styles.workbenchSummaryHeader}>
        <div>
          <h4 className={styles.detailHeading}>Pair a Windows computer</h4>
          <p className={styles.helperText}>This registers the computer providing Helper access. Source devices are identified separately.</p>
        </div>
        <button type="button" className={styles.updateButton} onClick={() => setOpen(false)} disabled={busy}>Cancel</button>
      </div>
      {!authorization && (
        <>
          <label className={styles.formLabel}>
            Computer-friendly name
            <input className={styles.formInput} value={computerAlias} maxLength={255} autoComplete="off" placeholder="Family laptop" onChange={(event) => setComputerAlias(event.target.value)} disabled={busy} />
          </label>
          <button type="button" className={styles.updateButton} onClick={() => void beginPairing()} disabled={busy}>{busy ? "Preparing..." : "Begin Pairing"}</button>
        </>
      )}
      {authorization && !paired && (
        <div className={styles.createSourceControls}>
          <p className={styles.helperText}>On that computer, open PowerShell as the normal signed-in user, run this command, and enter the one-time code only when the Helper prompts for it.</p>
          <label className={styles.formLabel}>
            PowerShell command
            <textarea className={`${styles.formInput} ${styles.readOnlyInput}`} value={command} readOnly rows={4} />
          </label>
          <label className={styles.formLabel}>
            One-time pairing code (expires {new Date(authorization.expires_at).toLocaleTimeString()})
            <textarea className={`${styles.formInput} ${styles.readOnlyInput}`} value={authorization.pairing_code} readOnly rows={3} />
          </label>
          <button type="button" className={styles.updateButton} onClick={() => void checkPairing()} disabled={busy}>{busy ? "Checking..." : "Check Pairing"}</button>
        </div>
      )}
      {paired && <p className={styles.bannerSuccess}>Windows computer paired and authenticated.</p>}
      {error && <p className={styles.bannerError}>{error}</p>}
    </section>
  );
}

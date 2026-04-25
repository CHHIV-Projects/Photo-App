"use client";

import { useCallback, useEffect, useState } from "react";

import { getAdminSummary } from "@/lib/api";
import type { AdminSummaryResponse } from "@/types/ui-api";

import styles from "./admin-view.module.css";

export default function AdminView() {
  const [summary, setSummary] = useState<AdminSummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const loadSummary = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage("");

    try {
      const response = await getAdminSummary();
      setSummary(response);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to load admin summary.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSummary();
  }, [loadSummary]);

  return (
    <section className={styles.adminRoot}>
      <header className={styles.header}>
        <div>
          <p className={styles.kicker}>Milestone 12.18</p>
          <h2 className={styles.title}>Admin Settings Foundation</h2>
          <p className={styles.subtitle}>
            Read-only operational summary with placeholder areas for future maintenance and settings controls.
          </p>
        </div>
        <button type="button" className={styles.refreshButton} onClick={() => void loadSummary()} disabled={isLoading}>
          {isLoading ? "Refreshing..." : "Refresh"}
        </button>
      </header>

      {errorMessage && <div className={styles.errorBanner}>{errorMessage}</div>}

      <div className={styles.grid}>
        <article className={styles.card}>
          <h3 className={styles.cardTitle}>Assets</h3>
          <p className={styles.metric}>{summary?.assets.total ?? 0}</p>
          <p className={styles.meta}>Visible: {summary?.assets.visible ?? 0}</p>
          <p className={styles.meta}>Demoted: {summary?.assets.demoted ?? 0}</p>
        </article>

        <article className={styles.card}>
          <h3 className={styles.cardTitle}>Duplicate Groups</h3>
          <p className={styles.metric}>{summary?.duplicates.total_groups ?? 0}</p>
          <div className={styles.breakdownList}>
            {(summary?.duplicates.by_type ?? []).length === 0 ? (
              <p className={styles.meta}>No typed groups yet.</p>
            ) : (
              (summary?.duplicates.by_type ?? []).map((entry) => (
                <p key={entry.group_type} className={styles.meta}>
                  {entry.group_type}: {entry.count}
                </p>
              ))
            )}
          </div>
        </article>

        <article className={styles.card}>
          <h3 className={styles.cardTitle}>Faces</h3>
          <p className={styles.metric}>{summary?.faces.total ?? 0}</p>
          <p className={styles.meta}>Unassigned: {summary?.faces.unassigned ?? 0}</p>
        </article>

        <article className={styles.card}>
          <h3 className={styles.cardTitle}>Places</h3>
          <p className={styles.metric}>{summary?.places.total ?? 0}</p>
          <p className={styles.meta}>With user label: {summary?.places.with_user_label ?? 0}</p>
          <p className={styles.meta}>Without user label: {summary?.places.without_user_label ?? 0}</p>
          <p className={styles.meta}>Linked to assets: {summary?.places.linked_to_assets ?? 0}</p>
          <p className={styles.meta}>Empty places: {summary?.places.empty ?? 0}</p>
        </article>

        <article className={`${styles.card} ${styles.placeholderCard}`.trim()}>
          <h3 className={styles.cardTitle}>Maintenance</h3>
          <p className={styles.placeholderText}>
            Job triggers and integrity actions will be added in a later milestone.
          </p>
          <button type="button" className={styles.placeholderButton} disabled>
            Run Maintenance Job (Coming Soon)
          </button>
        </article>

        <article className={`${styles.card} ${styles.placeholderCard}`.trim()}>
          <h3 className={styles.cardTitle}>Settings</h3>
          <p className={styles.placeholderText}>
            Configurable thresholds and runtime preferences will be introduced in future milestones.
          </p>
          <button type="button" className={styles.placeholderButton} disabled>
            Edit Settings (Coming Soon)
          </button>
        </article>
      </div>

      <p className={styles.generatedAt}>
        Snapshot time: {summary?.generated_at ? new Date(summary.generated_at).toLocaleString() : "-"}
      </p>
    </section>
  );
}

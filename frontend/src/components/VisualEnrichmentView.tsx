"use client";

import { useEffect, useMemo, useState } from "react";

import {
  getGlobalPlaceObservations,
  patchGlobalPlaceObservation,
  resolveApiUrl,
} from "@/lib/api";
import type { PlaceObservationSummary } from "@/types/ui-api";
import styles from "./visual-enrichment-view.module.css";

interface VisualEnrichmentViewProps {
  onOpenPhoto: (sha256: string) => void;
}

const STATUS_OPTIONS = ["pending", "accepted", "rejected", "ignored"] as const;

type ObservationStatusFilter = (typeof STATUS_OPTIONS)[number];

function shortSha(value: string | null | undefined): string {
  if (!value) return "unknown";
  return value.slice(0, 12);
}

export default function VisualEnrichmentView({ onOpenPhoto }: VisualEnrichmentViewProps) {
  const [statusFilter, setStatusFilter] = useState<ObservationStatusFilter>("pending");
  const [observations, setObservations] = useState<PlaceObservationSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [updatingObservationId, setUpdatingObservationId] = useState<number | null>(null);
  const [expandedObservationIds, setExpandedObservationIds] = useState<Set<number>>(new Set());

  const loadObservations = async (nextStatus: ObservationStatusFilter) => {
    setIsLoading(true);
    setErrorMessage("");
    try {
      const response = await getGlobalPlaceObservations({
        sourceType: "google_vision",
        observationType: "landmark",
        status: nextStatus,
        limit: 200,
        offset: 0,
      });
      setObservations(response.items);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to load landmark/context candidates");
      setObservations([]);
    } finally {
      setIsLoading(false);
    }
  };

  const upsertObservation = (updated: PlaceObservationSummary) => {
    setObservations((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
  };

  const removeObservation = (observationId: number) => {
    setObservations((prev) => prev.filter((item) => item.id !== observationId));
  };

  const handleStatusUpdate = async (
    observationId: number,
    status: "accepted" | "rejected" | "ignored",
  ) => {
    setUpdatingObservationId(observationId);
    setErrorMessage("");
    try {
      const updated = await patchGlobalPlaceObservation(observationId, { status });
      if (statusFilter === "pending" && updated.status !== "pending") {
        removeObservation(observationId);
      } else {
        upsertObservation(updated);
      }
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to update candidate status");
    } finally {
      setUpdatingObservationId(null);
    }
  };

  useEffect(() => {
    void loadObservations(statusFilter);
  }, [statusFilter]);

  const candidateCountLabel = useMemo(() => {
    const count = observations.length;
    return `${count} ${count === 1 ? "candidate" : "candidates"}`;
  }, [observations]);

  return (
    <div className={styles.container}>
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <div>
            <h2 className={styles.sectionTitle}>Landmark / Context Candidates</h2>
            <p className={styles.sectionSubtitle}>
              Review Google Vision landmark/context candidates without changing Place assignment.
            </p>
          </div>
          <div className={styles.headerControls}>
            <label className={styles.filterLabel}>
              Status
              <select
                className={styles.filterSelect}
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value as ObservationStatusFilter)}
              >
                {STATUS_OPTIONS.map((option) => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </select>
            </label>
            <span className={styles.countBadge}>{candidateCountLabel}</span>
          </div>
        </div>

        {isLoading && <p className={styles.loading}>Loading candidates...</p>}
        {errorMessage && <p className={styles.error}>{errorMessage}</p>}
        {!isLoading && observations.length === 0 && (
          <p className={styles.empty}>No Google Vision landmark/context candidates in this status.</p>
        )}

        <div className={styles.candidateList}>
          {observations.map((observation) => {
            const isExpanded = expandedObservationIds.has(observation.id);
            const assetSha = observation.asset?.asset_sha256 ?? observation.asset_sha256;
            const displayName = observation.asset?.filename?.trim() || shortSha(assetSha);
            const previewUrl = resolveApiUrl(observation.asset?.display_url ?? observation.asset?.image_url ?? null);
            const candidateLabel = observation.raw_label
              || observation.formatted_address
              || [observation.city, observation.state, observation.country].filter(Boolean).join(", ")
              || "(No suggested context label)";

            return (
              <article key={observation.id} className={styles.candidateCard}>
                <div className={styles.assetMetaRow}>
                  <div className={styles.thumbnailShell}>
                    {previewUrl ? (
                      <img src={previewUrl} alt={displayName} className={styles.thumbnail} />
                    ) : (
                      <div className={styles.thumbnailPlaceholder}>N/A</div>
                    )}
                  </div>
                  <div className={styles.assetTextCol}>
                    <div className={styles.assetName}>{displayName}</div>
                    <div className={styles.badgeRow}>
                      <span className={styles.badge}>source: {observation.source_type}</span>
                      <span className={styles.badge}>status: {observation.status}</span>
                      <span className={styles.badge}>confidence: {observation.confidence ?? "n/a"}</span>
                      {observation.linked_place && (
                        <span className={styles.badge}>linked place: {observation.linked_place.display_label}</span>
                      )}
                    </div>
                    {observation.created_at_utc && (
                      <div className={styles.metaLine}>Created: {new Date(observation.created_at_utc).toLocaleString()}</div>
                    )}
                  </div>
                </div>

                <div className={styles.candidateLabel}>Suggested context: {candidateLabel}</div>

                <div className={styles.actionRow}>
                  <button
                    type="button"
                    className={styles.primaryButton}
                    disabled={updatingObservationId === observation.id}
                    onClick={() => { void handleStatusUpdate(observation.id, "accepted"); }}
                  >
                    Accept
                  </button>
                  <button
                    type="button"
                    className={styles.dangerButton}
                    disabled={updatingObservationId === observation.id}
                    onClick={() => { void handleStatusUpdate(observation.id, "rejected"); }}
                  >
                    Reject
                  </button>
                  <button
                    type="button"
                    className={styles.secondaryButton}
                    disabled={updatingObservationId === observation.id}
                    onClick={() => { void handleStatusUpdate(observation.id, "ignored"); }}
                  >
                    Ignore
                  </button>
                  <button
                    type="button"
                    className={styles.secondaryButton}
                    onClick={() => {
                      setExpandedObservationIds((prev) => {
                        const next = new Set(prev);
                        if (next.has(observation.id)) {
                          next.delete(observation.id);
                        } else {
                          next.add(observation.id);
                        }
                        return next;
                      });
                    }}
                  >
                    {isExpanded ? "Hide Details" : "Details"}
                  </button>
                  <button
                    type="button"
                    className={styles.secondaryButton}
                    disabled={!assetSha}
                    onClick={() => {
                      if (assetSha) {
                        onOpenPhoto(assetSha);
                      }
                    }}
                  >
                    Open Asset
                  </button>
                </div>

                {isExpanded && (
                  <pre className={styles.detailsBox}>{JSON.stringify({
                    observation_id: observation.id,
                    observation_type: observation.observation_type,
                    latitude: observation.latitude,
                    longitude: observation.longitude,
                    raw_response_json: observation.raw_response_json,
                  }, null, 2)}</pre>
                )}
              </article>
            );
          })}
        </div>
      </section>

      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Candidate Selection</h3>
        <p className={styles.placeholderText}>
          Future workflow: choose candidate pools such as selected assets, collections, albums, place groups,
          no-GPS assets, or duplicate-group canonicals.
        </p>
      </section>

      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Run History / Reports</h3>
        <p className={styles.placeholderText}>
          Google Vision test harness reports are written under storage/logs/google_vision_reports/.
          A future milestone will surface run history here.
        </p>
      </section>

      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Future Labels / Objects</h3>
        <p className={styles.placeholderText}>
          Label and object candidates are currently report-only. A future milestone will review whether they become
          tags/context labels.
        </p>
      </section>

      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Future No-GPS Location Candidates</h3>
        <p className={styles.placeholderText}>
          Assets without GPS will use a separate, more cautious inference workflow. No location data is applied
          automatically.
        </p>
      </section>
    </div>
  );
}

"use client";

import { useEffect, useMemo, useState } from "react";

import {
  acceptObservationAsContext,
  getAssetContextLabels,
  getContextLabelPropagationPreview,
  getGlobalPlaceObservations,
  patchGlobalPlaceObservation,
  propagateContextLabel,
  resolveApiUrl,
} from "@/lib/api";
import type {
  AssetContextLabelSummary,
  ContextLabelPropagationPreviewResponse,
  ContextLabelPropagationResponse,
  PlaceObservationSummary,
} from "@/types/ui-api";
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
  const [contextLabelsByAsset, setContextLabelsByAsset] = useState<Record<string, AssetContextLabelSummary[]>>({});
  const [labelDraftByObservation, setLabelDraftByObservation] = useState<Record<number, string>>({});
  const [propagationPreview, setPropagationPreview] = useState<ContextLabelPropagationPreviewResponse | null>(null);
  const [selectedPropagationTargets, setSelectedPropagationTargets] = useState<Set<string>>(new Set());
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [isPropagating, setIsPropagating] = useState(false);
  const [propagationResult, setPropagationResult] = useState<ContextLabelPropagationResponse | null>(null);

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

  const loadContextLabels = async () => {
    try {
      const response = await getAssetContextLabels({
        contextType: "landmark",
        status: "active",
        limit: 500,
        offset: 0,
      });
      const grouped: Record<string, AssetContextLabelSummary[]> = {};
      for (const item of response.items) {
        grouped[item.asset_sha256] = grouped[item.asset_sha256] ?? [];
        grouped[item.asset_sha256].push(item);
      }
      setContextLabelsByAsset(grouped);
    } catch {
      // Keep candidate loading resilient if context-label list fetch fails.
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

  const handleAcceptAsContext = async (observation: PlaceObservationSummary) => {
    setUpdatingObservationId(observation.id);
    setErrorMessage("");
    try {
      const draft = labelDraftByObservation[observation.id]?.trim();
      const response = await acceptObservationAsContext(observation.id, {
        label: draft || undefined,
      });
      if (statusFilter === "pending" && response.observation_status !== "pending") {
        removeObservation(observation.id);
      } else {
        upsertObservation({
          ...observation,
          status: response.observation_status,
        });
      }

      setContextLabelsByAsset((prev) => {
        const existingForAsset = prev[response.context_label.asset_sha256] ?? [];
        const alreadyThere = existingForAsset.some((item) => item.id === response.context_label.id);
        return {
          ...prev,
          [response.context_label.asset_sha256]: alreadyThere
            ? existingForAsset
            : [response.context_label, ...existingForAsset],
        };
      });
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to accept candidate as context");
    } finally {
      setUpdatingObservationId(null);
    }
  };

  const openPropagationPreview = async (label: AssetContextLabelSummary) => {
    setIsPreviewLoading(true);
    setErrorMessage("");
    setPropagationResult(null);
    try {
      const response = await getContextLabelPropagationPreview(label.id);
      setPropagationPreview(response);
      const defaults = new Set(
        response.targets.filter((item) => item.default_selected && item.selectable).map((item) => item.asset_sha256),
      );
      setSelectedPropagationTargets(defaults);
      if (response.message) {
        setErrorMessage(response.message);
      }
    } catch (err) {
      setPropagationPreview(null);
      setSelectedPropagationTargets(new Set());
      setErrorMessage(err instanceof Error ? err.message : "Failed to load propagation preview");
    } finally {
      setIsPreviewLoading(false);
    }
  };

  const togglePropagationTarget = (assetSha: string) => {
    setSelectedPropagationTargets((prev) => {
      const next = new Set(prev);
      if (next.has(assetSha)) {
        next.delete(assetSha);
      } else {
        next.add(assetSha);
      }
      return next;
    });
  };

  const handleConfirmPropagation = async () => {
    if (!propagationPreview) {
      return;
    }
    setIsPropagating(true);
    setErrorMessage("");
    try {
      const targetList = Array.from(selectedPropagationTargets);
      const result = await propagateContextLabel(propagationPreview.source_label.id, {
        target_asset_sha256s: targetList,
      });
      setPropagationResult(result);
      await loadContextLabels();
      setPropagationPreview(null);
      setSelectedPropagationTargets(new Set());
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to propagate context label");
    } finally {
      setIsPropagating(false);
    }
  };

  useEffect(() => {
    void loadObservations(statusFilter);
  }, [statusFilter]);

  useEffect(() => {
    void loadContextLabels();
  }, []);

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
        {propagationResult && (
          <p className={styles.success}>
            Added: {propagationResult.added_count} | Already present: {propagationResult.already_present_count} |
            Skipped: {propagationResult.skipped_count} | Failed: {propagationResult.failed_count}
          </p>
        )}
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
            const existingContextLabels = assetSha ? (contextLabelsByAsset[assetSha] ?? []) : [];
            const labelDraft = labelDraftByObservation[observation.id] ?? candidateLabel;

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

                <div className={styles.labelInputRow}>
                  <label className={styles.labelInputLabel} htmlFor={`context-label-${observation.id}`}>
                    Context label
                  </label>
                  <input
                    id={`context-label-${observation.id}`}
                    className={styles.labelInput}
                    value={labelDraft}
                    onChange={(event) => {
                      const value = event.target.value;
                      setLabelDraftByObservation((prev) => ({
                        ...prev,
                        [observation.id]: value,
                      }));
                    }}
                    disabled={updatingObservationId === observation.id}
                  />
                </div>

                {existingContextLabels.length > 0 && (
                  <div className={styles.existingContextRow}>
                    <span className={styles.existingContextLabel}>Existing context:</span>
                    <div className={styles.existingContextBadges}>
                      {existingContextLabels.map((item) => (
                        <div key={item.id} className={styles.contextChip}>
                          <span className={styles.badge}>
                            {item.context_type}: {item.label}
                          </span>
                          {item.context_type === "landmark" && item.status === "active" && item.duplicate_group_id ? (
                            <button
                              type="button"
                              className={styles.inlineActionButton}
                              disabled={isPreviewLoading || isPropagating}
                              onClick={() => { void openPropagationPreview(item); }}
                            >
                              Propagate to Duplicate Group
                            </button>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className={styles.actionRow}>
                  <button
                    type="button"
                    className={styles.primaryButton}
                    disabled={updatingObservationId === observation.id}
                    onClick={() => { void handleAcceptAsContext(observation); }}
                  >
                    Accept as Context
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

      {propagationPreview && (
        <section className={styles.section}>
          <h3 className={styles.sectionTitle}>Propagate Context Label</h3>
          <p className={styles.sectionSubtitle}>
            This will apply the accepted context label to selected duplicate-group members. It will not change Places,
            locations, source files, or metadata.
          </p>
          <div className={styles.previewSummary}>
            <span className={styles.badge}>Label: {propagationPreview.source_label.context_type}: {propagationPreview.source_label.label}</span>
            {propagationPreview.duplicate_group_id !== null && (
              <span className={styles.badge}>Duplicate group: #{propagationPreview.duplicate_group_id}</span>
            )}
            <span className={styles.badge}>Eligible targets: {propagationPreview.eligible_target_count}</span>
          </div>

          {propagationPreview.message && <p className={styles.empty}>{propagationPreview.message}</p>}

          {propagationPreview.targets.length > 0 && (
            <div className={styles.targetList}>
              {propagationPreview.targets.map((target) => {
                const previewUrl = resolveApiUrl(target.display_url ?? target.image_url ?? null);
                const checked = selectedPropagationTargets.has(target.asset_sha256);
                return (
                  <label key={target.asset_sha256} className={styles.targetRow}>
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={!target.selectable || isPropagating}
                      onChange={() => togglePropagationTarget(target.asset_sha256)}
                    />
                    <div className={styles.targetThumbShell}>
                      {previewUrl ? (
                        <img src={previewUrl} alt={target.asset_filename} className={styles.thumbnail} />
                      ) : (
                        <div className={styles.thumbnailPlaceholder}>N/A</div>
                      )}
                    </div>
                    <div className={styles.targetText}>
                      <div className={styles.assetName}>{target.asset_filename}</div>
                      <div className={styles.metaLine}>
                        {target.already_has_label ? "already present" : "will add"}
                        {target.is_canonical ? " | canonical" : ""}
                      </div>
                    </div>
                  </label>
                );
              })}
            </div>
          )}

          <div className={styles.actionRow}>
            <button
              type="button"
              className={styles.primaryButton}
              disabled={isPropagating || selectedPropagationTargets.size === 0}
              onClick={() => { void handleConfirmPropagation(); }}
            >
              Confirm Propagation
            </button>
            <button
              type="button"
              className={styles.secondaryButton}
              disabled={isPropagating}
              onClick={() => {
                setPropagationPreview(null);
                setSelectedPropagationTargets(new Set());
              }}
            >
              Cancel
            </button>
          </div>
        </section>
      )}

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

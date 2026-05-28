"use client";

import { useEffect, useMemo, useState } from "react";

import {
  acceptObservationAsContext,
  getAssetContextLabelSummaries,
  getCollections,
  getAssetContextLabels,
  getContextLabelPropagationPreview,
  getGlobalPlaceObservations,
  patchGlobalPlaceObservation,
  previewVisualEnrichmentCandidates,
  propagateContextLabel,
  resolveApiUrl,
  runVisualEnrichmentGoogleVision,
} from "@/lib/api";
import type {
  AssetContextLabelSummary,
  CollectionSummary,
  ContextLabelPropagationPreviewResponse,
  ContextLabelPropagationResponse,
  PlaceObservationSummary,
  VisualEnrichmentCandidatePreviewResponse,
  VisualEnrichmentRunResponse,
  VisualEnrichmentWorkingSetAsset,
} from "@/types/ui-api";
import styles from "./visual-enrichment-view.module.css";

interface VisualEnrichmentViewProps {
  onOpenPhoto: (sha256: string) => void;
  selectedWorkingSetAssets: VisualEnrichmentWorkingSetAsset[];
  onClearWorkingSet: () => void;
}

const STATUS_OPTIONS = ["pending", "accepted", "rejected", "ignored"] as const;

type ObservationStatusFilter = (typeof STATUS_OPTIONS)[number];

function shortSha(value: string | null | undefined): string {
  if (!value) return "unknown";
  return value.slice(0, 12);
}

export default function VisualEnrichmentView({ onOpenPhoto, selectedWorkingSetAssets, onClearWorkingSet }: VisualEnrichmentViewProps) {
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
  const [collections, setCollections] = useState<CollectionSummary[]>([]);
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(null);
  const [canonicalOnly, setCanonicalOnly] = useState(true);
  const [excludeExistingObservations, setExcludeExistingObservations] = useState(true);
  const [excludeExistingContextLabels, setExcludeExistingContextLabels] = useState(true);
  const [candidatePreview, setCandidatePreview] = useState<VisualEnrichmentCandidatePreviewResponse | null>(null);
  const [previewSelection, setPreviewSelection] = useState<Set<string>>(new Set());
  const [candidateSource, setCandidateSource] = useState<"selected" | "collection">("collection");
  const [showCollectionSource, setShowCollectionSource] = useState(false);
  const [isCandidatePreviewLoading, setIsCandidatePreviewLoading] = useState(false);
  const [isRunningCandidates, setIsRunningCandidates] = useState(false);
  const [runResult, setRunResult] = useState<VisualEnrichmentRunResponse | null>(null);
  const [runLiveMode, setRunLiveMode] = useState(true);
  const [runUseMockProvider, setRunUseMockProvider] = useState(false);
  const [runFeatureLandmark, setRunFeatureLandmark] = useState(true);
  const [runFeatureWeb, setRunFeatureWeb] = useState(false);
  const [runFeatureLabel, setRunFeatureLabel] = useState(false);
  const [runFeatureObject, setRunFeatureObject] = useState(false);
  const [showAdvancedDiagnostics, setShowAdvancedDiagnostics] = useState(false);
  const [showDeveloperControls, setShowDeveloperControls] = useState(false);
  const [landmarkSummaryByAsset, setLandmarkSummaryByAsset] = useState<Record<string, { labels: string[]; count: number }>>({});

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
      setLandmarkSummaryByAsset((prev) => {
        const existing = prev[response.context_label.asset_sha256];
        const existingLabels = existing?.labels ?? [];
        if (existingLabels.includes(response.context_label.label)) {
          return prev;
        }
        return {
          ...prev,
          [response.context_label.asset_sha256]: {
            labels: [response.context_label.label, ...existingLabels],
            count: (existing?.count ?? 0) + 1,
          },
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

  const loadCollections = async () => {
    try {
      const response = await getCollections();
      setCollections(response.items);
      if (response.items.length > 0) {
        setSelectedCollectionId((prev) => prev ?? response.items[0].collection_id);
      }
    } catch {
      // Keep remaining visual enrichment workflows available if collection list fails.
    }
  };

  const handlePreviewCandidates = async () => {
    if (!selectedCollectionId) {
      setErrorMessage("Choose a collection before previewing candidates.");
      return;
    }

    setIsCandidatePreviewLoading(true);
    setErrorMessage("");
    setRunResult(null);

    try {
      const preview = await previewVisualEnrichmentCandidates({
        pool_type: "collection",
        pool_id: selectedCollectionId,
        canonical_only: canonicalOnly,
        exclude_existing_observations: excludeExistingObservations,
        exclude_existing_context_labels: excludeExistingContextLabels,
        limit: 50,
      });
      setCandidatePreview(preview);
      setPreviewSelection(new Set(preview.assets.map((item) => item.asset_sha256)));
    } catch (err) {
      setCandidatePreview(null);
      setPreviewSelection(new Set());
      setErrorMessage(err instanceof Error ? err.message : "Failed to preview candidates");
    } finally {
      setIsCandidatePreviewLoading(false);
    }
  };

  const togglePreviewCandidate = (assetSha256: string) => {
    setPreviewSelection((prev) => {
      const next = new Set(prev);
      if (next.has(assetSha256)) {
        next.delete(assetSha256);
      } else {
        next.add(assetSha256);
      }
      return next;
    });
  };

  const handleRunCandidates = async () => {
    const assetSha256s = candidateSource === "selected"
      ? selectedWorkingSetAssets.map((item) => item.asset_sha256)
      : Array.from(previewSelection);

    if (candidateSource === "collection" && !candidatePreview) {
      setErrorMessage("Preview candidates before running.");
      return;
    }

    if (assetSha256s.length === 0) {
      setErrorMessage(candidateSource === "selected" ? "No selected assets available to run." : "Select at least one candidate to run.");
      return;
    }

    if (!runFeatureLandmark && !runFeatureWeb && !runFeatureLabel && !runFeatureObject) {
      setErrorMessage("Enable at least one detection feature before running.");
      return;
    }

    if (runLiveMode) {
      const confirmed = window.confirm(
        runFeatureWeb
          ? "Live mode will call Google Vision for selected assets. Web Detection may return web/entity matches and broader image-context clues. Continue with live run?"
          : "Live mode will call Google Vision for selected assets. Continue with live run?",
      );
      if (!confirmed) {
        return;
      }
    }

    setIsRunningCandidates(true);
    setErrorMessage("");

    try {
      const result = await runVisualEnrichmentGoogleVision({
        asset_sha256s: assetSha256s,
        live: runLiveMode,
        mock_provider: runLiveMode ? false : runUseMockProvider,
        feature_landmark: runFeatureLandmark,
        feature_web: runFeatureWeb,
        feature_label: runFeatureLabel,
        feature_object: runFeatureObject,
      });
      setRunResult(result);
      await loadObservations(statusFilter);
    } catch (err) {
      setRunResult(null);
      setErrorMessage(err instanceof Error ? err.message : "Failed to run visual enrichment candidates");
    } finally {
      setIsRunningCandidates(false);
    }
  };

  useEffect(() => {
    void loadObservations(statusFilter);
  }, [statusFilter]);

  useEffect(() => {
    void loadContextLabels();
  }, []);

  useEffect(() => {
    void loadCollections();
  }, []);

  useEffect(() => {
    if (selectedWorkingSetAssets.length > 0) {
      setCandidateSource("selected");
    } else if (candidateSource === "selected") {
      setCandidateSource("collection");
    }
  }, [selectedWorkingSetAssets, candidateSource]);

  useEffect(() => {
    const shas = selectedWorkingSetAssets.map((item) => item.asset_sha256);
    if (shas.length === 0) {
      return;
    }
    let isCancelled = false;
    async function loadSummary(): Promise<void> {
      try {
        const response = await getAssetContextLabelSummaries(shas);
        if (isCancelled) {
          return;
        }
        const next: Record<string, { labels: string[]; count: number }> = {};
        for (const item of response.items) {
          next[item.asset_sha256] = { labels: item.landmark_labels, count: item.count };
        }
        setLandmarkSummaryByAsset((prev) => ({ ...prev, ...next }));
      } catch {
        // Keep selected-asset mode usable when summary lookup fails.
      }
    }

    void loadSummary();
    return () => {
      isCancelled = true;
    };
  }, [selectedWorkingSetAssets]);

  const candidateCountLabel = useMemo(() => {
    const count = observations.length;
    return `${count} ${count === 1 ? "candidate" : "candidates"}`;
  }, [observations]);

  const runAssetCount = candidateSource === "selected"
    ? selectedWorkingSetAssets.length
    : previewSelection.size;

  const formatLandmarkSummary = (assetSha: string): string | null => {
    const summary = landmarkSummaryByAsset[assetSha];
    if (!summary || summary.count === 0) {
      return null;
    }
    return `Landmark: ${summary.labels[0]}${summary.count > 1 ? ` +${summary.count - 1}` : ""}`;
  };

  const getSelectedAssetStatus = (assetSha: string): string => {
    if ((landmarkSummaryByAsset[assetSha]?.count ?? 0) > 0) {
      return "Accepted context";
    }
    const runAssetResult = runResult?.asset_results.find((item) => item.asset_sha256 === assetSha);
    if (!runAssetResult) {
      return "Not run";
    }
    if (runAssetResult.status === "failed") {
      return "Reviewed / ignored";
    }
    if (runAssetResult.landmarks.length > 0 || runAssetResult.web_entities.length > 0 || runAssetResult.labels.length > 0 || runAssetResult.objects.length > 0) {
      return runAssetResult.no_landmark ? "No landmark found" : "Suggestions available";
    }
    if (runAssetResult.no_landmark) {
      return "No landmark found";
    }
    return "Not run";
  };

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
        <p className={styles.sectionSubtitle}>
          Photo Review selected assets are primary when present. Collection pool remains available as a secondary source.
        </p>

        <div className={styles.sourceSwitchRow}>
          <button
            type="button"
            className={candidateSource === "selected" ? styles.primaryButton : styles.secondaryButton}
            disabled={selectedWorkingSetAssets.length === 0}
            onClick={() => setCandidateSource("selected")}
          >
            Selected Assets from Photo Review ({selectedWorkingSetAssets.length})
          </button>
          <button
            type="button"
            className={candidateSource === "collection" ? styles.primaryButton : styles.secondaryButton}
            onClick={() => {
              setCandidateSource("collection");
              setShowCollectionSource(true);
            }}
          >
            Collection Candidate Pool
          </button>
          {selectedWorkingSetAssets.length > 0 ? (
            <button type="button" className={styles.secondaryButton} onClick={onClearWorkingSet}>
              Clear Selected Working Set
            </button>
          ) : null}
        </div>

        {candidateSource === "selected" && (
          <>
            <div className={styles.previewSummary}>
              <span className={styles.badge}>Working set: {selectedWorkingSetAssets.length}</span>
            </div>
            <div className={styles.workingSetList}>
              {selectedWorkingSetAssets.map((asset) => {
                const previewUrl = resolveApiUrl(asset.display_url ?? asset.image_url ?? null);
                const landmarkSummary = formatLandmarkSummary(asset.asset_sha256);
                return (
                  <article key={asset.asset_sha256} className={styles.workingSetCard}>
                    <div className={styles.targetThumbShell}>
                      {previewUrl ? (
                        <img src={previewUrl} alt={asset.filename} className={styles.thumbnail} />
                      ) : (
                        <div className={styles.thumbnailPlaceholder}>N/A</div>
                      )}
                    </div>
                    <div className={styles.targetText}>
                      <div className={styles.assetName}>{asset.filename}</div>
                      <div className={styles.metaLine}>
                        {shortSha(asset.asset_sha256)}
                        {asset.is_canonical ? " | canonical" : " | duplicate"}
                        {asset.duplicate_group_id ? ` | group #${asset.duplicate_group_id}` : ""}
                      </div>
                      <div className={styles.metaLine}>{getSelectedAssetStatus(asset.asset_sha256)}</div>
                      {landmarkSummary ? <div className={styles.metaLine}>{landmarkSummary}</div> : null}
                    </div>
                    <button
                      type="button"
                      className={styles.secondaryButton}
                      onClick={() => onOpenPhoto(asset.asset_sha256)}
                    >
                      Open
                    </button>
                  </article>
                );
              })}
            </div>
          </>
        )}

        {candidateSource === "collection" && (
          <>
            {selectedWorkingSetAssets.length > 0 && !showCollectionSource ? (
              <div className={styles.previewSummary}>
                <span className={styles.badge}>Collection source is secondary while selected assets are active.</span>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={() => setShowCollectionSource(true)}
                >
                  Show Collection Source
                </button>
              </div>
            ) : null}

            {(selectedWorkingSetAssets.length === 0 || showCollectionSource) ? (
              <>
                <div className={styles.selectionControls}>
          <label className={styles.filterLabel}>
            Collection
            <select
              className={styles.filterSelect}
              value={selectedCollectionId ?? ""}
              onChange={(event) => setSelectedCollectionId(Number(event.target.value) || null)}
            >
              {collections.length === 0 && <option value="">No collections</option>}
              {collections.map((item) => (
                <option key={item.collection_id} value={item.collection_id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>

          <label className={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={canonicalOnly}
              onChange={(event) => setCanonicalOnly(event.target.checked)}
            />
            Canonical only
          </label>

          <label className={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={excludeExistingObservations}
              onChange={(event) => setExcludeExistingObservations(event.target.checked)}
            />
            Exclude previously reviewed landmark observations (pending/accepted/ignored/rejected)
          </label>

          <label className={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={excludeExistingContextLabels}
              onChange={(event) => setExcludeExistingContextLabels(event.target.checked)}
            />
            Exclude existing landmark context labels
          </label>

          <button
            type="button"
            className={styles.primaryButton}
            disabled={isCandidatePreviewLoading || !selectedCollectionId}
            onClick={() => { void handlePreviewCandidates(); }}
          >
            {isCandidatePreviewLoading ? "Previewing..." : "Preview Candidates"}
          </button>
                </div>

                {candidatePreview && (
              <>
                <div className={styles.previewSummary}>
                  <span className={styles.badge}>Candidates: {candidatePreview.candidate_count}</span>
                  <span className={styles.badge}>Excluded observations: {candidatePreview.excluded_existing_observations_count}</span>
                  <span className={styles.badge}>Excluded context labels: {candidatePreview.excluded_existing_context_labels_count}</span>
                  <span className={styles.badge}>Run count: {candidatePreview.run_count}</span>
                  <span className={styles.badge}>Showing: {candidatePreview.showing_count}</span>
                </div>

                <div className={styles.previewTable}>
                  {candidatePreview.assets.map((asset) => {
                    const checked = previewSelection.has(asset.asset_sha256);
                    const previewUrl = resolveApiUrl(asset.display_url ?? asset.image_url ?? null);
                    return (
                      <label key={asset.asset_sha256} className={styles.targetRow}>
                        <input
                          type="checkbox"
                          checked={checked}
                          disabled={isRunningCandidates}
                          onChange={() => togglePreviewCandidate(asset.asset_sha256)}
                        />
                        <div className={styles.targetThumbShell}>
                          {previewUrl ? (
                            <img src={previewUrl} alt={asset.filename} className={styles.thumbnail} />
                          ) : (
                            <div className={styles.thumbnailPlaceholder}>N/A</div>
                          )}
                        </div>
                        <div className={styles.targetText}>
                          <div className={styles.assetName}>{asset.filename}</div>
                          <div className={styles.metaLine}>
                            {shortSha(asset.asset_sha256)}
                            {asset.is_canonical ? " | canonical" : " | duplicate"}
                            {asset.duplicate_group_id ? ` | group #${asset.duplicate_group_id}` : ""}
                            {asset.has_landmark_observation ? " | has observation" : ""}
                            {asset.has_landmark_context_label ? " | has context label" : ""}
                          </div>
                        </div>
                        <button
                          type="button"
                          className={styles.secondaryButton}
                          disabled={isRunningCandidates}
                          onClick={(event) => {
                            event.preventDefault();
                            onOpenPhoto(asset.asset_sha256);
                          }}
                        >
                          Open
                        </button>
                      </label>
                    );
                  })}
                </div>
              </>
                )}
              </>
            ) : null}
          </>
        )}

        <div className={styles.runControls}>
          <span className={styles.badge}>Mode: {runLiveMode ? "Live" : "Dry-run"}</span>
          <button
            type="button"
            className={styles.secondaryButton}
            disabled={isRunningCandidates}
            onClick={() => setShowAdvancedDiagnostics((prev) => !prev)}
          >
            {showAdvancedDiagnostics ? "Hide Diagnostics" : "Diagnostics"}
          </button>
          <button
            type="button"
            className={styles.secondaryButton}
            disabled={isRunningCandidates}
            onClick={() => setShowDeveloperControls((prev) => !prev)}
          >
            {showDeveloperControls ? "Hide Developer" : "Developer Options"}
          </button>

          <button
            type="button"
            className={styles.primaryButton}
            disabled={isRunningCandidates || runAssetCount === 0}
            onClick={() => { void handleRunCandidates(); }}
          >
            {isRunningCandidates ? "Running..." : `Run Selected (${runAssetCount})`}
          </button>
        </div>

        {showAdvancedDiagnostics && (
          <div className={styles.advancedPanel}>
            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={runFeatureLandmark}
                onChange={(event) => setRunFeatureLandmark(event.target.checked)}
                disabled={isRunningCandidates}
              />
              Landmark Detection
            </label>
            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={runFeatureWeb}
                onChange={(event) => setRunFeatureWeb(event.target.checked)}
                disabled={isRunningCandidates}
              />
              Web Detection
            </label>
            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={runFeatureLabel}
                onChange={(event) => setRunFeatureLabel(event.target.checked)}
                disabled={isRunningCandidates}
              />
              Label Diagnostics
            </label>
            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={runFeatureObject}
                onChange={(event) => setRunFeatureObject(event.target.checked)}
                disabled={isRunningCandidates}
              />
              Object Diagnostics
            </label>
          </div>
        )}

        {showDeveloperControls && (
          <div className={styles.advancedPanel}>
            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={runLiveMode}
                onChange={(event) => {
                  const nextLiveMode = event.target.checked;
                  setRunLiveMode(nextLiveMode);
                  if (nextLiveMode) {
                    setRunUseMockProvider(false);
                  }
                }}
                disabled={isRunningCandidates}
              />
              Use live provider calls
            </label>
            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={runUseMockProvider}
                onChange={(event) => setRunUseMockProvider(event.target.checked)}
                disabled={isRunningCandidates || runLiveMode}
              />
              Use mock provider in dry-run
            </label>
          </div>
        )}

        {runResult && (
          <>
            <p className={styles.success}>
              Mode: {runResult.mode} | Requested: {runResult.requested_count} | Processed: {runResult.processed_count} |
              Created pending observations: {runResult.observations_created_count} | No landmark: {runResult.no_landmark_count} |
              Failed: {runResult.failed_count}
            </p>
            <div className={styles.resultsPanel}>
              {runResult.asset_results.map((assetResult) => (
                <article key={assetResult.asset_sha256} className={styles.resultCard}>
                  <div className={styles.assetName}>{assetResult.filename}</div>
                  <div className={styles.metaLine}>
                    {shortSha(assetResult.asset_sha256)} | status: {assetResult.status}
                    {assetResult.no_landmark ? " | no landmark" : ""}
                    {assetResult.error ? ` | error: ${assetResult.error}` : ""}
                  </div>
                  <div className={styles.resultGrid}>
                    <div>
                      <strong>Landmarks:</strong>{" "}
                      {assetResult.landmarks.length > 0
                        ? assetResult.landmarks.map((item) => `${item.description} (${item.score ?? "n/a"})`).join("; ")
                        : "none"}
                    </div>
                    {runResult.features_requested.includes("web") && (
                      <div>
                        <strong>Web Entities:</strong>{" "}
                        {assetResult.web_entities.length > 0
                          ? assetResult.web_entities.map((item) => `${item.description} (${item.score ?? "n/a"})`).join("; ")
                          : "none"}
                      </div>
                    )}
                    {runResult.features_requested.includes("web") && (
                      <div>
                        <strong>Best Guess:</strong>{" "}
                        {assetResult.best_guess_labels.length > 0 ? assetResult.best_guess_labels.join("; ") : "none"}
                      </div>
                    )}
                    {runResult.features_requested.includes("label") && (
                      <div>
                        <strong>Labels:</strong>{" "}
                        {assetResult.labels.length > 0
                          ? assetResult.labels.map((item) => `${item.description} (${item.score ?? "n/a"})`).join("; ")
                          : "none"}
                      </div>
                    )}
                    {runResult.features_requested.includes("object") && (
                      <div>
                        <strong>Objects:</strong>{" "}
                        {assetResult.objects.length > 0
                          ? assetResult.objects.map((item) => `${item.name} (${item.score ?? "n/a"})`).join("; ")
                          : "none"}
                      </div>
                    )}
                  </div>
                  <div className={styles.metaLine}>Created observations: {assetResult.created_observations}</div>
                </article>
              ))}
            </div>
          </>
        )}
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

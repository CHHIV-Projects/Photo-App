"use client";

import { useEffect, useMemo, useState } from "react";

import {
  acceptObservationAsContext,
  createAssetContextLabel,
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

type ReviewSuggestion = {
  key: string;
  label: string;
  sourceType: "google_vision" | "google_vision_web";
  confidence: number | null;
};

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
  const [assetRunBySha, setAssetRunBySha] = useState<Record<string, VisualEnrichmentRunResponse["asset_results"][number]>>({});
  const [selectedSuggestionByAsset, setSelectedSuggestionByAsset] = useState<Record<string, string>>({});
  const [manualLabelByAsset, setManualLabelByAsset] = useState<Record<string, string>>({});
  const [ignoredAssets, setIgnoredAssets] = useState<Set<string>>(new Set());
  const [rejectedAssets, setRejectedAssets] = useState<Set<string>>(new Set());
  const [runningMoreContextByAsset, setRunningMoreContextByAsset] = useState<Record<string, boolean>>({});
  const [showMoreContextByAsset, setShowMoreContextByAsset] = useState<Record<string, boolean>>({});
  const [moreContextOptionsByAsset, setMoreContextOptionsByAsset] = useState<
    Record<string, { landmark: boolean; web: boolean; label: boolean; object: boolean }>
  >({});

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

  const mergeRunAssets = (result: VisualEnrichmentRunResponse) => {
    setAssetRunBySha((prev) => {
      const next = { ...prev };
      for (const item of result.asset_results) {
        next[item.asset_sha256] = item;
      }
      return next;
    });
  };

  const getReviewSuggestions = (assetSha256: string): ReviewSuggestion[] => {
    const runAsset = assetRunBySha[assetSha256];
    if (!runAsset) {
      return [];
    }
    const items: ReviewSuggestion[] = [];
    for (const landmark of runAsset.landmarks) {
      if (!landmark.description) {
        continue;
      }
      items.push({
        key: `landmark:${landmark.description}`,
        label: `Landmark: ${landmark.description}`,
        sourceType: "google_vision",
        confidence: landmark.score,
      });
    }
    for (const entity of runAsset.web_entities) {
      if (!entity.description) {
        continue;
      }
      items.push({
        key: `web:${entity.description}`,
        label: `Web Entity: ${entity.description}`,
        sourceType: "google_vision_web",
        confidence: entity.score,
      });
    }
    for (const guess of runAsset.best_guess_labels) {
      if (!guess) {
        continue;
      }
      items.push({
        key: `best_guess:${guess}`,
        label: `Best Guess: ${guess}`,
        sourceType: "google_vision_web",
        confidence: null,
      });
    }
    return items;
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
    const useSelectedAssets = selectedWorkingSetAssets.length > 0 || candidateSource === "selected";
    const assetSha256s = useSelectedAssets
      ? selectedWorkingSetAssets.map((item) => item.asset_sha256)
      : Array.from(previewSelection);

    if (!useSelectedAssets && !candidatePreview) {
      setErrorMessage("Preview candidates before running.");
      return;
    }

    if (assetSha256s.length === 0) {
      setErrorMessage(useSelectedAssets ? "No selected assets available to run." : "Select at least one candidate to run.");
      return;
    }

    if (!useSelectedAssets && !runFeatureLandmark && !runFeatureWeb && !runFeatureLabel && !runFeatureObject) {
      setErrorMessage("Enable at least one detection feature before running.");
      return;
    }

    if (runLiveMode) {
      const confirmed = window.confirm(
        useSelectedAssets
          ? "Live mode will run landmark detection for selected assets. Continue with live run?"
          : (runFeatureWeb
              ? "Live mode will call Google Vision for selected assets. Web Detection may return web/entity matches and broader image-context clues. Continue with live run?"
              : "Live mode will call Google Vision for selected assets. Continue with live run?"),
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
        feature_landmark: useSelectedAssets ? true : runFeatureLandmark,
        feature_web: useSelectedAssets ? false : runFeatureWeb,
        feature_label: useSelectedAssets ? false : runFeatureLabel,
        feature_object: useSelectedAssets ? false : runFeatureObject,
      });
      setRunResult(result);
      mergeRunAssets(result);
      await loadObservations(statusFilter);
    } catch (err) {
      setRunResult(null);
      setErrorMessage(err instanceof Error ? err.message : "Failed to run visual enrichment candidates");
    } finally {
      setIsRunningCandidates(false);
    }
  };

  const ensureMoreContextOptions = (assetSha256: string) => {
    setMoreContextOptionsByAsset((prev) => {
      if (prev[assetSha256]) {
        return prev;
      }
      return {
        ...prev,
        [assetSha256]: {
          landmark: false,
          web: true,
          label: true,
          object: true,
        },
      };
    });
  };

  const handleRunMoreContext = async (assetSha256: string) => {
    const options = moreContextOptionsByAsset[assetSha256] ?? {
      landmark: false,
      web: true,
      label: true,
      object: true,
    };
    if (!options.landmark && !options.web && !options.label && !options.object) {
      setErrorMessage("Select at least one feature before running more context.");
      return;
    }

    if (runLiveMode) {
      const confirmed = window.confirm("Live mode will run additional context features for this asset. Continue?");
      if (!confirmed) {
        return;
      }
    }

    setRunningMoreContextByAsset((prev) => ({ ...prev, [assetSha256]: true }));
    setErrorMessage("");
    try {
      const result = await runVisualEnrichmentGoogleVision({
        asset_sha256s: [assetSha256],
        live: runLiveMode,
        mock_provider: runLiveMode ? false : runUseMockProvider,
        feature_landmark: options.landmark,
        feature_web: options.web,
        feature_label: options.label,
        feature_object: options.object,
      });
      mergeRunAssets(result);
      await loadObservations(statusFilter);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to run more context for asset");
    } finally {
      setRunningMoreContextByAsset((prev) => ({ ...prev, [assetSha256]: false }));
    }
  };

  const handleAcceptSelectedSuggestion = async (assetSha256: string) => {
    const selectedKey = selectedSuggestionByAsset[assetSha256];
    if (!selectedKey) {
      setErrorMessage("Select one context suggestion before accepting.");
      return;
    }
    const suggestion = getReviewSuggestions(assetSha256).find((item) => item.key === selectedKey);
    if (!suggestion) {
      setErrorMessage("Selected suggestion is no longer available.");
      return;
    }

    setUpdatingObservationId(-1);
    setErrorMessage("");
    try {
      const response = await createAssetContextLabel({
        asset_sha256: assetSha256,
        label: suggestion.label.replace(/^Landmark: |^Web Entity: |^Best Guess: /, ""),
        context_type: "landmark",
        source_type: suggestion.sourceType,
        confidence: suggestion.confidence,
      });
      setLandmarkSummaryByAsset((prev) => {
        const existing = prev[assetSha256];
        const labels = existing?.labels ?? [];
        if (labels.includes(response.context_label.label)) {
          return prev;
        }
        return {
          ...prev,
          [assetSha256]: {
            labels: [response.context_label.label, ...labels],
            count: (existing?.count ?? 0) + 1,
          },
        };
      });
      setRejectedAssets((prev) => {
        const next = new Set(prev);
        next.delete(assetSha256);
        return next;
      });
      setIgnoredAssets((prev) => {
        const next = new Set(prev);
        next.delete(assetSha256);
        return next;
      });
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to accept selected context suggestion");
    } finally {
      setUpdatingObservationId(null);
    }
  };

  const handleAcceptManualEntry = async (assetSha256: string) => {
    const manualLabel = (manualLabelByAsset[assetSha256] ?? "").trim();
    if (!manualLabel) {
      setErrorMessage("Enter a manual context label before accepting.");
      return;
    }

    setUpdatingObservationId(-1);
    setErrorMessage("");
    try {
      const response = await createAssetContextLabel({
        asset_sha256: assetSha256,
        label: manualLabel,
        context_type: "landmark",
        source_type: "user",
        confidence: null,
      });
      setLandmarkSummaryByAsset((prev) => {
        const existing = prev[assetSha256];
        const labels = existing?.labels ?? [];
        if (labels.includes(response.context_label.label)) {
          return prev;
        }
        return {
          ...prev,
          [assetSha256]: {
            labels: [response.context_label.label, ...labels],
            count: (existing?.count ?? 0) + 1,
          },
        };
      });
      setRejectedAssets((prev) => {
        const next = new Set(prev);
        next.delete(assetSha256);
        return next;
      });
      setIgnoredAssets((prev) => {
        const next = new Set(prev);
        next.delete(assetSha256);
        return next;
      });
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to accept manual context label");
    } finally {
      setUpdatingObservationId(null);
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
      setShowCollectionSource(false);
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

  const hasSelectedWorkingSet = selectedWorkingSetAssets.length > 0;

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
    if (rejectedAssets.has(assetSha)) {
      return "Reviewed / rejected";
    }
    if (ignoredAssets.has(assetSha)) {
      return "Reviewed / ignored";
    }
    const runAssetResult = assetRunBySha[assetSha] ?? runResult?.asset_results.find((item) => item.asset_sha256 === assetSha);
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
      {!hasSelectedWorkingSet && (
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
      )}

      {!hasSelectedWorkingSet && propagationPreview && (
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
          Photo Review selected assets are the primary review workflow. Collection pool is available as a secondary source.
        </p>
        {errorMessage && <p className={styles.error}>{errorMessage}</p>}
        {propagationResult && (
          <p className={styles.success}>
            Added: {propagationResult.added_count} | Already present: {propagationResult.already_present_count} |
            Skipped: {propagationResult.skipped_count} | Failed: {propagationResult.failed_count}
          </p>
        )}

        {hasSelectedWorkingSet && (
          <>
            <div className={styles.previewSummary}>
              <span className={styles.badge}>Working set: {selectedWorkingSetAssets.length}</span>
              <button
                type="button"
                className={styles.primaryButton}
                disabled={isRunningCandidates || selectedWorkingSetAssets.length === 0}
                onClick={() => { void handleRunCandidates(); }}
              >
                {isRunningCandidates ? "Running..." : `Run Landmark Detection (${selectedWorkingSetAssets.length})`}
              </button>
              <button type="button" className={styles.secondaryButton} onClick={onClearWorkingSet}>
                Clear Selected Working Set
              </button>
            </div>
            <div className={styles.workingSetList}>
              {selectedWorkingSetAssets.map((asset) => {
                const previewUrl = resolveApiUrl(asset.display_url ?? asset.image_url ?? null);
                const landmarkSummary = formatLandmarkSummary(asset.asset_sha256);
                return (
                  <article key={asset.asset_sha256} className={styles.workingSetCard}>
                    <div className={styles.workingSetThumbShell}>
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
                  </article>
                );
              })}
            </div>
          </>
        )}

        {(!hasSelectedWorkingSet || showCollectionSource) && (
          <>
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
          </>
        )}

        {hasSelectedWorkingSet && !showCollectionSource ? (
          <div className={styles.previewSummary}>
            <span className={styles.badge}>Collection candidate pool is collapsed while selected assets are active.</span>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={() => {
                setShowCollectionSource(true);
                setCandidateSource("collection");
              }}
            >
              Show Collection Candidate Pool
            </button>
          </div>
        ) : null}

        {hasSelectedWorkingSet && showCollectionSource ? (
          <div className={styles.previewSummary}>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={() => {
                setShowCollectionSource(false);
                setCandidateSource("selected");
              }}
            >
              Hide Collection Candidate Pool
            </button>
          </div>
        ) : null}

        <div className={styles.runControls}>
          <span className={styles.badge}>Mode: {runLiveMode ? "Live" : "Dry-run"}</span>
          {!hasSelectedWorkingSet && (
            <button
              type="button"
              className={styles.secondaryButton}
              disabled={isRunningCandidates}
              onClick={() => setShowAdvancedDiagnostics((prev) => !prev)}
            >
              {showAdvancedDiagnostics ? "Hide Diagnostics" : "Diagnostics"}
            </button>
          )}
          <button
            type="button"
            className={styles.secondaryButton}
            disabled={isRunningCandidates}
            onClick={() => setShowDeveloperControls((prev) => !prev)}
          >
            {showDeveloperControls ? "Hide Developer" : "Developer Options"}
          </button>

          {!hasSelectedWorkingSet && (
            <button
              type="button"
              className={styles.primaryButton}
              disabled={isRunningCandidates || runAssetCount === 0}
              onClick={() => { void handleRunCandidates(); }}
            >
              {isRunningCandidates ? "Running..." : `Run Selected (${runAssetCount})`}
            </button>
          )}
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

        {hasSelectedWorkingSet && (
          <div className={styles.assetReviewList}>
            {selectedWorkingSetAssets.map((asset) => {
              const previewUrl = resolveApiUrl(asset.display_url ?? asset.image_url ?? null);
              const assetStatus = getSelectedAssetStatus(asset.asset_sha256);
              const suggestions = getReviewSuggestions(asset.asset_sha256);
              const selectedSuggestion = selectedSuggestionByAsset[asset.asset_sha256] ?? "";
              const moreContext = moreContextOptionsByAsset[asset.asset_sha256] ?? {
                landmark: false,
                web: true,
                label: true,
                object: true,
              };
              const isRunningMoreContext = runningMoreContextByAsset[asset.asset_sha256] ?? false;

              return (
                <article key={asset.asset_sha256} className={styles.assetReviewCard}>
                  <div className={styles.assetReviewPreview}>
                    {previewUrl ? (
                      <img src={previewUrl} alt={asset.filename} className={styles.assetReviewImage} />
                    ) : (
                      <div className={styles.assetReviewPlaceholder}>N/A</div>
                    )}
                  </div>
                  <div className={styles.assetReviewBody}>
                    <div className={styles.assetName}>{asset.filename}</div>
                    <div className={styles.metaLine}>
                      {shortSha(asset.asset_sha256)}
                      {asset.is_canonical ? " | canonical" : " | duplicate"}
                      {asset.duplicate_group_id ? ` | group #${asset.duplicate_group_id}` : ""}
                    </div>
                    <div className={styles.metaLine}>Status: {assetStatus}</div>
                    {formatLandmarkSummary(asset.asset_sha256) ? (
                      <div className={styles.metaLine}>{formatLandmarkSummary(asset.asset_sha256)}</div>
                    ) : null}

                    <div className={styles.suggestionBlock}>
                      <div className={styles.suggestionTitle}>Detected Suggestions (select one)</div>
                      {suggestions.length === 0 ? (
                        <div className={styles.metaLine}>No suggestions yet. Run landmark or more context first.</div>
                      ) : (
                        <div className={styles.suggestionList}>
                          {suggestions.map((item) => (
                            <label key={item.key} className={styles.suggestionRow}>
                              <input
                                type="radio"
                                name={`suggestion-${asset.asset_sha256}`}
                                checked={selectedSuggestion === item.key}
                                onChange={() => {
                                  setSelectedSuggestionByAsset((prev) => ({
                                    ...prev,
                                    [asset.asset_sha256]: item.key,
                                  }));
                                }}
                              />
                              <span>{item.label}</span>
                              {item.confidence !== null ? <span className={styles.metaLine}>({item.confidence})</span> : null}
                            </label>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className={styles.manualEntryRow}>
                      <label className={styles.labelInputLabel} htmlFor={`manual-label-${asset.asset_sha256}`}>Manual Context Label</label>
                      <input
                        id={`manual-label-${asset.asset_sha256}`}
                        className={styles.labelInput}
                        value={manualLabelByAsset[asset.asset_sha256] ?? ""}
                        onChange={(event) => {
                          const value = event.target.value;
                          setManualLabelByAsset((prev) => ({ ...prev, [asset.asset_sha256]: value }));
                        }}
                        placeholder="Type landmark/context label"
                      />
                    </div>

                    <div className={styles.actionRow}>
                      <button
                        type="button"
                        className={styles.primaryButton}
                        disabled={updatingObservationId === -1 || !selectedSuggestion}
                        onClick={() => { void handleAcceptSelectedSuggestion(asset.asset_sha256); }}
                      >
                        Accept Selected as Context
                      </button>
                      <button
                        type="button"
                        className={styles.secondaryButton}
                        disabled={updatingObservationId === -1}
                        onClick={() => { void handleAcceptManualEntry(asset.asset_sha256); }}
                      >
                        Accept Manual Entry
                      </button>
                      <button
                        type="button"
                        className={styles.dangerButton}
                        onClick={() => {
                          setRejectedAssets((prev) => new Set(prev).add(asset.asset_sha256));
                          setIgnoredAssets((prev) => {
                            const next = new Set(prev);
                            next.delete(asset.asset_sha256);
                            return next;
                          });
                        }}
                      >
                        Reject
                      </button>
                      <button
                        type="button"
                        className={styles.secondaryButton}
                        onClick={() => {
                          setIgnoredAssets((prev) => new Set(prev).add(asset.asset_sha256));
                          setRejectedAssets((prev) => {
                            const next = new Set(prev);
                            next.delete(asset.asset_sha256);
                            return next;
                          });
                        }}
                      >
                        Ignore
                      </button>
                      <button
                        type="button"
                        className={styles.secondaryButton}
                        onClick={() => {
                          setShowMoreContextByAsset((prev) => ({
                            ...prev,
                            [asset.asset_sha256]: !prev[asset.asset_sha256],
                          }));
                          ensureMoreContextOptions(asset.asset_sha256);
                        }}
                      >
                        {showMoreContextByAsset[asset.asset_sha256] ? "Hide More Context" : "Run More Context"}
                      </button>
                      <button
                        type="button"
                        className={styles.secondaryButton}
                        onClick={() => onOpenPhoto(asset.asset_sha256)}
                      >
                        Open Asset
                      </button>
                    </div>

                    {showMoreContextByAsset[asset.asset_sha256] ? (
                      <div className={styles.advancedPanel}>
                        <label className={styles.checkboxLabel}>
                          <input
                            type="checkbox"
                            checked={moreContext.landmark}
                            onChange={(event) => setMoreContextOptionsByAsset((prev) => ({
                              ...prev,
                              [asset.asset_sha256]: { ...moreContext, landmark: event.target.checked },
                            }))}
                          />
                          Landmark
                        </label>
                        <label className={styles.checkboxLabel}>
                          <input
                            type="checkbox"
                            checked={moreContext.web}
                            onChange={(event) => setMoreContextOptionsByAsset((prev) => ({
                              ...prev,
                              [asset.asset_sha256]: { ...moreContext, web: event.target.checked },
                            }))}
                          />
                          Web
                        </label>
                        <label className={styles.checkboxLabel}>
                          <input
                            type="checkbox"
                            checked={moreContext.label}
                            onChange={(event) => setMoreContextOptionsByAsset((prev) => ({
                              ...prev,
                              [asset.asset_sha256]: { ...moreContext, label: event.target.checked },
                            }))}
                          />
                          Label
                        </label>
                        <label className={styles.checkboxLabel}>
                          <input
                            type="checkbox"
                            checked={moreContext.object}
                            onChange={(event) => setMoreContextOptionsByAsset((prev) => ({
                              ...prev,
                              [asset.asset_sha256]: { ...moreContext, object: event.target.checked },
                            }))}
                          />
                          Object
                        </label>
                        <button
                          type="button"
                          className={styles.primaryButton}
                          disabled={isRunningMoreContext}
                          onClick={() => { void handleRunMoreContext(asset.asset_sha256); }}
                        >
                          {isRunningMoreContext ? "Running..." : "Run More Context"}
                        </button>
                      </div>
                    ) : null}
                  </div>
                </article>
              );
            })}
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

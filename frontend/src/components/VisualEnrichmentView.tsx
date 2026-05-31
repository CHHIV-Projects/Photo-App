"use client";

import { useEffect, useMemo, useState } from "react";

import {
  createAssetContextLabel,
  getAssetContextLabels,
  getAssetContextLabelSummaries,
  getContextLabelPropagationPreview,
  getGlobalPlaceObservations,
  patchGlobalPlaceObservation,
  propagateContextLabel,
  resolveApiUrl,
  runVisualEnrichmentGoogleVision,
} from "@/lib/api";
import type {
  AssetContextLabelSummary,
  ContextLabelPropagationPreviewResponse,
  ContextLabelPropagationResponse,
  VisualEnrichmentRunResponse,
  VisualEnrichmentWorkingSetAsset,
} from "@/types/ui-api";
import styles from "./visual-enrichment-view.module.css";

interface VisualEnrichmentViewProps {
  onOpenPhoto: (sha256: string) => void;
  selectedWorkingSetAssets: VisualEnrichmentWorkingSetAsset[];
  onClearWorkingSet: () => void;
}

type ReviewSuggestion = {
  key: string;
  label: string;
  sourceType: "google_vision" | "google_vision_web";
  confidence: number | null;
};

type ObservationLandmarkSuggestion = {
  label: string;
  confidence: number | null;
};

type AssetObservationReviewState = {
  hasPending: boolean;
  hasAccepted: boolean;
  hasRejected: boolean;
  hasIgnored: boolean;
};

type QueueWorkItem = {
  representative: VisualEnrichmentWorkingSetAsset;
  selectedCount: number;
  canonicalUnavailable: boolean;
};

function shortSha(value: string | null | undefined): string {
  if (!value) return "unknown";
  return value.slice(0, 12);
}

export default function VisualEnrichmentView({ onOpenPhoto, selectedWorkingSetAssets, onClearWorkingSet }: VisualEnrichmentViewProps) {
  const [errorMessage, setErrorMessage] = useState("");
  const [updatingObservationId, setUpdatingObservationId] = useState<number | null>(null);
  const [propagationPreview, setPropagationPreview] = useState<ContextLabelPropagationPreviewResponse | null>(null);
  const [selectedPropagationTargets, setSelectedPropagationTargets] = useState<Set<string>>(new Set());
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [isPropagating, setIsPropagating] = useState(false);
  const [propagationResult, setPropagationResult] = useState<ContextLabelPropagationResponse | null>(null);
  const [isRunningCandidates, setIsRunningCandidates] = useState(false);
  const [runResult, setRunResult] = useState<VisualEnrichmentRunResponse | null>(null);
  const [runLiveMode, setRunLiveMode] = useState(true);
  const [runUseMockProvider, setRunUseMockProvider] = useState(false);
  const [showDeveloperControls, setShowDeveloperControls] = useState(false);
  const [landmarkSummaryByAsset, setLandmarkSummaryByAsset] = useState<Record<string, { labels: string[]; count: number }>>({});
  const [assetRunBySha, setAssetRunBySha] = useState<Record<string, VisualEnrichmentRunResponse["asset_results"][number]>>({});
  const [selectedSuggestionByAsset, setSelectedSuggestionByAsset] = useState<Record<string, string>>({});
  const [manualLabelByAsset, setManualLabelByAsset] = useState<Record<string, string>>({});
  const [ignoredAssets, setIgnoredAssets] = useState<Set<string>>(new Set());
  const [rejectedAssets, setRejectedAssets] = useState<Set<string>>(new Set());
  const [runningMoreContextByAsset, setRunningMoreContextByAsset] = useState<Record<string, boolean>>({});
  const [showMoreContextByAsset, setShowMoreContextByAsset] = useState<Record<string, boolean>>({});
  const [showDetailsByAsset, setShowDetailsByAsset] = useState<Record<string, boolean>>({});
  const [moreContextOptionsByAsset, setMoreContextOptionsByAsset] = useState<
    Record<string, { landmark: boolean; web: boolean; label: boolean; object: boolean }>
  >({});
  const [applyToDuplicateGroupByAsset, setApplyToDuplicateGroupByAsset] = useState<Record<string, boolean>>({});
  const [dismissedQueueAssets, setDismissedQueueAssets] = useState<Set<string>>(new Set());
  const [previouslyScannedByAsset, setPreviouslyScannedByAsset] = useState<Record<string, boolean>>({});
  const [observationReviewStateByAsset, setObservationReviewStateByAsset] = useState<Record<string, AssetObservationReviewState>>({});
  const [landmarkObservationSuggestionsByAsset, setLandmarkObservationSuggestionsByAsset] = useState<Record<string, ObservationLandmarkSuggestion[]>>({});
  const [sessionScannedAssets, setSessionScannedAssets] = useState<Set<string>>(new Set());
  const [acceptedManualAssets, setAcceptedManualAssets] = useState<Set<string>>(new Set());
  const [acceptedContextAssets, setAcceptedContextAssets] = useState<Set<string>>(new Set());
  const [persistedManualAcceptedByAsset, setPersistedManualAcceptedByAsset] = useState<Record<string, boolean>>({});
  const [hidePreviouslyRejected, setHidePreviouslyRejected] = useState(false);
  const [queueCardFilter, setQueueCardFilter] = useState<"all" | "with_suggestions" | "without_suggestions">("all");
  const [suggestionReviewFilter, setSuggestionReviewFilter] = useState<"all" | "pending" | "reviewed">("all");

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
    const seen = new Set<string>();
    const items: ReviewSuggestion[] = [];
    const observationSuggestions = landmarkObservationSuggestionsByAsset[assetSha256] ?? [];
    for (const observationSuggestion of observationSuggestions) {
      const normalized = observationSuggestion.label.trim().toLowerCase();
      if (!normalized || seen.has(normalized)) {
        continue;
      }
      seen.add(normalized);
      items.push({
        key: `observation_landmark:${normalized}`,
        label: `Landmark: ${observationSuggestion.label}`,
        sourceType: "google_vision",
        confidence: observationSuggestion.confidence,
      });
    }

    const runAsset = assetRunBySha[assetSha256];
    if (!runAsset) {
      return items;
    }
    for (const landmark of runAsset.landmarks) {
      if (!landmark.description) {
        continue;
      }
      const normalized = landmark.description.trim().toLowerCase();
      if (!normalized || seen.has(normalized)) {
        continue;
      }
      seen.add(normalized);
      items.push({
        key: `landmark:${normalized}`,
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
      setPropagationPreview(null);
      setSelectedPropagationTargets(new Set());
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to propagate context label");
    } finally {
      setIsPropagating(false);
    }
  };

  const isPreviouslyScannedAsset = (assetSha256: string): boolean => {
    if (sessionScannedAssets.has(assetSha256)) {
      return true;
    }
    if (previouslyScannedByAsset[assetSha256]) {
      return true;
    }
    if ((landmarkSummaryByAsset[assetSha256]?.count ?? 0) > 0) {
      return true;
    }
    if (assetRunBySha[assetSha256] !== undefined) {
      return true;
    }
    return false;
  };

  const handleRunCandidates = async () => {
    const queueAssetShas = activeQueueItems
      .map((item) => item.representative.asset_sha256)
      .filter((sha) => (landmarkSummaryByAsset[sha]?.count ?? 0) === 0)
      .filter((sha) => !ignoredAssets.has(sha) && !rejectedAssets.has(sha))
      .filter((sha) => !isPreviouslyScannedAsset(sha));
    const assetSha256s = queueAssetShas;

    if (assetSha256s.length === 0) {
      setErrorMessage("No unresolved unscanned queue cards available. Use Force Rescan for previously scanned assets.");
      return;
    }

    if (runLiveMode) {
      const confirmed = window.confirm("Live mode will run landmark detection for selected assets. Continue with live run?");
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
        feature_landmark: true,
        feature_web: false,
        feature_label: false,
        feature_object: false,
      });
      setRunResult(result);
      mergeRunAssets(result);
      setSessionScannedAssets((prev) => {
        const next = new Set(prev);
        for (const sha of assetSha256s) {
          next.add(sha);
        }
        return next;
      });
    } catch (err) {
      setRunResult(null);
      setErrorMessage(err instanceof Error ? err.message : "Failed to run visual enrichment candidates");
    } finally {
      setIsRunningCandidates(false);
    }
  };

  const dismissQueueCard = (assetSha256: string) => {
    setDismissedQueueAssets((prev) => {
      const next = new Set(prev);
      next.add(assetSha256);
      return next;
    });
  };

  const handleClearQueue = () => {
    setDismissedQueueAssets(new Set(normalizedQueue.map((item) => item.representative.asset_sha256)));
    onClearWorkingSet();
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
      if (options.landmark) {
        setSessionScannedAssets((prev) => new Set(prev).add(assetSha256));
      }
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to run more context for asset");
    } finally {
      setRunningMoreContextByAsset((prev) => ({ ...prev, [assetSha256]: false }));
    }
  };

  const handleRunLandmarkForCard = async (assetSha256: string) => {
    if (runLiveMode) {
      const confirmed = window.confirm("Live mode will run landmark detection for this asset. Continue?");
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
        feature_landmark: true,
        feature_web: false,
        feature_label: false,
        feature_object: false,
      });
      mergeRunAssets(result);
      setSessionScannedAssets((prev) => new Set(prev).add(assetSha256));
      setPreviouslyScannedByAsset((prev) => ({ ...prev, [assetSha256]: true }));
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to run landmark detection for asset");
    } finally {
      setRunningMoreContextByAsset((prev) => ({ ...prev, [assetSha256]: false }));
    }
  };

  const handleForceRescan = async (assetSha256: string) => {
    if (runLiveMode) {
      const confirmed = window.confirm("Force Rescan will rerun landmark detection for this asset. Continue?");
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
        feature_landmark: true,
        feature_web: false,
        feature_label: false,
        feature_object: false,
      });
      mergeRunAssets(result);
      setSessionScannedAssets((prev) => new Set(prev).add(assetSha256));
      setPreviouslyScannedByAsset((prev) => ({ ...prev, [assetSha256]: true }));
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to force rescan asset");
    } finally {
      setRunningMoreContextByAsset((prev) => ({ ...prev, [assetSha256]: false }));
    }
  };

  const handleRejectOrIgnoreCard = async (assetSha256: string, status: "rejected" | "ignored") => {
    setUpdatingObservationId(-1);
    setErrorMessage("");
    try {
      const response = await getGlobalPlaceObservations({
        assetSha256: assetSha256,
        sourceType: "google_vision",
        observationType: "landmark",
        limit: 200,
        offset: 0,
      });
      const pendingItems = response.items.filter((item) => item.status === "pending");
      if (pendingItems.length > 0) {
        await Promise.all(pendingItems.map((item) => patchGlobalPlaceObservation(item.id, { status })));
      }

      if (status === "rejected") {
        setRejectedAssets((prev) => new Set(prev).add(assetSha256));
        setIgnoredAssets((prev) => {
          const next = new Set(prev);
          next.delete(assetSha256);
          return next;
        });
      } else {
        setIgnoredAssets((prev) => new Set(prev).add(assetSha256));
        setRejectedAssets((prev) => {
          const next = new Set(prev);
          next.delete(assetSha256);
          return next;
        });
      }

      setSessionScannedAssets((prev) => new Set(prev).add(assetSha256));
      setPreviouslyScannedByAsset((prev) => ({ ...prev, [assetSha256]: true }));

      dismissQueueCard(assetSha256);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : `Failed to mark card ${status}`);
    } finally {
      setUpdatingObservationId(null);
    }
  };

  const maybePropagateAcceptedLabel = async (assetSha256: string, labelId: number) => {
    const shouldApply = applyToDuplicateGroupByAsset[assetSha256] ?? true;
    if (!shouldApply) {
      return;
    }

    try {
      const preview = await getContextLabelPropagationPreview(labelId);
      if (preview.targets.length === 0) {
        return;
      }
      const targetShas = preview.targets
        .filter((item) => item.selectable && !item.already_has_label)
        .map((item) => item.asset_sha256);
      if (targetShas.length === 0) {
        return;
      }
      const result = await propagateContextLabel(labelId, { target_asset_sha256s: targetShas });
      setPropagationResult(result);
    } catch {
      setErrorMessage("Context accepted, but duplicate-group propagation partially failed.");
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
      setAcceptedContextAssets((prev) => new Set(prev).add(assetSha256));
      setAcceptedManualAssets((prev) => {
        const next = new Set(prev);
        next.delete(assetSha256);
        return next;
      });
      await maybePropagateAcceptedLabel(assetSha256, response.context_label.id);
      dismissQueueCard(assetSha256);
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
      setAcceptedManualAssets((prev) => new Set(prev).add(assetSha256));
      setAcceptedContextAssets((prev) => {
        const next = new Set(prev);
        next.delete(assetSha256);
        return next;
      });
      await maybePropagateAcceptedLabel(assetSha256, response.context_label.id);
      dismissQueueCard(assetSha256);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to accept manual context label");
    } finally {
      setUpdatingObservationId(null);
    }
  };

  const workingSetSignature = useMemo(
    () => selectedWorkingSetAssets.map((asset) => asset.asset_sha256).join("|"),
    [selectedWorkingSetAssets],
  );

  useEffect(() => {
    if (selectedWorkingSetAssets.length > 0) {
      setDismissedQueueAssets(new Set());
    }
  }, [workingSetSignature, selectedWorkingSetAssets.length]);

  const normalizedQueue = useMemo<QueueWorkItem[]>(() => {
    const singletonItems: QueueWorkItem[] = [];
    const groupedByDuplicate: Record<number, VisualEnrichmentWorkingSetAsset[]> = {};
    for (const asset of selectedWorkingSetAssets) {
      if (asset.duplicate_group_id === null) {
        singletonItems.push({
          representative: asset,
          selectedCount: 1,
          canonicalUnavailable: false,
        });
        continue;
      }
      groupedByDuplicate[asset.duplicate_group_id] = groupedByDuplicate[asset.duplicate_group_id] ?? [];
      groupedByDuplicate[asset.duplicate_group_id].push(asset);
    }

    const groupedItems = Object.values(groupedByDuplicate).map((group) => {
      const canonical = group.find((item) => item.is_canonical);
      return {
        representative: canonical ?? group[0],
        selectedCount: group.length,
        canonicalUnavailable: canonical === undefined,
      };
    });

    return [...singletonItems, ...groupedItems];
  }, [selectedWorkingSetAssets]);

  const activeQueueItems = useMemo(
    () => normalizedQueue.filter((item) => !dismissedQueueAssets.has(item.representative.asset_sha256)),
    [normalizedQueue, dismissedQueueAssets],
  );

  useEffect(() => {
    const shas = normalizedQueue.map((item) => item.representative.asset_sha256);
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
  }, [normalizedQueue]);

  useEffect(() => {
    const shas = normalizedQueue.map((item) => item.representative.asset_sha256);
    if (shas.length === 0) {
      return;
    }
    let isCancelled = false;

    async function loadPersistedManualAcceptance(): Promise<void> {
      try {
        const results = await Promise.all(shas.map(async (sha) => {
          const response = await getAssetContextLabels({
            assetSha256: sha,
            contextType: "landmark",
            status: "active",
            limit: 200,
            offset: 0,
          });
          const hasManual = response.items.some((item) => item.source_type === "user");
          return [sha, hasManual] as const;
        }));

        if (isCancelled) {
          return;
        }

        const next: Record<string, boolean> = {};
        for (const [sha, hasManual] of results) {
          next[sha] = hasManual;
        }
        setPersistedManualAcceptedByAsset((prev) => ({ ...prev, ...next }));
      } catch {
        // Keep queue usable if persisted manual-status lookup fails.
      }
    }

    void loadPersistedManualAcceptance();
    return () => {
      isCancelled = true;
    };
  }, [normalizedQueue]);

  useEffect(() => {
    const shas = normalizedQueue.map((item) => item.representative.asset_sha256);
    if (shas.length === 0) {
      return;
    }
    let isCancelled = false;

    async function loadPreviouslyScanned(): Promise<void> {
      try {
        const results = await Promise.all(shas.map(async (sha) => {
          const response = await getGlobalPlaceObservations({
            assetSha256: sha,
            sourceType: "google_vision",
            observationType: "landmark",
            limit: 200,
            offset: 0,
          });
          const hasPending = response.items.some((item) => item.status === "pending");
          const hasAccepted = response.items.some((item) => item.status === "accepted");
          const hasRejected = response.items.some((item) => item.status === "rejected");
          const hasIgnored = response.items.some((item) => item.status === "ignored");
          const pendingSuggestions = response.items
            .filter((item) => item.status === "pending")
            .map((item) => ({
              label: (item.raw_label ?? "").trim(),
              confidence: item.confidence,
            }))
            .filter((item) => item.label.length > 0);
          return [sha, {
            scanned: response.count > 0,
            hasPending,
            hasAccepted,
            hasRejected,
            hasIgnored,
            pendingSuggestions,
          }] as const;
        }));

        if (isCancelled) {
          return;
        }
        const next: Record<string, boolean> = {};
        const nextReviewState: Record<string, AssetObservationReviewState> = {};
        const nextLandmarkSuggestions: Record<string, ObservationLandmarkSuggestion[]> = {};
        for (const [sha, state] of results) {
          next[sha] = state.scanned;
          nextReviewState[sha] = {
            hasPending: state.hasPending,
            hasAccepted: state.hasAccepted,
            hasRejected: state.hasRejected,
            hasIgnored: state.hasIgnored,
          };
          nextLandmarkSuggestions[sha] = state.pendingSuggestions;
        }
        setPreviouslyScannedByAsset((prev) => ({ ...prev, ...next }));
        setObservationReviewStateByAsset((prev) => ({ ...prev, ...nextReviewState }));
        setLandmarkObservationSuggestionsByAsset((prev) => ({ ...prev, ...nextLandmarkSuggestions }));
      } catch {
        // Keep queue usable even if scanned-status lookup fails.
      }
    }

    void loadPreviouslyScanned();
    return () => {
      isCancelled = true;
    };
  }, [normalizedQueue]);

  const hasSelectedWorkingSet = normalizedQueue.length > 0;

  const formatLandmarkSummary = (assetSha: string): string | null => {
    const summary = landmarkSummaryByAsset[assetSha];
    if (!summary || summary.count === 0) {
      return null;
    }
    return `Landmark: ${summary.labels[0]}${summary.count > 1 ? ` +${summary.count - 1}` : ""}`;
  };

  const getSelectedAssetStatus = (assetSha: string): string => {
    if (acceptedManualAssets.has(assetSha) || persistedManualAcceptedByAsset[assetSha]) {
      return "Accepted Manual Entry";
    }
    if (acceptedContextAssets.has(assetSha) || (landmarkSummaryByAsset[assetSha]?.count ?? 0) > 0) {
      return "Accepted Context";
    }
    if (rejectedAssets.has(assetSha)) {
      return "Rejected suggestions";
    }
    if (ignoredAssets.has(assetSha)) {
      return "Previously scanned";
    }
    const runAssetResult = assetRunBySha[assetSha] ?? runResult?.asset_results.find((item) => item.asset_sha256 === assetSha);
    if (!runAssetResult) {
      return isPreviouslyScannedAsset(assetSha) ? "Previously scanned (not run this session)" : "Not run";
    }
    if (runAssetResult.status === "failed") {
      return "Previously scanned";
    }
    if (runAssetResult.landmarks.length > 0 || runAssetResult.web_entities.length > 0 || runAssetResult.labels.length > 0 || runAssetResult.objects.length > 0) {
      return runAssetResult.no_landmark ? "No landmark found" : "Suggestions available";
    }
    if (runAssetResult.no_landmark) {
      return "No landmark found";
    }
    return "Not run";
  };

  const filteredQueueItems = useMemo(() => activeQueueItems.filter((queueItem) => {
    const assetSha = queueItem.representative.asset_sha256;
    const runAsset = assetRunBySha[assetSha] ?? runResult?.asset_results.find((item) => item.asset_sha256 === assetSha);
    const hasLandmarkFromRun = (runAsset?.landmarks.length ?? 0) > 0;
    const hasPendingLandmarkSuggestions = (landmarkObservationSuggestionsByAsset[assetSha]?.length ?? 0) > 0;
    const hasLandmarkSuggestions = hasLandmarkFromRun || hasPendingLandmarkSuggestions;
    const hasAcceptedContext = (landmarkSummaryByAsset[assetSha]?.count ?? 0) > 0 || acceptedContextAssets.has(assetSha) || acceptedManualAssets.has(assetSha);
    const reviewState = observationReviewStateByAsset[assetSha] ?? {
      hasPending: false,
      hasAccepted: false,
      hasRejected: false,
      hasIgnored: false,
    };
    const hasRejectedState = rejectedAssets.has(assetSha) || reviewState.hasRejected;
    const hasReviewedState = hasAcceptedContext || hasRejectedState || reviewState.hasAccepted;
    const hasPendingState = !hasReviewedState;

    if (hidePreviouslyRejected && hasRejectedState) {
      return false;
    }

    if (queueCardFilter === "with_suggestions" && !hasLandmarkSuggestions) {
      return false;
    }
    if (queueCardFilter === "without_suggestions" && hasLandmarkSuggestions) {
      return false;
    }

    if (suggestionReviewFilter === "all") {
      return true;
    }
    if (suggestionReviewFilter === "pending") {
      return hasPendingState;
    }
    return hasReviewedState;
  }), [activeQueueItems, assetRunBySha, runResult, landmarkObservationSuggestionsByAsset, landmarkSummaryByAsset, acceptedContextAssets, acceptedManualAssets, rejectedAssets, observationReviewStateByAsset, queueCardFilter, suggestionReviewFilter, hidePreviouslyRejected]);

  return (
    <div className={styles.container}>

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
        <h3 className={styles.sectionTitle}>Visual Enrichment Work Queue</h3>
        <p className={styles.sectionSubtitle}>
          {hasSelectedWorkingSet
            ? "Selected photos are normalized into one active queue card per work item."
            : "No active selected queue."}
        </p>
        {errorMessage && <p className={styles.error}>{errorMessage}</p>}
        {propagationResult && (
          <p className={styles.success}>
            Added: {propagationResult.added_count} | Already present: {propagationResult.already_present_count} |
            Skipped: {propagationResult.skipped_count} | Failed: {propagationResult.failed_count}
          </p>
        )}
        {runResult && (
          <p className={styles.success}>
            Mode: {runResult.mode} | Requested: {runResult.requested_count} | Processed: {runResult.processed_count} |
            Created pending observations: {runResult.observations_created_count} | No landmark: {runResult.no_landmark_count} |
            Failed: {runResult.failed_count}
          </p>
        )}

        {hasSelectedWorkingSet && (
          <>
            <div className={styles.previewSummary}>
              <span className={styles.badge}>Active cards: {activeQueueItems.length}</span>
              {normalizedQueue.length < selectedWorkingSetAssets.length ? (
                <span className={styles.badge}>Collapsed {selectedWorkingSetAssets.length} selected assets to {normalizedQueue.length} queue items</span>
              ) : null}
              <button
                type="button"
                className={styles.primaryButton}
                disabled={isRunningCandidates || activeQueueItems.length === 0}
                onClick={() => { void handleRunCandidates(); }}
              >
                {isRunningCandidates ? "Running..." : "Run Landmark Detection"}
              </button>
              <button type="button" className={styles.secondaryButton} onClick={handleClearQueue}>
                Clear Queue
              </button>
            </div>
            <div className={styles.previewSummary}>
              <span className={styles.badge}>Show:</span>
              <button
                type="button"
                className={queueCardFilter === "all" ? styles.toggleButtonActive : styles.toggleButtonInactive}
                onClick={() => setQueueCardFilter("all")}
                aria-pressed={queueCardFilter === "all"}
              >
                All
              </button>
              <button
                type="button"
                className={queueCardFilter === "with_suggestions" ? styles.toggleButtonActive : styles.toggleButtonInactive}
                onClick={() => setQueueCardFilter("with_suggestions")}
                aria-pressed={queueCardFilter === "with_suggestions"}
              >
                With landmark suggestions
              </button>
              <button
                type="button"
                className={queueCardFilter === "without_suggestions" ? styles.toggleButtonActive : styles.toggleButtonInactive}
                onClick={() => setQueueCardFilter("without_suggestions")}
                aria-pressed={queueCardFilter === "without_suggestions"}
              >
                Without landmark suggestions
              </button>
              <button
                type="button"
                className={hidePreviouslyRejected ? styles.toggleButtonActive : styles.toggleButtonInactive}
                onClick={() => setHidePreviouslyRejected((prev) => !prev)}
                aria-pressed={hidePreviouslyRejected}
              >
                {hidePreviouslyRejected ? "Show Previously Rejected" : "Hide Previously Rejected"}
              </button>
            </div>
            {queueCardFilter !== "all" ? (
              <div className={styles.previewSummary}>
                <span className={styles.badge}>Suggestion state:</span>
                <button
                  type="button"
                  className={suggestionReviewFilter === "all" ? styles.toggleButtonActive : styles.toggleButtonInactive}
                  onClick={() => setSuggestionReviewFilter("all")}
                  aria-pressed={suggestionReviewFilter === "all"}
                >
                  All
                </button>
                <button
                  type="button"
                  className={suggestionReviewFilter === "pending" ? styles.toggleButtonActive : styles.toggleButtonInactive}
                  onClick={() => setSuggestionReviewFilter("pending")}
                  aria-pressed={suggestionReviewFilter === "pending"}
                >
                  Not reviewed (pending)
                </button>
                <button
                  type="button"
                  className={suggestionReviewFilter === "reviewed" ? styles.toggleButtonActive : styles.toggleButtonInactive}
                  onClick={() => setSuggestionReviewFilter("reviewed")}
                  aria-pressed={suggestionReviewFilter === "reviewed"}
                >
                  Reviewed
                </button>
              </div>
            ) : null}
            {activeQueueItems.length === 0 ? (
              <p className={styles.empty}>No active Visual Enrichment work items. Select photos in Photo Review and send them here to begin.</p>
            ) : filteredQueueItems.length === 0 ? (
              <p className={styles.empty}>No cards match current filter.</p>
            ) : null}
          </>
        )}

          {!hasSelectedWorkingSet ? (
            <p className={styles.empty}>No active Visual Enrichment work items. Select photos in Photo Review and send them here to begin.</p>
          ) : null}

          {hasSelectedWorkingSet ? (
            <div className={styles.runControls}>
              <span className={styles.badge}>Mode: {runLiveMode ? "Live" : "Dry-run"}</span>
              <button
                type="button"
                className={styles.secondaryButton}
                disabled={isRunningCandidates}
                onClick={() => setShowDeveloperControls((prev) => !prev)}
              >
                {showDeveloperControls ? "Hide Developer" : "Developer Options"}
              </button>
            </div>
          ) : null}

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
            {filteredQueueItems.map((queueItem) => {
              const asset = queueItem.representative;
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
              const hasPreviousScan = previouslyScannedByAsset[asset.asset_sha256] ?? false;
              const hasEligibleDuplicateTargets = Boolean(asset.duplicate_group_id) && queueItem.selectedCount > 1;

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
                    {queueItem.selectedCount > 1 ? <div className={styles.metaLine}>{queueItem.selectedCount} selected assets collapsed to this card.</div> : null}
                    {queueItem.canonicalUnavailable ? <div className={styles.metaLine}>Canonical representative unavailable; using selected asset.</div> : null}
                    <div className={styles.metaLine}>Status: {assetStatus}</div>
                    {isPreviouslyScannedAsset(asset.asset_sha256) ? <div className={styles.metaLine}>Previously scanned</div> : null}
                    {formatLandmarkSummary(asset.asset_sha256) ? (
                      <div className={styles.metaLine}>{formatLandmarkSummary(asset.asset_sha256)}</div>
                    ) : null}

                    {hasEligibleDuplicateTargets ? (
                      <label className={styles.checkboxLabel}>
                        <input
                          type="checkbox"
                          checked={applyToDuplicateGroupByAsset[asset.asset_sha256] ?? true}
                          onChange={(event) => {
                            setApplyToDuplicateGroupByAsset((prev) => ({
                              ...prev,
                              [asset.asset_sha256]: event.target.checked,
                            }));
                          }}
                        />
                        Apply to duplicate group
                      </label>
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
                      <label className={styles.labelInputLabel} htmlFor={`manual-label-${asset.asset_sha256}`}>Context Label</label>
                      <input
                        id={`manual-label-${asset.asset_sha256}`}
                        className={styles.labelInput}
                        value={manualLabelByAsset[asset.asset_sha256] ?? (landmarkSummaryByAsset[asset.asset_sha256]?.labels?.[0] ?? "")}
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
                      {!hasPreviousScan ? (
                        <button
                          type="button"
                          className={styles.secondaryButton}
                          disabled={isRunningMoreContext}
                          onClick={() => { void handleRunLandmarkForCard(asset.asset_sha256); }}
                        >
                          Run Landmark Detection
                        </button>
                      ) : null}
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
                        onClick={() => { void handleRejectOrIgnoreCard(asset.asset_sha256, "rejected"); }}
                      >
                        Reject Suggestions
                      </button>
                      <button
                        type="button"
                        className={styles.secondaryButton}
                        onClick={() => { void handleRejectOrIgnoreCard(asset.asset_sha256, "ignored"); }}
                      >
                        Ignore Asset
                      </button>
                      {hasPreviousScan ? (
                        <button
                          type="button"
                          className={styles.secondaryButton}
                          disabled={isRunningMoreContext}
                          onClick={() => { void handleForceRescan(asset.asset_sha256); }}
                        >
                          Force Rescan
                        </button>
                      ) : null}
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
                        onClick={() => {
                          setShowDetailsByAsset((prev) => ({
                            ...prev,
                            [asset.asset_sha256]: !prev[asset.asset_sha256],
                          }));
                        }}
                      >
                        {showDetailsByAsset[asset.asset_sha256] ? "Hide Details" : "Details"}
                      </button>
                      <button
                        type="button"
                        className={styles.secondaryButton}
                        onClick={() => onOpenPhoto(asset.asset_sha256)}
                      >
                        Open Asset
                      </button>
                    </div>

                    {showDetailsByAsset[asset.asset_sha256] ? (
                      <pre className={styles.detailsBox}>{JSON.stringify({
                        asset_sha256: asset.asset_sha256,
                        status: assetStatus,
                        previously_scanned: hasPreviousScan,
                        selected_count_collapsed: queueItem.selectedCount,
                        suggestions: suggestions.map((item) => ({
                          key: item.key,
                          label: item.label,
                          confidence: item.confidence,
                        })),
                        latest_run: assetRunBySha[asset.asset_sha256] ?? null,
                      }, null, 2)}</pre>
                    ) : null}

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

      </section>

    </div>
  );
}

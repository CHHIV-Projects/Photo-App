import styles from "@/components/review-screen.module.css";
import type {
  ClusterDetail as ClusterDetailType,
  ClusterSuggestionResponse,
  ClusterSummary,
  PersonSummary,
} from "@/types/ui-api";
import { useEffect, useState } from "react";

import { FaceGrid } from "@/components/FaceGrid";
import { PersonAssignForm } from "@/components/PersonAssignForm";
import { getClusterSuggestions } from "@/lib/api";

interface ClusterDetailProps {
  clusterDetail: ClusterDetailType | null;
  isLoadingDetail: boolean;
  detailErrorMessage: string | null;
  people: PersonSummary[];
  isLoadingPeople: boolean;
  assignErrorMessage: string | null;
  actionErrorMessage: string | null;
  isAssigning: boolean;
  isIgnoringCluster: boolean;
  isMergingCluster: boolean;
  clusters: ClusterSummary[];
  selectedClusterId: number | null;
  onAssign: (personId: number) => Promise<void>;
  onIgnoreCluster: () => Promise<void>;
  onMergeClusters: (targetClusterId: number) => Promise<boolean>;
  onMergeValidationError: (message: string) => void;
  onRemoveFace: (faceId: number) => Promise<boolean>;
  onMoveFace: (faceId: number, targetClusterId: number) => Promise<boolean>;
  onSelectCluster: (clusterId: number) => void;
}

export function ClusterDetail({
  clusterDetail,
  isLoadingDetail,
  detailErrorMessage,
  people,
  isLoadingPeople,
  assignErrorMessage,
  actionErrorMessage,
  isAssigning,
  isIgnoringCluster,
  isMergingCluster,
  clusters,
  selectedClusterId,
  onAssign,
  onIgnoreCluster,
  onMergeClusters,
  onMergeValidationError,
  onRemoveFace,
  onMoveFace,
  onSelectCluster
}: ClusterDetailProps) {
  type MergePreviewState = {
    sourceClusterId: number;
    targetClusterId: number;
    sourcePersonName: string;
    targetPersonName: string;
    sourceFaceCount: number;
    targetFaceCount: number;
    sourceWillBeDeleted: boolean;
  };

  const [targetClusterInput, setTargetClusterInput] = useState<string>("");
  const [mergePreview, setMergePreview] = useState<MergePreviewState | null>(null);
  const [suggestions, setSuggestions] = useState<ClusterSuggestionResponse | null>(null);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const [suggestionsErrorMessage, setSuggestionsErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!clusterDetail) {
      setSuggestions(null);
      return;
    }

    const clusterId = clusterDetail.cluster_id;

    async function loadSuggestions() {
      setIsLoadingSuggestions(true);
      setSuggestionsErrorMessage(null);
      try {
        const response = await getClusterSuggestions(clusterId);
        setSuggestions(response);
      } catch (error) {
        setSuggestionsErrorMessage(getErrorMessage(error, "Failed to load suggestions."));
        setSuggestions(null);
      } finally {
        setIsLoadingSuggestions(false);
      }
    }

    void loadSuggestions();
  }, [clusterDetail?.cluster_id]);

  const currentIndex = clusters.findIndex((c) => c.cluster_id === selectedClusterId);
  const prevClusterId = currentIndex > 0 ? clusters[currentIndex - 1].cluster_id : null;
  const nextClusterId =
    currentIndex >= 0 && currentIndex < clusters.length - 1
      ? clusters[currentIndex + 1].cluster_id
      : null;

  const handleIgnoreClick = async () => {
    if (!clusterDetail) {
      return;
    }

    if (!window.confirm("Ignore this cluster?")) {
      return;
    }

    await onIgnoreCluster();
  };

  const handleMergeClick = async () => {
    if (!clusterDetail) {
      return;
    }

    const normalizedTargetClusterId = targetClusterInput.trim();
    if (!normalizedTargetClusterId) {
      onMergeValidationError("Target cluster is required.");
      return;
    }

    const targetClusterId = Number(normalizedTargetClusterId);
    if (!Number.isInteger(targetClusterId) || targetClusterId <= 0) {
      onMergeValidationError("Target cluster must be a positive number.");
      return;
    }

    if (targetClusterId === clusterDetail.cluster_id) {
      onMergeValidationError("Cannot merge a cluster into itself.");
      return;
    }

    const targetCluster = clusters.find((cluster) => cluster.cluster_id === targetClusterId);
    if (!targetCluster) {
      onMergeValidationError(
        "Target cluster is not currently loaded. Adjust filters or load scope, then retry merge."
      );
      return;
    }

    if (targetCluster.is_ignored) {
      onMergeValidationError("Cannot merge into an ignored cluster.");
      return;
    }

    if (
      clusterDetail.person_id !== null &&
      targetCluster.person_id !== null &&
      clusterDetail.person_id !== targetCluster.person_id
    ) {
      onMergeValidationError(
        `Merge blocked: source is assigned to ${clusterDetail.person_name ?? `Person #${clusterDetail.person_id}`}, target is assigned to ${targetCluster.person_name ?? `Person #${targetCluster.person_id}`}. Reassign first.`
      );
      return;
    }

    setMergePreview({
      sourceClusterId: clusterDetail.cluster_id,
      targetClusterId,
      sourcePersonName: clusterDetail.person_name ?? "Unassigned",
      targetPersonName: targetCluster.person_name ?? "Unassigned",
      sourceFaceCount: clusterDetail.faces.length,
      targetFaceCount: targetCluster.face_count,
      sourceWillBeDeleted: true,
    });
  };

  const handleConfirmMerge = async () => {
    if (!mergePreview) {
      return;
    }

    const didMerge = await onMergeClusters(mergePreview.targetClusterId);
    if (didMerge) {
      setTargetClusterInput("");
      setMergePreview(null);
    }
  };

  const topSuggestion = suggestions?.suggested_people[0] ?? null;
  const alternateSuggestions =
    suggestions && suggestions.suggestion_state !== "high_confidence"
      ? suggestions.suggested_people.slice(1, 3)
      : [];

  const suggestionLabel =
    suggestions?.suggestion_state === "high_confidence"
      ? "Strong suggestion"
      : suggestions?.suggestion_state === "tentative"
        ? "Tentative suggestion"
        : "No strong suggestion";

  return (
    <section className={styles.panel}>
      <header className={styles.panelHeader}>
        <div className={styles.panelTitleRow}>
          <h2 className={styles.panelTitle}>Selected Cluster</h2>
          <span className={styles.panelMeta}>
            {clusterDetail ? `${clusterDetail.faces.length} faces` : "No selection"}
          </span>
        </div>
      </header>
      <div className={styles.clusterNavControls}>
        <button
          type="button"
          className={styles.clusterNavButton}
          onClick={() => prevClusterId !== null && onSelectCluster(prevClusterId)}
          disabled={prevClusterId === null}
        >
          ← Previous
        </button>
        <span className={styles.clusterNavMeta}>
          {currentIndex >= 0 ? `${currentIndex + 1} of ${clusters.length}` : ""}
        </span>
        <button
          type="button"
          className={styles.clusterNavButton}
          onClick={() => nextClusterId !== null && onSelectCluster(nextClusterId)}
          disabled={nextClusterId === null}
        >
          Next →
        </button>
      </div>
      <div className={styles.panelBody}>
        {isLoadingDetail ? <div className={styles.message}>Loading cluster detail...</div> : null}
        {detailErrorMessage ? <div className={styles.errorMessage}>{detailErrorMessage}</div> : null}
        {!isLoadingDetail && !detailErrorMessage && !clusterDetail ? (
          <div className={styles.emptyState}>No cluster selected.</div>
        ) : null}
        {!isLoadingDetail && !detailErrorMessage && clusterDetail ? (
          <div className={styles.detailGrid}>
            <div className={styles.infoCard}>
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>Cluster</span>
                <span>#{clusterDetail.cluster_id}</span>
              </div>
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>Assigned</span>
                <span>{clusterDetail.person_name ?? "Unassigned"}</span>
              </div>
              <div className={styles.actionRow}>
                <button
                  type="button"
                  className={styles.dangerButton}
                  onClick={handleIgnoreClick}
                  disabled={isIgnoringCluster}
                >
                  {isIgnoringCluster ? "Ignoring..." : "Ignore Cluster"}
                </button>
              </div>

              <div className={styles.mergeSection}>
                <p className={styles.mergeTitle}>Merge Cluster</p>
                <label className={styles.mergeLabel} htmlFor="target-cluster-id">
                  Target Cluster ID
                </label>
                <div className={styles.mergeControls}>
                  <input
                    id="target-cluster-id"
                    className={styles.mergeInput}
                    type="number"
                    min={1}
                    step={1}
                    value={targetClusterInput}
                    onChange={(event) => setTargetClusterInput(event.target.value)}
                    disabled={isMergingCluster}
                  />
                  <button
                    type="button"
                    className={styles.assignButton}
                    onClick={handleMergeClick}
                    disabled={isMergingCluster}
                  >
                    {isMergingCluster ? "Merging..." : "Merge Into Target"}
                  </button>
                </div>
              </div>
            </div>

            <PersonAssignForm
              people={people}
              selectedPersonId={clusterDetail.person_id}
              isLoadingPeople={isLoadingPeople}
              isSubmitting={isAssigning}
              errorMessage={assignErrorMessage}
              onAssign={onAssign}
            />

            <div className={styles.infoCard}>
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>Suggestions</span>
                <span className={styles.suggestionStateBadge}>{suggestionLabel}</span>
              </div>

              {isLoadingSuggestions ? <p className={styles.clusterButtonMeta}>Loading suggestions...</p> : null}
              {suggestionsErrorMessage ? (
                <div className={styles.errorMessage}>{suggestionsErrorMessage}</div>
              ) : null}

              {!isLoadingSuggestions && !suggestionsErrorMessage && suggestions ? (
                <>
                  <p className={styles.clusterButtonMeta}>{suggestions.explanation}</p>

                  {topSuggestion ? (
                    <div className={styles.suggestionTopRow}>
                      <div className={styles.suggestionTextBlock}>
                        <p className={styles.suggestionName}>{topSuggestion.person_name}</p>
                        <p className={styles.suggestionMeta}>
                          Score {topSuggestion.confidence_score.toFixed(3)}
                        </p>
                      </div>
                      <button
                        type="button"
                        className={styles.assignButton}
                        disabled={isAssigning}
                        onClick={() => onAssign(topSuggestion.person_id)}
                      >
                        Assign
                      </button>
                    </div>
                  ) : null}

                  {alternateSuggestions.length > 0 ? (
                    <ul className={styles.suggestionList}>
                      {alternateSuggestions.map((candidate) => (
                        <li key={candidate.person_id} className={styles.suggestionItem}>
                          <span>
                            {candidate.person_name} ({candidate.confidence_score.toFixed(3)})
                          </span>
                          <button
                            type="button"
                            className={styles.suggestionAssignButton}
                            disabled={isAssigning}
                            onClick={() => onAssign(candidate.person_id)}
                          >
                            Assign
                          </button>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </>
              ) : null}
            </div>

            {actionErrorMessage ? (
              <div className={styles.errorMessage}>{actionErrorMessage}</div>
            ) : null}

            {mergePreview ? (
              <div className={styles.mergeConfirmOverlay}>
                <div className={styles.mergeConfirmDialog} role="dialog" aria-modal="true" aria-label="Confirm cluster merge">
                  <h3 className={styles.mergeConfirmTitle}>Confirm Cluster Merge</h3>
                  <div className={styles.mergeConfirmGrid}>
                    <span className={styles.infoLabel}>Source cluster</span>
                    <span>#{mergePreview.sourceClusterId}</span>
                    <span className={styles.infoLabel}>Target cluster</span>
                    <span>#{mergePreview.targetClusterId}</span>
                    <span className={styles.infoLabel}>Source assigned person</span>
                    <span>{mergePreview.sourcePersonName}</span>
                    <span className={styles.infoLabel}>Target assigned person</span>
                    <span>{mergePreview.targetPersonName}</span>
                    <span className={styles.infoLabel}>Source face count</span>
                    <span>{mergePreview.sourceFaceCount}</span>
                    <span className={styles.infoLabel}>Target face count</span>
                    <span>{mergePreview.targetFaceCount}</span>
                    <span className={styles.infoLabel}>Source cluster deletion</span>
                    <span>{mergePreview.sourceWillBeDeleted ? "Yes" : "No"}</span>
                  </div>
                  <p className={styles.mergeConfirmWarning}>
                    This will move faces from the source cluster into the target cluster and remove the source cluster.
                    This action is not currently reversible.
                  </p>
                  <div className={styles.actionRow}>
                    <button
                      type="button"
                      className={styles.assignButton}
                      onClick={() => {
                        void handleConfirmMerge();
                      }}
                      disabled={isMergingCluster}
                    >
                      {isMergingCluster ? "Merging..." : "Confirm Merge"}
                    </button>
                    <button
                      type="button"
                      className={styles.clusterNavButton}
                      onClick={() => setMergePreview(null)}
                      disabled={isMergingCluster}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            ) : null}

            <div className={styles.detailGrid}>
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>Faces</span>
              </div>
              <FaceGrid
                faces={clusterDetail.faces}
                selectedClusterId={clusterDetail.cluster_id}
                onRemoveFace={onRemoveFace}
                onMoveFace={onMoveFace}
              />
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function getErrorMessage(error: unknown, fallbackMessage: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallbackMessage;
}

import styles from "@/components/review-screen.module.css";
import type { ClusterDetail as ClusterDetailType, ClusterSummary, PersonSummary } from "@/types/ui-api";
import { useState } from "react";

import { FaceGrid } from "@/components/FaceGrid";
import { PersonAssignForm } from "@/components/PersonAssignForm";

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
  const [targetClusterInput, setTargetClusterInput] = useState<string>("");

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

    if (
      !window.confirm(
        "Are you sure you want to merge this cluster into the target cluster? This cannot be undone."
      )
    ) {
      return;
    }

    const didMerge = await onMergeClusters(targetClusterId);
    if (didMerge) {
      setTargetClusterInput("");
    }
  };

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

            {actionErrorMessage ? (
              <div className={styles.errorMessage}>{actionErrorMessage}</div>
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

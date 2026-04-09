import styles from "@/components/review-screen.module.css";
import type { ClusterDetail as ClusterDetailType, PersonSummary } from "@/types/ui-api";

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
  onAssign: (personId: number) => Promise<void>;
  onIgnoreCluster: () => Promise<void>;
  onRemoveFace: (faceId: number) => Promise<boolean>;
  onMoveFace: (faceId: number, targetClusterId: number) => Promise<boolean>;
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
  onAssign,
  onIgnoreCluster,
  onRemoveFace,
  onMoveFace
}: ClusterDetailProps) {
  const handleIgnoreClick = async () => {
    if (!clusterDetail) {
      return;
    }

    if (!window.confirm("Ignore this cluster?")) {
      return;
    }

    await onIgnoreCluster();
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

import { useEffect, useRef } from "react";

import styles from "@/components/review-screen.module.css";
import type { ClusterSummary } from "@/types/ui-api";

interface ClusterListProps {
  clusters: ClusterSummary[];
  selectedClusterId: number | null;
  isLoading: boolean;
  errorMessage: string | null;
  onSelectCluster: (clusterId: number) => void;
}

export function ClusterList({
  clusters,
  selectedClusterId,
  isLoading,
  errorMessage,
  onSelectCluster
}: ClusterListProps) {
  const clusterRefs = useRef<Map<number, HTMLButtonElement>>(new Map());

  useEffect(() => {
    if (selectedClusterId !== null) {
      const el = clusterRefs.current.get(selectedClusterId);
      el?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [selectedClusterId]);

  return (
    <section className={styles.panel}>
      <header className={styles.panelHeader}>
        <div className={styles.panelTitleRow}>
          <h2 className={styles.panelTitle}>Clusters</h2>
          <span className={styles.panelMeta}>{clusters.length} loaded</span>
        </div>
      </header>
      <div className={styles.panelBody}>
        {isLoading ? <div className={styles.message}>Loading clusters...</div> : null}
        {errorMessage ? <div className={styles.errorMessage}>{errorMessage}</div> : null}
        {!isLoading && !errorMessage && clusters.length === 0 ? (
          <div className={styles.emptyState}>No clusters found.</div>
        ) : null}
        {!isLoading && !errorMessage && clusters.length > 0 ? (
          <div className={styles.clusterList}>
            {clusters.map((cluster) => {
              const isSelected = cluster.cluster_id === selectedClusterId;
              return (
                <button
                  key={cluster.cluster_id}
                  type="button"
                  ref={(el) => {
                    if (el) {
                      clusterRefs.current.set(cluster.cluster_id, el);
                    } else {
                      clusterRefs.current.delete(cluster.cluster_id);
                    }
                  }}
                  className={`${styles.clusterButton} ${isSelected ? styles.clusterButtonActive : ""}`.trim()}
                  onClick={() => onSelectCluster(cluster.cluster_id)}
                >
                  <h3 className={styles.clusterButtonTitle}>Cluster #{cluster.cluster_id}</h3>
                  <p className={styles.clusterButtonMeta}>{cluster.face_count} faces</p>
                  <p className={styles.clusterButtonLabel}>
                    {cluster.person_name ?? "Unassigned"}
                  </p>
                </button>
              );
            })}
          </div>
        ) : null}
      </div>
    </section>
  );
}

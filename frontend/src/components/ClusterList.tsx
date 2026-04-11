import { useEffect, useRef, useState } from "react";

import styles from "@/components/review-screen.module.css";
import type { ClusterSummary } from "@/types/ui-api";

type FilterMode = "all" | "unassigned" | "min1" | "min2" | "min5";

const FILTER_OPTIONS: { mode: FilterMode; label: string }[] = [
  { mode: "all", label: "All" },
  { mode: "unassigned", label: "Unassigned" },
  { mode: "min1", label: "1+" },
  { mode: "min2", label: "2+" },
  { mode: "min5", label: "5+" }
];

const MIN_FACE_COUNT: Record<FilterMode, number> = {
  all: 0,
  unassigned: 0,
  min1: 1,
  min2: 2,
  min5: 5
};

function applyFilter(clusters: ClusterSummary[], mode: FilterMode): ClusterSummary[] {
  return clusters.filter((cluster) => {
    if (mode === "unassigned" && cluster.person_id !== null) return false;
    if (cluster.face_count < MIN_FACE_COUNT[mode]) return false;
    return true;
  });
}

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
  const [filterMode, setFilterMode] = useState<FilterMode>("all");

  const visibleClusters = applyFilter(clusters, filterMode);

  useEffect(() => {
    if (selectedClusterId !== null) {
      const el = clusterRefs.current.get(selectedClusterId);
      el?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [selectedClusterId]);

  useEffect(() => {
    if (selectedClusterId === null) return;
    const stillVisible = visibleClusters.some(
      (cluster) => cluster.cluster_id === selectedClusterId
    );
    if (!stillVisible && visibleClusters.length > 0) {
      onSelectCluster(visibleClusters[0].cluster_id);
    }
  }, [selectedClusterId, visibleClusters, onSelectCluster]);

  return (
    <section className={styles.panel}>
      <header className={styles.panelHeader}>
        <div className={styles.panelTitleRow}>
          <h2 className={styles.panelTitle}>Clusters</h2>
          <span className={styles.panelMeta}>{visibleClusters.length} visible</span>
        </div>
      </header>

      <div className={styles.panelBody}>
        <div className={styles.filterBar}>
          {FILTER_OPTIONS.map(({ mode, label }) => (
            <button
              key={mode}
              type="button"
              className={`${styles.filterButton} ${
                filterMode === mode ? styles.filterButtonActive : ""
              }`.trim()}
              onClick={() => setFilterMode(mode)}
            >
              {label}
            </button>
          ))}
        </div>

        {isLoading ? <div className={styles.message}>Loading clusters...</div> : null}
        {errorMessage ? <div className={styles.errorMessage}>{errorMessage}</div> : null}

        {!isLoading && !errorMessage && visibleClusters.length === 0 ? (
          <div className={styles.emptyState}>
            {clusters.length === 0 ? "No clusters found." : "No clusters match this filter."}
          </div>
        ) : null}

        {!isLoading && !errorMessage && visibleClusters.length > 0 ? (
          <div className={styles.clusterList}>
            {visibleClusters.map((cluster) => {
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
                  className={`${styles.clusterButton} ${
                    isSelected ? styles.clusterButtonActive : ""
                  }`.trim()}
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

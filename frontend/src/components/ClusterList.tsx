import { useEffect, useRef, useState } from "react";

import styles from "@/components/review-screen.module.css";
import type { ClusterSummary } from "@/types/ui-api";

type FilterMode = "all" | "assigned" | "unassigned" | "ignored";

const FILTER_OPTIONS: { mode: FilterMode; label: string }[] = [
  { mode: "all", label: "All" },
  { mode: "assigned", label: "Assigned" },
  { mode: "unassigned", label: "Unassigned" },
  { mode: "ignored", label: "Ignored" },
];

function applyStatusFilter(clusters: ClusterSummary[], mode: FilterMode): ClusterSummary[] {
  return clusters.filter((cluster) => {
    if (mode === "all") return !cluster.is_ignored;
    if (mode === "assigned") return !cluster.is_ignored && cluster.person_id !== null;
    if (mode === "unassigned") return !cluster.is_ignored && cluster.person_id === null;
    return cluster.is_ignored;
  });
}

function applyPersonFilter(clusters: ClusterSummary[], personQuery: string): ClusterSummary[] {
  const query = personQuery.trim().toLowerCase();
  if (!query) {
    return clusters;
  }

  return clusters.filter((cluster) => {
    if (!cluster.person_name) {
      return "unassigned".includes(query);
    }
    return cluster.person_name.toLowerCase().includes(query);
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
  const [personSearchQuery, setPersonSearchQuery] = useState("");

  const visibleClusters = applyPersonFilter(applyStatusFilter(clusters, filterMode), personSearchQuery);

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
        <input
          type="search"
          className={styles.searchInput}
          placeholder="Filter clusters by person name..."
          value={personSearchQuery}
          onChange={(event) => setPersonSearchQuery(event.target.value)}
        />

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
                  {cluster.is_ignored ? <p className={styles.clusterButtonMeta}>Ignored</p> : null}
                </button>
              );
            })}
          </div>
        ) : null}
      </div>
    </section>
  );
}

import { useEffect, useRef } from "react";

import styles from "@/components/review-screen.module.css";
import type { ClusterSummary } from "@/types/ui-api";

type FilterMode = "all" | "assigned" | "unassigned" | "ignored";

const FILTER_OPTIONS: { mode: FilterMode; label: string }[] = [
  { mode: "all", label: "All" },
  { mode: "assigned", label: "Assigned" },
  { mode: "unassigned", label: "Unassigned" },
  { mode: "ignored", label: "Ignored" },
];

interface ClusterListProps {
  clusters: ClusterSummary[];
  filterMode: FilterMode;
  personSearchQuery: string;
  totalCount: number;
  offset: number;
  pageSize: number;
  selectedClusterId: number | null;
  isLoading: boolean;
  errorMessage: string | null;
  onFilterModeChange: (mode: FilterMode) => void;
  onPersonSearchQueryChange: (value: string) => void;
  onPageChange: (nextOffset: number) => void;
  onSelectCluster: (clusterId: number) => void;
}

export function ClusterList({
  clusters,
  filterMode,
  personSearchQuery,
  totalCount,
  offset,
  pageSize,
  selectedClusterId,
  isLoading,
  errorMessage,
  onFilterModeChange,
  onPersonSearchQueryChange,
  onPageChange,
  onSelectCluster
}: ClusterListProps) {
  const clusterRefs = useRef<Map<number, HTMLButtonElement>>(new Map());
  const visibleClusters = clusters;
  const pageStart = totalCount === 0 ? 0 : offset + 1;
  const pageEnd = totalCount === 0 ? 0 : Math.min(offset + visibleClusters.length, totalCount);
  const canGoPrev = offset > 0;
  const canGoNext = offset + pageSize < totalCount;

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
          <span className={styles.panelMeta}>
            {visibleClusters.length} shown / {totalCount} total
          </span>
        </div>
      </header>

      <div className={styles.panelBody}>
        <input
          type="search"
          className={styles.searchInput}
          placeholder="Filter clusters by person name..."
          value={personSearchQuery}
          onChange={(event) => onPersonSearchQueryChange(event.target.value)}
        />

        <div className={styles.filterBar}>
          {FILTER_OPTIONS.map(({ mode, label }) => (
            <button
              key={mode}
              type="button"
              className={`${styles.filterButton} ${
                filterMode === mode ? styles.filterButtonActive : ""
              }`.trim()}
              onClick={() => onFilterModeChange(mode)}
            >
              {label}
            </button>
          ))}
        </div>

        <div className={styles.clusterNavControls}>
          <button
            type="button"
            className={styles.clusterNavButton}
            onClick={() => onPageChange(Math.max(0, offset - pageSize))}
            disabled={!canGoPrev || isLoading}
          >
            Prev
          </button>
          <span className={styles.clusterNavMeta}>
            {pageStart}-{pageEnd} of {totalCount}
          </span>
          <button
            type="button"
            className={styles.clusterNavButton}
            onClick={() => onPageChange(offset + pageSize)}
            disabled={!canGoNext || isLoading}
          >
            Next
          </button>
        </div>

        {isLoading ? <div className={styles.message}>Loading clusters...</div> : null}
        {errorMessage ? <div className={styles.errorMessage}>{errorMessage}</div> : null}

        {!isLoading && !errorMessage && visibleClusters.length === 0 ? (
          <div className={styles.emptyState}>
            {totalCount === 0 ? "No clusters found." : "No clusters match this filter."}
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

import { useMemo, useState } from "react";

import styles from "@/components/review-screen.module.css";
import { resolveApiUrl } from "@/lib/api";
import type { ClusterSummary, FaceSummary, PersonWithClusters } from "@/types/ui-api";

interface UnassignedFacesViewProps {
  faces: FaceSummary[];
  clusters: ClusterSummary[];
  peopleWithClusters: PersonWithClusters[];
  isLoading: boolean;
  errorMessage: string | null;
  actionErrorMessage: string | null;
  onMoveFace: (faceId: number, targetClusterId: number) => Promise<boolean>;
  onCreateCluster: (faceId: number) => Promise<boolean>;
  onValidationError: (message: string) => void;
}

export function UnassignedFacesView({
  faces,
  clusters,
  peopleWithClusters,
  isLoading,
  errorMessage,
  actionErrorMessage,
  onMoveFace,
  onCreateCluster,
  onValidationError
}: UnassignedFacesViewProps) {
  const [moveTargetByFaceId, setMoveTargetByFaceId] = useState<Record<number, string>>({});
  const [destinationSearchByFaceId, setDestinationSearchByFaceId] = useState<Record<number, string>>({});
  const [destinationSelectedByFaceId, setDestinationSelectedByFaceId] = useState<Record<number, boolean>>({});
  const [pendingMoveFaceId, setPendingMoveFaceId] = useState<number | null>(null);
  const [pendingCreateClusterFaceId, setPendingCreateClusterFaceId] = useState<number | null>(null);
  const [failedImageByFaceId, setFailedImageByFaceId] = useState<Record<number, boolean>>({});
  const [faceSearch, setFaceSearch] = useState("");
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const visibleFaces = useMemo(() => {
    const q = faceSearch.trim().toLowerCase();
    if (!q) return faces;
    return faces.filter(
      (f) =>
        String(f.face_id).includes(q) ||
        f.asset_sha256.slice(0, 12).toLowerCase().includes(q)
    );
  }, [faces, faceSearch]);

  // Build searchable cluster list combining ID and person name
  const searchableResults = useMemo(() => {
    const allResults: Array<{
      clusterId: number;
      personName: string | null;
      displayText: string;
    }> = [];

    clusters.forEach((cluster) => {
      const person = peopleWithClusters.find((p) => p.person_id === cluster.person_id);
      const personName = person?.display_name ?? null;
      allResults.push({
        clusterId: cluster.cluster_id,
        personName,
        displayText: personName
          ? `Cluster #${cluster.cluster_id} — ${personName} — ${cluster.face_count} faces`
          : `Cluster #${cluster.cluster_id} — ${cluster.face_count} faces`
      });
    });

    return allResults;
  }, [clusters, peopleWithClusters]);

  const getMatchingDestinations = (query: string) => {
    const q = query.trim().toLowerCase();
    if (!q) return [];

    return searchableResults.filter((result) => {
      const idMatch = String(result.clusterId).includes(q);
      const nameMatch = result.personName?.toLowerCase().includes(q) ?? false;
      return idMatch || nameMatch;
    });
  };

  const updateMoveTarget = (faceId: number, nextValue: string) => {
    setMoveTargetByFaceId((current) => ({
      ...current,
      [faceId]: nextValue
    }));
  };

  const clearMoveTarget = (faceId: number) => {
    setMoveTargetByFaceId((current) => {
      const next = { ...current };
      delete next[faceId];
      return next;
    });
  };

  const updateDestinationSearch = (faceId: number, nextValue: string) => {
    setDestinationSearchByFaceId((current) => ({
      ...current,
      [faceId]: nextValue
    }));
    setDestinationSelectedByFaceId((current) => ({
      ...current,
      [faceId]: false
    }));

    const numericValue = Number(nextValue.trim());
    if (Number.isInteger(numericValue) && numericValue > 0) {
      updateMoveTarget(faceId, String(numericValue));
      return;
    }

    clearMoveTarget(faceId);
  };

  const selectDestination = (
    faceId: number,
    clusterId: number,
    displayValue: string,
  ) => {
    updateMoveTarget(faceId, String(clusterId));
    setDestinationSearchByFaceId((current) => ({
      ...current,
      [faceId]: displayValue
    }));
    setDestinationSelectedByFaceId((current) => ({
      ...current,
      [faceId]: true
    }));
  };

  const handleMove = async (faceId: number) => {
    const selectedTarget = moveTargetByFaceId[faceId]?.trim() ?? "";
    const typedTarget = destinationSearchByFaceId[faceId]?.trim() ?? "";
    const draftTarget = selectedTarget || typedTarget;

    if (!draftTarget) {
      onValidationError("Target cluster is required.");
      return;
    }

    const parsedTarget = Number(draftTarget);
    if (!Number.isInteger(parsedTarget) || parsedTarget <= 0) {
      onValidationError("Enter a valid cluster id.");
      return;
    }

    setPendingMoveFaceId(faceId);
    setSuccessMessage(null);

    try {
      const moveSucceeded = await onMoveFace(faceId, parsedTarget);
      if (moveSucceeded) {
        clearMoveTarget(faceId);
        updateDestinationSearch(faceId, "");
        setDestinationSelectedByFaceId((current) => ({
          ...current,
          [faceId]: false
        }));
        setSuccessMessage(`Face moved to cluster #${parsedTarget}`);
        setTimeout(() => setSuccessMessage(null), 3000);
      }
    } finally {
      setPendingMoveFaceId(null);
    }
  };

  const handleCreateNewCluster = async (faceId: number) => {
    setPendingCreateClusterFaceId(faceId);
    setSuccessMessage(null);

    try {
      const createSucceeded = await onCreateCluster(faceId);
      if (createSucceeded) {
        clearMoveTarget(faceId);
        updateDestinationSearch(faceId, "");
        setDestinationSelectedByFaceId((current) => ({
          ...current,
          [faceId]: false
        }));
        setSuccessMessage("New cluster created for this face");
        setTimeout(() => setSuccessMessage(null), 3000);
      }
    } finally {
      setPendingCreateClusterFaceId(null);
    }
  };

  return (
    <section className={styles.panel}>
      <header className={styles.panelHeader}>
        <div className={styles.panelTitleRow}>
          <h2 className={styles.panelTitle}>Unassigned Faces</h2>
          <span className={styles.panelMeta}>{faces.length} loaded</span>
        </div>
      </header>

      <div className={styles.panelBody}>
        {isLoading ? <div className={styles.message}>Loading unassigned faces...</div> : null}
        {errorMessage ? <div className={styles.errorMessage}>{errorMessage}</div> : null}
        {actionErrorMessage ? <div className={styles.errorMessage}>{actionErrorMessage}</div> : null}
        {successMessage ? <div className={styles.message}>{successMessage}</div> : null}

        {!isLoading && !errorMessage && faces.length > 0 ? (
          <input
            type="search"
            className={styles.searchInput}
            placeholder="Search by face ID or asset hash..."
            value={faceSearch}
            onChange={(e) => setFaceSearch(e.target.value)}
          />
        ) : null}

        {!isLoading && !errorMessage && visibleFaces.length === 0 && faces.length > 0 ? (
          <div className={styles.emptyState}>No faces match your search.</div>
        ) : null}
        {!isLoading && !errorMessage && faces.length === 0 ? (
          <div className={styles.emptyState}>No unassigned faces found.</div>
        ) : null}

        {!isLoading && !errorMessage && visibleFaces.length > 0 ? (
          <div className={`${styles.faceGrid} ${styles.unassignedFaceGrid}`}>
            {visibleFaces.map((face) => {
              const destinationQuery = destinationSearchByFaceId[face.face_id] ?? "";
              const matchingDestinations = getMatchingDestinations(destinationQuery);
              const isDestinationSelected = destinationSelectedByFaceId[face.face_id] ?? false;

              return (
                <article key={face.face_id} className={styles.faceTile}>
                {resolveApiUrl(face.thumbnail_url) && !failedImageByFaceId[face.face_id] ? (
                  <img
                    className={styles.faceImage}
                    src={resolveApiUrl(face.thumbnail_url) ?? ""}
                    alt={`Face ${face.face_id}`}
                    onError={() =>
                      setFailedImageByFaceId((current) => ({
                        ...current,
                        [face.face_id]: true
                      }))
                    }
                  />
                ) : (
                  <div className={styles.facePlaceholder}>
                    <div>
                      <strong>Face #{face.face_id}</strong>
                      <div>No thumbnail</div>
                    </div>
                  </div>
                )}

                <div>
                  <p className={styles.faceTitle}>Face #{face.face_id}</p>
                  <p className={styles.faceMeta}>{face.asset_sha256.slice(0, 12)}</p>
                </div>

                <div className={styles.unassignedMoveSection}>
                  <div className={styles.destinationSearchWrap}>
                    <input
                      type="text"
                      className={styles.faceMoveInput}
                      placeholder="Cluster ID or name"
                      value={destinationQuery}
                      onChange={(event) => updateDestinationSearch(face.face_id, event.target.value)}
                      disabled={pendingMoveFaceId === face.face_id || pendingCreateClusterFaceId === face.face_id}
                    />
                    {destinationQuery && matchingDestinations.length > 0 && !isDestinationSelected ? (
                      <div className={styles.destinationResults}>
                        {matchingDestinations.map((result) => (
                          <button
                            key={result.clusterId}
                            type="button"
                            onClick={() =>
                              selectDestination(
                                face.face_id,
                                result.clusterId,
                                result.personName ?? `Cluster #${result.clusterId}`,
                              )
                            }
                            className={styles.destinationOption}
                          >
                            {result.displayText}
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>

                  <div className={styles.unassignedActionButtons}>
                    <button
                      type="button"
                      className={styles.faceMoveButton}
                      onClick={() => void handleMove(face.face_id)}
                      disabled={
                        pendingMoveFaceId === face.face_id ||
                        pendingCreateClusterFaceId === face.face_id ||
                        !(moveTargetByFaceId[face.face_id] || destinationQuery)
                      }
                    >
                      {pendingMoveFaceId === face.face_id ? "Moving..." : "Move"}
                    </button>
                    <button
                      type="button"
                      className={styles.faceMoveButton}
                      onClick={() => void handleCreateNewCluster(face.face_id)}
                      disabled={pendingMoveFaceId === face.face_id || pendingCreateClusterFaceId === face.face_id}
                    >
                      {pendingCreateClusterFaceId === face.face_id ? "Creating..." : "New Cluster"}
                    </button>
                  </div>
                </div>
                </article>
              );
            })}
          </div>
        ) : null}
      </div>
    </section>
  );
}

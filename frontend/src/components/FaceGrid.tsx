import { useMemo, useState } from "react";

import styles from "@/components/review-screen.module.css";
import { resolveApiUrl } from "@/lib/api";
import type { ClusterSummary, FaceSummary, PersonWithClusters } from "@/types/ui-api";

interface FaceGridProps {
  faces: FaceSummary[];
  selectedClusterId: number;
  currentPersonName: string | null;
  clusters: ClusterSummary[];
  peopleWithClusters: PersonWithClusters[];
  onRemoveFace: (faceId: number) => Promise<boolean>;
  onMoveFace: (faceId: number, targetClusterId: number) => Promise<boolean>;
}

interface PersonMatch {
  person: PersonWithClusters;
  reason: "exact_name" | "exact_alias" | "contains";
}

function normalizeLookupText(value: string): string {
  return value.trim().replace(/\s+/g, " ").toLowerCase();
}

function compareClustersForDefaultTarget(a: ClusterSummary, b: ClusterSummary): number {
  if (a.face_count !== b.face_count) {
    return b.face_count - a.face_count;
  }

  if (a.is_ignored !== b.is_ignored) {
    return a.is_ignored ? 1 : -1;
  }

  const aAssigned = a.person_id !== null;
  const bAssigned = b.person_id !== null;
  if (aAssigned !== bAssigned) {
    return aAssigned ? -1 : 1;
  }

  return a.cluster_id - b.cluster_id;
}

function resolvePeopleMatches(query: string, people: PersonWithClusters[]): PersonMatch[] {
  const normalizedQuery = normalizeLookupText(query);
  if (!normalizedQuery) {
    return [];
  }

  const exactNameMatches = people.filter(
    (person) => normalizeLookupText(person.display_name) === normalizedQuery
  );
  if (exactNameMatches.length > 0) {
    return exactNameMatches.map((person) => ({ person, reason: "exact_name" }));
  }

  const exactAliasMatches = people.filter((person) =>
    person.aliases.some((alias) => normalizeLookupText(alias) === normalizedQuery)
  );
  if (exactAliasMatches.length > 0) {
    return exactAliasMatches.map((person) => ({ person, reason: "exact_alias" }));
  }

  const containsMatches = people.filter((person) => {
    if (normalizeLookupText(person.display_name).includes(normalizedQuery)) {
      return true;
    }
    return person.aliases.some((alias) => normalizeLookupText(alias).includes(normalizedQuery));
  });
  return containsMatches.map((person) => ({ person, reason: "contains" }));
}

export function FaceGrid({
  faces,
  selectedClusterId,
  currentPersonName,
  clusters,
  peopleWithClusters,
  onRemoveFace,
  onMoveFace
}: FaceGridProps) {
  const [moveTargetByFaceId, setMoveTargetByFaceId] = useState<Record<number, string>>({});
  const [pendingRemoveFaceId, setPendingRemoveFaceId] = useState<number | null>(null);
  const [pendingMoveFaceId, setPendingMoveFaceId] = useState<number | null>(null);
  const [failedImageByFaceId, setFailedImageByFaceId] = useState<Record<number, boolean>>({});
  const [previewFaceId, setPreviewFaceId] = useState<number | null>(null);
  const [actionErrorMessage, setActionErrorMessage] = useState<string | null>(null);
  const [moveConfirmState, setMoveConfirmState] = useState<{
    faceId: number;
    person: PersonWithClusters;
    candidateClusters: ClusterSummary[];
    selectedTargetClusterId: number;
  } | null>(null);
  const faceById = useMemo(() => {
    const index = new Map<number, FaceSummary>();
    for (const face of faces) {
      index.set(face.face_id, face);
    }
    return index;
  }, [faces]);

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

  const handleRemove = async (faceId: number) => {
    if (!window.confirm("Remove this face from its cluster?")) {
      return;
    }

    setPendingRemoveFaceId(faceId);

    try {
      await onRemoveFace(faceId);
    } finally {
      setPendingRemoveFaceId(null);
    }
  };

  const handleMove = async (faceId: number) => {
    setActionErrorMessage(null);
    const draftTarget = moveTargetByFaceId[faceId]?.trim() ?? "";
    if (!draftTarget) {
      return;
    }

    const parsedTarget = Number(draftTarget);
    if (Number.isInteger(parsedTarget) && parsedTarget > 0) {
      if (parsedTarget === selectedClusterId) {
        setActionErrorMessage("Target cluster must be different from the selected cluster.");
        return;
      }

      setPendingMoveFaceId(faceId);

      try {
        const moveSucceeded = await onMoveFace(faceId, parsedTarget);
        if (moveSucceeded) {
          clearMoveTarget(faceId);
          if (previewFaceId === faceId) {
            setPreviewFaceId(null);
          }
        }
      } finally {
        setPendingMoveFaceId(null);
      }
      return;
    }

    const peopleMatches = resolvePeopleMatches(draftTarget, peopleWithClusters);
    if (peopleMatches.length === 0) {
      setActionErrorMessage("No person matched that name or alias.");
      return;
    }

    if (peopleMatches.length > 1) {
      setActionErrorMessage("Multiple people matched. Enter a more specific name or alias.");
      return;
    }

    const matchedPerson = peopleMatches[0].person;
    const candidateClusters = clusters
      .filter((cluster) => cluster.person_id === matchedPerson.person_id && !cluster.is_ignored)
      .sort(compareClustersForDefaultTarget);

    if (candidateClusters.length === 0) {
      setActionErrorMessage("No eligible clusters found for that person in the current loaded results.");
      return;
    }

    setMoveConfirmState({
      faceId,
      person: matchedPerson,
      candidateClusters,
      selectedTargetClusterId: candidateClusters[0].cluster_id,
    });
  };

  const handleConfirmMoveToPersonCluster = async () => {
    if (!moveConfirmState) {
      return;
    }

    const { faceId, selectedTargetClusterId } = moveConfirmState;
    if (selectedTargetClusterId === selectedClusterId) {
      setActionErrorMessage("Target cluster must be different from the selected cluster.");
      return;
    }

    setPendingMoveFaceId(faceId);

    try {
      const moveSucceeded = await onMoveFace(faceId, selectedTargetClusterId);
      if (moveSucceeded) {
        clearMoveTarget(faceId);
        setMoveConfirmState(null);
        if (previewFaceId === faceId) {
          setPreviewFaceId(null);
        }
      }
    } finally {
      setPendingMoveFaceId(null);
    }
  };

  const renderFaceActions = (face: FaceSummary) => {
    const isBusy = pendingRemoveFaceId === face.face_id || pendingMoveFaceId === face.face_id;

    return (
      <div className={styles.faceActions}>
        <button
          type="button"
          className={styles.faceDangerButton}
          onClick={() => void handleRemove(face.face_id)}
          disabled={isBusy}
        >
          {pendingRemoveFaceId === face.face_id ? "Removing..." : "Remove from cluster"}
        </button>

        <div className={styles.faceMoveRow}>
          <input
            type="text"
            className={styles.faceMoveInput}
            value={moveTargetByFaceId[face.face_id] ?? ""}
            placeholder={`Cluster ID or person/alias (not ${selectedClusterId})`}
            onChange={(event) => updateMoveTarget(face.face_id, event.target.value)}
            disabled={isBusy}
          />
          <button
            type="button"
            className={styles.faceMoveButton}
            onClick={() => void handleMove(face.face_id)}
            disabled={isBusy || !(moveTargetByFaceId[face.face_id]?.trim())}
          >
            {pendingMoveFaceId === face.face_id ? "Moving..." : "Move"}
          </button>
        </div>
      </div>
    );
  };

  if (faces.length === 0) {
    return <div className={styles.emptyState}>This cluster has no faces.</div>;
  }

  return (
    <>
      {actionErrorMessage ? <div className={styles.errorMessage}>{actionErrorMessage}</div> : null}

      <div className={styles.faceGrid}>
        {faces.map((face) => (
          <article key={face.face_id} className={styles.faceTile}>
            <button
              type="button"
              className={styles.facePreviewButton}
              onClick={() => {
                setActionErrorMessage(null);
                setPreviewFaceId(face.face_id);
              }}
            >
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
            </button>

            <div>
              <p className={styles.faceTitle}>Face #{face.face_id}</p>
              <p className={styles.faceMeta}>{face.asset_sha256}</p>
            </div>

            {renderFaceActions(face)}
          </article>
        ))}
      </div>

      {previewFaceId !== null ? (
        <div className={styles.mergeConfirmOverlay}>
          <div className={styles.mergeConfirmDialog} role="dialog" aria-modal="true" aria-label="Face preview">
            <h3 className={styles.mergeConfirmTitle}>Face Preview</h3>
            {(() => {
              const face = faceById.get(previewFaceId);
              if (!face) {
                return <div className={styles.errorMessage}>Face could not be loaded.</div>;
              }

              return (
                <>
                  {resolveApiUrl(face.thumbnail_url) && !failedImageByFaceId[face.face_id] ? (
                    <img
                      className={styles.faceImageLarge}
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
                    <div className={styles.facePlaceholderLarge}>
                      <div>
                        <strong>Face #{face.face_id}</strong>
                        <div>No thumbnail</div>
                      </div>
                    </div>
                  )}

                  <div className={styles.mergeConfirmGrid}>
                    <span className={styles.infoLabel}>Face ID</span>
                    <span>{face.face_id}</span>
                    <span className={styles.infoLabel}>Current cluster</span>
                    <span>#{selectedClusterId}</span>
                    <span className={styles.infoLabel}>Current person</span>
                    <span>{currentPersonName ?? "Unassigned"}</span>
                    <span className={styles.infoLabel}>Asset</span>
                    <span>{face.asset_sha256}</span>
                  </div>

                  {renderFaceActions(face)}
                </>
              );
            })()}

            <div className={styles.actionRow}>
              <button
                type="button"
                className={styles.clusterNavButton}
                onClick={() => setPreviewFaceId(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {moveConfirmState ? (
        <div className={styles.mergeConfirmOverlay}>
          <div className={styles.mergeConfirmDialog} role="dialog" aria-modal="true" aria-label="Confirm face move">
            <h3 className={styles.mergeConfirmTitle}>Confirm Face Move</h3>
            <div className={styles.mergeConfirmGrid}>
              <span className={styles.infoLabel}>Face</span>
              <span>#{moveConfirmState.faceId}</span>
              <span className={styles.infoLabel}>Resolved person</span>
              <span>{moveConfirmState.person.display_name}</span>
              <span className={styles.infoLabel}>Default target</span>
              <span>#{moveConfirmState.candidateClusters[0].cluster_id} ({moveConfirmState.candidateClusters[0].face_count} faces)</span>
            </div>

            {moveConfirmState.candidateClusters.length > 1 ? (
              <label className={styles.mergeLabel}>
                Override target cluster
                <select
                  className={styles.select}
                  value={moveConfirmState.selectedTargetClusterId}
                  onChange={(event) => {
                    const nextClusterId = Number(event.target.value);
                    setMoveConfirmState((current) =>
                      current
                        ? {
                            ...current,
                            selectedTargetClusterId: nextClusterId,
                          }
                        : current
                    );
                  }}
                >
                  {moveConfirmState.candidateClusters.map((cluster) => (
                    <option key={cluster.cluster_id} value={cluster.cluster_id}>
                      Cluster #{cluster.cluster_id} - {cluster.face_count} faces
                    </option>
                  ))}
                </select>
              </label>
            ) : null}

            <p className={styles.mergeConfirmWarning}>
              This will move one face into the selected target cluster.
            </p>

            <div className={styles.actionRow}>
              <button
                type="button"
                className={styles.assignButton}
                onClick={() => {
                  void handleConfirmMoveToPersonCluster();
                }}
                disabled={pendingMoveFaceId === moveConfirmState.faceId}
              >
                {pendingMoveFaceId === moveConfirmState.faceId ? "Moving..." : "Confirm Move"}
              </button>
              <button
                type="button"
                className={styles.clusterNavButton}
                onClick={() => setMoveConfirmState(null)}
                disabled={pendingMoveFaceId === moveConfirmState.faceId}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

import { useEffect, useMemo, useState } from "react";

import styles from "@/components/review-screen.module.css";
import { getPhotoDetail, resolveApiUrl } from "@/lib/api";
import type { ClusterSummary, FaceSummary, PersonWithClusters, PhotoDetail } from "@/types/ui-api";

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

function buildDirectAssetImagePathFromFace(face: FaceSummary): string | null {
  const filename = (face.filename ?? "").trim();
  if (!filename) {
    return null;
  }

  const dotIndex = filename.lastIndexOf(".");
  if (dotIndex < 0 || dotIndex === filename.length - 1) {
    return null;
  }

  const extension = filename.slice(dotIndex + 1).trim().toLowerCase();
  if (!/^[a-z0-9]+$/.test(extension)) {
    return null;
  }

  const prefix = face.asset_sha256.slice(0, 2);
  return `/media/assets/${prefix}/${face.asset_sha256}.${extension}`;
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
  const [failedFullImageByFaceId, setFailedFullImageByFaceId] = useState<Record<number, boolean>>({});
  const [loadedFullImageByFaceId, setLoadedFullImageByFaceId] = useState<Record<number, boolean>>({});
  const [fullImageOverrideByFaceId, setFullImageOverrideByFaceId] = useState<Record<number, string>>({});
  const [faceSearch, setFaceSearch] = useState("");
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [previewFaceId, setPreviewFaceId] = useState<number | null>(null);
  const [previewNaturalDims, setPreviewNaturalDims] = useState<{ w: number; h: number } | null>(null);
  const [photoDetailByAsset, setPhotoDetailByAsset] = useState<
    Record<string, { state: "loading" | "ready" | "error"; detail?: PhotoDetail; error?: string }>
  >({});

  const faceById = useMemo(() => {
    const index = new Map<number, FaceSummary>();
    for (const face of faces) {
      index.set(face.face_id, face);
    }
    return index;
  }, [faces]);

  const previewFace = useMemo(() => {
    if (previewFaceId === null) {
      return null;
    }
    return faceById.get(previewFaceId) ?? null;
  }, [faceById, previewFaceId]);

  useEffect(() => {
    if (!previewFace) {
      setPreviewNaturalDims(null);
      return;
    }

    const assetSha = previewFace.asset_sha256;
    const existing = photoDetailByAsset[assetSha];
    if (existing?.state === "ready" || existing?.state === "loading") {
      return;
    }

    let cancelled = false;
    setPhotoDetailByAsset((current) => ({
      ...current,
      [assetSha]: { state: "loading" },
    }));

    async function loadDetail() {
      try {
        const detail = await getPhotoDetail(assetSha);
        if (cancelled) {
          return;
        }
        setPhotoDetailByAsset((current) => ({
          ...current,
          [assetSha]: { state: "ready", detail },
        }));
      } catch (error) {
        if (cancelled) {
          return;
        }
        const message = error instanceof Error && error.message ? error.message : "Could not load full image context.";
        setPhotoDetailByAsset((current) => ({
          ...current,
          [assetSha]: { state: "error", error: message },
        }));
      }
    }

    void loadDetail();
    return () => {
      cancelled = true;
    };
  }, [photoDetailByAsset, previewFace]);

  useEffect(() => {
    if (previewFaceId === null) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setPreviewFaceId(null);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [previewFaceId]);

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
      aliases: string[];
      displayText: string;
    }> = [];

    clusters.forEach((cluster) => {
      const person = peopleWithClusters.find((p) => p.person_id === cluster.person_id);
      const personName = person?.display_name ?? null;
      allResults.push({
        clusterId: cluster.cluster_id,
        personName,
        aliases: person?.aliases ?? [],
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
      const aliasMatch = result.aliases.some((alias) => alias.toLowerCase().includes(q));
      return idMatch || nameMatch || aliasMatch;
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
        setSuccessMessage("New cluster created. This face may leave the list because it is no longer unassigned.");
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
                <button
                  type="button"
                  className={styles.facePreviewButton}
                  onClick={() => {
                    setPreviewFaceId(face.face_id);
                    setPreviewNaturalDims(null);
                    setFailedFullImageByFaceId((current) => ({
                      ...current,
                      [face.face_id]: false,
                    }));
                    setLoadedFullImageByFaceId((current) => ({
                      ...current,
                      [face.face_id]: false,
                    }));
                    setFullImageOverrideByFaceId((current) => {
                      const next = { ...current };
                      delete next[face.face_id];
                      return next;
                    });
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

        {previewFace ? (
          <div
            className={styles.mergeConfirmOverlay}
            onMouseDown={(event) => {
              if (event.target === event.currentTarget) {
                setPreviewFaceId(null);
              }
            }}
          >
            <div className={styles.mergeConfirmDialog} role="dialog" aria-modal="true" aria-label="Unassigned face preview">
              <h3 className={styles.mergeConfirmTitle}>Face Preview</h3>
              {(() => {
                const face = previewFace;
                const photoDetailState = photoDetailByAsset[face.asset_sha256];
                const photoDetail = photoDetailState?.state === "ready" ? photoDetailState.detail : null;
                const previewFaceInPhoto = photoDetail?.faces.find((candidate) => candidate.face_id === face.face_id) ?? null;
                const detailPreferredUrl = resolveApiUrl(photoDetail?.display_url || photoDetail?.image_url);
                const filenameFallbackUrl = resolveApiUrl(buildDirectAssetImagePathFromFace(face));
                const originalUrl = resolveApiUrl(photoDetail?.original_url);
                const fullImageUrl =
                  fullImageOverrideByFaceId[face.face_id] ||
                  detailPreferredUrl ||
                  filenameFallbackUrl ||
                  originalUrl;
                const fullImageFailed = failedFullImageByFaceId[face.face_id] ?? false;
                const fullImageLoaded = loadedFullImageByFaceId[face.face_id] ?? false;
                const canHighlightFace =
                  fullImageUrl !== null &&
                  !fullImageFailed &&
                  previewFaceInPhoto !== null &&
                  previewNaturalDims !== null &&
                  photoDetail?.display_rotation_degrees === 0;
                const displayFilename = (face.filename ?? "").trim() || photoDetail?.filename || "Filename unavailable";

                return (
                  <>
                    <div className={styles.mergeConfirmGrid}>
                      <span className={styles.infoLabel}>Filename</span>
                      <span>{displayFilename}</span>
                    </div>

                    {photoDetailState?.state === "loading" && !fullImageLoaded ? (
                      <div className={styles.loadingMessage}>Loading full image context...</div>
                    ) : null}

                    {fullImageUrl && !fullImageFailed ? (
                      <div className={styles.facePreviewContextShell}>
                        <img
                          className={styles.facePreviewContextImage}
                          src={fullImageUrl}
                          alt={displayFilename}
                          onLoad={(event) => {
                            const img = event.currentTarget;
                            setPreviewNaturalDims({ w: img.naturalWidth, h: img.naturalHeight });
                            setLoadedFullImageByFaceId((current) => ({
                              ...current,
                              [face.face_id]: true,
                            }));
                          }}
                          onError={() => {
                            if (filenameFallbackUrl && fullImageUrl !== filenameFallbackUrl) {
                              setLoadedFullImageByFaceId((current) => ({
                                ...current,
                                [face.face_id]: false,
                              }));
                              setFullImageOverrideByFaceId((current) => ({
                                ...current,
                                [face.face_id]: filenameFallbackUrl,
                              }));
                              return;
                            }
                            setFailedFullImageByFaceId((current) => ({
                              ...current,
                              [face.face_id]: true,
                            }));
                            setLoadedFullImageByFaceId((current) => ({
                              ...current,
                              [face.face_id]: false,
                            }));
                          }}
                        />
                        {canHighlightFace ? (
                          <div className={styles.faceOverlayLayer}>
                            <div
                              className={`${styles.faceBox} ${styles.faceBoxActive}`.trim()}
                              style={{
                                left: `${(previewFaceInPhoto.bbox.x / previewNaturalDims.w) * 100}%`,
                                top: `${(previewFaceInPhoto.bbox.y / previewNaturalDims.h) * 100}%`,
                                width: `${(previewFaceInPhoto.bbox.w / previewNaturalDims.w) * 100}%`,
                                height: `${(previewFaceInPhoto.bbox.h / previewNaturalDims.h) * 100}%`,
                              }}
                            />
                          </div>
                        ) : null}
                      </div>
                    ) : null}

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

                    {photoDetailState?.state !== "loading" && (fullImageUrl === null || fullImageFailed) ? (
                      <div className={styles.hintMessage}>Full image unavailable. Showing face crop only.</div>
                    ) : null}
                    {photoDetailState?.state !== "loading" && fullImageUrl !== null && !fullImageFailed && !canHighlightFace ? (
                      <div className={styles.hintMessage}>
                        Full image context loaded. Face highlight unavailable for this image configuration.
                      </div>
                    ) : null}
                    {photoDetailState?.state === "error" ? (
                      <div className={styles.errorMessage}>{photoDetailState.error}</div>
                    ) : null}

                    <div className={styles.mergeConfirmGrid}>
                      <span className={styles.infoLabel}>Face ID</span>
                      <span>{face.face_id}</span>
                      <span className={styles.infoLabel}>Current cluster</span>
                      <span>Unassigned</span>
                      <span className={styles.infoLabel}>Asset</span>
                      <span>{face.asset_sha256}</span>
                    </div>
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
      </div>
    </section>
  );
}

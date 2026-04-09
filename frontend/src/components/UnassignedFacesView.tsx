import { useState } from "react";

import styles from "@/components/review-screen.module.css";
import { resolveApiUrl } from "@/lib/api";
import type { FaceSummary } from "@/types/ui-api";

interface UnassignedFacesViewProps {
  faces: FaceSummary[];
  isLoading: boolean;
  errorMessage: string | null;
  actionErrorMessage: string | null;
  onMoveFace: (faceId: number, targetClusterId: number) => Promise<boolean>;
  onValidationError: (message: string) => void;
}

export function UnassignedFacesView({
  faces,
  isLoading,
  errorMessage,
  actionErrorMessage,
  onMoveFace,
  onValidationError
}: UnassignedFacesViewProps) {
  const [moveTargetByFaceId, setMoveTargetByFaceId] = useState<Record<number, string>>({});
  const [pendingMoveFaceId, setPendingMoveFaceId] = useState<number | null>(null);
  const [failedImageByFaceId, setFailedImageByFaceId] = useState<Record<number, boolean>>({});

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

  const handleMove = async (faceId: number) => {
    const draftTarget = moveTargetByFaceId[faceId]?.trim() ?? "";

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

    try {
      const moveSucceeded = await onMoveFace(faceId, parsedTarget);
      if (moveSucceeded) {
        clearMoveTarget(faceId);
      }
    } finally {
      setPendingMoveFaceId(null);
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

        {!isLoading && !errorMessage && faces.length === 0 ? (
          <div className={styles.emptyState}>No unassigned faces found.</div>
        ) : null}

        {!isLoading && !errorMessage && faces.length > 0 ? (
          <div className={styles.faceGrid}>
            {faces.map((face) => (
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

                <div className={styles.faceMoveRow}>
                  <input
                    type="number"
                    min={1}
                    className={styles.faceMoveInput}
                    value={moveTargetByFaceId[face.face_id] ?? ""}
                    placeholder="Target cluster id"
                    onChange={(event) => updateMoveTarget(face.face_id, event.target.value)}
                    disabled={pendingMoveFaceId === face.face_id}
                  />
                  <button
                    type="button"
                    className={styles.faceMoveButton}
                    onClick={() => void handleMove(face.face_id)}
                    disabled={pendingMoveFaceId === face.face_id}
                  >
                    {pendingMoveFaceId === face.face_id ? "Moving..." : "Move to Cluster"}
                  </button>
                </div>
              </article>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}

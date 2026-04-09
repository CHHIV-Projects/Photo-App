import { useState } from "react";

import styles from "@/components/review-screen.module.css";
import type { FaceSummary } from "@/types/ui-api";

interface FaceGridProps {
  faces: FaceSummary[];
  selectedClusterId: number;
  onRemoveFace: (faceId: number) => Promise<boolean>;
  onMoveFace: (faceId: number, targetClusterId: number) => Promise<boolean>;
}

export function FaceGrid({
  faces,
  selectedClusterId,
  onRemoveFace,
  onMoveFace
}: FaceGridProps) {
  const [moveTargetByFaceId, setMoveTargetByFaceId] = useState<Record<number, string>>({});
  const [pendingRemoveFaceId, setPendingRemoveFaceId] = useState<number | null>(null);
  const [pendingMoveFaceId, setPendingMoveFaceId] = useState<number | null>(null);

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
    const draftTarget = moveTargetByFaceId[faceId]?.trim() ?? "";
    const parsedTarget = Number(draftTarget);

    if (!draftTarget || Number.isNaN(parsedTarget) || parsedTarget < 1) {
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

  if (faces.length === 0) {
    return <div className={styles.emptyState}>This cluster has no faces.</div>;
  }

  return (
    <div className={styles.faceGrid}>
      {faces.map((face) => (
        <article key={face.face_id} className={styles.faceTile}>
          {face.thumbnail_url ? (
            <img
              className={styles.faceImage}
              src={face.thumbnail_url}
              alt={`Face ${face.face_id}`}
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
            <p className={styles.faceMeta}>{face.asset_sha256}</p>
          </div>

          <div className={styles.faceActions}>
            <button
              type="button"
              className={styles.faceDangerButton}
              onClick={() => void handleRemove(face.face_id)}
              disabled={pendingRemoveFaceId === face.face_id || pendingMoveFaceId === face.face_id}
            >
              {pendingRemoveFaceId === face.face_id ? "Removing..." : "Remove from cluster"}
            </button>

            <div className={styles.faceMoveRow}>
              <input
                type="number"
                min={1}
                className={styles.faceMoveInput}
                value={moveTargetByFaceId[face.face_id] ?? ""}
                placeholder={`Target cluster (not ${selectedClusterId})`}
                onChange={(event) => updateMoveTarget(face.face_id, event.target.value)}
                disabled={pendingMoveFaceId === face.face_id || pendingRemoveFaceId === face.face_id}
              />
              <button
                type="button"
                className={styles.faceMoveButton}
                onClick={() => void handleMove(face.face_id)}
                disabled={
                  pendingMoveFaceId === face.face_id ||
                  pendingRemoveFaceId === face.face_id ||
                  !(moveTargetByFaceId[face.face_id]?.trim())
                }
              >
                {pendingMoveFaceId === face.face_id ? "Moving..." : "Move"}
              </button>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

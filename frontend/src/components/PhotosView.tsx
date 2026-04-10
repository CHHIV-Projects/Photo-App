"use client";

import { useEffect, useRef, useState } from "react";

import { resolveApiUrl } from "@/lib/api";
import type { FaceInPhoto, PhotoDetail, PhotoSummary } from "@/types/ui-api";
import styles from "./photos-view.module.css";

interface Props {
  photos: PhotoSummary[];
  isLoading: boolean;
  errorMessage: string | null;
  selectedPhotoSha256: string | null;
  photoDetail: PhotoDetail | null;
  isLoadingDetail: boolean;
  photoDetailErrorMessage: string | null;
  onSelectPhoto: (sha256: string) => void;
}

export function PhotosView({
  photos,
  isLoading,
  errorMessage,
  selectedPhotoSha256,
  photoDetail,
  isLoadingDetail,
  photoDetailErrorMessage,
  onSelectPhoto,
}: Props) {
  const [selectedFaceId, setSelectedFaceId] = useState<number | null>(null);
  const [naturalDims, setNaturalDims] = useState<{ w: number; h: number } | null>(null);
  const [imageLoadError, setImageLoadError] = useState(false);
  const faceRowRefs = useRef<Map<number, HTMLLIElement>>(new Map());

  // Reset face selection and image state when the selected photo changes.
  useEffect(() => {
    setSelectedFaceId(null);
    setNaturalDims(null);
    setImageLoadError(false);
  }, [selectedPhotoSha256]);

  // Auto-scroll the face row into view when selection changes.
  useEffect(() => {
    if (selectedFaceId === null) return;
    const el = faceRowRefs.current.get(selectedFaceId);
    el?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [selectedFaceId]);

  function getFaceLabel(face: FaceInPhoto): string {
    if (face.person_name) return face.person_name;
    if (face.cluster_id !== null) return `Cluster #${face.cluster_id} — No Person Assigned`;
    return "Unassigned";
  }

  function toggleFace(faceId: number) {
    setSelectedFaceId((prev) => (prev === faceId ? null : faceId));
  }

  return (
    <div className={styles.layout}>
      {/* ── Photo list ────────────────────────────────────────────── */}
      <aside className={styles.panel}>
        <div className={styles.panelHeader}>
          <h2 className={styles.panelTitle}>Photos</h2>
          <span className={styles.panelCount}>{photos.length}</span>
        </div>

        <div className={styles.photoList}>
          {isLoading ? (
            <p className={styles.statusMessage}>Loading photos…</p>
          ) : errorMessage ? (
            <p className={styles.errorMessage}>{errorMessage}</p>
          ) : photos.length === 0 ? (
            <p className={styles.statusMessage}>No photos found.</p>
          ) : (
            photos.map((photo) => (
              <button
                key={photo.asset_sha256}
                type="button"
                className={
                  `${styles.photoItem} ${selectedPhotoSha256 === photo.asset_sha256 ? styles.photoItemActive : ""}`.trim()
                }
                onClick={() => onSelectPhoto(photo.asset_sha256)}
              >
                <div className={styles.photoThumb}>
                  <img
                    src={resolveApiUrl(photo.image_url) ?? ""}
                    alt={photo.filename}
                    className={styles.photoThumbImg}
                    onError={(e) => {
                      (e.currentTarget as HTMLImageElement).style.display = "none";
                    }}
                  />
                </div>
                <div className={styles.photoMeta}>
                  <span className={styles.photoFilename}>{photo.filename}</span>
                  <span className={styles.photoFaceCount}>
                    {photo.face_count} {photo.face_count === 1 ? "face" : "faces"}
                  </span>
                </div>
              </button>
            ))
          )}
        </div>
      </aside>

      {/* ── Photo detail ──────────────────────────────────────────── */}
      <div className={styles.detailArea}>
        {isLoadingDetail ? (
          <div className={styles.panel}>
            <p className={styles.statusMessage}>Loading photo…</p>
          </div>
        ) : photoDetailErrorMessage ? (
          <div className={styles.panel}>
            <p className={styles.errorMessage}>{photoDetailErrorMessage}</p>
          </div>
        ) : !photoDetail ? (
          <div className={styles.panel}>
            <p className={styles.statusMessage}>Select a photo to view.</p>
          </div>
        ) : (
          <>
            {/* Full image with face overlays */}
            <div className={styles.panel}>
              <div className={styles.imageWrapper}>
                {imageLoadError ? (
                  <div className={styles.imagePlaceholder}>Image unavailable</div>
                ) : (
                  <div className={styles.imageContainer}>
                    <img
                      src={resolveApiUrl(photoDetail.image_url) ?? ""}
                      alt={photoDetail.filename}
                      className={styles.fullImage}
                      onLoad={(e) => {
                        const img = e.currentTarget as HTMLImageElement;
                        setNaturalDims({ w: img.naturalWidth, h: img.naturalHeight });
                      }}
                      onError={() => setImageLoadError(true)}
                    />
                    {naturalDims &&
                      photoDetail.faces.map((face) => (
                        <div
                          key={face.face_id}
                          role="button"
                          tabIndex={0}
                          aria-label={getFaceLabel(face)}
                          className={
                            `${styles.faceBox} ${selectedFaceId === face.face_id ? styles.faceBoxActive : ""}`.trim()
                          }
                          style={{
                            left: `${(face.bbox.x / naturalDims.w) * 100}%`,
                            top: `${(face.bbox.y / naturalDims.h) * 100}%`,
                            width: `${(face.bbox.w / naturalDims.w) * 100}%`,
                            height: `${(face.bbox.h / naturalDims.h) * 100}%`,
                          }}
                          onClick={() => toggleFace(face.face_id)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") toggleFace(face.face_id);
                          }}
                          title={getFaceLabel(face)}
                        />
                      ))}
                  </div>
                )}
              </div>
              <p className={styles.imageFilename}>{photoDetail.filename}</p>
            </div>

            {/* Face list */}
            <div className={styles.panel}>
              <div className={styles.panelHeader}>
                <h2 className={styles.panelTitle}>Faces in Photo</h2>
                <span className={styles.panelCount}>{photoDetail.faces.length}</span>
              </div>

              {photoDetail.faces.length === 0 ? (
                <p className={styles.statusMessage}>No faces detected in this photo.</p>
              ) : (
                <ul className={styles.faceList}>
                  {photoDetail.faces.map((face) => (
                    <li
                      key={face.face_id}
                      ref={(el) => {
                        if (el) faceRowRefs.current.set(face.face_id, el);
                        else faceRowRefs.current.delete(face.face_id);
                      }}
                    >
                      <button
                        type="button"
                        className={
                          `${styles.faceRow} ${selectedFaceId === face.face_id ? styles.faceRowActive : ""}`.trim()
                        }
                        onClick={() => toggleFace(face.face_id)}
                      >
                        <span className={styles.faceId}>Face #{face.face_id}</span>
                        <span className={styles.faceSep}>—</span>
                        <span className={styles.faceIdentity}>{getFaceLabel(face)}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

"use client";

import type { CSSProperties } from "react";
import { useEffect, useMemo, useRef, useState } from "react";

import { getPhotoDetail, resolveApiUrl, setPhotoRotation } from "@/lib/api";
import { isVideoAssetFilename } from "@/lib/media";
import type { PhotoDetail, PhotoSummary } from "@/types/ui-api";
import styles from "./presentation-viewer.module.css";

interface Props {
  items: PhotoSummary[];
  initialIndex: number;
  onClose: () => void;
}

function formatCapturedAt(value: string | null): string | null {
  if (!value) {
    return null;
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
}

function normalizeRotation(value: number): 0 | 90 | 180 | 270 {
  const wrapped = ((value % 360) + 360) % 360;
  if (wrapped === 90 || wrapped === 180 || wrapped === 270) {
    return wrapped;
  }
  return 0;
}

function getImageTransform(rotation: 0 | 90 | 180 | 270): string {
  return `rotate(${rotation}deg)`;
}

function getErrorMessage(error: unknown, fallbackMessage: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallbackMessage;
}

export function PresentationViewer({ items, initialIndex, onClose }: Props) {
  const [currentIndex, setCurrentIndex] = useState(initialIndex);
  const [photoDetail, setPhotoDetail] = useState<PhotoDetail | null>(null);
  const [detailErrorMessage, setDetailErrorMessage] = useState<string | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isUpdatingRotation, setIsUpdatingRotation] = useState(false);
  const [rotationErrorMessage, setRotationErrorMessage] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [naturalDims, setNaturalDims] = useState<{ w: number; h: number } | null>(null);
  const [imageViewportWidth, setImageViewportWidth] = useState<number | null>(null);
  const [windowHeight, setWindowHeight] = useState<number>(900);
  const imageViewportRef = useRef<HTMLDivElement | null>(null);
  const viewerShellRef = useRef<HTMLDivElement | null>(null);
  const imageMaxHeightVh = isFullscreen ? 94 : 88;

  const clampedIndex = Math.min(Math.max(currentIndex, 0), Math.max(items.length - 1, 0));
  const currentItem = items[clampedIndex] ?? null;
  const isVideoAsset = currentItem ? isVideoAssetFilename(currentItem.filename) : false;
  const displayRotationDegrees = normalizeRotation(photoDetail?.display_rotation_degrees ?? 0);
  const isQuarterTurnRotation = displayRotationDegrees === 90 || displayRotationDegrees === 270;

  const imageUrl = useMemo(() => {
    if (currentItem === null) {
      return null;
    }
    return resolveApiUrl(photoDetail?.image_url ?? currentItem.image_url);
  }, [currentItem, photoDetail?.image_url]);

  useEffect(() => {
    setCurrentIndex(initialIndex);
  }, [initialIndex]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (document.fullscreenElement === viewerShellRef.current) {
          return;
        }
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key === "ArrowLeft") {
        event.preventDefault();
        setCurrentIndex((prev) => Math.max(prev - 1, 0));
        return;
      }

      if (event.key === "ArrowRight") {
        event.preventDefault();
        setCurrentIndex((prev) => Math.min(prev + 1, items.length - 1));
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [items.length, onClose]);

  useEffect(() => {
    if (typeof document === "undefined") {
      return;
    }

    const handleFullscreenChange = () => {
      setIsFullscreen(document.fullscreenElement === viewerShellRef.current);
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    handleFullscreenChange();

    return () => document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const element = imageViewportRef.current;
    const updateWindowHeight = () => setWindowHeight(window.innerHeight);
    updateWindowHeight();

    if (!element) {
      window.addEventListener("resize", updateWindowHeight);
      return () => window.removeEventListener("resize", updateWindowHeight);
    }

    const updateViewportWidth = () => setImageViewportWidth(element.clientWidth);
    updateViewportWidth();

    const observer = new ResizeObserver(() => {
      updateViewportWidth();
    });
    observer.observe(element);
    window.addEventListener("resize", updateWindowHeight);

    return () => {
      observer.disconnect();
      window.removeEventListener("resize", updateWindowHeight);
    };
  }, [currentItem?.asset_sha256]);

  useEffect(() => {
    setNaturalDims(null);
  }, [currentItem?.asset_sha256]);

  useEffect(() => {
    setRotationErrorMessage(null);
  }, [currentItem?.asset_sha256]);

  useEffect(() => {
    if (currentItem === null) {
      setPhotoDetail(null);
      setDetailErrorMessage(null);
      return;
    }

    let isCancelled = false;

    async function loadPhotoDetail() {
      setIsLoadingDetail(true);
      setDetailErrorMessage(null);

      try {
        const detail = await getPhotoDetail(currentItem.asset_sha256);
        if (!isCancelled) {
          setPhotoDetail(detail);
        }
      } catch (error) {
        if (!isCancelled) {
          setPhotoDetail(null);
          setDetailErrorMessage(error instanceof Error && error.message ? error.message : "Failed to load photo detail.");
        }
      } finally {
        if (!isCancelled) {
          setIsLoadingDetail(false);
        }
      }
    }

    void loadPhotoDetail();

    return () => {
      isCancelled = true;
    };
  }, [currentItem?.asset_sha256]);

  function getRotatedImageFrameStyle(rotation: 0 | 90 | 180 | 270): CSSProperties | undefined {
    if (rotation !== 90 && rotation !== 270) {
      return undefined;
    }

    if (!naturalDims || naturalDims.w <= 0 || naturalDims.h <= 0 || !imageViewportWidth) {
      return {
        maxWidth: "100%",
        maxHeight: `${imageMaxHeightVh}vh`,
      };
    }

    const rotatedAspectRatio = naturalDims.h / naturalDims.w;
    const maxHeight = Math.max(320, Math.floor(windowHeight * (imageMaxHeightVh / 100)));
    const width = Math.min(imageViewportWidth, maxHeight * rotatedAspectRatio);
    const height = width / rotatedAspectRatio;

    return {
      width: `${Math.round(width)}px`,
      height: `${Math.round(height)}px`,
    };
  }

  async function toggleFullscreen() {
    const container = viewerShellRef.current;
    if (!container || typeof document === "undefined") {
      return;
    }

    if (document.fullscreenElement === container) {
      await document.exitFullscreen();
      return;
    }

    if (document.fullscreenElement) {
      await document.exitFullscreen();
    }

    await container.requestFullscreen();
  }

  async function handleClose() {
    if (typeof document !== "undefined" && document.fullscreenElement === viewerShellRef.current) {
      await document.exitFullscreen();
    }
    onClose();
  }

  async function persistRotation(nextRotation: 0 | 90 | 180 | 270) {
    if (!photoDetail) {
      return;
    }

    const assetSha256 = photoDetail.asset_sha256;
    setIsUpdatingRotation(true);
    setRotationErrorMessage(null);

    try {
      const updated = await setPhotoRotation(assetSha256, nextRotation);
      setPhotoDetail((prev) =>
        prev && prev.asset_sha256 === assetSha256
          ? { ...prev, display_rotation_degrees: updated.display_rotation_degrees }
          : prev
      );
    } catch (error) {
      setRotationErrorMessage(getErrorMessage(error, "Failed to update rotation."));
    } finally {
      setIsUpdatingRotation(false);
    }
  }

  function rotateLeft() {
    void persistRotation(normalizeRotation(displayRotationDegrees - 90));
  }

  function rotateRight() {
    void persistRotation(normalizeRotation(displayRotationDegrees + 90));
  }

  function resetRotation() {
    if (displayRotationDegrees === 0) {
      return;
    }

    void persistRotation(0);
  }

  if (currentItem === null) {
    return null;
  }

  return (
    <div className={styles.overlay} role="dialog" aria-modal="true" aria-label="Presentation viewer">
      <button type="button" className={styles.backdrop} aria-label="Close presentation" onClick={() => void handleClose()} />
      <div className={`${styles.viewerShell} ${isFullscreen ? styles.viewerShellFullscreen : ""}`.trim()} ref={viewerShellRef}>
        <div className={styles.topBar}>
          <div className={styles.metaBlock}>
            <span className={styles.filename}>{photoDetail?.filename ?? currentItem.filename}</span>
            <span className={styles.metaLine}>
              {clampedIndex + 1} / {items.length}
              {currentItem.captured_at ? ` • ${formatCapturedAt(currentItem.captured_at)}` : ""}
            </span>
          </div>
          <div className={styles.topBarActions}>
            {!isVideoAsset ? (
              <>
                <button
                  type="button"
                  className={styles.closeButton}
                  onClick={rotateLeft}
                  disabled={isUpdatingRotation || !photoDetail}
                >
                  Rotate Left
                </button>
                <button
                  type="button"
                  className={styles.closeButton}
                  onClick={rotateRight}
                  disabled={isUpdatingRotation || !photoDetail}
                >
                  Rotate Right
                </button>
                <button
                  type="button"
                  className={styles.closeButton}
                  onClick={resetRotation}
                  disabled={isUpdatingRotation || !photoDetail || displayRotationDegrees === 0}
                >
                  Reset Rotation
                </button>
                <span className={styles.rotationValue}>Current: {displayRotationDegrees}°</span>
              </>
            ) : null}
            <button type="button" className={styles.closeButton} onClick={() => void toggleFullscreen()}>
              {isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
            </button>
            <button type="button" className={styles.closeButton} onClick={() => void handleClose()}>
              Close
            </button>
          </div>
        </div>

        <div className={styles.viewerFrame}>
          <button
            type="button"
            className={styles.navButton}
            onClick={() => setCurrentIndex((prev) => Math.max(prev - 1, 0))}
            disabled={clampedIndex === 0}
          >
            Previous
          </button>

          <div className={styles.mediaStage} ref={imageViewportRef}>
            {detailErrorMessage ? <p className={styles.errorMessage}>{detailErrorMessage}</p> : null}
            {rotationErrorMessage ? <p className={styles.errorMessage}>{rotationErrorMessage}</p> : null}
            {isLoadingDetail ? <p className={styles.loadingMessage}>Loading presentation…</p> : null}
            {isVideoAsset ? (
              <div className={styles.videoPlaceholder}>
                <span className={styles.videoBadge}>Video</span>
                <span className={styles.videoMessage}>Preview not available in presentation mode.</span>
              </div>
            ) : imageUrl ? (
              isQuarterTurnRotation ? (
                <div className={styles.rotatedImageViewport}>
                  <div className={styles.rotatedImageFrame} style={getRotatedImageFrameStyle(displayRotationDegrees)}>
                    <img
                      src={imageUrl}
                      alt={photoDetail?.filename ?? currentItem.filename}
                      className={`${styles.image} ${styles.rotatedImage}`}
                      style={{ transform: getImageTransform(displayRotationDegrees) }}
                      onLoad={(event) => {
                        const img = event.currentTarget as HTMLImageElement;
                        setNaturalDims({ w: img.naturalWidth, h: img.naturalHeight });
                      }}
                    />
                  </div>
                </div>
              ) : (
                <img
                  src={imageUrl}
                  alt={photoDetail?.filename ?? currentItem.filename}
                  className={styles.image}
                  style={{ transform: getImageTransform(displayRotationDegrees), maxHeight: `${imageMaxHeightVh}vh` }}
                  onLoad={(event) => {
                    const img = event.currentTarget as HTMLImageElement;
                    setNaturalDims({ w: img.naturalWidth, h: img.naturalHeight });
                  }}
                />
              )
            ) : (
              <p className={styles.errorMessage}>Media unavailable.</p>
            )}
          </div>

          <button
            type="button"
            className={styles.navButton}
            onClick={() => setCurrentIndex((prev) => Math.min(prev + 1, items.length - 1))}
            disabled={clampedIndex >= items.length - 1}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
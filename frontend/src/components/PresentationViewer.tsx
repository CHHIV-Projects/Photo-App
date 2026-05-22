"use client";

import type { CSSProperties } from "react";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  assignPerson,
  createPerson,
  getPeople,
  getPhotoDetail,
  getPhotoFaceOverlays,
  removeFaceFromCluster,
  resolveApiUrl,
  setPhotoRotation,
} from "@/lib/api";
import { isVideoAssetFilename } from "@/lib/media";
import type { FaceInPhoto, PersonSummary, PhotoDetail, PhotoFaceOverlayAsset, PhotoSummary } from "@/types/ui-api";
import styles from "./presentation-viewer.module.css";

interface Props {
  items: PhotoSummary[];
  initialIndex: number;
  onClose: () => void;
  onFaceAssignmentsChanged?: () => void;
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

function getFaceLabel(face: FaceInPhoto): string {
  if (face.person_name) return face.person_name;
  if (face.cluster_id !== null) return "Unassigned";
  return "Not assignable here";
}

function personMatchesSearch(person: PersonSummary, queryLower: string): boolean {
  if (person.display_name.toLowerCase().includes(queryLower)) {
    return true;
  }
  return person.aliases.some((alias) => alias.toLowerCase().includes(queryLower));
}

function getOverlayReferenceDims(
  overlay: PhotoFaceOverlayAsset | null,
  naturalDims: { w: number; h: number } | null,
): { w: number; h: number } | null {
  if (!overlay || !naturalDims || naturalDims.w <= 0 || naturalDims.h <= 0) {
    return null;
  }

  const canonicalWidth = overlay.canonical_width;
  const canonicalHeight = overlay.canonical_height;

  if (!canonicalWidth || !canonicalHeight || canonicalWidth <= 0 || canonicalHeight <= 0) {
    return naturalDims;
  }

  let referenceWidth = canonicalWidth;
  let referenceHeight = canonicalHeight;

  const naturalIsLandscape = naturalDims.w >= naturalDims.h;
  const canonicalIsLandscape = canonicalWidth >= canonicalHeight;
  if (naturalIsLandscape !== canonicalIsLandscape) {
    referenceWidth = canonicalHeight;
    referenceHeight = canonicalWidth;
  }

  return { w: referenceWidth, h: referenceHeight };
}

export function PresentationViewer({ items, initialIndex, onClose, onFaceAssignmentsChanged }: Props) {
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
  const [people, setPeople] = useState<PersonSummary[]>([]);
  const [isLoadingPeople, setIsLoadingPeople] = useState(false);
  const [overlayByAssetSha, setOverlayByAssetSha] = useState<Record<string, PhotoFaceOverlayAsset>>({});
  const [isLoadingOverlay, setIsLoadingOverlay] = useState(false);
  const [overlayErrorMessage, setOverlayErrorMessage] = useState<string | null>(null);
  const [hoveredFaceId, setHoveredFaceId] = useState<number | null>(null);
  const [selectedFaceId, setSelectedFaceId] = useState<number | null>(null);
  const [popoverAnchor, setPopoverAnchor] = useState<{ left: number; top: number } | null>(null);
  const [popoverPosition, setPopoverPosition] = useState<{ left: number; top: number } | null>(null);
  const [assignmentSearchText, setAssignmentSearchText] = useState("");
  const [assignmentPersonId, setAssignmentPersonId] = useState<number | null>(null);
  const [newPersonName, setNewPersonName] = useState("");
  const [isAssigningCluster, setIsAssigningCluster] = useState(false);
  const [assignmentMessage, setAssignmentMessage] = useState<string | null>(null);
  const [assignmentErrorMessage, setAssignmentErrorMessage] = useState<string | null>(null);
  const imageViewportRef = useRef<HTMLDivElement | null>(null);
  const viewerShellRef = useRef<HTMLDivElement | null>(null);
  const popoverRef = useRef<HTMLDivElement | null>(null);
  const imageMaxHeightVh = isFullscreen ? 94 : 88;

  const clampedIndex = Math.min(Math.max(currentIndex, 0), Math.max(items.length - 1, 0));
  const currentItem = items[clampedIndex] ?? null;
  const isVideoAsset = currentItem ? isVideoAssetFilename(currentItem.filename) : false;
  const displayRotationDegrees = normalizeRotation(photoDetail?.display_rotation_degrees ?? 0);
  const isQuarterTurnRotation = displayRotationDegrees === 90 || displayRotationDegrees === 270;
  const areFaceAssignmentsSuppressed = displayRotationDegrees !== 0;
  const currentAssetSha = currentItem?.asset_sha256 ?? null;
  const currentOverlay = currentAssetSha ? overlayByAssetSha[currentAssetSha] ?? null : null;
  const overlayFaces = currentOverlay?.faces ?? [];
  const filteredPeople = people.filter((person) =>
    personMatchesSearch(person, assignmentSearchText.trim().toLowerCase()),
  );
  const selectedOverlayFace = selectedFaceId !== null
    ? overlayFaces.find((face) => face.face_id === selectedFaceId) ?? null
    : null;
  const overlayReferenceDims = useMemo(
    () => getOverlayReferenceDims(currentOverlay, naturalDims),
    [currentOverlay, naturalDims],
  );
  const canRenderFaceOverlays =
    !isVideoAsset &&
    !areFaceAssignmentsSuppressed &&
    !isQuarterTurnRotation &&
    overlayReferenceDims !== null &&
    overlayFaces.length > 0;

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
    let isCancelled = false;

    async function loadPeopleList() {
      setIsLoadingPeople(true);
      try {
        const response = await getPeople();
        if (!isCancelled) {
          setPeople(response.items);
        }
      } catch {
        // Keep presentation flow usable even if person prefetch fails.
      } finally {
        if (!isCancelled) {
          setIsLoadingPeople(false);
        }
      }
    }

    void loadPeopleList();

    return () => {
      isCancelled = true;
    };
  }, []);

  useEffect(() => {
    if (currentAssetSha === null) {
      return;
    }

    let isCancelled = false;

    async function loadOverlayForCurrentAsset() {
      setIsLoadingOverlay(true);
      setOverlayErrorMessage(null);
      try {
        const response = await getPhotoFaceOverlays([currentAssetSha]);
        if (isCancelled) {
          return;
        }

        const overlay = response.items[0] ?? {
          asset_sha256: currentAssetSha,
          canonical_width: null,
          canonical_height: null,
          faces: [],
        };

        setOverlayByAssetSha((current) => ({
          ...current,
          [currentAssetSha]: overlay,
        }));
      } catch (error) {
        if (!isCancelled) {
          setOverlayErrorMessage(getErrorMessage(error, "Failed to load face overlays."));
        }
      } finally {
        if (!isCancelled) {
          setIsLoadingOverlay(false);
        }
      }
    }

    void loadOverlayForCurrentAsset();

    return () => {
      isCancelled = true;
    };
  }, [currentAssetSha]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (selectedFaceId !== null) {
          event.preventDefault();
          closeAssignmentPopover();
          return;
        }

        if (document.fullscreenElement === viewerShellRef.current) {
          return;
        }
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key === "ArrowLeft") {
        event.preventDefault();
        moveToPhoto(Math.max(clampedIndex - 1, 0));
        return;
      }

      if (event.key === "ArrowRight") {
        event.preventDefault();
        moveToPhoto(Math.min(clampedIndex + 1, items.length - 1));
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [clampedIndex, items.length, onClose, selectedFaceId]);

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
    setHoveredFaceId(null);
    closeAssignmentPopover();
  }, [currentItem?.asset_sha256]);

  useEffect(() => {
    if (selectedFaceId === null) {
      return;
    }

    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target as Element | null;
      if (!target) {
        return;
      }

      if (popoverRef.current?.contains(target)) {
        return;
      }

      if (target.closest(`.${styles.faceBox}`)) {
        return;
      }

      closeAssignmentPopover();
    };

    window.addEventListener("mousedown", handlePointerDown);
    return () => window.removeEventListener("mousedown", handlePointerDown);
  }, [selectedFaceId]);

  useEffect(() => {
    if (!popoverAnchor || !popoverRef.current || typeof window === "undefined") {
      return;
    }

    const popoverEl = popoverRef.current;
    const padding = 10;
    const popoverWidth = popoverEl.offsetWidth || 320;
    const popoverHeight = popoverEl.offsetHeight || 280;

    let left = popoverAnchor.left;
    let top = popoverAnchor.top;

    if (left + popoverWidth + padding > window.innerWidth) {
      left = Math.max(padding, popoverAnchor.left - popoverWidth - 18);
    }

    if (top + popoverHeight + padding > window.innerHeight) {
      top = Math.max(padding, window.innerHeight - popoverHeight - padding);
    }

    if (top < padding) {
      top = padding;
    }

    setPopoverPosition({ left, top });
  }, [popoverAnchor, selectedOverlayFace, isLoadingPeople, people.length, assignmentMessage, assignmentErrorMessage]);

  function closeAssignmentPopover() {
    setSelectedFaceId(null);
    setPopoverAnchor(null);
    setPopoverPosition(null);
    setAssignmentErrorMessage(null);
    setAssignmentMessage(null);
    setNewPersonName("");
    setHoveredFaceId(null);
  }

  function moveToPhoto(index: number) {
    const nextIndex = Math.min(Math.max(index, 0), Math.max(items.length - 1, 0));
    if (nextIndex === clampedIndex) {
      return;
    }
    closeAssignmentPopover();
    setCurrentIndex(nextIndex);
  }

  function patchOverlayAssignments(clusterId: number, personId: number, personName: string) {
    setOverlayByAssetSha((current) => {
      const next: Record<string, PhotoFaceOverlayAsset> = {};

      for (const [assetSha, overlay] of Object.entries(current)) {
        next[assetSha] = {
          ...overlay,
          faces: overlay.faces.map((face) =>
            face.cluster_id === clusterId
              ? { ...face, person_id: personId, person_name: personName }
              : face,
          ),
        };
      }

      return next;
    });
  }

  function openAssignmentPopover(face: FaceInPhoto, anchor: { left: number; top: number }) {
    setSelectedFaceId(face.face_id);
    setPopoverAnchor(anchor);
    setPopoverPosition(null);
    setAssignmentSearchText("");
    setAssignmentErrorMessage(null);
    setAssignmentMessage(null);
    setNewPersonName("");
    setAssignmentPersonId(face.person_id);
  }

  async function handleAssignToExistingPerson() {
    if (!selectedOverlayFace || selectedOverlayFace.cluster_id === null || assignmentPersonId === null) {
      return;
    }

    const target = people.find((person) => person.person_id === assignmentPersonId);
    if (!target) {
      setAssignmentErrorMessage("Select a valid person.");
      return;
    }

    const previousName = selectedOverlayFace.person_name;

    setIsAssigningCluster(true);
    setAssignmentErrorMessage(null);
    setAssignmentMessage(null);

    try {
      await assignPerson(selectedOverlayFace.cluster_id, assignmentPersonId);
      patchOverlayAssignments(selectedOverlayFace.cluster_id, assignmentPersonId, target.display_name);
      onFaceAssignmentsChanged?.();
      if (previousName && previousName !== target.display_name) {
        setAssignmentMessage(`Reassigned face cluster from ${previousName} to ${target.display_name}.`);
      } else {
        setAssignmentMessage(`Assigned face cluster to ${target.display_name}.`);
      }
      window.setTimeout(() => {
        closeAssignmentPopover();
      }, 1000);
    } catch (error) {
      setAssignmentErrorMessage(getErrorMessage(error, "Could not assign cluster. Please try again."));
    } finally {
      setIsAssigningCluster(false);
    }
  }

  async function handleCreatePersonAndAssign() {
    if (!selectedOverlayFace || selectedOverlayFace.cluster_id === null) {
      return;
    }

    const candidateName = newPersonName.trim();
    if (!candidateName) {
      setAssignmentErrorMessage("Enter a person name first.");
      return;
    }

    setIsAssigningCluster(true);
    setAssignmentErrorMessage(null);
    setAssignmentMessage(null);

    try {
      const response = await createPerson(candidateName);
      setPeople((current) => {
        if (current.some((person) => person.person_id === response.person.person_id)) {
          return current;
        }
        return [...current, response.person].sort((a, b) => a.display_name.localeCompare(b.display_name));
      });

      await assignPerson(selectedOverlayFace.cluster_id, response.person.person_id);
      patchOverlayAssignments(
        selectedOverlayFace.cluster_id,
        response.person.person_id,
        response.person.display_name,
      );
      onFaceAssignmentsChanged?.();

      setAssignmentMessage(`Created person ${response.person.display_name} and assigned face cluster.`);
      window.setTimeout(() => {
        closeAssignmentPopover();
      }, 1000);
    } catch (error) {
      let message = getErrorMessage(error, "Could not create person. Please try again.");
      if (message.toLowerCase().includes("already exists")) {
        message = "A person with this name already exists. Select the existing person instead.";
      }
      setAssignmentErrorMessage(message);
    } finally {
      setIsAssigningCluster(false);
    }
  }

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

  async function handleBackdropClick() {
    if (selectedFaceId !== null) {
      closeAssignmentPopover();
      return;
    }
    await handleClose();
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
      <button type="button" className={styles.backdrop} aria-label="Close presentation" onClick={() => void handleBackdropClick()} />
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
            onClick={() => moveToPhoto(clampedIndex - 1)}
            disabled={clampedIndex === 0}
          >
            Previous
          </button>

          <div
            className={styles.mediaStage}
            ref={imageViewportRef}
            onMouseLeave={() => setHoveredFaceId(null)}
          >
            {detailErrorMessage ? <p className={styles.errorMessage}>{detailErrorMessage}</p> : null}
            {rotationErrorMessage ? <p className={styles.errorMessage}>{rotationErrorMessage}</p> : null}
            {overlayErrorMessage ? <p className={styles.errorMessage}>{overlayErrorMessage}</p> : null}
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
                <div className={styles.imageFrame}>
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

                  {canRenderFaceOverlays ? (
                    <div className={styles.faceOverlayLayer}>
                      {overlayFaces.map((face) => (
                        <button
                          key={face.face_id}
                          type="button"
                          className={[
                            styles.faceBox,
                            hoveredFaceId === face.face_id || selectedFaceId === face.face_id
                              ? styles.faceBoxVisible
                              : "",
                            selectedFaceId === face.face_id ? styles.faceBoxActive : "",
                          ].filter(Boolean).join(" ")}
                          style={{
                            left: `${(face.bbox.x / overlayReferenceDims.w) * 100}%`,
                            top: `${(face.bbox.y / overlayReferenceDims.h) * 100}%`,
                            width: `${(face.bbox.w / overlayReferenceDims.w) * 100}%`,
                            height: `${(face.bbox.h / overlayReferenceDims.h) * 100}%`,
                          }}
                          onMouseEnter={() => {
                            setHoveredFaceId(face.face_id);
                          }}
                          onMouseLeave={() => {
                            setHoveredFaceId((current) => (current === face.face_id ? null : current));
                          }}
                          onClick={(event) => {
                            event.preventDefault();
                            event.stopPropagation();
                            const rect = event.currentTarget.getBoundingClientRect();
                            openAssignmentPopover(face, {
                              left: rect.right + 10,
                              top: rect.top,
                            });
                          }}
                          aria-label={getFaceLabel(face)}
                        >
                          {hoveredFaceId === face.face_id || selectedFaceId === face.face_id ? (
                            <span className={styles.faceLabel}>{getFaceLabel(face)}</span>
                          ) : null}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              )
            ) : (
              <p className={styles.errorMessage}>Media unavailable.</p>
            )}

            {!isVideoAsset && !isLoadingOverlay && !areFaceAssignmentsSuppressed ? (
              <p className={styles.hintMessage}>Move pointer over a face, then click to assign.</p>
            ) : null}

            {areFaceAssignmentsSuppressed ? (
              <p className={styles.hintMessage}>Face assignment is unavailable for rotated display in this view.</p>
            ) : null}

            {selectedOverlayFace && popoverAnchor ? (
              <div
                ref={popoverRef}
                className={styles.assignmentPopover}
                style={{
                  left: `${(popoverPosition ?? popoverAnchor).left}px`,
                  top: `${(popoverPosition ?? popoverAnchor).top}px`,
                }}
                onMouseDown={(event) => event.stopPropagation()}
              >
                <div className={styles.popoverHeader}>Assign Face</div>
                <p className={styles.popoverMeta}>Current: {getFaceLabel(selectedOverlayFace)}</p>
                <p className={styles.popoverMeta}>Cluster: {selectedOverlayFace.cluster_id ?? "N/A"}</p>

                <input
                  type="search"
                  className={styles.popoverInput}
                  placeholder="Search people..."
                  value={assignmentSearchText}
                  onChange={(event) => setAssignmentSearchText(event.target.value)}
                  disabled={isAssigningCluster || isLoadingPeople}
                />

                <select
                  className={styles.popoverInput}
                  value={assignmentPersonId ?? ""}
                  onChange={(event) => {
                    const value = event.target.value;
                    setAssignmentPersonId(value ? Number(value) : null);
                  }}
                  disabled={isAssigningCluster || isLoadingPeople || filteredPeople.length === 0}
                >
                  <option value="">Select person...</option>
                  {filteredPeople.map((person) => (
                    <option key={person.person_id} value={person.person_id}>
                      {person.display_name}
                    </option>
                  ))}
                </select>

                <div className={styles.popoverActionsRow}>
                  <button
                    type="button"
                    className={styles.popoverButton}
                    disabled={
                      isAssigningCluster ||
                      assignmentPersonId === null ||
                      selectedOverlayFace.cluster_id === null
                    }
                    onClick={() => {
                      void handleAssignToExistingPerson();
                    }}
                  >
                    {selectedOverlayFace.person_id ? "Reassign" : "Assign"}
                  </button>
                  <button
                    type="button"
                    className={`${styles.popoverButton} ${styles.popoverButtonDanger}`.trim()}
                    disabled={isAssigningCluster}
                    onClick={async () => {
                      setIsAssigningCluster(true);
                      setAssignmentErrorMessage(null);
                      setAssignmentMessage(null);
                      try {
                        await removeFaceFromCluster(selectedOverlayFace.face_id);
                        setOverlayByAssetSha((current) => {
                          const next = { ...current };
                          const overlay = next[currentAssetSha ?? ""];
                          if (overlay) {
                            next[currentAssetSha ?? ""] = {
                              ...overlay,
                              faces: overlay.faces.map((face) =>
                                face.face_id === selectedOverlayFace.face_id
                                  ? { ...face, cluster_id: null, person_id: null, person_name: null }
                                  : face
                              ),
                            };
                          }
                          return next;
                        });
                        onFaceAssignmentsChanged?.();
                        setAssignmentMessage("Face unassigned from cluster.");
                        window.setTimeout(() => {
                          closeAssignmentPopover();
                        }, 1000);
                      } catch (error) {
                        const message = error instanceof Error && error.message ? error.message : "Could not unassign face.";
                        setAssignmentErrorMessage(message);
                      } finally {
                        setIsAssigningCluster(false);
                      }
                    }}
                  >
                    Remove name
                  </button>
                  <button
                    type="button"
                    className={`${styles.popoverButton} ${styles.popoverButtonSecondary}`.trim()}
                    onClick={closeAssignmentPopover}
                    disabled={isAssigningCluster}
                  >
                    Cancel
                  </button>
                </div>

                <input
                  type="text"
                  className={styles.popoverInput}
                  placeholder="Create new person..."
                  value={newPersonName}
                  onChange={(event) => setNewPersonName(event.target.value)}
                  disabled={isAssigningCluster || selectedOverlayFace.cluster_id === null}
                />
                <button
                  type="button"
                  className={styles.popoverButton}
                  disabled={isAssigningCluster || selectedOverlayFace.cluster_id === null || newPersonName.trim().length === 0}
                  onClick={() => {
                    void handleCreatePersonAndAssign();
                  }}
                >
                  Create + Assign
                </button>

                {assignmentErrorMessage ? <p className={styles.popoverError}>{assignmentErrorMessage}</p> : null}
                {assignmentMessage ? <p className={styles.popoverSuccess}>{assignmentMessage}</p> : null}
              </div>
            ) : null}
          </div>

          <button
            type="button"
            className={styles.navButton}
            onClick={() => moveToPhoto(clampedIndex + 1)}
            disabled={clampedIndex >= items.length - 1}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
"use client";

import type { CSSProperties } from "react";
import { useEffect, useRef, useState } from "react";

import {
  addAssetsToAlbum,
  assignPhotoToEvent,
  getDuplicateMergeTargets,
  getAlbums,
  getAlbumsForAsset,
  getEvents,
  getPhotoDetail,
  mergeDuplicateAssets,
  removePhotoFromEvent,
  removeAssetsFromAlbum,
  resolveApiUrl,
  setPhotoRotation,
} from "@/lib/api";
import { PresentationViewer } from "@/components/PresentationViewer";
import { TimelineNav } from "@/components/TimelineNav";
import type {
  AlbumMembershipSummary,
  AlbumSummary,
  ContentTagSummary,
  DuplicateLineageMergeResponse,
  DuplicateMergeTargetSummary,
  EventImpactSummary,
  EventSummary,
  FaceInPhoto,
  PhotoDetail,
  PhotoSummary,
} from "@/types/ui-api";
import styles from "./photos-view.module.css";

interface Props {
  photos: PhotoSummary[];
  isLoading: boolean;
  errorMessage: string | null;
  searchQuery: string;
  cameraQuery: string;
  startDate: string;
  endDate: string;
  totalCount: number;
  offset: number;
  pageSize: number;
  timelineYear: number | null;
  timelineMonth: string;
  timelineDate: string;
  selectedPhotoSha256: string | null;
  photoDetail: PhotoDetail | null;
  isLoadingDetail: boolean;
  photoDetailErrorMessage: string | null;
  onSelectPhoto: (sha256: string) => void;
  onPhotoDetailUpdated: (detail: PhotoDetail) => void;
  onSearchFiltersChange: (filters: {
    query: string;
    camera: string;
    startDate: string;
    endDate: string;
  }) => void;
  onPageChange: (nextOffset: number) => void;
  onTimelineChange: (selection: {
    year: number | null;
    month: string;
    date: string;
  }) => void;
}

export function PhotosView({
  photos,
  isLoading,
  errorMessage,
  searchQuery,
  cameraQuery,
  startDate,
  endDate,
  totalCount,
  offset,
  pageSize,
  timelineYear,
  timelineMonth,
  timelineDate,
  selectedPhotoSha256,
  photoDetail,
  isLoadingDetail,
  photoDetailErrorMessage,
  onSelectPhoto,
  onPhotoDetailUpdated,
  onSearchFiltersChange,
  onPageChange,
  onTimelineChange,
}: Props) {
  const [selectedFaceId, setSelectedFaceId] = useState<number | null>(null);
  const [showAllProvenance, setShowAllProvenance] = useState(false);
  const [showAllExifObservations, setShowAllExifObservations] = useState(false);
  const [naturalDims, setNaturalDims] = useState<{ w: number; h: number } | null>(null);
  const [imageLoadError, setImageLoadError] = useState(false);
  const [photoSearch, setPhotoSearch] = useState(searchQuery);
  const [cameraSearch, setCameraSearch] = useState(cameraQuery);
  const [startDateFilter, setStartDateFilter] = useState(startDate);
  const [endDateFilter, setEndDateFilter] = useState(endDate);
  const [albums, setAlbums] = useState<AlbumSummary[]>([]);
  const [eventOptions, setEventOptions] = useState<EventSummary[]>([]);
  const [selectedEventTargetId, setSelectedEventTargetId] = useState<number | null>(null);
  const [isUpdatingEventAssignment, setIsUpdatingEventAssignment] = useState(false);
  const [eventActionErrorMessage, setEventActionErrorMessage] = useState<string | null>(null);
  const [eventActionSuccessMessage, setEventActionSuccessMessage] = useState<string | null>(null);
  const [photoAlbums, setPhotoAlbums] = useState<AlbumMembershipSummary[]>([]);
  const [selectedAlbumId, setSelectedAlbumId] = useState<number | null>(null);
  const [albumsErrorMessage, setAlbumsErrorMessage] = useState<string | null>(null);
  const [albumsSuccessMessage, setAlbumsSuccessMessage] = useState<string | null>(null);
  const [isUpdatingAlbums, setIsUpdatingAlbums] = useState(false);
  const [duplicateMergeSearch, setDuplicateMergeSearch] = useState("");
  const [duplicateMergeTargets, setDuplicateMergeTargets] = useState<DuplicateMergeTargetSummary[]>([]);
  const [selectedDuplicateMergeTargetSha, setSelectedDuplicateMergeTargetSha] = useState<string>("");
  const [isLoadingDuplicateTargets, setIsLoadingDuplicateTargets] = useState(false);
  const [isMergingDuplicateLineage, setIsMergingDuplicateLineage] = useState(false);
  const [duplicateMergeErrorMessage, setDuplicateMergeErrorMessage] = useState<string | null>(null);
  const [duplicateMergeSuccessMessage, setDuplicateMergeSuccessMessage] = useState<string | null>(null);
  const [displayRotationDegrees, setDisplayRotationDegrees] = useState<0 | 90 | 180 | 270>(0);
  const [isUpdatingRotation, setIsUpdatingRotation] = useState(false);
  const [rotationErrorMessage, setRotationErrorMessage] = useState<string | null>(null);
  const [presentationStartIndex, setPresentationStartIndex] = useState<number | null>(null);
  const faceRowRefs = useRef<Map<number, HTMLLIElement>>(new Map());
  const imageViewportRef = useRef<HTMLDivElement | null>(null);
  const [imageViewportWidth, setImageViewportWidth] = useState<number | null>(null);
  const [windowHeight, setWindowHeight] = useState<number>(900);

  useEffect(() => {
    setPhotoSearch(searchQuery);
  }, [searchQuery]);

  useEffect(() => {
    setCameraSearch(cameraQuery);
  }, [cameraQuery]);

  useEffect(() => {
    setStartDateFilter(startDate);
  }, [startDate]);

  useEffect(() => {
    setEndDateFilter(endDate);
  }, [endDate]);

  useEffect(() => {
    const debounceHandle = window.setTimeout(() => {
      onSearchFiltersChange({
        query: photoSearch,
        camera: cameraSearch,
        startDate: startDateFilter,
        endDate: endDateFilter,
      });
    }, 300);

    return () => {
      window.clearTimeout(debounceHandle);
    };
  }, [photoSearch, cameraSearch, startDateFilter, endDateFilter, onSearchFiltersChange]);

  useEffect(() => {
    if (photos.length === 0) {
      return;
    }

    // Auto-select first item only for initial empty selection.
    if (!selectedPhotoSha256) {
      onSelectPhoto(photos[0].asset_sha256);
      return;
    }

    // If the selected photo is not on the current page, keep the current detail selection
    // instead of jumping to the first result on each page turn.
    if (photos.some((photo) => photo.asset_sha256 === selectedPhotoSha256)) {
      return;
    }
  }, [photos, selectedPhotoSha256, onSelectPhoto]);

  // Reset face selection and image state when the selected photo changes.
  useEffect(() => {
    setSelectedFaceId(null);
    setShowAllProvenance(false);
    setShowAllExifObservations(false);
    setNaturalDims(null);
    setImageLoadError(false);
  }, [selectedPhotoSha256]);

  // Auto-scroll the face row into view when selection changes.
  useEffect(() => {
    if (selectedFaceId === null) return;
    const el = faceRowRefs.current.get(selectedFaceId);
    el?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [selectedFaceId]);

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
  }, [photoDetail?.asset_sha256]);

  useEffect(() => {
    if (!photoDetail) {
      setDisplayRotationDegrees(0);
      setRotationErrorMessage(null);
      return;
    }
    setDisplayRotationDegrees(photoDetail.display_rotation_degrees);
    setRotationErrorMessage(null);
  }, [photoDetail?.asset_sha256, photoDetail?.display_rotation_degrees]);

  useEffect(() => {
    async function loadAlbums() {
      try {
        const response = await getAlbums();
        setAlbums(response.items);
      } catch {
        // Keep Photos view functional if album list fails.
      }
    }

    void loadAlbums();
  }, []);

  useEffect(() => {
    async function loadEventOptions() {
      try {
        const response = await getEvents();
        setEventOptions(response.items);
      } catch {
        // Keep Photos view usable if event list fails.
      }
    }

    void loadEventOptions();
  }, []);

  useEffect(() => {
    if (!selectedPhotoSha256) {
      setPhotoAlbums([]);
      setAlbumsSuccessMessage(null);
      return;
    }

    const photoSha256 = selectedPhotoSha256;

    async function loadPhotoAlbumMembership() {
      setAlbumsErrorMessage(null);
      try {
        const response = await getAlbumsForAsset(photoSha256);
        setPhotoAlbums(response.items);
      } catch (error) {
        setAlbumsErrorMessage(getErrorMessage(error, "Failed to load album memberships."));
      }
    }

    void loadPhotoAlbumMembership();
  }, [selectedPhotoSha256]);

  useEffect(() => {
    if (albums.length === 0) {
      setSelectedAlbumId(null);
      return;
    }
    if (selectedAlbumId !== null && albums.some((album) => album.album_id === selectedAlbumId)) {
      return;
    }
    setSelectedAlbumId(albums[0].album_id);
  }, [albums, selectedAlbumId]);

  useEffect(() => {
    if (!photoDetail) {
      setSelectedEventTargetId(null);
      setEventActionErrorMessage(null);
      setEventActionSuccessMessage(null);
      return;
    }

    if (photoDetail.event?.event_id) {
      setSelectedEventTargetId(photoDetail.event.event_id);
      return;
    }

    setSelectedEventTargetId(eventOptions.length > 0 ? eventOptions[0].event_id : null);
  }, [photoDetail?.asset_sha256, photoDetail?.event?.event_id, eventOptions]);

  useEffect(() => {
    if (!photoDetail) {
      setDuplicateMergeSearch("");
      setDuplicateMergeTargets([]);
      setSelectedDuplicateMergeTargetSha("");
      setDuplicateMergeErrorMessage(null);
      setDuplicateMergeSuccessMessage(null);
      return;
    }

    setDuplicateMergeSearch("");
    setSelectedDuplicateMergeTargetSha("");
    setDuplicateMergeErrorMessage(null);
    setDuplicateMergeSuccessMessage(null);
  }, [photoDetail?.asset_sha256]);

  useEffect(() => {
    if (!photoDetail) {
      return;
    }

    let isCancelled = false;
    const sourceSha = photoDetail.asset_sha256;

    async function loadDuplicateMergeTargets() {
      setIsLoadingDuplicateTargets(true);
      try {
        const response = await getDuplicateMergeTargets(sourceSha, duplicateMergeSearch, 30);
        if (isCancelled) {
          return;
        }
        setDuplicateMergeTargets(response.items);
        setSelectedDuplicateMergeTargetSha((current) => {
          if (current && response.items.some((item) => item.asset_sha256 === current)) {
            return current;
          }
          return "";
        });
      } catch (error) {
        if (!isCancelled) {
          setDuplicateMergeTargets([]);
          setSelectedDuplicateMergeTargetSha("");
          setDuplicateMergeErrorMessage(getErrorMessage(error, "Failed to load duplicate merge targets."));
        }
      } finally {
        if (!isCancelled) {
          setIsLoadingDuplicateTargets(false);
        }
      }
    }

    const timeoutId = window.setTimeout(() => {
      void loadDuplicateMergeTargets();
    }, 220);

    return () => {
      isCancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [photoDetail?.asset_sha256, duplicateMergeSearch]);

  function getFaceLabel(face: FaceInPhoto): string {
    if (face.person_name) return face.person_name;
    if (face.cluster_id !== null) return `Cluster #${face.cluster_id} — No Person Assigned`;
    return "Unassigned";
  }

  function toggleFace(faceId: number) {
    setSelectedFaceId((prev) => (prev === faceId ? null : faceId));
  }

  function formatEventSummary(event: PhotoDetail["event"]): string {
    if (!event) {
      return "No event assigned";
    }

    if (event.label) {
      return `Event #${event.event_id} — ${event.label}`;
    }

    if (event.start_at || event.end_at) {
      const start = event.start_at ? formatDateTime(event.start_at) : "Unknown start";
      const end = event.end_at ? formatDateTime(event.end_at) : "Unknown end";
      return `Event #${event.event_id} — ${start} to ${end}`;
    }

    return `Event #${event.event_id}`;
  }

  function formatDateTime(value: string): string {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return value;
    }

    return parsed.toLocaleString();
  }

  function formatCoordinate(value: number | null | undefined): string {
    if (value === null || value === undefined) {
      return "—";
    }
    return value.toFixed(5);
  }

  function formatLocationSummary(location: PhotoDetail["location"]): string {
    if (!location || (location.latitude === null && location.longitude === null)) {
      return "No location data";
    }

    return `${formatCoordinate(location.latitude)}, ${formatCoordinate(location.longitude)}`;
  }

  function formatObservationLocation(latitude: number | null, longitude: number | null): string {
    if (latitude === null || longitude === null) {
      return "Unknown";
    }
    return `${formatCoordinate(latitude)}, ${formatCoordinate(longitude)}`;
  }

  function getCaptureTypeLabel(captureType: PhotoDetail["capture_type"]): string {
    if (captureType === "digital") return "Digital";
    if (captureType === "scan") return "Scan";
    return "Unknown";
  }

  function getCaptureTrustLabel(captureTimeTrust: PhotoDetail["capture_time_trust"]): string {
    if (captureTimeTrust === "high") return "High Confidence";
    if (captureTimeTrust === "low") return "Low Confidence";
    return "Unknown";
  }

  function getQualityLabel(score: number | null): string {
    if (score === null) return "Unknown";
    if (score >= 80) return "High";
    if (score >= 50) return "Medium";
    return "Low";
  }

  function formatProvenanceDate(value: string | null): string {
    if (!value) return "Unknown ingestion time";
    return formatDateTime(value);
  }

  function formatWinnerFields(fields: string[]): string {
    if (fields.length === 0) {
      return "No canonical fields won";
    }
    return `Won: ${fields.join(", ")}`;
  }

  function normalizeComparableString(value: string | null | undefined): string {
    return (value ?? "").trim().toLowerCase();
  }

  function normalizeComparableTimestamp(value: string | null | undefined): string {
    if (!value) {
      return "";
    }

    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return value.trim();
    }
    return parsed.toISOString();
  }

  function hasSameCanonicalObservationFields(
    left: PhotoDetail["metadata_observations"][number],
    right: PhotoDetail["metadata_observations"][number]
  ): boolean {
    return (
      normalizeComparableTimestamp(left.captured_at_observed) ===
        normalizeComparableTimestamp(right.captured_at_observed) &&
      (left.gps_latitude ?? null) === (right.gps_latitude ?? null) &&
      (left.gps_longitude ?? null) === (right.gps_longitude ?? null) &&
      normalizeComparableString(left.camera_make) === normalizeComparableString(right.camera_make) &&
      normalizeComparableString(left.camera_model) === normalizeComparableString(right.camera_model) &&
      (left.width ?? null) === (right.width ?? null) &&
      (left.height ?? null) === (right.height ?? null)
    );
  }

  function getErrorMessage(error: unknown, fallbackMessage: string): string {
    if (error instanceof Error && error.message) {
      return error.message;
    }
    return fallbackMessage;
  }

  function formatEventOptionLabel(event: EventSummary): string {
    const title = event.label?.trim() ? event.label.trim() : `Event #${event.event_id}`;
    const start = formatDateTime(event.start_time);
    const end = formatDateTime(event.end_time);
    return `${title} (${start} - ${end})`;
  }

  function applyEventImpactSummary(summary: EventImpactSummary | null): void {
    if (!summary) {
      return;
    }

    setEventOptions((prev) => {
      const next = [...prev];
      const index = next.findIndex((item) => item.event_id === summary.event_id);
      const normalized: EventSummary = {
        event_id: summary.event_id,
        label: summary.label,
        start_time: summary.start_time ?? new Date(0).toISOString(),
        end_time: summary.end_time ?? new Date(0).toISOString(),
        photo_count: summary.photo_count,
        face_count: summary.face_count,
      };
      if (index >= 0) {
        next[index] = normalized;
      } else {
        next.push(normalized);
      }
      next.sort((a, b) => new Date(b.start_time).getTime() - new Date(a.start_time).getTime());
      return next;
    });
  }

  async function handleRemoveFromEvent() {
    if (!photoDetail) {
      return;
    }

    setIsUpdatingEventAssignment(true);
    setEventActionErrorMessage(null);
    setEventActionSuccessMessage(null);

    try {
      const response = await removePhotoFromEvent(photoDetail.asset_sha256);
      applyEventImpactSummary(response.old_event);
      applyEventImpactSummary(response.new_event);
      onPhotoDetailUpdated({
        ...photoDetail,
        event: response.event,
      });
      setEventActionSuccessMessage("Removed photo from event.");
    } catch (error) {
      setEventActionErrorMessage(getErrorMessage(error, "Failed to remove photo from event."));
    } finally {
      setIsUpdatingEventAssignment(false);
    }
  }

  async function handleAssignToEvent() {
    if (!photoDetail || selectedEventTargetId === null) {
      setEventActionErrorMessage("Select an event first.");
      return;
    }

    if (photoDetail.event?.event_id === selectedEventTargetId) {
      setEventActionErrorMessage("Photo is already assigned to that event.");
      return;
    }

    setIsUpdatingEventAssignment(true);
    setEventActionErrorMessage(null);
    setEventActionSuccessMessage(null);

    try {
      const response = await assignPhotoToEvent(photoDetail.asset_sha256, selectedEventTargetId);
      applyEventImpactSummary(response.old_event);
      applyEventImpactSummary(response.new_event);
      onPhotoDetailUpdated({
        ...photoDetail,
        event: response.event,
      });
      setEventActionSuccessMessage("Updated photo event assignment.");
    } catch (error) {
      setEventActionErrorMessage(getErrorMessage(error, "Failed to assign photo to event."));
    } finally {
      setIsUpdatingEventAssignment(false);
    }
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

  function getRotatedImageFrameStyle(rotation: 0 | 90 | 180 | 270): CSSProperties | undefined {
    if (rotation !== 90 && rotation !== 270) {
      return undefined;
    }

    if (!naturalDims || naturalDims.w <= 0 || naturalDims.h <= 0 || !imageViewportWidth) {
      return {
        maxWidth: "100%",
        maxHeight: "72vh",
      };
    }

    const rotatedAspectRatio = naturalDims.h / naturalDims.w;
    const maxHeight = Math.max(320, Math.floor(windowHeight * 0.72));
    const width = Math.min(imageViewportWidth, maxHeight * rotatedAspectRatio);
    const height = width / rotatedAspectRatio;

    return {
      width: `${Math.round(width)}px`,
      height: `${Math.round(height)}px`,
    };
  }

  async function persistRotation(nextRotation: 0 | 90 | 180 | 270) {
    if (!photoDetail) return;

    setIsUpdatingRotation(true);
    setRotationErrorMessage(null);

    try {
      const assetSha256 = photoDetail.asset_sha256;
      const updated = await setPhotoRotation(assetSha256, nextRotation);
      setDisplayRotationDegrees(updated.display_rotation_degrees);
      onPhotoDetailUpdated({
        ...photoDetail,
        display_rotation_degrees: updated.display_rotation_degrees,
      });
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
    if (displayRotationDegrees === 0) return;
    void persistRotation(0);
  }

  function openPresentationMode() {
    if (!selectedPhotoSha256) {
      return;
    }

    const currentIndex = photos.findIndex((photo) => photo.asset_sha256 === selectedPhotoSha256);
    if (currentIndex >= 0) {
      setPresentationStartIndex(currentIndex);
    }
  }

  async function closePresentationMode() {
    setPresentationStartIndex(null);
    if (!selectedPhotoSha256) {
      return;
    }

    try {
      const refreshedDetail = await getPhotoDetail(selectedPhotoSha256);
      setDisplayRotationDegrees(refreshedDetail.display_rotation_degrees);
      onPhotoDetailUpdated(refreshedDetail);
    } catch {
      // Keep current state if refresh fails; next photo selection will reload detail.
    }
  }

  async function refreshAlbumStateForPhoto(assetSha256: string) {
    const [albumListResponse, membershipResponse] = await Promise.all([
      getAlbums(),
      getAlbumsForAsset(assetSha256),
    ]);
    setAlbums(albumListResponse.items);
    setPhotoAlbums(membershipResponse.items);
  }

  async function handleAddPhotoToAlbum() {
    if (!photoDetail || selectedAlbumId === null) {
      setAlbumsErrorMessage("Select an album first.");
      return;
    }

    setIsUpdatingAlbums(true);
    setAlbumsErrorMessage(null);
    setAlbumsSuccessMessage(null);

    try {
      await addAssetsToAlbum(selectedAlbumId, [photoDetail.asset_sha256]);
      await refreshAlbumStateForPhoto(photoDetail.asset_sha256);
      const selectedAlbum = albums.find((album) => album.album_id === selectedAlbumId);
      setAlbumsSuccessMessage(
        selectedAlbum ? `Added to album: ${selectedAlbum.name}` : "Photo added to album."
      );
    } catch (error) {
      setAlbumsErrorMessage(getErrorMessage(error, "Failed to add photo to album."));
    } finally {
      setIsUpdatingAlbums(false);
    }
  }

  async function handleRemovePhotoFromAlbum() {
    if (!photoDetail || selectedAlbumId === null) {
      setAlbumsErrorMessage("Select an album first.");
      return;
    }

    setIsUpdatingAlbums(true);
    setAlbumsErrorMessage(null);
    setAlbumsSuccessMessage(null);

    try {
      await removeAssetsFromAlbum(selectedAlbumId, [photoDetail.asset_sha256]);
      await refreshAlbumStateForPhoto(photoDetail.asset_sha256);
      const selectedAlbum = albums.find((album) => album.album_id === selectedAlbumId);
      setAlbumsSuccessMessage(
        selectedAlbum ? `Removed from album: ${selectedAlbum.name}` : "Photo removed from album."
      );
    } catch (error) {
      setAlbumsErrorMessage(getErrorMessage(error, "Failed to remove photo from album."));
    } finally {
      setIsUpdatingAlbums(false);
    }
  }

  function formatDuplicateTargetOption(target: DuplicateMergeTargetSummary): string {
    const captured = target.captured_at ? formatDateTime(target.captured_at) : "No date";
    const canonical = target.is_canonical ? "canonical" : "member";
    return `${target.filename} • ${captured} • Group #${target.duplicate_group_id} (${target.duplicate_count}, ${canonical})`;
  }

  function buildDuplicateMergeSuccessMessage(response: DuplicateLineageMergeResponse): string {
    const canonicalShort = response.resulting_canonical_asset_sha256.slice(0, 10);
    return `Merged into group #${response.resulting_group_id}. Canonical: ${canonicalShort}... (${response.affected_member_count} assets).`;
  }

  async function handleMergeDuplicateLineage() {
    if (!photoDetail) {
      return;
    }
    if (!selectedDuplicateMergeTargetSha) {
      setDuplicateMergeErrorMessage("Select a target asset first.");
      return;
    }

    setIsMergingDuplicateLineage(true);
    setDuplicateMergeErrorMessage(null);
    setDuplicateMergeSuccessMessage(null);

    try {
      const response = await mergeDuplicateAssets(photoDetail.asset_sha256, selectedDuplicateMergeTargetSha);
      setDuplicateMergeSuccessMessage(buildDuplicateMergeSuccessMessage(response));

      const refreshed = await getPhotoDetail(photoDetail.asset_sha256);
      onPhotoDetailUpdated(refreshed);
    } catch (error) {
      setDuplicateMergeErrorMessage(getErrorMessage(error, "Failed to merge duplicate lineage."));
    } finally {
      setIsMergingDuplicateLineage(false);
    }
  }

  const areFaceOverlaysSuppressed = displayRotationDegrees !== 0;
  const isQuarterTurnRotation = displayRotationDegrees === 90 || displayRotationDegrees === 270;
  const allExifObservations = photoDetail?.metadata_observations ?? [];
  const provenanceExifObservations = allExifObservations.filter(
    (item) => item.observation_origin === "provenance"
  );
  const defaultExifObservations = allExifObservations.filter((item) => {
    if (item.observation_origin !== "vault") {
      return true;
    }

    return !provenanceExifObservations.some((provItem) =>
      hasSameCanonicalObservationFields(item, provItem)
    );
  });
  const hiddenVaultObservationCount = allExifObservations.length - defaultExifObservations.length;
  const exifObservationsForDisplay = showAllExifObservations
    ? allExifObservations
    : defaultExifObservations.slice(0, 3);
  const selectedPhotoIndex = selectedPhotoSha256
    ? photos.findIndex((photo) => photo.asset_sha256 === selectedPhotoSha256)
    : -1;

  function selectPreviousPhoto() {
    if (selectedPhotoIndex <= 0) {
      return;
    }
    onSelectPhoto(photos[selectedPhotoIndex - 1].asset_sha256);
  }

  function selectNextPhoto() {
    if (selectedPhotoIndex < 0 || selectedPhotoIndex >= photos.length - 1) {
      return;
    }
    onSelectPhoto(photos[selectedPhotoIndex + 1].asset_sha256);
  }

  return (
    <div className={styles.layout}>
      <div className={styles.sidebarStack}>
        <TimelineNav
          selectedYear={timelineYear}
          selectedMonth={timelineMonth}
          selectedDate={timelineDate}
          onTimelineChange={onTimelineChange}
        />

        {/* ── Photo list ────────────────────────────────────────────── */}
        <aside className={styles.panel}>
          <div className={styles.panelHeader}>
            <h2 className={styles.panelTitle}>Photos</h2>
            <span className={styles.panelCount}>{totalCount}</span>
          </div>

          <div className={styles.searchWrapper}>
            <input
              type="search"
              className={styles.searchInput}
              placeholder="Search filename..."
              value={photoSearch}
              onChange={(e) => setPhotoSearch(e.target.value)}
            />
            <input
              type="search"
              className={styles.searchInput}
              placeholder="Camera make/model..."
              value={cameraSearch}
              onChange={(e) => setCameraSearch(e.target.value)}
            />
            <div className={styles.dateRangeRow}>
              <input
                type="date"
                className={styles.searchInput}
                value={startDateFilter}
                onChange={(e) => setStartDateFilter(e.target.value)}
                aria-label="Start date"
              />
              <input
                type="date"
                className={styles.searchInput}
                value={endDateFilter}
                onChange={(e) => setEndDateFilter(e.target.value)}
                aria-label="End date"
              />
            </div>
            <p className={styles.searchHint}>Year: set 01-01 to 12-31. Month: set first to last day (for example 2024-05-01 to 2024-05-31).</p>
          </div>

          <div className={styles.photoList}>
            {isLoading ? (
              <p className={styles.statusMessage}>Loading photos…</p>
            ) : errorMessage ? (
              <p className={styles.errorMessage}>{errorMessage}</p>
            ) : photos.length === 0 ? (
              <p className={styles.statusMessage}>No results found.</p>
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

          <div className={styles.pagination}>
            <button
              type="button"
              className={styles.paginationButton}
              disabled={isLoading || offset <= 0}
              onClick={() => onPageChange(Math.max(0, offset - pageSize))}
            >
              ← Previous Page
            </button>
            <span className={styles.paginationInfo}>
              Page {Math.floor(offset / pageSize) + 1} of {Math.max(1, Math.ceil(totalCount / pageSize))}
            </span>
            <button
              type="button"
              className={styles.paginationButton}
              disabled={isLoading || offset + pageSize >= totalCount}
              onClick={() => onPageChange(offset + pageSize)}
            >
              Next Page →
            </button>
          </div>
        </aside>
      </div>

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
            <div className={styles.detailTopGrid}>
              {/* Full image with face overlays */}
              <div className={styles.panel}>
                <div className={styles.imageWrapper}>
                  <div className={styles.rotationControls}>
                    <button
                      type="button"
                      className={styles.rotationButton}
                      onClick={selectPreviousPhoto}
                      disabled={selectedPhotoIndex <= 0}
                    >
                      Prev Photo
                    </button>
                    <button
                      type="button"
                      className={styles.rotationButton}
                      onClick={selectNextPhoto}
                      disabled={selectedPhotoIndex < 0 || selectedPhotoIndex >= photos.length - 1}
                    >
                      Next Photo
                    </button>
                    <button
                      type="button"
                      className={styles.rotationButton}
                      onClick={openPresentationMode}
                    >
                      Presentation Mode
                    </button>
                    <button
                      type="button"
                      className={styles.rotationButton}
                      onClick={rotateLeft}
                      disabled={isUpdatingRotation}
                    >
                      Rotate Left
                    </button>
                    <button
                      type="button"
                      className={styles.rotationButton}
                      onClick={rotateRight}
                      disabled={isUpdatingRotation}
                    >
                      Rotate Right
                    </button>
                    <button
                      type="button"
                      className={styles.rotationButton}
                      onClick={resetRotation}
                      disabled={isUpdatingRotation || displayRotationDegrees === 0}
                    >
                      Reset Rotation
                    </button>
                    <span className={styles.rotationValue}>Current: {displayRotationDegrees}°</span>
                  </div>
                  {rotationErrorMessage ? <p className={styles.errorInline}>{rotationErrorMessage}</p> : null}
                  {imageLoadError ? (
                    <div className={styles.imagePlaceholder}>Image unavailable</div>
                  ) : (
                    <div className={styles.imageContainer} ref={imageViewportRef}>
                      {isQuarterTurnRotation ? (
                        <div className={styles.rotatedImageViewport}>
                          <div className={styles.rotatedImageFrame} style={getRotatedImageFrameStyle(displayRotationDegrees)}>
                            <img
                              src={resolveApiUrl(photoDetail.image_url) ?? ""}
                              alt={photoDetail.filename}
                              className={`${styles.fullImage} ${styles.rotatedFullImage}`}
                              style={{ transform: getImageTransform(displayRotationDegrees) }}
                              onLoad={(e) => {
                                const img = e.currentTarget as HTMLImageElement;
                                setNaturalDims({ w: img.naturalWidth, h: img.naturalHeight });
                              }}
                              onError={() => setImageLoadError(true)}
                            />
                          </div>
                        </div>
                      ) : (
                        <img
                          src={resolveApiUrl(photoDetail.image_url) ?? ""}
                          alt={photoDetail.filename}
                          className={styles.fullImage}
                          style={{ transform: getImageTransform(displayRotationDegrees) }}
                          onLoad={(e) => {
                            const img = e.currentTarget as HTMLImageElement;
                            setNaturalDims({ w: img.naturalWidth, h: img.naturalHeight });
                          }}
                          onError={() => setImageLoadError(true)}
                        />
                      )}
                      {!areFaceOverlaysSuppressed &&
                        naturalDims &&
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
                  {areFaceOverlaysSuppressed && photoDetail.faces.length > 0 ? (
                    <p className={styles.metadataSubtle}>Face overlays are hidden while rotation is not 0°.</p>
                  ) : null}
                </div>
                <p className={styles.imageFilename}>{photoDetail.filename}</p>
              </div>

              <div className={styles.panel}>
                <div className={styles.panelHeader}>
                  <h2 className={styles.panelTitle}>Photo Details</h2>
                </div>
                <div className={styles.metadataBody}>
                  <section className={styles.metadataSection}>
                    <h3 className={styles.metadataSectionTitle}>Photo</h3>
                    <div className={styles.metadataRow}>
                      <span className={styles.metadataLabel}>Filename</span>
                      <span className={styles.metadataValue}>{photoDetail.filename}</span>
                    </div>
                    <div className={styles.metadataRow}>
                      <span className={styles.metadataLabel}>Asset SHA</span>
                      <span className={`${styles.metadataValue} ${styles.metadataWrap}`}>
                        {photoDetail.asset_sha256}
                      </span>
                    </div>
                    <div className={styles.metadataRow}>
                      <span className={styles.metadataLabel}>Type</span>
                      <span className={styles.metadataValue}>{getCaptureTypeLabel(photoDetail.capture_type)}</span>
                    </div>
                    <div className={styles.metadataRow}>
                      <span className={styles.metadataLabel}>Capture Time</span>
                      <span className={styles.metadataValue}>{getCaptureTrustLabel(photoDetail.capture_time_trust)}</span>
                    </div>
                    <div className={styles.metadataRow}>
                      <span className={styles.metadataLabel}>Face Count</span>
                      <span className={styles.metadataValue}>{photoDetail.faces.length}</span>
                    </div>
                    <div className={styles.metadataRow}>
                      <span className={styles.metadataLabel}>Display Rotation</span>
                      <span className={styles.metadataValue}>{displayRotationDegrees}°</span>
                    </div>
                    <div className={styles.metadataRow}>
                      <span className={styles.metadataLabel}>Canonical</span>
                      <span className={styles.metadataValue}>
                        {photoDetail.is_canonical ? "Canonical asset" : "Duplicate of canonical"}
                      </span>
                    </div>
                    <div className={styles.metadataRow}>
                      <span className={styles.metadataLabel}>Quality</span>
                      <span className={styles.metadataValue}>
                        {getQualityLabel(photoDetail.quality_score)}
                        {photoDetail.quality_score !== null ? ` (${photoDetail.quality_score.toFixed(2)})` : ""}
                      </span>
                    </div>
                  </section>

                  <section className={styles.metadataSection}>
                    <h3 className={styles.metadataSectionTitle}>Context</h3>
                    <div className={styles.metadataRow}>
                      <span className={styles.metadataLabel}>Event</span>
                      <span className={styles.metadataValue}>{formatEventSummary(photoDetail.event)}</span>
                    </div>
                    <div className={styles.eventActionRow}>
                      <select
                        className={styles.eventSelect}
                        value={selectedEventTargetId ?? ""}
                        onChange={(event) => setSelectedEventTargetId(Number(event.target.value))}
                        disabled={isUpdatingEventAssignment || eventOptions.length === 0}
                      >
                        {eventOptions.length === 0 ? <option value="">No events available</option> : null}
                        {eventOptions.map((event) => (
                          <option key={event.event_id} value={event.event_id}>
                            {formatEventOptionLabel(event)}
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        className={styles.eventButton}
                        onClick={handleAssignToEvent}
                        disabled={isUpdatingEventAssignment || selectedEventTargetId === null}
                      >
                        Assign
                      </button>
                      <button
                        type="button"
                        className={styles.eventButton}
                        onClick={handleRemoveFromEvent}
                        disabled={isUpdatingEventAssignment || !photoDetail.event}
                      >
                        Remove
                      </button>
                    </div>
                    {eventActionErrorMessage ? <p className={styles.errorInline}>{eventActionErrorMessage}</p> : null}
                    {eventActionSuccessMessage ? <p className={styles.successInline}>{eventActionSuccessMessage}</p> : null}
                    <div className={styles.metadataRow}>
                      <span className={styles.metadataLabel}>Location</span>
                      <span className={styles.metadataValue}>{formatLocationSummary(photoDetail.location)}</span>
                    </div>
                    <div className={styles.metadataRow}>
                      <span className={styles.metadataLabel}>Duplicate Group</span>
                      <span className={styles.metadataValue}>
                        {photoDetail.duplicate_group_id
                          ? `#${photoDetail.duplicate_group_id} (${photoDetail.duplicate_group_type ?? "near"})`
                          : "None"}
                      </span>
                    </div>
                    <div className={styles.metadataRow}>
                      <span className={styles.metadataLabel}>Duplicates</span>
                      <span className={styles.metadataValue}>{photoDetail.duplicate_count}</span>
                    </div>
                    <div className={styles.metadataRow}>
                      <span className={styles.metadataLabel}>Canonical Asset SHA</span>
                      <span className={`${styles.metadataValue} ${styles.metadataWrap}`}>
                        {photoDetail.canonical_asset_sha256 ?? "Unknown"}
                      </span>
                    </div>

                    <div className={styles.duplicateControlRoot}>
                      <span className={styles.metadataLabel}>Near-Duplicate Control</span>
                      <input
                        type="text"
                        className={styles.duplicateSearchInput}
                        placeholder="Search target filename..."
                        value={duplicateMergeSearch}
                        onChange={(event) => setDuplicateMergeSearch(event.target.value)}
                        disabled={isMergingDuplicateLineage}
                      />
                      <select
                        className={styles.duplicateTargetSelect}
                        value={selectedDuplicateMergeTargetSha}
                        onChange={(event) => setSelectedDuplicateMergeTargetSha(event.target.value)}
                        disabled={isLoadingDuplicateTargets || isMergingDuplicateLineage || duplicateMergeTargets.length === 0}
                      >
                        <option value="">
                          {isLoadingDuplicateTargets ? "Loading targets..." : "Select target asset in another lineage"}
                        </option>
                        {duplicateMergeTargets.map((target) => (
                          <option key={target.asset_sha256} value={target.asset_sha256}>
                            {formatDuplicateTargetOption(target)}
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        className={styles.duplicateMergeButton}
                        onClick={handleMergeDuplicateLineage}
                        disabled={isMergingDuplicateLineage || isLoadingDuplicateTargets || !selectedDuplicateMergeTargetSha}
                      >
                        {isMergingDuplicateLineage ? "Merging..." : "Merge Into Target Lineage"}
                      </button>
                      {duplicateMergeErrorMessage ? <p className={styles.errorInline}>{duplicateMergeErrorMessage}</p> : null}
                      {duplicateMergeSuccessMessage ? <p className={styles.successInline}>{duplicateMergeSuccessMessage}</p> : null}
                    </div>
                  </section>

                  <section className={styles.metadataSection}>
                    <h3 className={styles.metadataSectionTitle}>Albums</h3>
                    {albums.length === 0 ? (
                      <p className={styles.metadataValue}>No albums yet. Create one in the Albums view.</p>
                    ) : (
                      <>
                        <div className={styles.albumActionRow}>
                          <select
                            className={styles.albumSelect}
                            value={selectedAlbumId ?? ""}
                            onChange={(event) => setSelectedAlbumId(Number(event.target.value))}
                          >
                            {albums.map((album) => (
                              <option key={album.album_id} value={album.album_id}>
                                {album.name}
                              </option>
                            ))}
                          </select>
                          <button
                            type="button"
                            className={styles.albumButton}
                            onClick={handleAddPhotoToAlbum}
                            disabled={isUpdatingAlbums}
                          >
                            Add
                          </button>
                          <button
                            type="button"
                            className={styles.albumButton}
                            onClick={handleRemovePhotoFromAlbum}
                            disabled={isUpdatingAlbums}
                          >
                            Remove
                          </button>
                        </div>
                        {photoAlbums.length > 0 ? (
                          <ul className={styles.albumMembershipList}>
                            {photoAlbums.map((album) => (
                              <li key={album.album_id} className={styles.albumMembershipItem}>
                                {album.name}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className={styles.metadataValue}>This photo is not in any album yet.</p>
                        )}
                      </>
                    )}
                    {albumsErrorMessage ? <p className={styles.errorInline}>{albumsErrorMessage}</p> : null}
                    {albumsSuccessMessage ? <p className={styles.successInline}>{albumsSuccessMessage}</p> : null}
                  </section>

                  <section className={styles.metadataSection}>
                    <h3 className={styles.metadataSectionTitle}>Provenance</h3>
                    {photoDetail.provenance.length === 0 ? (
                      <p className={styles.metadataValue}>No provenance available</p>
                    ) : (
                      <>
                        <ul className={styles.provenanceList}>
                          {(showAllProvenance ? photoDetail.provenance : photoDetail.provenance.slice(0, 3)).map((item, index) => (
                            <li key={`${item.source_path}-${index}`} className={styles.provenanceItem}>
                              <span className={`${styles.metadataValue} ${styles.metadataWrap}`}>{item.source_path}</span>
                              <span className={styles.metadataSubtle}>
                                Source: {item.source_label ?? "Unknown"} ({item.source_type ?? "unknown"})
                              </span>
                              {item.source_root_path ? (
                                <span className={`${styles.metadataSubtle} ${styles.metadataWrap}`}>
                                  Root: {item.source_root_path}
                                </span>
                              ) : null}
                              {item.source_relative_path ? (
                                <span className={`${styles.metadataSubtle} ${styles.metadataWrap}`}>
                                  Relative: {item.source_relative_path}
                                </span>
                              ) : null}
                              {(item.ingestion_source_id !== null || item.ingestion_run_id !== null) ? (
                                <span className={styles.metadataSubtle}>
                                  IDs: source #{item.ingestion_source_id ?? "-"}, run #{item.ingestion_run_id ?? "-"}
                                </span>
                              ) : null}
                              <span className={styles.metadataSubtle}>{formatProvenanceDate(item.ingested_at)}</span>
                            </li>
                          ))}
                        </ul>
                        {photoDetail.provenance.length > 3 ? (
                          <button
                            type="button"
                            className={styles.provenanceToggle}
                            onClick={() => setShowAllProvenance((prev) => !prev)}
                          >
                            {showAllProvenance ? "Show fewer" : `Show all (${photoDetail.provenance.length})`}
                          </button>
                        ) : null}
                      </>
                    )}
                  </section>

                  <section className={styles.metadataSection}>
                    <h3 className={styles.metadataSectionTitle}>EXIF Canonicalization</h3>
                    {photoDetail.canonical_metadata ? (
                      <>
                        <div className={styles.metadataRow}>
                          <span className={styles.metadataLabel}>Canonical Captured At</span>
                          <span className={styles.metadataValue}>
                            {photoDetail.canonical_metadata.captured_at
                              ? formatDateTime(photoDetail.canonical_metadata.captured_at)
                              : "Unknown"}
                          </span>
                        </div>
                        <div className={styles.metadataRow}>
                          <span className={styles.metadataLabel}>Canonical Camera</span>
                          <span className={styles.metadataValue}>
                            {photoDetail.canonical_metadata.camera_make || photoDetail.canonical_metadata.camera_model
                              ? `${photoDetail.canonical_metadata.camera_make ?? ""} ${photoDetail.canonical_metadata.camera_model ?? ""}`.trim()
                              : "Unknown"}
                          </span>
                        </div>
                        <div className={styles.metadataRow}>
                          <span className={styles.metadataLabel}>Canonical Dimensions</span>
                          <span className={styles.metadataValue}>
                            {photoDetail.canonical_metadata.width && photoDetail.canonical_metadata.height
                              ? `${photoDetail.canonical_metadata.width} × ${photoDetail.canonical_metadata.height}`
                              : "Unknown"}
                          </span>
                        </div>
                        <div className={styles.metadataRow}>
                          <span className={styles.metadataLabel}>Canonical Location</span>
                          <span className={styles.metadataValue}>{formatLocationSummary(photoDetail.location)}</span>
                        </div>
                      </>
                    ) : (
                      <p className={styles.metadataValue}>No canonical metadata available</p>
                    )}

                    {allExifObservations.length === 0 ? (
                      <p className={styles.metadataValue}>No metadata observations available</p>
                    ) : (
                      <>
                        <ul className={styles.provenanceList}>
                          {exifObservationsForDisplay.map((item) => (
                            <li key={item.id} className={styles.provenanceItem}>
                              <span className={styles.metadataSubtle}>
                                Origin: {item.observation_origin} ({item.observed_source_type ?? "unknown"})
                                {item.observed_extension ? ` ${item.observed_extension}` : ""}
                              </span>
                              {item.observed_source_path ? (
                                <span className={`${styles.metadataValue} ${styles.metadataWrap}`}>
                                  {item.observed_source_path}
                                </span>
                              ) : null}
                              <span className={styles.metadataSubtle}>
                                {item.exif_datetime_original
                                  ? `DateTimeOriginal: ${formatDateTime(item.exif_datetime_original)}`
                                  : "DateTimeOriginal: Unknown"}
                              </span>
                              <span className={styles.metadataSubtle}>
                                {item.captured_at_observed
                                  ? `Captured At: ${formatDateTime(item.captured_at_observed)}`
                                  : "Captured At: Unknown"}
                              </span>
                              <span className={styles.metadataSubtle}>
                                GPS: {formatObservationLocation(item.gps_latitude, item.gps_longitude)}
                              </span>
                              <span className={styles.metadataSubtle}>
                                Camera: {(item.camera_make || "").trim()} {(item.camera_model || "").trim()} 
                                {!item.camera_make && !item.camera_model ? "Unknown" : ""}
                              </span>
                              <span className={styles.metadataSubtle}>
                                Dimensions: {item.width && item.height ? `${item.width} × ${item.height}` : "Unknown"}
                              </span>
                              <span className={styles.winnerBadge}>{formatWinnerFields(item.winner_fields)}</span>
                              <span className={styles.metadataSubtle}>
                                {item.is_legacy_seeded ? "Legacy seeded" : "Observed"}
                                {item.created_at_utc ? ` • ${formatDateTime(item.created_at_utc)}` : ""}
                              </span>
                            </li>
                          ))}
                        </ul>
                        {!showAllExifObservations && hiddenVaultObservationCount > 0 ? (
                          <span className={styles.metadataSubtle}>
                            {hiddenVaultObservationCount} redundant vault observation
                            {hiddenVaultObservationCount === 1 ? "" : "s"} hidden by default.
                          </span>
                        ) : null}
                        {allExifObservations.length > 3 || hiddenVaultObservationCount > 0 ? (
                          <button
                            type="button"
                            className={styles.provenanceToggle}
                            onClick={() => setShowAllExifObservations((prev) => !prev)}
                          >
                            {showAllExifObservations
                              ? "Show default view"
                              : `Show all for audit (${allExifObservations.length})`}
                          </button>
                        ) : null}
                      </>
                    )}
                  </section>
                </div>
              </div>
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

            {/* Content Tags */}
            {photoDetail.content_tags.length > 0 && (
              <div className={styles.panel}>
                <div className={styles.panelHeader}>
                  <h2 className={styles.panelTitle}>Content Tags</h2>
                  <span className={styles.panelCount}>{photoDetail.content_tags.length}</span>
                </div>
                <ContentTagsSection tags={photoDetail.content_tags} />
              </div>
            )}
          </>
        )}
      </div>
      {presentationStartIndex !== null ? (
        <PresentationViewer
          items={photos}
          initialIndex={presentationStartIndex}
          onClose={() => {
            void closePresentationMode();
          }}
        />
      ) : null}
    </div>
  );
}

function ContentTagsSection({ tags }: { tags: ContentTagSummary[] }) {
  const objects = tags.filter((t) => t.tag_type === "object");
  const scenes = tags.filter((t) => t.tag_type === "scene");

  return (
    <div className={styles.contentTagsRoot}>
      {objects.length > 0 && (
        <div className={styles.contentTagsGroup}>
          <span className={styles.contentTagsGroupLabel}>Objects</span>
          <ul className={styles.contentTagsList}>
            {objects.map((t) => (
              <li key={t.tag} className={styles.contentTag}>{t.tag}</li>
            ))}
          </ul>
        </div>
      )}
      {scenes.length > 0 && (
        <div className={styles.contentTagsGroup}>
          <span className={styles.contentTagsGroupLabel}>Scenes</span>
          <ul className={styles.contentTagsList}>
            {scenes.map((t) => (
              <li key={t.tag} className={styles.contentTag}>{t.tag}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

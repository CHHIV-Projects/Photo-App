"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { PresentationViewer } from "@/components/PresentationViewer";
import styles from "@/components/photo-review-view.module.css";
import {
  addAssetsToCollection,
  assignFaceToPerson,
  assignPerson,
  batchAddPhotosToAlbum,
  batchCreateAlbumFromPhotos,
  batchUpdatePhotoVisibility,
  createPerson,
  getCollections,
  getAlbums,
  getEvents,
  getPhotoFaceOverlays,
  getPeople,
  getTimelineSummary,
  resolveApiUrl,
  searchPhotos,
  removeFaceFromCluster,
} from "@/lib/api";
import type {
  AlbumSummary,
  CollectionSummary,
  EventSummary,
  FaceInPhoto,
  PersonSummary,
  PhotoFaceOverlayAsset,
  PhotoSummary,
  SearchPhotoSummary,
} from "@/types/ui-api";

const MONTH_MAP: Record<string, string> = {
  january: "01", jan: "01",
  february: "02", feb: "02",
  march: "03", mar: "03",
  april: "04", apr: "04",
  may: "05",
  june: "06", jun: "06",
  july: "07", jul: "07",
  august: "08", aug: "08",
  september: "09", sep: "09", sept: "09",
  october: "10", oct: "10",
  november: "11", nov: "11",
  december: "12", dec: "12",
};

const MONTH_NUM_TO_NAME: Record<string, string> = {
  "01": "January",
  "02": "February",
  "03": "March",
  "04": "April",
  "05": "May",
  "06": "June",
  "07": "July",
  "08": "August",
  "09": "September",
  "10": "October",
  "11": "November",
  "12": "December",
};

interface ParsedQuery {
  year?: number;
  monthNum?: string;
  cameraQuery?: string;
  freeTextTokens: string[];
}

// Prefixes that are not yet supported by the backend.
// The prefix is stripped and the value is routed to free-text search (q).
const UNSUPPORTED_PREFIXES = ["person:", "event:", "place:", "source:", "album:", "filename:"];

function parseSearchQuery(input: string): ParsedQuery {
  const tokens = input.trim().split(/\s+/).filter(Boolean);
  let year: number | undefined;
  let monthNum: string | undefined;
  let cameraQuery: string | undefined;
  const freeTextTokens: string[] = [];

  for (const token of tokens) {
    if (/^\d{4}$/.test(token)) {
      const n = Number(token);
      if (n >= 1900 && n <= 2100) {
        year = n;
        continue;
      }
    }
    const mapped = MONTH_MAP[token.toLowerCase()];
    if (mapped) {
      monthNum = mapped;
      continue;
    }
    const lowerToken = token.toLowerCase();
    if (lowerToken.startsWith("camera:")) {
      // Explicit camera: prefix — route to camera filter
      const value = token.slice("camera:".length).trim();
      if (value) {
        cameraQuery = value;
      }
      continue;
    }
    // Unsupported structured prefixes — strip prefix, route value to free text
    const unsupported = UNSUPPORTED_PREFIXES.find((p) => lowerToken.startsWith(p));
    if (unsupported) {
      const value = token.slice(unsupported.length).trim();
      if (value) {
        freeTextTokens.push(value);
      }
      continue;
    }
    // Plain text — route to free-text search (q)
    freeTextTokens.push(token);
  }

  return { year, monthNum, cameraQuery, freeTextTokens };
}

function buildSearchText(year: string, monthNum: string, camera: string, freeText: string): string {
  const parts: string[] = [];
  if (year) parts.push(year);
  if (monthNum) {
    const name = MONTH_NUM_TO_NAME[monthNum];
    if (name) parts.push(name);
  }
  if (camera.trim()) parts.push(`camera:${camera.trim()}`);
  if (freeText.trim()) parts.push(freeText.trim());
  return parts.join(" ");
}

interface PhotoReviewViewProps {
  onOpenPhotoDetail: (sha256: string) => void;
  onOpenDuplicateGroup: (groupId: number) => void;
  onFaceAssignmentsChanged?: () => void;
}

const PAGE_SIZE = 80;

type FaceOverlayMode = "off" | "hover" | "always";

interface SelectedOverlayFace {
  assetSha256: string;
  faceId: number;
}

function getFaceLabel(face: FaceInPhoto): string {
  if (face.person_name) return face.person_name;
  if (face.cluster_id !== null) return `Cluster #${face.cluster_id} - No Person Assigned`;
  return "Unclustered face";
}

function personMatchesSearch(person: PersonSummary, queryLower: string): boolean {
  if (person.display_name.toLowerCase().includes(queryLower)) {
    return true;
  }
  return person.aliases.some((alias) => alias.toLowerCase().includes(queryLower));
}

function getOverlayReferenceDims(
  overlay: PhotoFaceOverlayAsset,
  naturalDims: { w: number; h: number } | undefined
): { w: number; h: number } | null {
  if (!naturalDims || naturalDims.w <= 0 || naturalDims.h <= 0) {
    if (overlay.canonical_width && overlay.canonical_height) {
      return { w: overlay.canonical_width, h: overlay.canonical_height };
    }
    return null;
  }

  if (!overlay.canonical_width || !overlay.canonical_height) {
    return naturalDims;
  }

  let referenceWidth = overlay.canonical_width;
  let referenceHeight = overlay.canonical_height;
  const naturalIsLandscape = naturalDims.w >= naturalDims.h;
  const canonicalIsLandscape = overlay.canonical_width >= overlay.canonical_height;
  if (naturalIsLandscape !== canonicalIsLandscape) {
    referenceWidth = overlay.canonical_height;
    referenceHeight = overlay.canonical_width;
  }

  return { w: referenceWidth, h: referenceHeight };
}

export function PhotoReviewView({
  onOpenPhotoDetail,
  onOpenDuplicateGroup,
  onFaceAssignmentsChanged,
}: PhotoReviewViewProps) {
  const [items, setItems] = useState<SearchPhotoSummary[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [offset, setOffset] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [batchMessage, setBatchMessage] = useState<string | null>(null);
  const [isRunningBatchAction, setIsRunningBatchAction] = useState(false);

  const [albums, setAlbums] = useState<AlbumSummary[]>([]);
  const [people, setPeople] = useState<PersonSummary[]>([]);
  const [events, setEvents] = useState<EventSummary[]>([]);
  const [selectedAlbumId, setSelectedAlbumId] = useState<number | null>(null);
  const [collections, setCollections] = useState<CollectionSummary[]>([]);
  const [isCollectionConfirmOpen, setIsCollectionConfirmOpen] = useState(false);
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(null);
  const [collectionSearchQuery, setCollectionSearchQuery] = useState("");
  const [isLoadingCollections, setIsLoadingCollections] = useState(false);

  const [selectedAssets, setSelectedAssets] = useState<Set<string>>(new Set());
  const [presentationStartIndex, setPresentationStartIndex] = useState<number | null>(null);
  const [presentationHasPendingRefresh, setPresentationHasPendingRefresh] = useState(false);

  const [searchText, setSearchText] = useState("");
  const [year, setYear] = useState<string>("");
  const [month, setMonth] = useState<string>("");
  const [camera, setCamera] = useState("");
  const [freeText, setFreeText] = useState("");
  const [visibilityFilter, setVisibilityFilter] = useState<"visible" | "demoted" | "all">("visible");
  const [mediaTypeFilter, setMediaTypeFilter] = useState<"all" | "photos" | "videos">("all");
  const [showLivePhotoMotionClips, setShowLivePhotoMotionClips] = useState(false);
  const [hasLocation, setHasLocation] = useState(false);
  const [hasFaces, setHasFaces] = useState(false);
  const [hasUnassignedFaces, setHasUnassignedFaces] = useState(false);
  const [undated, setUndated] = useState(false);
  const [yearOptions, setYearOptions] = useState<string[]>([]);
  const [monthOptions, setMonthOptions] = useState<Array<{ value: string; label: string }>>([]);
  const [selectedPeopleIds, setSelectedPeopleIds] = useState<number[]>([]);
  const [peopleSearchQuery, setPeopleSearchQuery] = useState("");
  const [selectedPersonCandidateId, setSelectedPersonCandidateId] = useState<number | null>(null);
  const [selectedAlbumForFilter, setSelectedAlbumForFilter] = useState<number | null>(null);
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);
  const [placeQuery, setPlaceQuery] = useState("");
  const [provenanceQuery, setProvenanceQuery] = useState("");
  const [faceOverlayMode, setFaceOverlayMode] = useState<FaceOverlayMode>("hover");
  const [overlaysByAsset, setOverlaysByAsset] = useState<Record<string, PhotoFaceOverlayAsset>>({});
  const [loadingOverlayAssets, setLoadingOverlayAssets] = useState<Record<string, true>>({});
  const [hoveredAssetSha256, setHoveredAssetSha256] = useState<string | null>(null);
  const [hoveredFaceKey, setHoveredFaceKey] = useState<string | null>(null);
  const [imageNaturalDimsByAsset, setImageNaturalDimsByAsset] = useState<Record<string, { w: number; h: number }>>({});
  const [selectedOverlayFace, setSelectedOverlayFace] = useState<SelectedOverlayFace | null>(null);
  const [assignmentPersonId, setAssignmentPersonId] = useState<number | null>(null);
  const [newPersonName, setNewPersonName] = useState("");
  const [isAssigningCluster, setIsAssigningCluster] = useState(false);
  const [assignmentMessage, setAssignmentMessage] = useState<string | null>(null);
  const [assignmentErrorMessage, setAssignmentErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!assignmentMessage) return;
    const id = window.setTimeout(() => setAssignmentMessage(null), 1500);
    return () => window.clearTimeout(id);
  }, [assignmentMessage]);

  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const assignmentPanelRef = useRef<HTMLDivElement | null>(null);
  const yearRef = useRef(year);
  yearRef.current = year;

  const selectedCount = selectedAssets.size;
  const selectedShaList = useMemo(() => Array.from(selectedAssets), [selectedAssets]);

  const selectedCollection = useMemo(
    () => collections.find((item) => item.collection_id === selectedCollectionId) ?? null,
    [collections, selectedCollectionId]
  );

  const filteredCollections = useMemo(() => {
    const query = collectionSearchQuery.trim().toLowerCase();
    if (!query) {
      return collections;
    }
    return collections.filter((item) => item.name.toLowerCase().includes(query));
  }, [collections, collectionSearchQuery]);

  const selectedAssetLabelSamples = useMemo(() => {
    const bySha = new Map(items.map((item) => [item.asset_sha256, item.filename]));
    return selectedShaList.slice(0, 6).map((sha) => bySha.get(sha) ?? `${sha.slice(0, 12)}...`);
  }, [items, selectedShaList]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      const parsed = parseSearchQuery(searchText);
      const currentYear = yearRef.current;

      let newYear: string;
      if (parsed.year !== undefined) {
        newYear = String(parsed.year);
      } else if (parsed.monthNum && currentYear) {
        newYear = currentYear;
      } else {
        newYear = "";
      }

      const newMonth = parsed.monthNum && newYear ? parsed.monthNum : "";
      const newCamera = parsed.cameraQuery ?? "";
      const newFreeText = parsed.freeTextTokens.join(" ");

      setYear(newYear);
      setMonth(newMonth);
      setCamera(newCamera);
      setFreeText(newFreeText);
    }, 300);
    return () => window.clearTimeout(handle);
  }, [searchText]);

  const monthLabelByValue = useMemo(
    () =>
      new Map<string, string>([
        ["01", "Jan"],
        ["02", "Feb"],
        ["03", "Mar"],
        ["04", "Apr"],
        ["05", "May"],
        ["06", "Jun"],
        ["07", "Jul"],
        ["08", "Aug"],
        ["09", "Sep"],
        ["10", "Oct"],
        ["11", "Nov"],
        ["12", "Dec"],
      ]),
    []
  );

  useEffect(() => {
    let isCancelled = false;

    async function loadYearOptions(): Promise<void> {
      try {
        const response = await getTimelineSummary();
        if (isCancelled) {
          return;
        }

        const values = response.items
          .map((item) => item.period_key)
          .filter((periodKey) => /^\d{4}$/.test(periodKey));
        setYearOptions(values);
      } catch {
        if (!isCancelled) {
          setYearOptions([]);
        }
      }
    }

    void loadYearOptions();
    return () => {
      isCancelled = true;
    };
  }, []);

  async function loadCollectionsForBatch(preferredCollectionId?: number | null): Promise<void> {
    setIsLoadingCollections(true);
    try {
      const response = await getCollections();
      setCollections(response.items);
      if (response.items.length === 0) {
        setSelectedCollectionId(null);
        return;
      }
      const candidateId = preferredCollectionId ?? selectedCollectionId;
      if (candidateId !== null && response.items.some((item) => item.collection_id === candidateId)) {
        setSelectedCollectionId(candidateId);
        return;
      }
      setSelectedCollectionId(response.items[0].collection_id);
    } catch {
      setCollections([]);
      setSelectedCollectionId(null);
    } finally {
      setIsLoadingCollections(false);
    }
  }

  useEffect(() => {
    let isCancelled = false;

    async function loadPeople(): Promise<void> {
      try {
        const response = await getPeople();
        if (!isCancelled) {
          const sorted = [...response.items].sort((a, b) => a.display_name.localeCompare(b.display_name));
          setPeople(sorted);
        }
      } catch {
        if (!isCancelled) {
          setPeople([]);
        }
      }
    }

    void loadPeople();
    return () => {
      isCancelled = true;
    };
  }, []);

  useEffect(() => {
    let isCancelled = false;

    async function loadEvents(): Promise<void> {
      try {
        const response = await getEvents();
        if (!isCancelled) {
          const sorted = response.items
            .filter((eventItem) => Boolean(eventItem.label?.trim()))
            .sort((a, b) => {
            const aLabel = a.label?.trim() || "";
            const bLabel = b.label?.trim() || "";
            return aLabel.localeCompare(bLabel);
          });
          setEvents(sorted);
        }
      } catch {
        if (!isCancelled) {
          setEvents([]);
        }
      }
    }

    void loadEvents();
    return () => {
      isCancelled = true;
    };
  }, []);

  useEffect(() => {
    let isCancelled = false;

    async function loadMonthOptions(selectedYear: string): Promise<void> {
      if (!selectedYear) {
        setMonthOptions([]);
        return;
      }

      try {
        const response = await getTimelineSummary({ year: Number(selectedYear) });
        if (isCancelled) {
          return;
        }

        const values = response.items
          .map((item) => item.period_key)
          .filter((periodKey) => /^\d{4}-\d{2}$/.test(periodKey))
          .map((periodKey) => periodKey.slice(5))
          .sort((a, b) => a.localeCompare(b));

        const nextOptions = values.map((value) => ({
          value,
          label: monthLabelByValue.get(value) ?? value,
        }));

        setMonthOptions(nextOptions);
      } catch {
        if (!isCancelled) {
          setMonthOptions([]);
        }
      }
    }

    void loadMonthOptions(year);
    return () => {
      isCancelled = true;
    };
  }, [year, monthLabelByValue]);

  useEffect(() => {
    if (!month) {
      return;
    }
    const stillAvailable = monthOptions.some((option) => option.value === month);
    if (!stillAvailable) {
      setMonth("");
    }
  }, [month, monthOptions]);

  useEffect(() => {
    let isCancelled = false;

    async function loadAlbums(): Promise<void> {
      try {
        const response = await getAlbums();
        if (!isCancelled) {
          setAlbums(response.items);
        }
      } catch {
        if (!isCancelled) {
          setAlbums([]);
        }
      }
    }

    void loadAlbums();
    return () => {
      isCancelled = true;
    };
  }, []);

  useEffect(() => {
    let isCancelled = false;

    async function loadCollections(): Promise<void> {
      try {
        const response = await getCollections();
        if (isCancelled) {
          return;
        }
        const sorted = [...response.items].sort((a, b) => a.name.localeCompare(b.name));
        setCollections(sorted);
      } catch {
        if (!isCancelled) {
          setCollections([]);
        }
      }
    }

    void loadCollections();
    return () => {
      isCancelled = true;
    };
  }, []);

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

  async function loadPage(nextOffset: number, reset: boolean): Promise<void> {
    if (isLoading) {
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const activeYear = year && !month ? Number(year) : undefined;
      const activeMonth = year && month ? `${year}-${month}` : undefined;
      const personIdsString = selectedPeopleIds.length > 0 ? selectedPeopleIds.join(",") : undefined;
      const response = await searchPhotos({
        q: freeText || undefined,
        year: activeYear,
        month: activeMonth,
        camera: camera || undefined,
        personIds: personIdsString,
        albumId: selectedAlbumForFilter || undefined,
        eventId: selectedEventId || undefined,
        placeQuery: placeQuery || undefined,
        provenanceQuery: provenanceQuery || undefined,
        visibilityFilter,
        mediaTypeFilter,
        includeLivePhotoMotionCompanions: showLivePhotoMotionClips,
        hasLocation: hasLocation ? true : undefined,
        hasFaces: hasFaces ? true : undefined,
        hasUnassignedFaces: hasUnassignedFaces ? true : undefined,
        undated: undated || undefined,
        canonicalFirst: true,
        offset: nextOffset,
        limit: PAGE_SIZE,
      });

      setItems((prev) => {
        if (reset) {
          return response.items;
        }
        const existing = new Set(prev.map((item) => item.asset_sha256));
        const merged = [...prev];
        for (const item of response.items) {
          if (!existing.has(item.asset_sha256)) {
            merged.push(item);
            existing.add(item.asset_sha256);
          }
        }
        return merged;
      });
      setOffset(nextOffset);
      setTotalCount(response.total_count);
    } catch (error) {
      const message = error instanceof Error && error.message ? error.message : "Failed to load photo review items.";
      setErrorMessage(message);
    } finally {
      setIsLoading(false);
    }
  }

  async function reloadFromStart(): Promise<void> {
    setSelectedAssets(new Set());
    setItems([]);
    setOffset(0);
    setTotalCount(0);
    await loadPage(0, true);
  }

  useEffect(() => {
    void reloadFromStart();
  }, [
    year,
    month,
    camera,
    freeText,
    selectedPeopleIds,
    selectedAlbumForFilter,
    selectedEventId,
    placeQuery,
    provenanceQuery,
    visibilityFilter,
    mediaTypeFilter,
    showLivePhotoMotionClips,
    hasLocation,
    hasFaces,
    hasUnassignedFaces,
    undated,
  ]);

  const hasMore = items.length < totalCount;

  useEffect(() => {
    const currentAssetSet = new Set(items.map((item) => item.asset_sha256));
    setOverlaysByAsset((current) => {
      const next: Record<string, PhotoFaceOverlayAsset> = {};
      let changed = false;
      for (const [assetSha256, overlay] of Object.entries(current)) {
        if (currentAssetSet.has(assetSha256)) {
          next[assetSha256] = overlay;
        } else {
          changed = true;
        }
      }
      return changed ? next : current;
    });
    setLoadingOverlayAssets((current) => {
      const next: Record<string, true> = {};
      let changed = false;
      for (const assetSha256 of Object.keys(current)) {
        if (currentAssetSet.has(assetSha256)) {
          next[assetSha256] = true;
        } else {
          changed = true;
        }
      }
      return changed ? next : current;
    });
    setImageNaturalDimsByAsset((current) => {
      const next: Record<string, { w: number; h: number }> = {};
      let changed = false;
      for (const [assetSha256, dims] of Object.entries(current)) {
        if (currentAssetSet.has(assetSha256)) {
          next[assetSha256] = dims;
        } else {
          changed = true;
        }
      }
      return changed ? next : current;
    });
  }, [items]);

  useEffect(() => {
    if (faceOverlayMode !== "off") {
      return;
    }
    setHoveredAssetSha256(null);
    setHoveredFaceKey(null);
  }, [faceOverlayMode]);

  useEffect(() => {
    if (faceOverlayMode === "off") {
      return;
    }
    const candidateAssetShas = items
      .filter((item) => item.face_count > 0)
      .map((item) => item.asset_sha256)
      .filter((assetSha256) => overlaysByAsset[assetSha256] === undefined && loadingOverlayAssets[assetSha256] === undefined)
      .slice(0, 40);

    if (candidateAssetShas.length === 0) {
      return;
    }

    setLoadingOverlayAssets((current) => {
      const next = { ...current };
      for (const assetSha256 of candidateAssetShas) {
        next[assetSha256] = true;
      }
      return next;
    });

    async function loadOverlays(): Promise<void> {
      try {
        const response = await getPhotoFaceOverlays(candidateAssetShas);
        setOverlaysByAsset((current) => {
          const next = { ...current };
          for (const overlay of response.items) {
            next[overlay.asset_sha256] = overlay;
          }
          return next;
        });
      } catch {
        // Keep browsing flow resilient even if overlay fetch fails.
      } finally {
        setLoadingOverlayAssets((current) => {
          const next = { ...current };
          for (const assetSha256 of candidateAssetShas) {
            delete next[assetSha256];
          }
          return next;
        });
      }
    }

    void loadOverlays();
  }, [faceOverlayMode, items, overlaysByAsset, loadingOverlayAssets]);

  const selectedOverlayFaceEntry = useMemo(() => {
    if (!selectedOverlayFace) {
      return null;
    }
    const overlay = overlaysByAsset[selectedOverlayFace.assetSha256];
    const face = overlay?.faces.find((candidate) => candidate.face_id === selectedOverlayFace.faceId);
    if (!face) {
      return null;
    }
    return {
      assetSha256: selectedOverlayFace.assetSha256,
      overlay,
      face,
    };
  }, [overlaysByAsset, selectedOverlayFace]);

  useEffect(() => {
    if (!selectedOverlayFaceEntry) {
      setAssignmentPersonId(null);
      return;
    }
    setAssignmentPersonId(selectedOverlayFaceEntry.face.person_id ?? null);
  }, [selectedOverlayFaceEntry]);

  useEffect(() => {
    if (!selectedOverlayFaceEntry || !assignmentPanelRef.current || typeof window === "undefined") {
      return;
    }

    const panel = assignmentPanelRef.current;
    const rect = panel.getBoundingClientRect();
    const viewportPadding = 24;
    const isVisible = rect.top >= viewportPadding && rect.bottom <= window.innerHeight - viewportPadding;
    if (isVisible) {
      return;
    }

    panel.scrollIntoView({ behavior: "smooth", block: "start", inline: "nearest" });
  }, [selectedOverlayFaceEntry]);

  function patchClusterAssignment(clusterId: number, personId: number, personName: string): void {
    setOverlaysByAsset((current) => {
      const next: Record<string, PhotoFaceOverlayAsset> = {};
      for (const [assetSha256, overlay] of Object.entries(current)) {
        let changed = false;
        const nextFaces = overlay.faces.map((face) => {
          if (face.cluster_id !== clusterId) {
            return face;
          }
          changed = true;
          return {
            ...face,
            person_id: personId,
            person_name: personName,
          };
        });

        next[assetSha256] = changed
          ? {
              ...overlay,
              faces: nextFaces,
            }
          : overlay;
      }
      return next;
    });
  }

  async function refreshOverlayForAsset(assetSha256: string): Promise<void> {
    const response = await getPhotoFaceOverlays([assetSha256]);
    const updated = response.items.find((item) => item.asset_sha256 === assetSha256);
    if (!updated) {
      return;
    }
    setOverlaysByAsset((current) => ({
      ...current,
      [assetSha256]: updated,
    }));
  }

  async function handleAssignSelectedClusterToPerson(targetPersonId: number): Promise<void> {
    if (!selectedOverlayFaceEntry) {
      return;
    }

    const clusterId = selectedOverlayFaceEntry.face.cluster_id;
    const previousName = selectedOverlayFaceEntry.face.person_name;
    const targetPerson = people.find((person) => person.person_id === targetPersonId);
    const targetPersonName = targetPerson?.display_name ?? `Person #${targetPersonId}`;

    setIsAssigningCluster(true);
    setAssignmentMessage(null);
    setAssignmentErrorMessage(null);

    try {
      if (clusterId === null) {
        await assignFaceToPerson(selectedOverlayFaceEntry.face.face_id, targetPersonId);
        await refreshOverlayForAsset(selectedOverlayFaceEntry.assetSha256);
      } else {
        await assignPerson(clusterId, targetPersonId);
        patchClusterAssignment(clusterId, targetPersonId, targetPersonName);
      }
      onFaceAssignmentsChanged?.();
      if (previousName && previousName !== targetPersonName) {
        setAssignmentMessage(
          clusterId === null
            ? `Reassigned face from ${previousName} to ${targetPersonName}.`
            : `Reassigned face cluster from ${previousName} to ${targetPersonName}.`
        );
      } else {
        setAssignmentMessage(clusterId === null ? `Assigned face to ${targetPersonName}.` : `Assigned face cluster to ${targetPersonName}.`);
      }
    } catch (error) {
      const message = error instanceof Error && error.message ? error.message : "Could not assign cluster. Please try again.";
      setAssignmentErrorMessage(message);
    } finally {
      setIsAssigningCluster(false);
    }
  }

  async function handleCreatePersonAndAssign(): Promise<void> {
    if (!selectedOverlayFaceEntry) {
      return;
    }

    const candidateName = newPersonName.trim();
    if (!candidateName) {
      setAssignmentErrorMessage("Enter a person name first.");
      return;
    }

    const clusterId = selectedOverlayFaceEntry.face.cluster_id;

    setIsAssigningCluster(true);
    setAssignmentMessage(null);
    setAssignmentErrorMessage(null);

    try {
      const response = await createPerson(candidateName);
      setPeople((current) => {
        const already = current.some((person) => person.person_id === response.person.person_id);
        if (already) {
          return current;
        }
        return [...current, response.person].sort((a, b) => a.display_name.localeCompare(b.display_name));
      });
      setNewPersonName("");
      setAssignmentPersonId(response.person.person_id);
      if (clusterId === null) {
        await assignFaceToPerson(selectedOverlayFaceEntry.face.face_id, response.person.person_id);
        await refreshOverlayForAsset(selectedOverlayFaceEntry.assetSha256);
      } else {
        await assignPerson(clusterId, response.person.person_id);
        patchClusterAssignment(clusterId, response.person.person_id, response.person.display_name);
      }
      onFaceAssignmentsChanged?.();
      setAssignmentMessage(
        clusterId === null
          ? `Created person ${response.person.display_name} and assigned face.`
          : `Created person ${response.person.display_name} and assigned face cluster.`
      );
    } catch (error) {
      let message = error instanceof Error && error.message
        ? error.message
        : "Could not create person. Please try again.";
      if (message.toLowerCase().includes("already exists")) {
        message = "A person with this name already exists. Select the existing person instead.";
      }
      setAssignmentErrorMessage(message);
    } finally {
      setIsAssigningCluster(false);
    }
  }

  useEffect(() => {
    if (!sentinelRef.current || !hasMore || isLoading) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const first = entries[0];
        if (!first.isIntersecting || isLoading || !hasMore) {
          return;
        }
        void loadPage(offset + PAGE_SIZE, false);
      },
      { rootMargin: "300px 0px" }
    );

    observer.observe(sentinelRef.current);
    return () => observer.disconnect();
  }, [offset, hasMore, isLoading]);

  function removeUndatedFilter(): void {
    setUndated(false);
  }

  function handleYearDropdownChange(newYear: string): void {
    setYear(newYear);
    setMonth("");
    setSearchText(buildSearchText(newYear, "", camera, freeText));
  }

  function handleMonthDropdownChange(newMonth: string): void {
    setMonth(newMonth);
    setSearchText(buildSearchText(year, newMonth, camera, freeText));
  }

  function removeYearChip(): void {
    setYear("");
    setMonth("");
    setSearchText(buildSearchText("", "", camera, freeText));
  }

  function removeMonthChip(): void {
    setMonth("");
    setSearchText(buildSearchText(year, "", camera, freeText));
  }

  function removeCameraChip(): void {
    setCamera("");
    setSearchText(buildSearchText(year, month, "", freeText));
  }

  function toggleSelectAsset(assetSha256: string): void {
    setSelectedAssets((current) => {
      const next = new Set(current);
      if (next.has(assetSha256)) {
        next.delete(assetSha256);
      } else {
        next.add(assetSha256);
      }
      return next;
    });
  }

  function handleClearSelection(): void {
    setSelectedAssets(new Set());
  }

  function handleSelectAllVisible(): void {
    setSelectedAssets(new Set(items.map((item) => item.asset_sha256)));
  }

  const filteredPeopleOptions = useMemo(() => {
    const q = peopleSearchQuery.trim().toLowerCase();
    return people.filter((person) => {
      if (selectedPeopleIds.includes(person.person_id)) {
        return false;
      }
      if (!q) {
        return true;
      }
      return personMatchesSearch(person, q);
    });
  }, [people, peopleSearchQuery, selectedPeopleIds]);

  const selectedPeople = useMemo(
    () =>
      selectedPeopleIds
        .map((personId) => people.find((person) => person.person_id === personId))
        .filter((person): person is PersonSummary => person !== undefined),
    [people, selectedPeopleIds]
  );

  useEffect(() => {
    if (filteredPeopleOptions.length === 0) {
      setSelectedPersonCandidateId(null);
      return;
    }

    // Only auto-select if user has typed a search query
    if (peopleSearchQuery.trim() && selectedPersonCandidateId === null) {
      setSelectedPersonCandidateId(filteredPeopleOptions[0].person_id);
      return;
    }

    // If current selection is no longer available, select first
    if (selectedPersonCandidateId !== null) {
      const candidateStillAvailable = filteredPeopleOptions.some(
        (person) => person.person_id === selectedPersonCandidateId
      );

      if (!candidateStillAvailable) {
        setSelectedPersonCandidateId(filteredPeopleOptions[0].person_id);
      }
    }
  }, [filteredPeopleOptions, selectedPersonCandidateId, peopleSearchQuery]);

  function addSelectedPerson(): void {
    if (selectedPersonCandidateId === null) {
      return;
    }
    setSelectedPeopleIds((current) => {
      if (current.includes(selectedPersonCandidateId)) {
        return current;
      }
      return [...current, selectedPersonCandidateId];
    });
  }

  function removeSelectedPerson(personId: number): void {
    setSelectedPeopleIds((current) => current.filter((id) => id !== personId));
  }

  function clearStructuredFilters(): void {
    setSelectedPeopleIds([]);
    setSelectedPersonCandidateId(null);
    setPeopleSearchQuery("");
    setSelectedAlbumForFilter(null);
    setSelectedEventId(null);
    setSelectedCollectionId(null);
    setPlaceQuery("");
    setProvenanceQuery("");
  }

  async function handleBatchVisibility(action: "demote" | "restore"): Promise<void> {
    if (selectedShaList.length === 0) {
      return;
    }

    setIsRunningBatchAction(true);
    setBatchMessage(null);

    try {
      const response = await batchUpdatePhotoVisibility(selectedShaList, action);
      setBatchMessage(
        `${response.updated_count} updated, ${response.noop_count} unchanged, ${response.failed_count} failed (${action}).`
      );
      setSelectedAssets(new Set());
      await reloadFromStart();
    } catch (error) {
      const message = error instanceof Error && error.message ? error.message : `Failed to ${action} assets.`;
      setErrorMessage(message);
    } finally {
      setIsRunningBatchAction(false);
    }
  }

  async function handleBatchAddToAlbum(): Promise<void> {
    if (selectedShaList.length === 0 || selectedAlbumId === null) {
      return;
    }

    setIsRunningBatchAction(true);
    setBatchMessage(null);

    try {
      const response = await batchAddPhotosToAlbum(selectedAlbumId, selectedShaList);
      setBatchMessage(
        `${response.album_name}: ${response.added_count} added, ${response.already_in_album_count} already in album, ${response.failed_count} failed.`
      );
      setSelectedAssets(new Set());
      const albumsResponse = await getAlbums();
      setAlbums(albumsResponse.items);
    } catch (error) {
      const message = error instanceof Error && error.message ? error.message : "Failed to add selected assets to album.";
      setErrorMessage(message);
    } finally {
      setIsRunningBatchAction(false);
    }
  }

  async function handleBatchAddToCollection(): Promise<void> {
    if (selectedShaList.length === 0 || selectedCollectionId === null) {
      return;
    }

    setIsRunningBatchAction(true);
    setBatchMessage(null);

    try {
      const response = await addAssetsToCollection(selectedCollectionId, selectedShaList);
      const collectionName = selectedCollection?.name ?? `Collection #${selectedCollectionId}`;
      setBatchMessage(
        `${collectionName}: requested ${response.requested_count}, added ${response.added_count}, already present ${response.already_present_count}, failed ${response.failed_count}.`
      );
      setSelectedAssets(new Set());
      setIsCollectionConfirmOpen(false);
      await loadCollectionsForBatch(selectedCollectionId);
    } catch (error) {
      const message = error instanceof Error && error.message ? error.message : "Failed to add selected assets to collection.";
      setErrorMessage(message);
    } finally {
      setIsRunningBatchAction(false);
    }
  }

  async function handleBatchCreateAlbum(): Promise<void> {
    if (selectedShaList.length === 0) {
      return;
    }
    const albumName = window.prompt("New album name");
    if (!albumName || !albumName.trim()) {
      return;
    }

    setIsRunningBatchAction(true);
    setBatchMessage(null);

    try {
      const response = await batchCreateAlbumFromPhotos(albumName.trim(), null, selectedShaList);
      setBatchMessage(
        `${response.album_name} created: ${response.added_count} added, ${response.already_in_album_count} already in album, ${response.failed_count} failed.`
      );
      setSelectedAssets(new Set());
      const albumsResponse = await getAlbums();
      setAlbums(albumsResponse.items);
      setSelectedAlbumId(response.album_id);
    } catch (error) {
      const message = error instanceof Error && error.message ? error.message : "Failed to create album from selection.";
      setErrorMessage(message);
    } finally {
      setIsRunningBatchAction(false);
    }
  }

  const presentationItems = useMemo<PhotoSummary[]>(
    () =>
      items.map((item) => ({
        asset_sha256: item.asset_sha256,
        filename: item.filename,
        image_url: item.image_url,
        display_url: item.display_url,
        original_url: item.original_url,
        has_display_preview: item.has_display_preview,
        display_source: item.display_source,
        captured_at: item.captured_at,
        capture_time_trust: item.capture_time_trust,
        face_count: item.face_count,
        has_live_photo_motion_companion: item.has_live_photo_motion_companion,
        is_live_photo_motion_companion: item.is_live_photo_motion_companion,
        live_photo_still_asset_sha256: item.live_photo_still_asset_sha256,
      })),
    [items]
  );

  function handlePresentationFaceAssignmentsChanged(): void {
    setPresentationHasPendingRefresh(true);
    onFaceAssignmentsChanged?.();
  }

  async function handleClosePresentation(): Promise<void> {
    setPresentationStartIndex(null);
    if (!presentationHasPendingRefresh) {
      return;
    }
    setPresentationHasPendingRefresh(false);
    await reloadFromStart();
  }

  return (
    <div className={styles.container}>
      <div className={styles.toolbar}>
        <div className={styles.searchRow}>
          <input
            type="search"
            value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            placeholder="Search photos... e.g. 2023, March, camera:Canon, IMG_5653"
            className={styles.searchInput}
          />
        </div>

        {(year || month || camera || undated) && (
          <div className={styles.chipRow}>
            {year && (
              <span className={styles.chip}>
                Year: {year}
                <button type="button" className={styles.chipRemove} onClick={removeYearChip} aria-label="Remove year filter">×</button>
              </span>
            )}
            {month && (
              <span className={styles.chip}>
                Month: {MONTH_NUM_TO_NAME[month] ?? month}
                <button type="button" className={styles.chipRemove} onClick={removeMonthChip} aria-label="Remove month filter">×</button>
              </span>
            )}
            {camera && (
              <span className={styles.chip}>
                Camera: {camera}
                <button type="button" className={styles.chipRemove} onClick={removeCameraChip} aria-label="Remove camera filter">×</button>
              </span>
            )}
            {undated && (
              <span className={styles.chip}>
                Undated
                <button type="button" className={styles.chipRemove} onClick={removeUndatedFilter} aria-label="Remove undated filter">×</button>
              </span>
            )}
          </div>
        )}

        <div className={styles.fieldRow}>
          <label className={styles.fieldLabel}>
            Year
            <select value={year} onChange={(event) => handleYearDropdownChange(event.target.value)} className={styles.select}>
              <option value="">All</option>
              {yearOptions.map((value) => (
                <option key={value} value={value}>{value}</option>
              ))}
            </select>
          </label>

          <label className={styles.fieldLabel}>
            Month
            <select value={month} onChange={(event) => handleMonthDropdownChange(event.target.value)} className={styles.select} disabled={!year}>
              <option value="">All</option>
              {monthOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>

          <label className={styles.fieldLabel}>
            Visibility
            <select
              value={visibilityFilter}
              onChange={(event) => setVisibilityFilter(event.target.value as "visible" | "demoted" | "all")}
              className={styles.select}
            >
              <option value="visible">Visible</option>
              <option value="demoted">Demoted</option>
              <option value="all">All</option>
            </select>
          </label>

          <label className={styles.fieldLabel}>
            Media Type
            <select
              value={mediaTypeFilter}
              onChange={(event) => setMediaTypeFilter(event.target.value as "all" | "photos" | "videos")}
              className={styles.select}
            >
              <option value="all">All</option>
              <option value="photos">Photos</option>
              <option value="videos">Videos</option>
            </select>
          </label>

          <label className={styles.fieldLabel}>
            Collection
            <select
              value={selectedCollectionId ?? ""}
              onChange={(event) => setSelectedCollectionId(event.target.value ? Number(event.target.value) : null)}
              className={styles.select}
            >
              <option value="">All collections</option>
              {collections.map((collection) => (
                <option key={collection.collection_id} value={collection.collection_id}>{collection.name}</option>
              ))}
            </select>
          </label>

          <label className={styles.fieldLabel}>
            Album
            <select
              value={selectedAlbumForFilter ?? ""}
              onChange={(event) => setSelectedAlbumForFilter(event.target.value ? Number(event.target.value) : null)}
              className={styles.select}
            >
              <option value="">All albums</option>
              {albums.map((album) => (
                <option key={album.album_id} value={album.album_id}>{album.name}</option>
              ))}
            </select>
          </label>

          <label className={styles.fieldLabel}>
            Event
            <select
              value={selectedEventId ?? ""}
              onChange={(event) => setSelectedEventId(event.target.value ? Number(event.target.value) : null)}
              className={styles.select}
            >
              <option value="">All events</option>
              {events.map((eventItem) => (
                <option key={eventItem.event_id} value={eventItem.event_id}>
                  {eventItem.label?.trim() || `Event #${eventItem.event_id}`}
                </option>
              ))}
            </select>
          </label>

        </div>

        <div className={styles.fieldRow}>
          <label className={styles.fieldLabelWide}>
            <span className={styles.inputHint}>Type a name, then click Add from Matching people.</span>
            People (select by name)
            <input
              type="text"
              value={peopleSearchQuery}
              onChange={(event) => setPeopleSearchQuery(event.target.value)}
              placeholder="Filter people by name"
              className={styles.input}
            />
          </label>

          <label className={styles.fieldLabelWide}>
            Matching people
            <div className={styles.inlineControlRow}>
              <select
                value={selectedPersonCandidateId ?? ""}
                onChange={(event) => setSelectedPersonCandidateId(event.target.value ? Number(event.target.value) : null)}
                className={styles.select}
              >
                <option value="">Select person</option>
                {filteredPeopleOptions.map((person) => (
                  <option key={person.person_id} value={person.person_id}>{person.display_name}</option>
                ))}
              </select>
              <button type="button" className={styles.actionButton} onClick={addSelectedPerson} disabled={selectedPersonCandidateId === null}>
                Add
              </button>
            </div>
          </label>

          <label className={styles.fieldLabelWide}>
            Place contains
            <input
              type="text"
              value={placeQuery}
              onChange={(event) => setPlaceQuery(event.target.value)}
              placeholder="e.g., San Francisco, USA"
              className={styles.input}
            />
          </label>

          <label className={styles.fieldLabelWide}>
            Source / Folder contains
            <input
              type="text"
              value={provenanceQuery}
              onChange={(event) => setProvenanceQuery(event.target.value)}
              placeholder="e.g., iCloud, 2023/Vacation"
              className={styles.input}
            />
          </label>

          <button type="button" className={styles.actionButton} onClick={clearStructuredFilters}>
            Clear structured filters
          </button>
        </div>

        {selectedPeople.length > 0 ? (
          <div className={styles.chipRow}>
            {selectedPeople.map((person) => (
              <span key={person.person_id} className={styles.chip}>
                People: {person.display_name}
                <button
                  type="button"
                  className={styles.chipRemove}
                  onClick={() => removeSelectedPerson(person.person_id)}
                  aria-label={`Remove ${person.display_name} filter`}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        ) : null}

        <div className={styles.fieldRow}>

          <label className={styles.checkboxLabel}>
            <input type="checkbox" checked={showLivePhotoMotionClips} onChange={(event) => setShowLivePhotoMotionClips(event.target.checked)} />
            Show Live Photo motion clips
          </label>

          <label className={styles.checkboxLabel}>
            <input type="checkbox" checked={hasLocation} onChange={(event) => setHasLocation(event.target.checked)} />
            Has Location
          </label>

          <label className={styles.checkboxLabel}>
            <input type="checkbox" checked={hasFaces} onChange={(event) => setHasFaces(event.target.checked)} />
            Has Faces
          </label>

          <label className={styles.checkboxLabel}>
            <input type="checkbox" checked={hasUnassignedFaces} onChange={(event) => setHasUnassignedFaces(event.target.checked)} />
            Unassigned Faces
          </label>

          <label className={styles.checkboxLabel}>
            <input type="checkbox" checked={undated} onChange={(event) => setUndated(event.target.checked)} />
            Undated
          </label>

          <label className={styles.fieldLabel}>
            Face boxes
            <select
              value={faceOverlayMode}
              onChange={(event) => setFaceOverlayMode(event.target.value as FaceOverlayMode)}
              className={styles.select}
            >
              <option value="off">Off</option>
              <option value="hover">Hover</option>
              <option value="always">Always</option>
            </select>
          </label>
        </div>

        <div className={styles.countRow}>{items.length} / {totalCount} photos</div>
      </div>

      {selectedCount > 0 ? (
        <div className={styles.batchToolbar}>
          <div className={styles.batchCount}>{selectedCount} selected</div>
          <div className={styles.batchActions}>
            <button type="button" className={styles.actionButtonDanger} disabled={isRunningBatchAction} onClick={() => void handleBatchVisibility("demote")}>Demote selected</button>
            <button type="button" className={styles.actionButton} disabled={isRunningBatchAction} onClick={() => void handleBatchVisibility("restore")}>Restore selected</button>
            <select
              value={selectedAlbumId ?? ""}
              onChange={(event) => setSelectedAlbumId(event.target.value ? Number(event.target.value) : null)}
              className={styles.select}
              disabled={isRunningBatchAction || albums.length === 0}
            >
              {albums.length === 0 ? <option value="">No albums</option> : albums.map((album) => (
                <option key={album.album_id} value={album.album_id}>{album.name}</option>
              ))}
            </select>
            <button type="button" className={styles.actionButton} disabled={isRunningBatchAction || selectedAlbumId === null} onClick={() => void handleBatchAddToAlbum()}>Add to album</button>
            <button type="button" className={styles.actionButton} disabled={isRunningBatchAction} onClick={() => void handleBatchCreateAlbum()}>Create album from selected</button>
            <button type="button" className={styles.actionButton} disabled={isRunningBatchAction} onClick={handleSelectAllVisible}>Select all visible</button>
            <button type="button" className={styles.actionButton} disabled={isRunningBatchAction} onClick={handleClearSelection}>Clear selection</button>
            <button
              type="button"
              className={styles.actionButton}
              disabled={isRunningBatchAction}
              onClick={() => {
                setCollectionSearchQuery("");
                setErrorMessage(null);
                setIsCollectionConfirmOpen(true);
                void loadCollectionsForBatch();
              }}
            >
              Add selected to Collection
            </button>
            <button type="button" className={styles.actionButton} disabled>Create Collection (12.52)</button>
          </div>
        </div>
      ) : null}

      {isCollectionConfirmOpen ? (
        <div className={styles.batchConfirmPanel}>
          <h3 className={styles.batchConfirmTitle}>Add Selected Assets to Collection</h3>
          <p className={styles.batchConfirmMeta}>Selected assets: {selectedCount}</p>
          <p className={styles.batchConfirmMeta}>This adds assets idempotently. Existing memberships are kept and counted.</p>

          {isLoadingCollections ? (
            <p className={styles.batchConfirmMeta}>Loading collections...</p>
          ) : collections.length === 0 ? (
            <div className={styles.batchConfirmWarning}>
              <p>No Collections exist yet. Create a Collection first.</p>
            </div>
          ) : (
            <>
              <label className={styles.fieldLabelWide}>
                Find Collection
                <input
                  type="text"
                  value={collectionSearchQuery}
                  onChange={(event) => setCollectionSearchQuery(event.target.value)}
                  className={styles.input}
                  placeholder="Search by name"
                />
              </label>
              <div className={styles.collectionPickerList}>
                {filteredCollections.length === 0 ? (
                  <p className={styles.batchConfirmMeta}>No collections match this search.</p>
                ) : (
                  filteredCollections.map((item) => (
                    <button
                      key={item.collection_id}
                      type="button"
                      className={`${styles.collectionPickerItem} ${selectedCollectionId === item.collection_id ? styles.collectionPickerItemActive : ""}`.trim()}
                      onClick={() => setSelectedCollectionId(item.collection_id)}
                    >
                      <span>{item.name}</span>
                      <span>{item.direct_asset_count} direct assets | {item.album_count} albums</span>
                    </button>
                  ))
                )}
              </div>
            </>
          )}

          {selectedAssetLabelSamples.length > 0 ? (
            <div>
              <p className={styles.batchConfirmMeta}>Sample selected assets</p>
              <ul className={styles.batchConfirmSampleList}>
                {selectedAssetLabelSamples.map((label, index) => (
                  <li key={`selected-collection-sample-${index}`}>{label}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {selectedCollection ? (
            <p className={styles.batchConfirmMeta}>Target Collection: {selectedCollection.name}</p>
          ) : null}

          <div className={styles.batchConfirmActions}>
            <button
              type="button"
              className={styles.actionButton}
              disabled={isRunningBatchAction || selectedCollectionId === null || collections.length === 0}
              onClick={() => void handleBatchAddToCollection()}
            >
              {isRunningBatchAction ? "Adding..." : "Confirm Add to Collection"}
            </button>
            <button
              type="button"
              className={styles.actionButton}
              disabled={isRunningBatchAction}
              onClick={() => setIsCollectionConfirmOpen(false)}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}

      {errorMessage ? <div className={styles.errorMessage}>{errorMessage}</div> : null}
      {batchMessage ? <div className={styles.batchMessage}>{batchMessage}</div> : null}

      {selectedOverlayFaceEntry ? (
        <div className={styles.assignmentPanel} ref={assignmentPanelRef}>
          <div className={styles.assignmentPanelHeader}>
            <h3 className={styles.assignmentTitle}>Face assignment</h3>
            <span className={styles.assignmentMeta}>Asset {selectedOverlayFaceEntry.assetSha256.slice(0, 10)}...</span>
          </div>
          <div className={styles.assignmentSummary}>
            <span>Face #{selectedOverlayFaceEntry.face.face_id}</span>
            <span>Cluster #{selectedOverlayFaceEntry.face.cluster_id ?? "-"}</span>
            <span>Current: {getFaceLabel(selectedOverlayFaceEntry.face)}</span>
            <span>
              {selectedOverlayFaceEntry.face.cluster_face_count !== null && selectedOverlayFaceEntry.face.cluster_face_count !== undefined
                ? `${selectedOverlayFaceEntry.face.cluster_face_count} face(s) in cluster`
                : "Cluster face count unavailable"}
            </span>
          </div>
          <div className={styles.assignmentActionsRow}>
            <select
              value={assignmentPersonId ?? ""}
              onChange={(event) => setAssignmentPersonId(event.target.value ? Number(event.target.value) : null)}
              className={styles.select}
              disabled={isAssigningCluster}
            >
              <option value="">Select person</option>
              {people.map((person) => (
                <option key={person.person_id} value={person.person_id}>{person.display_name}</option>
              ))}
            </select>
            <button
              type="button"
              className={styles.actionButton}
              onClick={() => assignmentPersonId !== null && void handleAssignSelectedClusterToPerson(assignmentPersonId)}
              disabled={isAssigningCluster || assignmentPersonId === null}
            >
              {selectedOverlayFaceEntry.face.cluster_id === null
                ? (selectedOverlayFaceEntry.face.person_id ? "Reassign face" : "Assign face")
                : (selectedOverlayFaceEntry.face.person_id ? "Reassign cluster" : "Assign cluster")}
            </button>
            <button
              type="button"
              className={styles.actionButtonDanger}
              onClick={async () => {
                setIsAssigningCluster(true);
                setAssignmentMessage(null);
                setAssignmentErrorMessage(null);
                try {
                  await removeFaceFromCluster(selectedOverlayFaceEntry.face.face_id);
                  setOverlaysByAsset((current) => {
                    const next = { ...current };
                    const overlay = next[selectedOverlayFaceEntry.assetSha256];
                    if (overlay) {
                      next[selectedOverlayFaceEntry.assetSha256] = {
                        ...overlay,
                        faces: overlay.faces.map((face) =>
                          face.face_id === selectedOverlayFaceEntry.face.face_id
                            ? { ...face, cluster_id: null, person_id: null, person_name: null }
                            : face
                        ),
                      };
                    }
                    return next;
                  });
                  setAssignmentMessage("Face unassigned from cluster.");
                } catch (error) {
                  const message = error instanceof Error && error.message ? error.message : "Could not unassign face.";
                  setAssignmentErrorMessage(message);
                } finally {
                  setIsAssigningCluster(false);
                }
              }}
              disabled={isAssigningCluster}
            >
              Remove name
            </button>
          </div>
          <div className={styles.assignmentActionsRow}>
            <input
              type="text"
              value={newPersonName}
              onChange={(event) => setNewPersonName(event.target.value)}
              placeholder="Create new person"
              className={styles.input}
              disabled={isAssigningCluster}
            />
            <button
              type="button"
              className={styles.actionButton}
              onClick={() => void handleCreatePersonAndAssign()}
              disabled={isAssigningCluster || !newPersonName.trim()}
            >
              Create + assign
            </button>
          </div>
          {assignmentMessage ? <div className={styles.batchMessage}>{assignmentMessage}</div> : null}
          {assignmentErrorMessage ? <div className={styles.errorMessage}>{assignmentErrorMessage}</div> : null}
        </div>
      ) : null}

      <div className={styles.grid}>
        {items.map((item, index) => {
          const overlay = overlaysByAsset[item.asset_sha256];
          const naturalDims = imageNaturalDimsByAsset[item.asset_sha256];
          const referenceDims = overlay ? getOverlayReferenceDims(overlay, naturalDims) : null;
          const shouldShowOverlays =
            faceOverlayMode === "always" || (faceOverlayMode === "hover" && hoveredAssetSha256 === item.asset_sha256);

          return (
          <div key={item.asset_sha256} className={`${styles.card} ${selectedAssets.has(item.asset_sha256) ? styles.cardSelected : ""}`.trim()}>
            <div className={styles.cardSelectRow}>
              <label className={styles.cardSelectLabel}>
                <input type="checkbox" checked={selectedAssets.has(item.asset_sha256)} onChange={() => toggleSelectAsset(item.asset_sha256)} />
                Select
              </label>
            </div>

            <div
              className={styles.imageShell}
              onMouseEnter={() => setHoveredAssetSha256(item.asset_sha256)}
              onMouseLeave={() => {
                setHoveredAssetSha256((current) => (current === item.asset_sha256 ? null : current));
                setHoveredFaceKey((current) => (current?.startsWith(`${item.asset_sha256}:`) ? null : current));
              }}
            >
              <button type="button" className={styles.imageButton} onClick={() => setPresentationStartIndex(index)}>
                <img
                  src={resolveApiUrl(item.image_url) ?? ""}
                  alt={item.filename}
                  className={styles.image}
                  loading="lazy"
                  onLoad={(event) => {
                    const img = event.currentTarget;
                    setImageNaturalDimsByAsset((current) => ({
                      ...current,
                      [item.asset_sha256]: { w: img.naturalWidth, h: img.naturalHeight },
                    }));
                  }}
                />
              </button>

              {faceOverlayMode !== "off" && shouldShowOverlays && overlay && referenceDims ? (
                <div className={styles.faceOverlayLayer}>
                  {overlay.faces.map((face) => {
                    const faceKey = `${item.asset_sha256}:${face.face_id}`;
                    const isSelected =
                      selectedOverlayFace?.assetSha256 === item.asset_sha256 &&
                      selectedOverlayFace.faceId === face.face_id;
                    return (
                      <button
                        key={face.face_id}
                        type="button"
                        className={`${styles.faceBox} ${isSelected ? styles.faceBoxActive : ""}`.trim()}
                        style={{
                          left: `${(face.bbox.x / referenceDims.w) * 100}%`,
                          top: `${(face.bbox.y / referenceDims.h) * 100}%`,
                          width: `${(face.bbox.w / referenceDims.w) * 100}%`,
                          height: `${(face.bbox.h / referenceDims.h) * 100}%`,
                        }}
                        onMouseEnter={() => setHoveredFaceKey(faceKey)}
                        onMouseLeave={() => setHoveredFaceKey((current) => (current === faceKey ? null : current))}
                        onClick={(event) => {
                          event.stopPropagation();
                          setSelectedOverlayFace({ assetSha256: item.asset_sha256, faceId: face.face_id });
                          setAssignmentMessage(null);
                          setAssignmentErrorMessage(null);
                        }}
                        title={getFaceLabel(face)}
                        aria-label={getFaceLabel(face)}
                      >
                        {hoveredFaceKey === faceKey ? <span className={styles.faceLabel}>{getFaceLabel(face)}</span> : null}
                      </button>
                    );
                  })}
                </div>
              ) : null}
            </div>

            <div className={styles.filename} title={item.filename}>{item.filename}</div>

            {(item.has_live_photo_motion_companion || item.is_live_photo_motion_companion) && (
              <div className={styles.badgeRow}>
                {item.has_live_photo_motion_companion ? <span className={styles.badgeLivePhoto}>Live Photo</span> : null}
                {item.is_live_photo_motion_companion ? <span className={styles.badgeLivePhotoMotion}>Live Photo Motion</span> : null}
              </div>
            )}

            {item.face_count > 0 && (
              <div className={styles.badgeRow}>
                <span className={styles.badgeNeutral}>{item.face_count} face{item.face_count !== 1 ? "s" : ""}</span>
                <span className={styles.badgePositive}>{item.assigned_face_count} assigned</span>
                <span className={styles.badgeWarning}>{item.unassigned_face_count} unassigned</span>
              </div>
            )}

            <div className={styles.actionRow}>
              <button type="button" className={styles.actionButton} onClick={() => onOpenPhotoDetail(item.asset_sha256)}>Open Detail</button>
              {item.duplicate_group_id !== null ? (
                <button type="button" className={styles.actionButton} onClick={() => onOpenDuplicateGroup(item.duplicate_group_id as number)}>Open Group</button>
              ) : null}
            </div>
          </div>
        );
        })}
      </div>

      {isLoading ? <div className={styles.loadingMessage}>Loading...</div> : null}
      {!isLoading && items.length === 0 && !errorMessage ? <div className={styles.emptyState}>No photos found for current filters.</div> : null}
      <div ref={sentinelRef} className={styles.sentinel} />

      {presentationStartIndex !== null && items.length > 0 ? (
        <PresentationViewer
          items={presentationItems}
          initialIndex={presentationStartIndex}
          onFaceAssignmentsChanged={handlePresentationFaceAssignmentsChanged}
          onClose={() => {
            void handleClosePresentation();
          }}
        />
      ) : null}
    </div>
  );
}


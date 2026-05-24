"use client";

import { useEffect, useMemo, useState } from "react";

import {
  createAlbumFromSourceReviewLevel,
  createCollectionFromSourceReviewLevel,
  createEventFromSourceReviewLevel,
  getPeople,
  getSourceReviewAsset,
  getSourceReviewMatches,
  resolveApiUrl,
} from "@/lib/api";
import type {
  PersonSummary,
  SourceReviewAssetResponse,
  SourceReviewCreateAlbumResponse,
  SourceReviewCreateCollectionResponse,
  SourceReviewCreateEventResponse,
  SourceReviewHierarchyLevel,
  SourceReviewMatchesResponse,
  SourceReviewProvenanceRow,
} from "@/types/ui-api";
import styles from "./source-review-view.module.css";

interface SourceReviewViewProps {
  assetSha256: string | null;
  onOpenPhotoDetail: (assetSha256: string) => void;
  onOpenAlbums: () => void;
  onOpenCollections: () => void;
  onOpenEvents: () => void;
}

const MATCH_LIMIT = 50;

interface DateClue {
  raw: string;
  normalized: string | null;
  isObvious: boolean;
}

interface CandidateCard {
  key: string;
  title: string;
  proposedValue: string;
  detail: string;
}

interface EventDateCandidate {
  startDate: string | null;
  endDate: string | null;
  interpretation: string | null;
  precision: "month_range" | "year_range" | "year_only" | "unknown";
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return "Unknown";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

function normalizeWhitespace(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

function stripLeadingIndex(value: string): string {
  return value
    .replace(/^\s*\(?\d{1,4}\)?\s*(?:[.)]|-\s*|\s+-\s+)\s*/u, "")
    .replace(/^\s*\(?\d{1,2}(?:\.\d{1,2})+\)?\s*-\s*/u, "");
}

function buildSuggestedLabel(rawSegment: string): string {
  const noIndex = stripLeadingIndex(rawSegment);
  const noExtension = noIndex.replace(/\.[a-zA-Z0-9]{2,5}$/u, "");
  const cleaned = normalizeWhitespace(noExtension.replace(/[\-_]+/g, " "));
  return cleaned || normalizeWhitespace(rawSegment);
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function toFourDigitYear(value: string): number | null {
  const trimmed = value.trim().replace(/['\u2019]s$/u, "");
  if (!/^\d{2,4}$/u.test(trimmed)) {
    return null;
  }
  if (trimmed.length === 4) {
    const asInt = Number.parseInt(trimmed, 10);
    return asInt >= 1800 && asInt <= 2100 ? asInt : null;
  }
  const twoDigit = Number.parseInt(trimmed, 10);
  return twoDigit <= 29 ? 2000 + twoDigit : 1900 + twoDigit;
}

function normalizeMonth(monthValue: string): number | null {
  const month = Number.parseInt(monthValue, 10);
  if (Number.isNaN(month) || month < 1 || month > 12) {
    return null;
  }
  return month;
}

function formatMonthLabel(year: number, month: number): string {
  return new Date(Date.UTC(year, month - 1, 1)).toLocaleString(undefined, {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

function lastDayOfMonth(year: number, month: number): number {
  return new Date(Date.UTC(year, month, 0)).getUTCDate();
}

function deriveEventDateCandidate(segmentText: string): EventDateCandidate {
  const raw = normalizeWhitespace(segmentText);
  if (!raw) {
    return { startDate: null, endDate: null, interpretation: null, precision: "unknown" };
  }

  const monthRangeMatch = raw.match(/(\d{1,2})\s*[-/]\s*(\d{2,4})\s*(?:to|-|\u2013|\u2014)\s*(\d{1,2})\s*[-/]\s*(\d{2,4})/iu);
  if (monthRangeMatch) {
    const startMonth = normalizeMonth(monthRangeMatch[1]);
    const startYear = toFourDigitYear(monthRangeMatch[2]);
    const endMonth = normalizeMonth(monthRangeMatch[3]);
    const endYear = toFourDigitYear(monthRangeMatch[4]);
    if (startMonth && startYear && endMonth && endYear) {
      const startDate = `${startYear}-${String(startMonth).padStart(2, "0")}-01`;
      const endDate = `${endYear}-${String(endMonth).padStart(2, "0")}-${String(lastDayOfMonth(endYear, endMonth)).padStart(2, "0")}`;
      return {
        startDate,
        endDate,
        interpretation: `Interpreted as month range: ${formatMonthLabel(startYear, startMonth)} to ${formatMonthLabel(endYear, endMonth)}`,
        precision: "month_range",
      };
    }
  }

  const yearRangeMatch = raw.match(/((?:19|20)\d{2})\s*(?:to|-|\u2013|\u2014)\s*(\d{2,4}|\d{2}['\u2019]s)/iu);
  if (yearRangeMatch) {
    const startYear = toFourDigitYear(yearRangeMatch[1]);
    let endYear: number | null = null;
    if (/\d{2}['\u2019]s$/u.test(yearRangeMatch[2])) {
      const decadeYear = toFourDigitYear(yearRangeMatch[2]);
      endYear = decadeYear ? decadeYear + 9 : null;
    } else {
      endYear = toFourDigitYear(yearRangeMatch[2]);
    }
    if (startYear && endYear) {
      return {
        startDate: `${startYear}-01-01`,
        endDate: `${endYear}-12-31`,
        interpretation: `Interpreted as year range: ${startYear} to ${endYear}`,
        precision: "year_range",
      };
    }
  }

  const singleYearMatch = raw.match(/\b((?:19|20)\d{2})\b/u);
  if (singleYearMatch) {
    const year = Number.parseInt(singleYearMatch[1], 10);
    return {
      startDate: `${year}-01-01`,
      endDate: `${year}-12-31`,
      interpretation: `Interpreted as year: ${year}`,
      precision: "year_only",
    };
  }

  return {
    startDate: null,
    endDate: null,
    interpretation: null,
    precision: "unknown",
  };
}

function detectDateClue(segmentText: string): DateClue | null {
  const raw = normalizeWhitespace(segmentText);
  if (!raw) {
    return null;
  }

  const monthRangeMatch = raw.match(/(\d{1,2})\s*[-/]\s*(\d{2,4})\s*(?:to|-|\u2013|\u2014)\s*(\d{1,2})\s*[-/]\s*(\d{2,4})/iu);
  if (monthRangeMatch) {
    const startMonth = normalizeMonth(monthRangeMatch[1]);
    const startYear = toFourDigitYear(monthRangeMatch[2]);
    const endMonth = normalizeMonth(monthRangeMatch[3]);
    const endYear = toFourDigitYear(monthRangeMatch[4]);
    if (startMonth && startYear && endMonth && endYear) {
      return {
        raw,
        normalized: `${startYear}-${String(startMonth).padStart(2, "0")} to ${endYear}-${String(endMonth).padStart(2, "0")}`,
        isObvious: true,
      };
    }
    return { raw, normalized: null, isObvious: false };
  }

  const yearRangeMatch = raw.match(/((?:19|20)\d{2})\s*(?:to|-|\u2013|\u2014)\s*(\d{2,4}|\d{2}['\u2019]s)/iu);
  if (yearRangeMatch) {
    const startYear = toFourDigitYear(yearRangeMatch[1]);
    let endYear: number | null = null;
    if (/\d{2}['\u2019]s$/u.test(yearRangeMatch[2])) {
      const decade = toFourDigitYear(yearRangeMatch[2]);
      endYear = decade ? decade + 9 : null;
    } else {
      endYear = toFourDigitYear(yearRangeMatch[2]);
    }
    if (startYear && endYear) {
      return {
        raw,
        normalized: `${startYear} to ${endYear}`,
        isObvious: true,
      };
    }
    return { raw, normalized: null, isObvious: false };
  }

  const singleYearMatch = raw.match(/\b((?:19|20)\d{2})\b/u);
  if (singleYearMatch) {
    return {
      raw,
      normalized: singleYearMatch[1],
      isObvious: true,
    };
  }

  return null;
}

function findPeopleClues(segmentText: string, people: PersonSummary[]): string[] {
  const normalizedSegment = normalizeWhitespace(segmentText.toLowerCase());
  if (!normalizedSegment) {
    return [];
  }

  const matchedDisplayNames = new Set<string>();
  for (const person of people) {
    const candidates = [person.display_name, ...person.aliases]
      .map((value) => normalizeWhitespace(value))
      .filter((value) => value.length >= 3);
    for (const candidate of candidates) {
      const pattern = new RegExp(`\\b${escapeRegExp(candidate.toLowerCase()).replace(/\s+/g, "\\s+")}\\b`, "u");
      if (pattern.test(normalizedSegment)) {
        matchedDisplayNames.add(person.display_name);
        break;
      }
    }
  }

  return [...matchedDisplayNames].sort((left, right) => left.localeCompare(right));
}

function buildCandidateCards(params: {
  selectedSegmentText: string;
  selectedPrefix: string | null;
  hierarchyMode: "relative" | "full_source_path";
  matchCount: number | null;
  people: PersonSummary[];
}): CandidateCard[] {
  const suggestedLabel = buildSuggestedLabel(params.selectedSegmentText || "Untitled");
  const peopleClues = findPeopleClues(params.selectedSegmentText, params.people);
  const dateClue = detectDateClue(params.selectedSegmentText);
  const targetCountText = params.matchCount === null ? "match count pending" : `${params.matchCount} matching assets`;
  const modeText = params.hierarchyMode === "relative" ? "relative hierarchy" : "full source path hierarchy";
  const selectedPrefixText = params.selectedPrefix ?? "(level not selected)";

  const dateDetail = !dateClue
    ? "No obvious date format detected from this segment."
    : dateClue.normalized
      ? `Raw: ${dateClue.raw} | Interpreted: ${dateClue.normalized}`
      : `Raw: ${dateClue.raw}`;

  const personDetail = peopleClues.length > 0
    ? `Matched existing people/aliases: ${peopleClues.join(", ")}`
    : "No conservative person-name match found in existing People aliases.";

  return [
    {
      key: "collection",
      title: "Could become Collection",
      proposedValue: "Broad top-level grouping from this provenance level.",
      detail: `${targetCountText} would be a candidate top-level grouping from ${modeText}.`,
    },
    {
      key: "album",
      title: "Could become Album",
      proposedValue: suggestedLabel,
      detail: `Preview based on selected prefix: ${selectedPrefixText}`,
    },
    {
      key: "event",
      title: "Could become Event",
      proposedValue: suggestedLabel,
      detail: dateDetail,
    },
    {
      key: "person",
      title: "Could suggest Person Clue",
      proposedValue: peopleClues.length > 0 ? peopleClues.join(", ") : suggestedLabel,
      detail: personDetail,
    },
    {
      key: "date",
      title: "Could suggest Date Clue",
      proposedValue: dateClue?.normalized ?? dateClue?.raw ?? suggestedLabel,
      detail: dateDetail,
    },
    {
      key: "place",
      title: "Could suggest Place Clue",
      proposedValue: suggestedLabel,
      detail: "Preview only. Place mapping requires manual review against Places entities.",
    },
    {
      key: "tag",
      title: "Could suggest Tag/Title",
      proposedValue: suggestedLabel,
      detail: "Light cleanup applied; raw segment remains visible for confidence checks.",
    },
    {
      key: "review",
      title: "Could mark as Reviewed",
      proposedValue: targetCountText,
      detail: "Preview only. No review state changes are written in this milestone.",
    },
    {
      key: "ignore",
      title: "Could ignore this level",
      proposedValue: selectedPrefixText,
      detail: "Preview only. Ignore behavior is intentionally disabled in this milestone.",
    },
    {
      key: "semantic-root",
      title: "Could become Semantic Root",
      proposedValue: suggestedLabel,
      detail: "Preview only / Coming later. No source_root_path mutation and no persistence.",
    },
  ];
}

export function SourceReviewView({ assetSha256, onOpenPhotoDetail, onOpenAlbums, onOpenCollections, onOpenEvents }: SourceReviewViewProps) {
  const [assetResponse, setAssetResponse] = useState<SourceReviewAssetResponse | null>(null);
  const [hierarchyMode, setHierarchyMode] = useState<"relative" | "full_source_path">("relative");
  const [people, setPeople] = useState<PersonSummary[]>([]);
  const [selectedProvenanceId, setSelectedProvenanceId] = useState<number | null>(null);
  const [selectedLevelIndex, setSelectedLevelIndex] = useState<number | null>(null);
  const [matches, setMatches] = useState<SourceReviewMatchesResponse | null>(null);
  const [isLoadingAsset, setIsLoadingAsset] = useState(false);
  const [isLoadingMatches, setIsLoadingMatches] = useState(false);
  const [assetErrorMessage, setAssetErrorMessage] = useState<string | null>(null);
  const [matchesErrorMessage, setMatchesErrorMessage] = useState<string | null>(null);
  const [isAlbumDialogOpen, setIsAlbumDialogOpen] = useState(false);
  const [albumNameInput, setAlbumNameInput] = useState("");
  const [isCollectionDialogOpen, setIsCollectionDialogOpen] = useState(false);
  const [collectionNameInput, setCollectionNameInput] = useState("");
  const [collectionSingleFileConfirmChecked, setCollectionSingleFileConfirmChecked] = useState(false);
  const [isSubmittingCollection, setIsSubmittingCollection] = useState(false);
  const [collectionActionError, setCollectionActionError] = useState<string | null>(null);
  const [collectionActionResult, setCollectionActionResult] = useState<SourceReviewCreateCollectionResponse | null>(null);
  const [singleFileConfirmChecked, setSingleFileConfirmChecked] = useState(false);
  const [isSubmittingAlbum, setIsSubmittingAlbum] = useState(false);
  const [albumActionError, setAlbumActionError] = useState<string | null>(null);
  const [albumActionResult, setAlbumActionResult] = useState<SourceReviewCreateAlbumResponse | null>(null);
  const [albumNameConflictResult, setAlbumNameConflictResult] = useState<SourceReviewCreateAlbumResponse | null>(null);
  const [isEventDialogOpen, setIsEventDialogOpen] = useState(false);
  const [eventLabelInput, setEventLabelInput] = useState("");
  const [eventStartDateInput, setEventStartDateInput] = useState("");
  const [eventEndDateInput, setEventEndDateInput] = useState("");
  const [eventPrecisionNote, setEventPrecisionNote] = useState<string | null>(null);
  const [eventSingleFileConfirmChecked, setEventSingleFileConfirmChecked] = useState(false);
  const [isSubmittingEvent, setIsSubmittingEvent] = useState(false);
  const [eventActionError, setEventActionError] = useState<string | null>(null);
  const [eventActionResult, setEventActionResult] = useState<SourceReviewCreateEventResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    void getPeople()
      .then((response) => {
        if (!cancelled) {
          setPeople(response.items);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setPeople([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setAssetResponse(null);
    setSelectedProvenanceId(null);
    setSelectedLevelIndex(null);
    setHierarchyMode("relative");
    setMatches(null);
    setAssetErrorMessage(null);
    setMatchesErrorMessage(null);

    if (!assetSha256) {
      return;
    }

    let cancelled = false;
    setIsLoadingAsset(true);

    void getSourceReviewAsset(assetSha256)
      .then((payload) => {
        if (cancelled) {
          return;
        }
        setAssetResponse(payload);
        const initialProvenanceId = payload.selected_provenance_id;
        setSelectedProvenanceId(initialProvenanceId);
        const selectedRow = payload.provenance_rows.find((row) => row.provenance_id === initialProvenanceId);
        if (selectedRow && selectedRow.hierarchy_levels.length > 0) {
          setSelectedLevelIndex(0);
        }
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        setAssetErrorMessage(getErrorMessage(error, "Failed to load Source Review details."));
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoadingAsset(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [assetSha256]);

  const selectedProvenanceRow: SourceReviewProvenanceRow | null = useMemo(() => {
    if (!assetResponse || selectedProvenanceId === null) {
      return null;
    }
    return assetResponse.provenance_rows.find((row) => row.provenance_id === selectedProvenanceId) ?? null;
  }, [assetResponse, selectedProvenanceId]);

  const hierarchyLevels = useMemo(() => {
    if (!selectedProvenanceRow) {
      return [];
    }
    return hierarchyMode === "full_source_path"
      ? selectedProvenanceRow.hierarchy_levels_full
      : selectedProvenanceRow.hierarchy_levels_relative;
  }, [selectedProvenanceRow, hierarchyMode]);

  const selectedHierarchyLevel: SourceReviewHierarchyLevel | null = useMemo(() => {
    if (selectedLevelIndex === null) {
      return null;
    }
    return hierarchyLevels.find((level) => level.level_index === selectedLevelIndex) ?? null;
  }, [hierarchyLevels, selectedLevelIndex]);

  const candidateCards = useMemo(() => {
    if (!selectedHierarchyLevel) {
      return [];
    }
    return buildCandidateCards({
      selectedSegmentText: selectedHierarchyLevel.segment_text,
      selectedPrefix: matches?.selected_prefix ?? null,
      hierarchyMode,
      matchCount: matches?.total_count ?? null,
      people,
    });
  }, [selectedHierarchyLevel, matches, hierarchyMode, people]);

  const proposedAlbumName = useMemo(() => {
    if (!selectedHierarchyLevel) {
      return "";
    }
    return buildSuggestedLabel(selectedHierarchyLevel.segment_text || "Untitled");
  }, [selectedHierarchyLevel]);

  const proposedCollectionName = useMemo(() => {
    if (!selectedHierarchyLevel) {
      return "";
    }
    return buildSuggestedLabel(selectedHierarchyLevel.segment_text || "Untitled");
  }, [selectedHierarchyLevel]);

  const proposedEventName = useMemo(() => {
    if (!selectedHierarchyLevel) {
      return "";
    }
    return buildSuggestedLabel(selectedHierarchyLevel.segment_text || "Untitled");
  }, [selectedHierarchyLevel]);

  const parsedEventDateCandidate = useMemo(() => {
    if (!selectedHierarchyLevel) {
      return { startDate: null, endDate: null, interpretation: null, precision: "unknown" as const };
    }
    return deriveEventDateCandidate(selectedHierarchyLevel.segment_text);
  }, [selectedHierarchyLevel]);

  const canCreateAlbum = Boolean(matches && matches.total_count > 0 && selectedProvenanceId !== null && selectedLevelIndex !== null);
  const canCreateCollection = canCreateAlbum;
  const canCreateEvent = canCreateAlbum;

  const requiresSingleFileConfirm = Boolean(selectedHierarchyLevel?.is_filename);

  const confirmActionDisabled =
    !canCreateAlbum ||
    !albumNameInput.trim() ||
    isSubmittingAlbum ||
    (requiresSingleFileConfirm && !singleFileConfirmChecked);

  const confirmCollectionActionDisabled =
    !canCreateCollection ||
    !collectionNameInput.trim() ||
    isSubmittingCollection ||
    (requiresSingleFileConfirm && !collectionSingleFileConfirmChecked);

  const confirmEventActionDisabled =
    !canCreateEvent ||
    !eventLabelInput.trim() ||
    isSubmittingEvent ||
    (requiresSingleFileConfirm && !eventSingleFileConfirmChecked);

  async function submitCreateAlbum(conflictMode: "ask" | "use_existing") {
    if (!matches || selectedProvenanceId === null || selectedLevelIndex === null) {
      return;
    }

    setIsSubmittingAlbum(true);
    setAlbumActionError(null);

    try {
      const response = await createAlbumFromSourceReviewLevel({
        provenance_id: selectedProvenanceId,
        level_index: selectedLevelIndex,
        hierarchy_mode: hierarchyMode,
        album_name: albumNameInput,
        conflict_mode: conflictMode,
      });

      if (response.outcome === "name_conflict") {
        setAlbumNameConflictResult(response);
        setAlbumActionResult(null);
        return;
      }

      setAlbumNameConflictResult(null);
      setAlbumActionResult(response);
    } catch (error: unknown) {
      setAlbumActionError(getErrorMessage(error, "Failed to create album from selected provenance level."));
    } finally {
      setIsSubmittingAlbum(false);
    }
  }

  async function submitCreateCollection() {
    if (!matches || selectedProvenanceId === null || selectedLevelIndex === null) {
      return;
    }

    setIsSubmittingCollection(true);
    setCollectionActionError(null);

    try {
      const response = await createCollectionFromSourceReviewLevel({
        provenance_id: selectedProvenanceId,
        level_index: selectedLevelIndex,
        hierarchy_mode: hierarchyMode,
        collection_name: collectionNameInput,
      });
      setCollectionActionResult(response);
    } catch (error: unknown) {
      setCollectionActionError(getErrorMessage(error, "Failed to create collection from selected provenance level."));
    } finally {
      setIsSubmittingCollection(false);
    }
  }

  async function submitCreateEvent() {
    if (!matches || selectedProvenanceId === null || selectedLevelIndex === null) {
      return;
    }

    setIsSubmittingEvent(true);
    setEventActionError(null);

    try {
      const response = await createEventFromSourceReviewLevel({
        provenance_id: selectedProvenanceId,
        level_index: selectedLevelIndex,
        hierarchy_mode: hierarchyMode,
        event_label: eventLabelInput,
        start_at: eventStartDateInput.trim() ? eventStartDateInput : null,
        end_at: eventEndDateInput.trim() ? eventEndDateInput : null,
        existing_event_policy: "skip_existing",
      });
      setEventActionResult(response);
    } catch (error: unknown) {
      setEventActionError(getErrorMessage(error, "Failed to create event from selected provenance level."));
    } finally {
      setIsSubmittingEvent(false);
    }
  }

  useEffect(() => {
    setMatches(null);
    setMatchesErrorMessage(null);

    if (selectedProvenanceId === null || selectedLevelIndex === null) {
      return;
    }

    let cancelled = false;
    setIsLoadingMatches(true);
    void getSourceReviewMatches({
      provenanceId: selectedProvenanceId,
      levelIndex: selectedLevelIndex,
      hierarchyMode,
      limit: MATCH_LIMIT,
    })
      .then((payload) => {
        if (cancelled) {
          return;
        }
        setMatches(payload);
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        setMatchesErrorMessage(getErrorMessage(error, "Failed to load matching assets for this level."));
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoadingMatches(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedProvenanceId, selectedLevelIndex, hierarchyMode]);

  useEffect(() => {
    if (!selectedProvenanceRow) {
      setSelectedLevelIndex(null);
      return;
    }
    if (
      selectedLevelIndex === null ||
      selectedLevelIndex < 0 ||
      selectedLevelIndex >= hierarchyLevels.length
    ) {
      setSelectedLevelIndex(hierarchyLevels.length > 0 ? 0 : null);
    }
  }, [hierarchyLevels, selectedLevelIndex, selectedProvenanceRow]);

  useEffect(() => {
    setIsCollectionDialogOpen(false);
    setCollectionActionError(null);
    setCollectionActionResult(null);
    setCollectionSingleFileConfirmChecked(false);
    setCollectionNameInput(proposedCollectionName);
    setIsAlbumDialogOpen(false);
    setAlbumActionError(null);
    setAlbumActionResult(null);
    setAlbumNameConflictResult(null);
    setSingleFileConfirmChecked(false);
    setAlbumNameInput(proposedAlbumName);
    setIsEventDialogOpen(false);
    setEventActionError(null);
    setEventActionResult(null);
    setEventSingleFileConfirmChecked(false);
    setEventLabelInput(proposedEventName);
    setEventStartDateInput(parsedEventDateCandidate.startDate ?? "");
    setEventEndDateInput(parsedEventDateCandidate.endDate ?? "");
    setEventPrecisionNote(parsedEventDateCandidate.interpretation);
  }, [
    parsedEventDateCandidate.endDate,
    parsedEventDateCandidate.interpretation,
    parsedEventDateCandidate.startDate,
    proposedAlbumName,
    proposedCollectionName,
    proposedEventName,
    selectedProvenanceId,
    selectedLevelIndex,
    hierarchyMode,
  ]);

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <h2 className={styles.title}>Source Review</h2>
        <p className={styles.subtitle}>Provenance workspace for hierarchy/prefix exploration with collection, album, and event creation enabled for selected levels.</p>
      </header>

      {!assetSha256 ? (
        <div className={styles.panel}>
          <p className={styles.status}>Open Photo Detail and choose "Open Source Review" to begin.</p>
        </div>
      ) : isLoadingAsset ? (
        <div className={styles.panel}>
          <p className={styles.status}>Loading Source Review data…</p>
        </div>
      ) : assetErrorMessage ? (
        <div className={styles.panel}>
          <p className={styles.error}>{assetErrorMessage}</p>
        </div>
      ) : !assetResponse ? (
        <div className={styles.panel}>
          <p className={styles.status}>No Source Review data available.</p>
        </div>
      ) : (
        <>
          <section className={styles.assetSummary}>
            <div className={styles.assetPreviewWrap}>
              {resolveApiUrl(assetResponse.asset.image_url) ? (
                <img
                  src={resolveApiUrl(assetResponse.asset.image_url) ?? ""}
                  alt={assetResponse.asset.filename}
                  className={styles.assetPreview}
                />
              ) : (
                <div className={styles.assetPreviewPlaceholder}>No preview</div>
              )}
            </div>
            <div className={styles.assetMeta}>
              <h3 className={styles.assetFilename}>{assetResponse.asset.filename}</h3>
              <p className={styles.assetLine}>Asset SHA: {assetResponse.asset.asset_sha_short}</p>
              <p className={styles.assetLine}>Captured: {formatDateTime(assetResponse.asset.captured_at)}</p>
              <p className={styles.assetLine}>Provenance rows: {assetResponse.asset.provenance_count}</p>
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() => onOpenPhotoDetail(assetResponse.asset.asset_sha256)}
              >
                Back to Photo Detail
              </button>
            </div>
          </section>

          <section className={styles.workspace}>
            <div className={styles.panel}>
              <h3 className={styles.panelTitle}>Provenance Rows</h3>
              {assetResponse.provenance_rows.length === 0 ? (
                <p className={styles.status}>No provenance found for this asset.</p>
              ) : (
                <ul className={styles.list}>
                  {assetResponse.provenance_rows.map((row) => (
                    <li key={row.provenance_id}>
                      <button
                        type="button"
                        className={`${styles.rowButton} ${selectedProvenanceId === row.provenance_id ? styles.rowButtonActive : ""}`.trim()}
                        onClick={() => {
                          setSelectedProvenanceId(row.provenance_id);
                          setSelectedLevelIndex(0);
                        }}
                      >
                        <span className={styles.rowPrimary}>Source: {row.source_label ?? "Unknown"} ({row.source_type ?? "unknown"})</span>
                        <span className={styles.rowSubtle}>{row.source_relative_path ?? "Relative path unavailable"}</span>
                        <span className={styles.rowSubtle}>{row.source_path}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className={styles.panel}>
              <h3 className={styles.panelTitle}>Hierarchy Levels</h3>
              <div className={styles.modeSwitch}>
                <button
                  type="button"
                  className={`${styles.modeButton} ${hierarchyMode === "relative" ? styles.modeButtonActive : ""}`.trim()}
                  onClick={() => setHierarchyMode("relative")}
                >
                  Relative hierarchy
                </button>
                <button
                  type="button"
                  className={`${styles.modeButton} ${hierarchyMode === "full_source_path" ? styles.modeButtonActive : ""}`.trim()}
                  onClick={() => setHierarchyMode("full_source_path")}
                >
                  Full path hierarchy
                </button>
              </div>
              {!selectedProvenanceRow ? (
                <p className={styles.status}>Select a provenance row to inspect hierarchy levels.</p>
              ) : hierarchyLevels.length === 0 ? (
                <p className={styles.status}>No hierarchy segments found for this provenance row.</p>
              ) : (
                <>
                  {hierarchyMode === "relative" && selectedProvenanceRow.fallback_reason ? (
                    <p className={styles.notice}>{selectedProvenanceRow.fallback_reason}</p>
                  ) : null}
                  {hierarchyMode === "full_source_path" ? (
                    <p className={styles.notice}>Showing full source path levels, including parent/root folders.</p>
                  ) : null}
                  <ul className={styles.list}>
                    {hierarchyLevels.map((level) => (
                      <li key={level.level_index}>
                        <button
                          type="button"
                          className={`${styles.rowButton} ${selectedLevelIndex === level.level_index ? styles.rowButtonActive : ""}`.trim()}
                          onClick={() => setSelectedLevelIndex(level.level_index)}
                        >
                          <span className={styles.rowPrimary}>L{level.level_number}: {level.segment_text}</span>
                          <span className={styles.rowSubtle}>{level.display_prefix}</span>
                          {level.is_technical_hint ? <span className={styles.technicalHint}>technical/source path</span> : null}
                        </button>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>

            <div className={styles.panel}>
              <h3 className={styles.panelTitle}>Matching Assets</h3>
              {isLoadingMatches ? (
                <p className={styles.status}>Loading matching assets…</p>
              ) : matchesErrorMessage ? (
                <p className={styles.error}>{matchesErrorMessage}</p>
              ) : !matches ? (
                <p className={styles.status}>Select a hierarchy level to load matching assets.</p>
              ) : matches.total_count === 0 ? (
                <p className={styles.status}>No matching assets under this level.</p>
              ) : (
                <>
                  <p className={styles.matchSummary}>
                    {matches.is_limited
                      ? `Showing first ${matches.limit} of ${matches.total_count} matching assets`
                      : `Showing ${matches.total_count} matching assets`}
                  </p>
                  <ul className={styles.matchGrid}>
                    {matches.items.map((item) => (
                      <li key={item.asset_sha256} className={styles.matchCard}>
                        <button
                          type="button"
                          className={styles.matchButton}
                          onClick={() => onOpenPhotoDetail(item.asset_sha256)}
                          title="Open in Photo Detail"
                        >
                          {resolveApiUrl(item.image_url) ? (
                            <img
                              src={resolveApiUrl(item.image_url) ?? ""}
                              alt={item.filename}
                              className={styles.matchThumb}
                            />
                          ) : (
                            <div className={styles.matchThumbPlaceholder}>No preview</div>
                          )}
                          <span className={styles.matchFilename}>{item.filename}</span>
                          <span className={styles.rowSubtle}>{formatDateTime(item.captured_at)}</span>
                          {item.matched_path_fragment ? (
                            <span className={styles.rowSubtle}>{item.matched_path_fragment}</span>
                          ) : null}
                        </button>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          </section>

          <section className={styles.panel}>
            <h3 className={styles.panelTitle}>Candidate Actions</h3>
            {!selectedHierarchyLevel ? (
              <p className={styles.status}>Select a hierarchy level to preview candidate actions.</p>
            ) : (
              <>
                <p className={styles.noticeStrong}>Collection, Album, and Event creation are active in this milestone. Other actions remain preview-only.</p>
                <p className={styles.notice}>
                  Raw segment: <span className={styles.segmentRaw}>{selectedHierarchyLevel.segment_text}</span>
                </p>
                <div className={styles.candidateGrid}>
                  {candidateCards.map((card) => (
                    <article key={card.key} className={styles.candidateCard}>
                      <p className={styles.candidateTitle}>{card.title}</p>
                      <p className={styles.candidateValue}>{card.proposedValue}</p>
                      <p className={styles.candidateDetail}>{card.detail}</p>
                      {card.key === "collection" ? (
                        <button
                          type="button"
                          className={styles.actionButton}
                          disabled={!canCreateCollection || isLoadingMatches}
                          onClick={() => {
                            setCollectionNameInput(proposedCollectionName);
                            setCollectionSingleFileConfirmChecked(false);
                            setCollectionActionError(null);
                            setCollectionActionResult(null);
                            setIsCollectionDialogOpen(true);
                          }}
                        >
                          Create Collection
                        </button>
                      ) : card.key === "album" ? (
                        <button
                          type="button"
                          className={styles.actionButton}
                          disabled={!canCreateAlbum || isLoadingMatches}
                          onClick={() => {
                            setAlbumNameInput(proposedAlbumName);
                            setSingleFileConfirmChecked(false);
                            setAlbumActionError(null);
                            setAlbumActionResult(null);
                            setAlbumNameConflictResult(null);
                            setIsAlbumDialogOpen(true);
                          }}
                        >
                          Create Album
                        </button>
                      ) : card.key === "event" ? (
                        <button
                          type="button"
                          className={styles.actionButton}
                          disabled={!canCreateEvent || isLoadingMatches}
                          onClick={() => {
                            setEventLabelInput(proposedEventName);
                            setEventStartDateInput(parsedEventDateCandidate.startDate ?? "");
                            setEventEndDateInput(parsedEventDateCandidate.endDate ?? "");
                            setEventPrecisionNote(parsedEventDateCandidate.interpretation);
                            setEventSingleFileConfirmChecked(false);
                            setEventActionError(null);
                            setEventActionResult(null);
                            setIsEventDialogOpen(true);
                          }}
                        >
                          Create Event
                        </button>
                      ) : (
                        <button type="button" className={styles.placeholderAction} disabled>
                          Preview only / Coming later
                        </button>
                      )}
                    </article>
                  ))}
                </div>

                {isCollectionDialogOpen ? (
                  <div className={styles.confirmPanel}>
                    <h4 className={styles.confirmTitle}>Create Collection from Selected Provenance Level</h4>
                    <label className={styles.fieldLabel}>
                      Collection name
                      <input
                        type="text"
                        value={collectionNameInput}
                        onChange={(event) => setCollectionNameInput(event.target.value)}
                        className={styles.textInput}
                        maxLength={255}
                      />
                    </label>

                    <ul className={styles.contextList}>
                      <li>Source: {selectedProvenanceRow?.source_label ?? "Unknown"} ({selectedProvenanceRow?.source_type ?? "unknown"})</li>
                      <li>Hierarchy mode: {hierarchyMode}</li>
                      <li>Selected segment: {selectedHierarchyLevel.segment_text}</li>
                      <li>Selected prefix: {matches?.selected_prefix ?? "-"}</li>
                      <li>Matching asset count: {matches?.total_count ?? 0}</li>
                    </ul>

                    {requiresSingleFileConfirm ? (
                      <div className={styles.warningBox}>
                        <p className={styles.warningText}>This level appears to be a single file. The collection may contain only this asset.</p>
                        <label className={styles.checkboxLabel}>
                          <input
                            type="checkbox"
                            checked={collectionSingleFileConfirmChecked}
                            onChange={(event) => setCollectionSingleFileConfirmChecked(event.target.checked)}
                          />
                          I understand this may create a very small collection.
                        </label>
                      </div>
                    ) : null}

                    <p className={styles.notice}>
                      This will create a top-level collection and add matching assets directly to it. No source files, provenance, dates, people, or events will be changed.
                    </p>

                    {matches && matches.items.length > 0 ? (
                      <>
                        <p className={styles.matchSummary}>Sample matching assets</p>
                        <ul className={styles.sampleList}>
                          {matches.items.slice(0, 6).map((item) => (
                            <li key={`collection-sample-${item.asset_sha256}`} className={styles.sampleItem}>
                              {item.filename}
                            </li>
                          ))}
                        </ul>
                      </>
                    ) : null}

                    {collectionActionError ? <p className={styles.error}>{collectionActionError}</p> : null}

                    {collectionActionResult ? (
                      <div className={styles.successBox}>
                        <p className={styles.successText}>Created collection "{collectionActionResult.collection_name}".</p>
                        <p className={styles.status}>
                          Added: {collectionActionResult.added_count} | Already present: {collectionActionResult.already_present_count} | Failed: {collectionActionResult.failed_count}
                        </p>
                        <div className={styles.dialogActions}>
                          <button type="button" className={styles.actionButton} onClick={onOpenCollections}>
                            Open Collections
                          </button>
                          <button
                            type="button"
                            className={styles.secondaryButton}
                            onClick={() => setIsCollectionDialogOpen(false)}
                          >
                            Close
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className={styles.dialogActions}>
                        <button
                          type="button"
                          className={styles.actionButton}
                          disabled={confirmCollectionActionDisabled}
                          onClick={() => void submitCreateCollection()}
                        >
                          {isSubmittingCollection ? "Creating..." : "Confirm Create Collection"}
                        </button>
                        <button
                          type="button"
                          className={styles.secondaryButton}
                          disabled={isSubmittingCollection}
                          onClick={() => setIsCollectionDialogOpen(false)}
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>
                ) : null}

                {isAlbumDialogOpen ? (
                  <div className={styles.confirmPanel}>
                    <h4 className={styles.confirmTitle}>Create Album from Selected Provenance Level</h4>
                    <label className={styles.fieldLabel}>
                      Album name
                      <input
                        type="text"
                        value={albumNameInput}
                        onChange={(event) => setAlbumNameInput(event.target.value)}
                        className={styles.textInput}
                        maxLength={255}
                      />
                    </label>

                    <ul className={styles.contextList}>
                      <li>Source: {selectedProvenanceRow?.source_label ?? "Unknown"} ({selectedProvenanceRow?.source_type ?? "unknown"})</li>
                      <li>Hierarchy mode: {hierarchyMode}</li>
                      <li>Selected segment: {selectedHierarchyLevel.segment_text}</li>
                      <li>Selected prefix: {matches?.selected_prefix ?? "-"}</li>
                      <li>Matching asset count: {matches?.total_count ?? 0}</li>
                    </ul>

                    {requiresSingleFileConfirm ? (
                      <div className={styles.warningBox}>
                        <p className={styles.warningText}>This level appears to be a single file. The album may contain only this asset.</p>
                        <label className={styles.checkboxLabel}>
                          <input
                            type="checkbox"
                            checked={singleFileConfirmChecked}
                            onChange={(event) => setSingleFileConfirmChecked(event.target.checked)}
                          />
                          I understand this may create a very small album.
                        </label>
                      </div>
                    ) : null}

                    <p className={styles.notice}>
                      This will create or use an album and add all matching assets under this prefix. No source files, provenance, dates, people, or events will be changed.
                    </p>

                    {matches && matches.items.length > 0 ? (
                      <>
                        <p className={styles.matchSummary}>Sample matching assets</p>
                        <ul className={styles.sampleList}>
                          {matches.items.slice(0, 6).map((item) => (
                            <li key={`sample-${item.asset_sha256}`} className={styles.sampleItem}>
                              {item.filename}
                            </li>
                          ))}
                        </ul>
                      </>
                    ) : null}

                    {albumNameConflictResult ? (
                      <div className={styles.warningBox}>
                        <p className={styles.warningText}>An album with this name already exists: {albumNameConflictResult.album_name}</p>
                        <div className={styles.dialogActions}>
                          <button
                            type="button"
                            className={styles.actionButton}
                            disabled={isSubmittingAlbum}
                            onClick={() => void submitCreateAlbum("use_existing")}
                          >
                            Use Existing Album and Add Assets
                          </button>
                          <button
                            type="button"
                            className={styles.secondaryButton}
                            disabled={isSubmittingAlbum}
                            onClick={() => setAlbumNameConflictResult(null)}
                          >
                            Enter Different Name
                          </button>
                        </div>
                      </div>
                    ) : null}

                    {albumActionError ? <p className={styles.error}>{albumActionError}</p> : null}

                    {albumActionResult ? (
                      <div className={styles.successBox}>
                        <p className={styles.successText}>
                          {albumActionResult.outcome === "created"
                            ? `Created album "${albumActionResult.album_name}".`
                            : `Used existing album "${albumActionResult.album_name}".`}
                        </p>
                        <p className={styles.status}>
                          Added: {albumActionResult.added_count} | Already present: {albumActionResult.already_present_count} | Failed: {albumActionResult.failed_count}
                        </p>
                        <div className={styles.dialogActions}>
                          <button type="button" className={styles.actionButton} onClick={onOpenAlbums}>
                            Open Albums
                          </button>
                          <button
                            type="button"
                            className={styles.secondaryButton}
                            onClick={() => setIsAlbumDialogOpen(false)}
                          >
                            Close
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className={styles.dialogActions}>
                        <button
                          type="button"
                          className={styles.actionButton}
                          disabled={confirmActionDisabled}
                          onClick={() => void submitCreateAlbum("ask")}
                        >
                          {isSubmittingAlbum ? "Creating..." : "Confirm Create Album"}
                        </button>
                        <button
                          type="button"
                          className={styles.secondaryButton}
                          disabled={isSubmittingAlbum}
                          onClick={() => setIsAlbumDialogOpen(false)}
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>
                ) : null}

                {isEventDialogOpen ? (
                  <div className={styles.confirmPanel}>
                    <h4 className={styles.confirmTitle}>Create Event from Selected Provenance Level</h4>
                    <label className={styles.fieldLabel}>
                      Event label
                      <input
                        type="text"
                        value={eventLabelInput}
                        onChange={(event) => setEventLabelInput(event.target.value)}
                        className={styles.textInput}
                        maxLength={255}
                      />
                    </label>

                    <div className={styles.dateGrid}>
                      <label className={styles.fieldLabel}>
                        Start date
                        <input
                          type="date"
                          value={eventStartDateInput}
                          onChange={(event) => setEventStartDateInput(event.target.value)}
                          className={styles.textInput}
                        />
                      </label>
                      <label className={styles.fieldLabel}>
                        End date
                        <input
                          type="date"
                          value={eventEndDateInput}
                          onChange={(event) => setEventEndDateInput(event.target.value)}
                          className={styles.textInput}
                        />
                      </label>
                    </div>

                    {eventPrecisionNote ? (
                      <p className={styles.noticeStrong}>{eventPrecisionNote}</p>
                    ) : (
                      <p className={styles.notice}>No obvious provenance date clue detected. On confirm, backend will infer from matching asset timestamps when available.</p>
                    )}

                    <ul className={styles.contextList}>
                      <li>Source: {selectedProvenanceRow?.source_label ?? "Unknown"} ({selectedProvenanceRow?.source_type ?? "unknown"})</li>
                      <li>Hierarchy mode: {hierarchyMode}</li>
                      <li>Selected segment: {selectedHierarchyLevel.segment_text}</li>
                      <li>Selected prefix: {matches?.selected_prefix ?? "-"}</li>
                      <li>Matching asset count: {matches?.total_count ?? 0}</li>
                      <li>Existing event policy: skip assets already assigned to another event</li>
                    </ul>

                    {requiresSingleFileConfirm ? (
                      <div className={styles.warningBox}>
                        <p className={styles.warningText}>This level appears to be a single file. This event may contain only this asset.</p>
                        <label className={styles.checkboxLabel}>
                          <input
                            type="checkbox"
                            checked={eventSingleFileConfirmChecked}
                            onChange={(event) => setEventSingleFileConfirmChecked(event.target.checked)}
                          />
                          I understand this may create a very small event.
                        </label>
                      </div>
                    ) : null}

                    <p className={styles.notice}>
                      This will create an event and assign eligible matching assets. No source files, provenance, captured dates, people, places, or tags will be changed.
                    </p>

                    {matches && matches.items.length > 0 ? (
                      <>
                        <p className={styles.matchSummary}>Sample matching assets</p>
                        <ul className={styles.sampleList}>
                          {matches.items.slice(0, 6).map((item) => (
                            <li key={`event-sample-${item.asset_sha256}`} className={styles.sampleItem}>
                              {item.filename}
                            </li>
                          ))}
                        </ul>
                      </>
                    ) : null}

                    {eventActionError ? <p className={styles.error}>{eventActionError}</p> : null}

                    {eventActionResult ? (
                      <div className={styles.successBox}>
                        <p className={styles.successText}>Created event "{eventActionResult.event_label ?? "(unlabeled)"}".</p>
                        <p className={styles.status}>
                          Assigned: {eventActionResult.assigned_count} | Skipped existing event: {eventActionResult.skipped_existing_event_count} | Failed: {eventActionResult.failed_count}
                        </p>
                        <p className={styles.notice}>Date source: {eventActionResult.date_range_source}</p>
                        <div className={styles.dialogActions}>
                          <button type="button" className={styles.actionButton} onClick={onOpenEvents}>
                            Open Events
                          </button>
                          <button
                            type="button"
                            className={styles.secondaryButton}
                            onClick={() => setIsEventDialogOpen(false)}
                          >
                            Close
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className={styles.dialogActions}>
                        <button
                          type="button"
                          className={styles.actionButton}
                          disabled={confirmEventActionDisabled}
                          onClick={() => void submitCreateEvent()}
                        >
                          {isSubmittingEvent ? "Creating..." : "Confirm Create Event"}
                        </button>
                        <button
                          type="button"
                          className={styles.secondaryButton}
                          disabled={isSubmittingEvent}
                          onClick={() => setIsEventDialogOpen(false)}
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>
                ) : null}
              </>
            )}
          </section>

          {selectedProvenanceRow ? (
            <details className={styles.debugPanel}>
              <summary>Debug Details</summary>
              <ul className={styles.debugList}>
                <li>Asset SHA256: {assetResponse.asset.asset_sha256}</li>
                <li>Provenance ID: {selectedProvenanceRow.provenance_id}</li>
                <li>Hierarchy mode: {hierarchyMode}</li>
                <li>Ingestion source ID: {selectedProvenanceRow.ingestion_source_id ?? "-"}</li>
                <li>Ingestion run ID: {selectedProvenanceRow.ingestion_run_id ?? "-"}</li>
                <li>Source root path: {selectedProvenanceRow.source_root_path ?? "-"}</li>
                <li>Source relative path: {selectedProvenanceRow.source_relative_path ?? "-"}</li>
                <li>Full source path: {selectedProvenanceRow.source_path}</li>
                <li>Parse mode used: {selectedProvenanceRow.parse_mode_used}</li>
                <li>Derived relative path: {selectedProvenanceRow.derived_relative_path ?? "-"}</li>
                <li>Normalized relative segments: {selectedProvenanceRow.normalized_segments_relative.join(" / ") || "-"}</li>
                <li>Normalized full-path segments: {selectedProvenanceRow.normalized_segments_full.join(" / ") || "-"}</li>
                <li>
                  Selected normalized prefix: {matches?.selected_prefix ?? "Select a hierarchy level to compute prefix"}
                </li>
              </ul>
            </details>
          ) : null}
        </>
      )}
    </div>
  );
}

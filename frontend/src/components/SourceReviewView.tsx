"use client";

import { useEffect, useMemo, useState } from "react";

import { getSourceReviewAsset, getSourceReviewMatches, resolveApiUrl } from "@/lib/api";
import type {
  SourceReviewAssetResponse,
  SourceReviewMatchesResponse,
  SourceReviewProvenanceRow,
} from "@/types/ui-api";
import styles from "./source-review-view.module.css";

interface SourceReviewViewProps {
  assetSha256: string | null;
  onOpenPhotoDetail: (assetSha256: string) => void;
}

const MATCH_LIMIT = 50;

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

export function SourceReviewView({ assetSha256, onOpenPhotoDetail }: SourceReviewViewProps) {
  const [assetResponse, setAssetResponse] = useState<SourceReviewAssetResponse | null>(null);
  const [hierarchyMode, setHierarchyMode] = useState<"relative" | "full_source_path">("relative");
  const [selectedProvenanceId, setSelectedProvenanceId] = useState<number | null>(null);
  const [selectedLevelIndex, setSelectedLevelIndex] = useState<number | null>(null);
  const [matches, setMatches] = useState<SourceReviewMatchesResponse | null>(null);
  const [isLoadingAsset, setIsLoadingAsset] = useState(false);
  const [isLoadingMatches, setIsLoadingMatches] = useState(false);
  const [assetErrorMessage, setAssetErrorMessage] = useState<string | null>(null);
  const [matchesErrorMessage, setMatchesErrorMessage] = useState<string | null>(null);

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

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <h2 className={styles.title}>Source Review</h2>
        <p className={styles.subtitle}>Read-only provenance workspace for hierarchy and path-prefix exploration.</p>
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
            <h3 className={styles.panelTitle}>Candidate Actions (Read-Only in 12.58.1)</h3>
            <div className={styles.actionRow}>
              {[
                "Create Collection",
                "Create Album",
                "Create Event",
                "Apply Person Clue",
                "Apply Date Range",
                "Apply Place Clue",
                "Apply Tag",
                "Mark Reviewed",
                "Ignore Level",
              ].map((label) => (
                <button key={label} type="button" className={styles.placeholderAction} disabled>
                  {label}
                </button>
              ))}
            </div>
            <p className={styles.notice}>Coming later. This workspace is read-only for milestone 12.58.1.</p>
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

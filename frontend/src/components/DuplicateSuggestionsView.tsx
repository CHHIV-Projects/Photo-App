"use client";

import { useEffect, useMemo, useState } from "react";

import styles from "@/components/duplicate-suggestions-view.module.css";
import {
  confirmDuplicateSuggestion,
  getDuplicateSuggestions,
  rejectDuplicateSuggestion,
  resolveApiUrl,
} from "@/lib/api";
import type { DuplicateSuggestionSummary } from "@/types/ui-api";

interface DuplicateSuggestionsViewProps {
  onOpenPhoto: (sha256: string) => void;
}

const PAGE_SIZE = 50;

export function DuplicateSuggestionsView({ onOpenPhoto }: DuplicateSuggestionsViewProps) {
  const [suggestions, setSuggestions] = useState<DuplicateSuggestionSummary[]>([]);
  const [offset, setOffset] = useState(0);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isActingOnPair, setIsActingOnPair] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    void loadSuggestions(0);
  }, []);

  async function loadSuggestions(nextOffset: number): Promise<void> {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const response = await getDuplicateSuggestions(nextOffset, PAGE_SIZE);
      setSuggestions(response.items);
      setTotalCount(response.total_count);
      setOffset(response.offset);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Failed to load duplicate suggestions."));
    } finally {
      setIsLoading(false);
    }
  }

  function pairKey(item: DuplicateSuggestionSummary): string {
    const a = item.asset_a.asset_sha256;
    const b = item.asset_b.asset_sha256;
    return a <= b ? `${a}:${b}` : `${b}:${a}`;
  }

  function removeSuggestionLocally(item: DuplicateSuggestionSummary, decrementTotal = false): void {
    const key = pairKey(item);
    setSuggestions((current) => current.filter((candidate) => pairKey(candidate) !== key));
    if (decrementTotal) {
      setTotalCount((current) => Math.max(0, current - 1));
    }
  }

  async function handleConfirm(item: DuplicateSuggestionSummary): Promise<void> {
    const key = pairKey(item);
    setIsActingOnPair(key);
    setErrorMessage(null);

    try {
      await confirmDuplicateSuggestion(item.asset_a.asset_sha256, item.asset_b.asset_sha256);
      await loadSuggestions(offset);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Failed to confirm duplicate suggestion."));
    } finally {
      setIsActingOnPair(null);
    }
  }

  async function handleReject(item: DuplicateSuggestionSummary): Promise<void> {
    const key = pairKey(item);
    setIsActingOnPair(key);
    setErrorMessage(null);

    try {
      await rejectDuplicateSuggestion(item.asset_a.asset_sha256, item.asset_b.asset_sha256);
      removeSuggestionLocally(item, true);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Failed to reject duplicate suggestion."));
    } finally {
      setIsActingOnPair(null);
    }
  }

  function handleSkip(item: DuplicateSuggestionSummary): void {
    removeSuggestionLocally(item, false);
  }

  const grouped = useMemo(() => {
    return {
      high: suggestions.filter((item) => item.confidence === "high"),
      medium: suggestions.filter((item) => item.confidence === "medium"),
      low: suggestions.filter((item) => item.confidence === "low"),
    };
  }, [suggestions]);

  const pageNumber = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));

  if (isLoading) {
    return (
      <div className={styles.container}>
        <div className={styles.loadingMessage}>Loading duplicate suggestions...</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.headerRow}>
        <div>
          <h2 className={styles.title}>Duplicate Suggestions</h2>
          <p className={styles.subtitle}>Deterministic queue ordered by confidence, then distance, then SHA.</p>
        </div>
        <div className={styles.countPill}>{totalCount} total suggestions</div>
      </div>

      {errorMessage ? <div className={styles.errorMessage}>{errorMessage}</div> : null}

      {suggestions.length === 0 ? (
        <div className={styles.emptyState}>No suggestions on this page. Try the next page or refresh.</div>
      ) : (
        <>
          <ConfidenceSection
            title="High Confidence"
            items={grouped.high}
            isActingOnPair={isActingOnPair}
            pairKey={pairKey}
            onConfirm={handleConfirm}
            onReject={handleReject}
            onSkip={handleSkip}
            onOpenPhoto={onOpenPhoto}
          />
          <ConfidenceSection
            title="Medium Confidence"
            items={grouped.medium}
            isActingOnPair={isActingOnPair}
            pairKey={pairKey}
            onConfirm={handleConfirm}
            onReject={handleReject}
            onSkip={handleSkip}
            onOpenPhoto={onOpenPhoto}
          />
          <ConfidenceSection
            title="Low Confidence"
            items={grouped.low}
            isActingOnPair={isActingOnPair}
            pairKey={pairKey}
            onConfirm={handleConfirm}
            onReject={handleReject}
            onSkip={handleSkip}
            onOpenPhoto={onOpenPhoto}
          />
        </>
      )}

      <div className={styles.paginationRow}>
        <button
          type="button"
          disabled={offset <= 0 || isLoading}
          onClick={() => {
            void loadSuggestions(Math.max(0, offset - PAGE_SIZE));
          }}
          className={styles.paginationButton}
        >
          Previous
        </button>
        <span className={styles.pageInfo}>Page {pageNumber} of {totalPages}</span>
        <button
          type="button"
          disabled={offset + PAGE_SIZE >= totalCount || isLoading}
          onClick={() => {
            void loadSuggestions(offset + PAGE_SIZE);
          }}
          className={styles.paginationButton}
        >
          Next
        </button>
      </div>
    </div>
  );
}

interface ConfidenceSectionProps {
  title: string;
  items: DuplicateSuggestionSummary[];
  isActingOnPair: string | null;
  pairKey: (item: DuplicateSuggestionSummary) => string;
  onConfirm: (item: DuplicateSuggestionSummary) => Promise<void>;
  onReject: (item: DuplicateSuggestionSummary) => Promise<void>;
  onSkip: (item: DuplicateSuggestionSummary) => void;
  onOpenPhoto: (sha256: string) => void;
}

function ConfidenceSection({
  title,
  items,
  isActingOnPair,
  pairKey,
  onConfirm,
  onReject,
  onSkip,
  onOpenPhoto,
}: ConfidenceSectionProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <section className={styles.section}>
      <h3 className={styles.sectionTitle}>{title}</h3>
      <div className={styles.cardGrid}>
        {items.map((item) => {
          const currentKey = pairKey(item);
          const isBusy = isActingOnPair === currentKey;

          return (
            <article key={currentKey} className={styles.card}>
              <div className={styles.pairGrid}>
                <AssetPane asset={item.asset_a} label="Asset A" onOpenPhoto={onOpenPhoto} />
                <AssetPane asset={item.asset_b} label="Asset B" onOpenPhoto={onOpenPhoto} />
              </div>

              <div className={styles.metaRow}>
                <span>Distance: {item.distance}</span>
                <span>Confidence: {item.confidence}</span>
              </div>

              <div className={styles.actionRow}>
                <button
                  type="button"
                  disabled={isBusy}
                  onClick={() => {
                    void onConfirm(item);
                  }}
                  className={styles.confirmButton}
                >
                  {isBusy ? "Working..." : "Confirm"}
                </button>
                <button
                  type="button"
                  disabled={isBusy}
                  onClick={() => {
                    void onReject(item);
                  }}
                  className={styles.rejectButton}
                >
                  Reject
                </button>
                <button
                  type="button"
                  disabled={isBusy}
                  onClick={() => onSkip(item)}
                  className={styles.skipButton}
                >
                  Skip
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

interface AssetPaneProps {
  asset: DuplicateSuggestionSummary["asset_a"];
  label: string;
  onOpenPhoto: (sha256: string) => void;
}

function AssetPane({ asset, label, onOpenPhoto }: AssetPaneProps) {
  return (
    <div className={styles.assetPane}>
      <div className={styles.assetLabel}>{label}</div>
      <img src={resolveApiUrl(asset.image_url) ?? ""} alt={asset.filename} className={styles.assetImage} />
      <div className={styles.assetFilename} title={asset.filename}>{asset.filename}</div>
      <div className={styles.assetMeta}>Quality: {asset.quality_score?.toFixed(2) ?? "N/A"}</div>
      <div className={styles.assetMeta}>
        Group: {asset.duplicate_group_id === null ? "None" : `#${asset.duplicate_group_id}`}
      </div>
      <button
        type="button"
        onClick={() => onOpenPhoto(asset.asset_sha256)}
        className={styles.openButton}
      >
        Open Photo
      </button>
    </div>
  );
}

function getErrorMessage(error: unknown, fallbackMessage: string) {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallbackMessage;
}

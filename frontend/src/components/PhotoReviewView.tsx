"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import styles from "@/components/photo-review-view.module.css";
import {
  demoteDuplicateGroupMember,
  getTimelineSummary,
  restoreDuplicateGroupMember,
  searchPhotos,
  setDuplicateGroupCanonical,
  resolveApiUrl,
} from "@/lib/api";
import type { SearchPhotoSummary } from "@/types/ui-api";

interface PhotoReviewViewProps {
  onOpenPhotoDetail: (sha256: string) => void;
  onOpenDuplicateGroup: (groupId: number) => void;
}

const PAGE_SIZE = 80;

export function PhotoReviewView({ onOpenPhotoDetail, onOpenDuplicateGroup }: PhotoReviewViewProps) {
  const [items, setItems] = useState<SearchPhotoSummary[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [offset, setOffset] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [busyAssetSha256, setBusyAssetSha256] = useState<string | null>(null);

  const [year, setYear] = useState<string>("");
  const [month, setMonth] = useState<string>("");
  const [cameraInput, setCameraInput] = useState("");
  const [cameraQuery, setCameraQuery] = useState("");
  const [hasLocation, setHasLocation] = useState(false);
  const [hasFaces, setHasFaces] = useState(false);
  const [yearOptions, setYearOptions] = useState<string[]>([]);
  const [monthOptions, setMonthOptions] = useState<Array<{ value: string; label: string }>>([]);

  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setCameraQuery(cameraInput.trim());
    }, 250);
    return () => window.clearTimeout(handle);
  }, [cameraInput]);

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

  async function loadPage(nextOffset: number, reset: boolean): Promise<void> {
    if (isLoading) {
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const activeYear = year && !month ? Number(year) : undefined;
      const activeMonth = year && month ? `${year}-${month}` : undefined;
      const response = await searchPhotos({
        year: activeYear,
        month: activeMonth,
        camera: cameraQuery || undefined,
        hasLocation: hasLocation ? true : undefined,
        hasFaces: hasFaces ? true : undefined,
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
    setItems([]);
    setOffset(0);
    setTotalCount(0);
    await loadPage(0, true);
  }

  useEffect(() => {
    void reloadFromStart();
  }, [year, month, cameraQuery, hasLocation, hasFaces]);

  const hasMore = items.length < totalCount;

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
  }, [offset, hasMore, isLoading, year, month, cameraQuery, hasLocation, hasFaces]);

  async function handleSetCanonical(assetSha256: string): Promise<void> {
    setBusyAssetSha256(assetSha256);
    try {
      await setDuplicateGroupCanonical(assetSha256);
      await reloadFromStart();
    } catch (error) {
      const message = error instanceof Error && error.message ? error.message : "Failed to set canonical.";
      setErrorMessage(message);
    } finally {
      setBusyAssetSha256(null);
    }
  }

  async function handleDemote(assetSha256: string): Promise<void> {
    setBusyAssetSha256(assetSha256);
    try {
      await demoteDuplicateGroupMember(assetSha256);
      await reloadFromStart();
    } catch (error) {
      const message = error instanceof Error && error.message ? error.message : "Failed to demote asset.";
      setErrorMessage(message);
    } finally {
      setBusyAssetSha256(null);
    }
  }

  async function handleRestore(assetSha256: string): Promise<void> {
    setBusyAssetSha256(assetSha256);
    try {
      await restoreDuplicateGroupMember(assetSha256);
      await reloadFromStart();
    } catch (error) {
      const message = error instanceof Error && error.message ? error.message : "Failed to restore asset.";
      setErrorMessage(message);
    } finally {
      setBusyAssetSha256(null);
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.toolbar}>
        <div className={styles.fieldRow}>
          <label className={styles.fieldLabel}>
            Year
            <select
              value={year}
              onChange={(event) => {
                const nextYear = event.target.value;
                setYear(nextYear);
                setMonth("");
              }}
              className={styles.select}
            >
              <option value="">All</option>
              {yearOptions.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>

          <label className={styles.fieldLabel}>
            Month
            <select
              value={month}
              onChange={(event) => setMonth(event.target.value)}
              className={styles.select}
              disabled={!year}
            >
              <option value="">All</option>
              {monthOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className={styles.fieldLabelWide}>
            Camera
            <input
              type="search"
              value={cameraInput}
              onChange={(event) => setCameraInput(event.target.value)}
              placeholder="Make or model"
              className={styles.input}
            />
          </label>

          <label className={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={hasLocation}
              onChange={(event) => setHasLocation(event.target.checked)}
            />
            Has Location
          </label>

          <label className={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={hasFaces}
              onChange={(event) => setHasFaces(event.target.checked)}
            />
            Has Faces
          </label>
        </div>

        <div className={styles.countRow}>{items.length} / {totalCount} photos</div>
      </div>

      {errorMessage && <div className={styles.errorMessage}>{errorMessage}</div>}

      <div className={styles.grid}>
        {items.map((item) => (
          <div key={item.asset_sha256} className={styles.card}>
            <button
              type="button"
              className={styles.imageButton}
              onClick={() => onOpenPhotoDetail(item.asset_sha256)}
            >
              <img
                src={resolveApiUrl(item.image_url) ?? ""}
                alt={item.filename}
                className={styles.image}
                loading="lazy"
              />
            </button>
            <div className={styles.filename} title={item.filename}>{item.filename}</div>
            <div className={styles.actionRow}>
              <button
                type="button"
                className={styles.actionButton}
                onClick={() => onOpenPhotoDetail(item.asset_sha256)}
              >
                Open Detail
              </button>

              {item.duplicate_group_id !== null && (
                <button
                  type="button"
                  className={styles.actionButton}
                  onClick={() => onOpenDuplicateGroup(item.duplicate_group_id as number)}
                >
                  Open Group
                </button>
              )}

              {item.duplicate_group_id !== null && !item.is_canonical && item.visibility_status === "visible" && (
                <button
                  type="button"
                  disabled={busyAssetSha256 === item.asset_sha256}
                  className={styles.actionButton}
                  onClick={() => {
                    void handleSetCanonical(item.asset_sha256);
                  }}
                >
                  Make Canonical
                </button>
              )}

              {item.duplicate_group_id !== null && !item.is_canonical && item.visibility_status === "visible" && (
                <button
                  type="button"
                  disabled={busyAssetSha256 === item.asset_sha256}
                  className={styles.actionButtonDanger}
                  onClick={() => {
                    void handleDemote(item.asset_sha256);
                  }}
                >
                  Demote
                </button>
              )}

              {item.duplicate_group_id !== null && item.visibility_status === "demoted" && (
                <button
                  type="button"
                  disabled={busyAssetSha256 === item.asset_sha256}
                  className={styles.actionButton}
                  onClick={() => {
                    void handleRestore(item.asset_sha256);
                  }}
                >
                  Restore
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {isLoading && <div className={styles.loadingMessage}>Loading...</div>}
      {!isLoading && items.length === 0 && !errorMessage && (
        <div className={styles.emptyState}>No photos found for current filters.</div>
      )}
      <div ref={sentinelRef} className={styles.sentinel} />
    </div>
  );
}

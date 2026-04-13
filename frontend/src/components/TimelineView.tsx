"use client";

import { useEffect, useMemo, useState } from "react";

import { getPhotoDetail, getPhotos, getTimelineSummary } from "@/lib/api";
import { PhotosView } from "@/components/PhotosView";
import type {
  PhotoDetail,
  PhotoSummary,
  TimelineBucketSummary,
  TimelineSummaryResponse
} from "@/types/ui-api";
import styles from "./timeline-view.module.css";

type CaptureTrust = "high" | "low" | "unknown";

const ALL_TRUST_VALUES: CaptureTrust[] = ["high", "low", "unknown"];

export function TimelineView() {
  const [selectedDecade, setSelectedDecade] = useState<number | null>(null);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [isUndatedSelected, setIsUndatedSelected] = useState(false);
  const [selectedTrusts, setSelectedTrusts] = useState<CaptureTrust[]>(ALL_TRUST_VALUES);

  const [timelineSummary, setTimelineSummary] = useState<TimelineSummaryResponse | null>(null);
  const [isLoadingTimeline, setIsLoadingTimeline] = useState(true);
  const [timelineErrorMessage, setTimelineErrorMessage] = useState<string | null>(null);

  const [photos, setPhotos] = useState<PhotoSummary[]>([]);
  const [isLoadingPhotos, setIsLoadingPhotos] = useState(true);
  const [photosErrorMessage, setPhotosErrorMessage] = useState<string | null>(null);
  const [selectedPhotoSha256, setSelectedPhotoSha256] = useState<string | null>(null);
  const [photoDetail, setPhotoDetail] = useState<PhotoDetail | null>(null);
  const [isLoadingPhotoDetail, setIsLoadingPhotoDetail] = useState(false);
  const [photoDetailErrorMessage, setPhotoDetailErrorMessage] = useState<string | null>(null);

  const summaryQuery = useMemo(() => {
    const trust = selectedTrusts.length === ALL_TRUST_VALUES.length ? undefined : selectedTrusts;

    if (selectedMonth) {
      return { month: selectedMonth, trust };
    }
    if (selectedYear !== null) {
      return { year: selectedYear, trust };
    }
    if (selectedDecade !== null) {
      return { decade: selectedDecade, trust };
    }
    return { trust };
  }, [selectedDecade, selectedMonth, selectedTrusts, selectedYear]);

  const photoQuery = useMemo(() => {
    const trust = selectedTrusts.length === ALL_TRUST_VALUES.length ? undefined : selectedTrusts;

    if (isUndatedSelected) {
      return { undated: true, trust };
    }
    if (selectedDate) {
      return { date: selectedDate, trust };
    }
    if (selectedMonth) {
      return { month: selectedMonth, trust };
    }
    if (selectedYear !== null) {
      return { year: selectedYear, trust };
    }
    if (selectedDecade !== null) {
      return { decade: selectedDecade, trust };
    }
    return { trust };
  }, [isUndatedSelected, selectedDate, selectedDecade, selectedMonth, selectedTrusts, selectedYear]);

  useEffect(() => {
    async function loadTimelineSummary() {
      setIsLoadingTimeline(true);
      setTimelineErrorMessage(null);

      try {
        const response = await getTimelineSummary(summaryQuery);
        setTimelineSummary(response);
      } catch (error) {
        setTimelineErrorMessage(getErrorMessage(error, "Failed to load timeline."));
        setTimelineSummary(null);
      } finally {
        setIsLoadingTimeline(false);
      }
    }

    void loadTimelineSummary();
  }, [summaryQuery]);

  useEffect(() => {
    async function loadFilteredPhotos() {
      setIsLoadingPhotos(true);
      setPhotosErrorMessage(null);

      try {
        const response = await getPhotos(photoQuery);
        setPhotos(response.items);
      } catch (error) {
        setPhotosErrorMessage(getErrorMessage(error, "Failed to load filtered photos."));
        setPhotos([]);
      } finally {
        setIsLoadingPhotos(false);
      }
    }

    void loadFilteredPhotos();
  }, [photoQuery]);

  useEffect(() => {
    if (photos.length === 0) {
      setSelectedPhotoSha256(null);
      setPhotoDetail(null);
      setPhotoDetailErrorMessage(null);
      return;
    }

    if (selectedPhotoSha256 && photos.some((photo) => photo.asset_sha256 === selectedPhotoSha256)) {
      return;
    }

    setSelectedPhotoSha256(photos[0].asset_sha256);
  }, [photos, selectedPhotoSha256]);

  useEffect(() => {
    if (!selectedPhotoSha256) {
      setPhotoDetail(null);
      return;
    }

    const photoSha256 = selectedPhotoSha256;

    async function loadPhoto() {
      setIsLoadingPhotoDetail(true);
      setPhotoDetailErrorMessage(null);

      try {
        const response = await getPhotoDetail(photoSha256);
        setPhotoDetail(response);
      } catch (error) {
        setPhotoDetailErrorMessage(getErrorMessage(error, "Failed to load photo detail."));
        setPhotoDetail(null);
      } finally {
        setIsLoadingPhotoDetail(false);
      }
    }

    void loadPhoto();
  }, [selectedPhotoSha256]);

  function handleToggleTrust(value: CaptureTrust) {
    setSelectedTrusts((current) => {
      if (current.includes(value)) {
        if (current.length === 1) {
          return current;
        }
        return current.filter((item) => item !== value);
      }
      return [...current, value].sort(
        (left, right) => ALL_TRUST_VALUES.indexOf(left) - ALL_TRUST_VALUES.indexOf(right)
      ) as CaptureTrust[];
    });
  }

  function handleSelectBucket(bucket: TimelineBucketSummary) {
    setIsUndatedSelected(false);
    setSelectedDate(null);

    if (bucket.level === "decade") {
      setSelectedDecade(Number(bucket.period_key));
      setSelectedYear(null);
      setSelectedMonth(null);
      return;
    }

    if (bucket.level === "year") {
      setSelectedYear(Number(bucket.period_key));
      setSelectedMonth(null);
      return;
    }

    if (bucket.level === "month") {
      setSelectedMonth(bucket.period_key);
      return;
    }

    if (bucket.level === "date") {
      setSelectedDate(bucket.period_key);
    }
  }

  function handleSelectUndated() {
    setIsUndatedSelected(true);
    setSelectedDecade(null);
    setSelectedYear(null);
    setSelectedMonth(null);
    setSelectedDate(null);
  }

  function resetTimeline() {
    setIsUndatedSelected(false);
    setSelectedDecade(null);
    setSelectedYear(null);
    setSelectedMonth(null);
    setSelectedDate(null);
  }

  function getSelectionLabel(): string {
    if (isUndatedSelected) return "Undated photos";
    if (selectedDate) return `Showing ${selectedDate}`;
    if (selectedMonth) return `Showing ${selectedMonth}`;
    if (selectedYear !== null) return `Showing ${selectedYear}`;
    if (selectedDecade !== null) return `Showing ${selectedDecade}s`;
    return "Showing all dated photos";
  }

  return (
    <div className={styles.layout}>
      <aside className={styles.sidebar}>
        <div className={styles.section}>
          <div className={styles.headingRow}>
            <h2 className={styles.heading}>Timeline</h2>
            <button type="button" className={styles.resetButton} onClick={resetTimeline}>
              Reset
            </button>
          </div>
          <p className={styles.helperText}>{getSelectionLabel()}</p>
          <div className={styles.breadcrumbs}>
            <button type="button" className={styles.crumb} onClick={resetTimeline}>
              Decades
            </button>
            {selectedDecade !== null ? (
              <button
                type="button"
                className={styles.crumb}
                onClick={() => {
                  setSelectedYear(null);
                  setSelectedMonth(null);
                  setSelectedDate(null);
                }}
              >
                {selectedDecade}s
              </button>
            ) : null}
            {selectedYear !== null ? (
              <button
                type="button"
                className={styles.crumb}
                onClick={() => {
                  setSelectedMonth(null);
                  setSelectedDate(null);
                }}
              >
                {selectedYear}
              </button>
            ) : null}
            {selectedMonth ? (
              <button
                type="button"
                className={styles.crumb}
                onClick={() => setSelectedDate(null)}
              >
                {selectedMonth}
              </button>
            ) : null}
          </div>
        </div>

        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>Trust Filter</h3>
          <div className={styles.trustGrid}>
            {ALL_TRUST_VALUES.map((value) => {
              const active = selectedTrusts.includes(value);
              return (
                <button
                  key={value}
                  type="button"
                  className={`${styles.trustButton} ${active ? styles.trustButtonActive : ""}`.trim()}
                  onClick={() => handleToggleTrust(value)}
                >
                  {value}
                </button>
              );
            })}
          </div>
        </div>

        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>Buckets</h3>
          {isLoadingTimeline ? (
            <p className={styles.statusMessage}>Loading timeline…</p>
          ) : timelineErrorMessage ? (
            <p className={styles.errorMessage}>{timelineErrorMessage}</p>
          ) : (
            <div className={styles.bucketList}>
              {timelineSummary?.undated_bucket ? (
                <button
                  type="button"
                  className={`${styles.bucketButton} ${isUndatedSelected ? styles.bucketButtonActive : ""}`.trim()}
                  onClick={handleSelectUndated}
                >
                  <span className={styles.bucketLabel}>{timelineSummary.undated_bucket.label}</span>
                  <span className={styles.bucketMeta}>{timelineSummary.undated_bucket.total_assets} photos</span>
                </button>
              ) : null}
              {(timelineSummary?.items ?? []).map((bucket) => {
                const isActive =
                  (!isUndatedSelected && selectedDate === bucket.period_key) ||
                  (!isUndatedSelected && selectedMonth === bucket.period_key) ||
                  (!isUndatedSelected && String(selectedYear ?? "") === bucket.period_key) ||
                  (!isUndatedSelected && String(selectedDecade ?? "") === bucket.period_key);

                return (
                  <button
                    key={`${bucket.level}-${bucket.period_key}`}
                    type="button"
                    className={`${styles.bucketButton} ${isActive ? styles.bucketButtonActive : ""}`.trim()}
                    onClick={() => handleSelectBucket(bucket)}
                  >
                    <span className={styles.bucketLabel}>{bucket.label}</span>
                    <span className={styles.bucketMeta}>{bucket.total_assets} photos</span>
                    <span className={styles.bucketTrusts}>
                      H {bucket.high_trust_count} · L {bucket.low_trust_count} · U {bucket.unknown_trust_count}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </aside>

      <div className={styles.photosPane}>
        <PhotosView
          photos={photos}
          isLoading={isLoadingPhotos}
          errorMessage={photosErrorMessage}
          selectedPhotoSha256={selectedPhotoSha256}
          photoDetail={photoDetail}
          isLoadingDetail={isLoadingPhotoDetail}
          photoDetailErrorMessage={photoDetailErrorMessage}
          onSelectPhoto={setSelectedPhotoSha256}
        />
      </div>
    </div>
  );
}

function getErrorMessage(error: unknown, fallbackMessage: string) {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallbackMessage;
}

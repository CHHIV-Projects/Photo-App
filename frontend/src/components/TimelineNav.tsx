"use client";

import { useEffect, useMemo, useState } from "react";

import { getTimelineSummary } from "@/lib/api";
import type { TimelineBucketSummary } from "@/types/ui-api";
import styles from "./timeline-nav.module.css";

interface Props {
  selectedYear: number | null;
  selectedMonth: string;
  selectedDate: string;
  onTimelineChange: (selection: {
    year: number | null;
    month: string;
    date: string;
  }) => void;
}

export function TimelineNav({
  selectedYear,
  selectedMonth,
  selectedDate,
  onTimelineChange,
}: Props) {
  const [items, setItems] = useState<TimelineBucketSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const summaryQuery = useMemo(() => {
    if (selectedMonth) {
      return { month: selectedMonth };
    }
    if (selectedYear !== null) {
      return { year: selectedYear };
    }
    return {};
  }, [selectedYear, selectedMonth]);

  useEffect(() => {
    async function loadTimeline() {
      setIsLoading(true);
      setErrorMessage(null);

      try {
        const response = await getTimelineSummary(summaryQuery);
        setItems(response.items.filter((item) => item.level !== "decade" && item.level !== "undated"));
      } catch (error) {
        setErrorMessage(getErrorMessage(error, "Failed to load timeline buckets."));
        setItems([]);
      } finally {
        setIsLoading(false);
      }
    }

    void loadTimeline();
  }, [summaryQuery]);

  function handleReset() {
    onTimelineChange({
      year: null,
      month: "",
      date: "",
    });
  }

  function handleSelectBucket(bucket: TimelineBucketSummary) {
    if (bucket.level === "year") {
      onTimelineChange({
        year: Number(bucket.period_key),
        month: "",
        date: "",
      });
      return;
    }

    if (bucket.level === "month") {
      onTimelineChange({
        year: selectedYear,
        month: bucket.period_key,
        date: "",
      });
      return;
    }

    if (bucket.level === "date") {
      onTimelineChange({
        year: selectedYear,
        month: selectedMonth,
        date: bucket.period_key,
      });
    }
  }

  const listTitle = !selectedYear
    ? "Years"
    : !selectedMonth
      ? `Months in ${selectedYear}`
      : `Days in ${formatMonthLabel(selectedMonth)}`;

  return (
    <aside className={styles.panel}>
      <div className={styles.headerRow}>
        <h2 className={styles.title}>Timeline</h2>
        <button type="button" className={styles.resetButton} onClick={handleReset}>
          Reset
        </button>
      </div>

      <div className={styles.breadcrumbs}>
        <button type="button" className={styles.crumb} onClick={handleReset}>
          All Photos
        </button>
        {selectedYear !== null ? (
          <button
            type="button"
            className={styles.crumb}
            onClick={() => onTimelineChange({ year: selectedYear, month: "", date: "" })}
          >
            {selectedYear}
          </button>
        ) : null}
        {selectedMonth ? (
          <button
            type="button"
            className={styles.crumb}
            onClick={() => onTimelineChange({ year: selectedYear, month: selectedMonth, date: "" })}
          >
            {formatMonthLabel(selectedMonth)}
          </button>
        ) : null}
        {selectedDate ? <span className={styles.crumbActive}>{formatDateLabel(selectedDate)}</span> : null}
      </div>

      <p className={styles.sectionTitle}>{listTitle}</p>

      <div className={styles.bucketList}>
        {isLoading ? (
          <p className={styles.statusMessage}>Loading timeline...</p>
        ) : errorMessage ? (
          <p className={styles.errorMessage}>{errorMessage}</p>
        ) : items.length === 0 ? (
          <p className={styles.statusMessage}>No photos found.</p>
        ) : (
          items.map((bucket) => {
            const isActive =
              (bucket.level === "year" && selectedYear === Number(bucket.period_key)) ||
              (bucket.level === "month" && selectedMonth === bucket.period_key) ||
              (bucket.level === "date" && selectedDate === bucket.period_key);

            return (
              <button
                key={bucket.period_key}
                type="button"
                className={`${styles.bucketButton} ${isActive ? styles.bucketButtonActive : ""}`.trim()}
                onClick={() => handleSelectBucket(bucket)}
              >
                <span className={styles.bucketLabel}>{formatBucketLabel(bucket)}</span>
                <span className={styles.bucketCount}>{bucket.total_assets}</span>
              </button>
            );
          })
        )}
      </div>
    </aside>
  );
}

function formatBucketLabel(bucket: TimelineBucketSummary): string {
  if (bucket.level === "month") {
    return formatMonthLabel(bucket.period_key);
  }
  if (bucket.level === "date") {
    return formatDateLabel(bucket.period_key);
  }
  return bucket.label;
}

function formatMonthLabel(value: string): string {
  const [year, month] = value.split("-").map(Number);
  if (!year || !month) {
    return value;
  }

  const label = new Date(year, month - 1, 1).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
  });
  return label;
}

function formatDateLabel(value: string): string {
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) {
    return value;
  }

  const label = new Date(year, month - 1, day).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
  return label;
}

function getErrorMessage(error: unknown, fallbackMessage: string) {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallbackMessage;
}
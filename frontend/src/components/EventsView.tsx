"use client";

import { useEffect, useRef, useState } from "react";

import { resolveApiUrl } from "@/lib/api";
import type { EventDetail, EventSummary, PhotoSummary } from "@/types/ui-api";
import styles from "./events-view.module.css";

interface Props {
  events: EventSummary[];
  isLoading: boolean;
  errorMessage: string | null;
  selectedEventId: number | null;
  eventDetail: EventDetail | null;
  isLoadingDetail: boolean;
  eventDetailErrorMessage: string | null;
  onSelectEvent: (eventId: number) => void;
  onOpenPhoto: (sha256: string) => void;
}

// ── Date/time helpers (browser local timezone) ────────────────────────────────

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(new Date(iso));
}

function formatTime(iso: string): string {
  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(iso));
}

function formatTimeRange(start: string, end: string): string {
  const startDate = new Date(start);
  const endDate = new Date(end);
  const isSameDay = startDate.toDateString() === endDate.toDateString();

  if (isSameDay) {
    const s = formatTime(start);
    const e = formatTime(end);
    return s === e ? s : `${s} – ${e}`;
  }

  return `${formatDate(start)} – ${formatDate(end)}`;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function EventsView({
  events,
  isLoading,
  errorMessage,
  selectedEventId,
  eventDetail,
  isLoadingDetail,
  eventDetailErrorMessage,
  onSelectEvent,
  onOpenPhoto,
}: Props) {
  const eventRefs = useRef<Map<number, HTMLButtonElement>>(new Map());

  // Auto-scroll selected event into view in the list.
  useEffect(() => {
    if (selectedEventId === null) return;
    eventRefs.current.get(selectedEventId)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [selectedEventId]);

  return (
    <div className={styles.layout}>
      {/* ── Event list ──────────────────────────────────────────────── */}
      <aside className={styles.panel}>
        <div className={styles.panelHeader}>
          <h2 className={styles.panelTitle}>Events</h2>
          <span className={styles.panelCount}>{events.length}</span>
        </div>

        <div className={styles.eventList}>
          {isLoading ? (
            <p className={styles.statusMessage}>Loading events…</p>
          ) : errorMessage ? (
            <p className={styles.errorMessage}>{errorMessage}</p>
          ) : events.length === 0 ? (
            <p className={styles.statusMessage}>No events found.</p>
          ) : (
            events.map((ev) => (
              <button
                key={ev.event_id}
                type="button"
                ref={(el) => {
                  if (el) eventRefs.current.set(ev.event_id, el);
                  else eventRefs.current.delete(ev.event_id);
                }}
                className={
                  `${styles.eventItem} ${selectedEventId === ev.event_id ? styles.eventItemActive : ""}`.trim()
                }
                onClick={() => onSelectEvent(ev.event_id)}
              >
                <span className={styles.eventDate}>{formatDate(ev.start_time)}</span>
                <span className={styles.eventTime}>{formatTimeRange(ev.start_time, ev.end_time)}</span>
                <span className={styles.eventStats}>
                  {ev.photo_count} {ev.photo_count === 1 ? "photo" : "photos"} &bull; {ev.face_count} {ev.face_count === 1 ? "face" : "faces"}
                </span>
              </button>
            ))
          )}
        </div>
      </aside>

      {/* ── Event detail ────────────────────────────────────────────── */}
      <div className={styles.detailArea}>
        {isLoadingDetail ? (
          <div className={styles.panel}>
            <p className={styles.statusMessage}>Loading event…</p>
          </div>
        ) : eventDetailErrorMessage ? (
          <div className={styles.panel}>
            <p className={styles.errorMessage}>{eventDetailErrorMessage}</p>
          </div>
        ) : !eventDetail ? (
          <div className={styles.panel}>
            <p className={styles.statusMessage}>Select an event to view its photos.</p>
          </div>
        ) : (
          <div className={styles.panel}>
            <div className={styles.detailHeader}>
              <div>
                <h2 className={styles.detailDate}>{formatDate(eventDetail.start_time)}</h2>
                <p className={styles.detailTime}>{formatTimeRange(eventDetail.start_time, eventDetail.end_time)}</p>
              </div>
              <span className={styles.panelCount}>
                {eventDetail.photos.length} {eventDetail.photos.length === 1 ? "photo" : "photos"}
              </span>
            </div>

            {eventDetail.photos.length === 0 ? (
              <p className={styles.statusMessage}>No photos in this event.</p>
            ) : (
              <div className={styles.photoGrid}>
                {eventDetail.photos.map((photo) => (
                  <EventPhotoCard
                    key={photo.asset_sha256}
                    photo={photo}
                    onClick={() => onOpenPhoto(photo.asset_sha256)}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Individual photo card ─────────────────────────────────────────────────────

function EventPhotoCard({ photo, onClick }: { photo: PhotoSummary; onClick: () => void }) {
  const [imgError, setImgError] = useState(false);
  const imageUrl = resolveApiUrl(photo.image_url);

  return (
    <button type="button" className={styles.photoCard} onClick={onClick} title={`Open ${photo.filename} in Photos view`}>
      <div className={styles.photoThumb}>
        {imageUrl && !imgError ? (
          <img
            src={imageUrl}
            alt={photo.filename}
            className={styles.photoThumbImg}
            onError={() => setImgError(true)}
          />
        ) : (
          <span className={styles.photoThumbPlaceholder}>?</span>
        )}
      </div>
      <div className={styles.photoMeta}>
        <span className={styles.photoFilename}>{photo.filename}</span>
        <span className={styles.photoFaceCount}>
          {photo.face_count} {photo.face_count === 1 ? "face" : "faces"}
        </span>
      </div>
    </button>
  );
}

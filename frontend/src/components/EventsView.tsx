"use client";

import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";

import { assignPhotoToEvent, removePhotoFromEvent, resolveApiUrl } from "@/lib/api";
import { isVideoAssetFilename } from "@/lib/media";
import { PresentationViewer } from "@/components/PresentationViewer";
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
  actionErrorMessage: string | null;
  isSavingLabel: boolean;
  isMergingEvent: boolean;
  onSelectEvent: (eventId: number) => void;
  onOpenPhoto: (sha256: string) => void;
  onUpdateLabel: (eventId: number, label: string) => Promise<boolean>;
  onMergeIntoEvent: (sourceEventId: number, targetEventId: number) => Promise<boolean>;
  onRefreshEventData: (eventId: number) => Promise<void>;
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

function isLikelyDateLabel(label: string): boolean {
  const normalized = label.trim();
  if (!normalized) {
    return false;
  }
  return !Number.isNaN(new Date(normalized).getTime());
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
  actionErrorMessage,
  isSavingLabel,
  isMergingEvent,
  onSelectEvent,
  onOpenPhoto,
  onUpdateLabel,
  onMergeIntoEvent,
  onRefreshEventData,
}: Props) {
  const eventRefs = useRef<Map<number, HTMLButtonElement>>(new Map());
  const [eventSearch, setEventSearch] = useState("");
  const [labelDraft, setLabelDraft] = useState("");
  const [mergeTargetId, setMergeTargetId] = useState("");
  const [photoTargetEventByAsset, setPhotoTargetEventByAsset] = useState<Record<string, string>>({});
  const [isMutatingPhotoEvent, setIsMutatingPhotoEvent] = useState(false);
  const [photoEventErrorMessage, setPhotoEventErrorMessage] = useState<string | null>(null);
  const [photoEventSuccessMessage, setPhotoEventSuccessMessage] = useState<string | null>(null);
  const [presentationStartIndex, setPresentationStartIndex] = useState<number | null>(null);

  const visibleEvents = useMemo(() => {
    const q = eventSearch.trim().toLowerCase();
    if (!q) return events;
    return events.filter((ev) => {
      const label = (ev.label ?? "").toLowerCase();
      return label.includes(q) || formatDate(ev.start_time).toLowerCase().includes(q);
    });
  }, [events, eventSearch]);

  const mergeCandidates = useMemo(() => {
    if (eventDetail === null) {
      return [];
    }

    return events.filter((event) => event.event_id !== eventDetail.event_id);
  }, [eventDetail, events]);

  const reassignCandidates = useMemo(() => {
    if (eventDetail === null) {
      return [];
    }

    const candidates = events.filter((event) => event.event_id !== eventDetail.event_id);

    return [...candidates].sort((left, right) => {
      const leftLabel = left.label?.trim() ?? "";
      const rightLabel = right.label?.trim() ?? "";
      const leftIsNonDateLabel = leftLabel !== "" && !isLikelyDateLabel(leftLabel);
      const rightIsNonDateLabel = rightLabel !== "" && !isLikelyDateLabel(rightLabel);

      if (leftIsNonDateLabel !== rightIsNonDateLabel) {
        return leftIsNonDateLabel ? -1 : 1;
      }

      if (leftIsNonDateLabel && rightIsNonDateLabel) {
        const labelCompare = leftLabel.localeCompare(rightLabel, undefined, { sensitivity: "base" });
        if (labelCompare !== 0) {
          return labelCompare;
        }
      }

      return new Date(right.start_time).getTime() - new Date(left.start_time).getTime();
    });
  }, [eventDetail, events]);

  // Auto-scroll selected event into view in the list.
  useEffect(() => {
    if (selectedEventId === null) return;
    eventRefs.current.get(selectedEventId)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [selectedEventId]);

  useEffect(() => {
    setLabelDraft(eventDetail?.label ?? "");
    setMergeTargetId("");
    setPhotoEventErrorMessage(null);
    setPhotoEventSuccessMessage(null);

    if (eventDetail === null || reassignCandidates.length === 0) {
      setPhotoTargetEventByAsset({});
      return;
    }

    const nextTargets: Record<string, string> = {};
    for (const photo of eventDetail.photos) {
      nextTargets[photo.asset_sha256] = "";
    }
    setPhotoTargetEventByAsset(nextTargets);
  }, [eventDetail, reassignCandidates]);

  function getErrorMessage(error: unknown, fallbackMessage: string): string {
    if (error instanceof Error && error.message) {
      return error.message;
    }

    return fallbackMessage;
  }

  async function handleRemovePhotoFromEvent(assetSha256: string) {
    if (eventDetail === null || isMutatingPhotoEvent) {
      return;
    }

    setIsMutatingPhotoEvent(true);
    setPhotoEventErrorMessage(null);
    setPhotoEventSuccessMessage(null);

    try {
      await removePhotoFromEvent(assetSha256);
      await onRefreshEventData(eventDetail.event_id);
      setPhotoEventSuccessMessage("Removed photo from event.");
    } catch (error) {
      setPhotoEventErrorMessage(getErrorMessage(error, "Failed to remove photo from event."));
    } finally {
      setIsMutatingPhotoEvent(false);
    }
  }

  async function handleAssignPhotoToEvent(assetSha256: string) {
    if (eventDetail === null || isMutatingPhotoEvent) {
      return;
    }

    const targetEventIdText = photoTargetEventByAsset[assetSha256] ?? "";
    const targetEventId = Number.parseInt(targetEventIdText, 10);
    if (Number.isNaN(targetEventId)) {
      setPhotoEventErrorMessage("Select a target event first.");
      return;
    }

    setIsMutatingPhotoEvent(true);
    setPhotoEventErrorMessage(null);
    setPhotoEventSuccessMessage(null);

    try {
      await assignPhotoToEvent(assetSha256, targetEventId);
      await onRefreshEventData(eventDetail.event_id);
      setPhotoEventSuccessMessage("Reassigned photo to the selected event.");
    } catch (error) {
      setPhotoEventErrorMessage(getErrorMessage(error, "Failed to reassign photo to event."));
    } finally {
      setIsMutatingPhotoEvent(false);
    }
  }

  async function handleLabelSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (eventDetail === null || isSavingLabel) {
      return;
    }

    const wasSaved = await onUpdateLabel(eventDetail.event_id, labelDraft);
    if (wasSaved) {
      setLabelDraft(labelDraft.trim());
    }
  }

  async function handleMergeSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (eventDetail === null || isMergingEvent || !mergeTargetId) {
      return;
    }

    const targetEventId = Number.parseInt(mergeTargetId, 10);
    if (Number.isNaN(targetEventId)) {
      return;
    }

    const wasMerged = await onMergeIntoEvent(eventDetail.event_id, targetEventId);
    if (wasMerged) {
      setMergeTargetId("");
    }
  }

  function openEventPresentation(assetSha256: string) {
    if (eventDetail === null) {
      return;
    }

    const currentIndex = eventDetail.photos.findIndex((photo) => photo.asset_sha256 === assetSha256);
    if (currentIndex >= 0) {
      setPresentationStartIndex(currentIndex);
    }
  }

  return (
    <div className={styles.layout}>
      {/* ── Event list ──────────────────────────────────────────────── */}
      <aside className={styles.panel}>
        <div className={styles.panelHeader}>
          <h2 className={styles.panelTitle}>Events</h2>
          <span className={styles.panelCount}>{events.length}</span>
        </div>

        <div className={styles.searchWrapper}>
          <input
            type="search"
            className={styles.searchInput}
            placeholder="Filter events by date..."
            value={eventSearch}
            onChange={(e) => setEventSearch(e.target.value)}
          />
        </div>

        <div className={styles.eventList}>
          {isLoading ? (
            <p className={styles.statusMessage}>Loading events…</p>
          ) : errorMessage ? (
            <p className={styles.errorMessage}>{errorMessage}</p>
          ) : visibleEvents.length === 0 && events.length > 0 ? (
            <p className={styles.statusMessage}>No events match your filter.</p>
          ) : events.length === 0 ? (
            <p className={styles.statusMessage}>No events found.</p>
          ) : (
            visibleEvents.map((ev) => (
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
                {ev.label ? <span className={styles.eventLabel}>{ev.label}</span> : null}
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
              <div className={styles.detailHeaderMain}>
                <form className={styles.labelEditor} onSubmit={handleLabelSubmit}>
                  <label className={styles.fieldLabel} htmlFor="event-label-input">
                    Event Label
                  </label>
                  <div className={styles.inlineFieldRow}>
                    <input
                      id="event-label-input"
                      type="text"
                      className={styles.textInput}
                      placeholder="Add an event label"
                      value={labelDraft}
                      onChange={(e) => setLabelDraft(e.target.value)}
                      disabled={isSavingLabel}
                    />
                    <button type="submit" className={styles.actionButton} disabled={isSavingLabel}>
                      {isSavingLabel ? "Saving..." : "Save Label"}
                    </button>
                  </div>
                </form>
                <h2 className={styles.detailDate}>{eventDetail.label ?? formatDate(eventDetail.start_time)}</h2>
                <p className={styles.detailTime}>{formatTimeRange(eventDetail.start_time, eventDetail.end_time)}</p>
              </div>
              <span className={styles.panelCount}>
                {eventDetail.photos.length} {eventDetail.photos.length === 1 ? "photo" : "photos"}
              </span>
            </div>

            <div className={styles.adminBar}>
              <form className={styles.mergeForm} onSubmit={handleMergeSubmit}>
                <label className={styles.fieldLabel} htmlFor="merge-target-select">
                  Merge This Event Into
                </label>
                <div className={styles.inlineFieldRow}>
                  <select
                    id="merge-target-select"
                    className={styles.selectInput}
                    value={mergeTargetId}
                    onChange={(e) => setMergeTargetId(e.target.value)}
                    disabled={isMergingEvent || mergeCandidates.length === 0}
                  >
                    <option value="">Select target event</option>
                    {mergeCandidates.map((event) => (
                      <option key={event.event_id} value={event.event_id}>
                        {event.label ?? formatDate(event.start_time)}
                      </option>
                    ))}
                  </select>
                  <button
                    type="submit"
                    className={styles.actionButton}
                    disabled={isMergingEvent || !mergeTargetId}
                  >
                    {isMergingEvent ? "Merging..." : "Merge Event"}
                  </button>
                </div>
              </form>
              {actionErrorMessage ? <p className={styles.inlineError}>{actionErrorMessage}</p> : null}
              {photoEventErrorMessage ? <p className={styles.inlineError}>{photoEventErrorMessage}</p> : null}
              {photoEventSuccessMessage ? <p className={styles.inlineSuccess}>{photoEventSuccessMessage}</p> : null}
            </div>

            {eventDetail.photos.length === 0 ? (
              <p className={styles.statusMessage}>No photos in this event.</p>
            ) : (
              <div className={styles.photoGrid}>
                {eventDetail.photos.map((photo) => (
                  <EventPhotoCard
                    key={photo.asset_sha256}
                    photo={photo}
                    targetEventId={photoTargetEventByAsset[photo.asset_sha256] ?? ""}
                    targetEvents={reassignCandidates}
                    isMutatingEvent={isMutatingPhotoEvent}
                    onTargetEventChange={(targetEventId) =>
                      setPhotoTargetEventByAsset((prev) => ({
                        ...prev,
                        [photo.asset_sha256]: targetEventId,
                      }))
                    }
                    onRemoveFromEvent={() => void handleRemovePhotoFromEvent(photo.asset_sha256)}
                    onAssignToEvent={() => void handleAssignPhotoToEvent(photo.asset_sha256)}
                    onOpenPhoto={() => onOpenPhoto(photo.asset_sha256)}
                    onPresent={() => openEventPresentation(photo.asset_sha256)}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
      {eventDetail && presentationStartIndex !== null ? (
        <PresentationViewer
          items={eventDetail.photos}
          initialIndex={presentationStartIndex}
          onClose={() => setPresentationStartIndex(null)}
        />
      ) : null}
    </div>
  );
}

// ── Individual photo card ─────────────────────────────────────────────────────

function EventPhotoCard({
  photo,
  targetEventId,
  targetEvents,
  isMutatingEvent,
  onTargetEventChange,
  onRemoveFromEvent,
  onAssignToEvent,
  onOpenPhoto,
  onPresent,
}: {
  photo: PhotoSummary;
  targetEventId: string;
  targetEvents: EventSummary[];
  isMutatingEvent: boolean;
  onTargetEventChange: (targetEventId: string) => void;
  onRemoveFromEvent: () => void;
  onAssignToEvent: () => void;
  onOpenPhoto: () => void;
  onPresent: () => void;
}) {
  const [imgError, setImgError] = useState(false);
  const imageUrl = resolveApiUrl(photo.image_url);
  const isVideoAsset = isVideoAssetFilename(photo.filename);

  return (
    <article className={styles.photoCard}>
      <button type="button" className={styles.photoThumbButton} onClick={onOpenPhoto} title={`Open ${photo.filename} in Photos view`}>
        <div className={styles.photoThumb}>
          {!isVideoAsset && imageUrl && !imgError ? (
            <img
              src={imageUrl}
              alt={photo.filename}
              className={styles.photoThumbImg}
              onError={() => setImgError(true)}
            />
          ) : (
            <span className={styles.photoThumbPlaceholder}>{isVideoAsset ? "Video" : "?"}</span>
          )}
        </div>
      </button>
      <div className={styles.photoMeta}>
        <span className={styles.photoFilename}>{photo.filename}</span>
        <span className={styles.photoFaceCount}>
          {photo.face_count} {photo.face_count === 1 ? "face" : "faces"}
        </span>
      </div>
      <div className={styles.photoActionRow}>
        <button type="button" className={styles.photoActionButton} onClick={onOpenPhoto}>
          Open
        </button>
        <button type="button" className={styles.photoActionButton} onClick={onPresent}>
          Present
        </button>
      </div>
      <div className={styles.photoEventControls}>
        <select
          className={styles.photoEventSelect}
          value={targetEventId}
          onChange={(event) => onTargetEventChange(event.target.value)}
          disabled={isMutatingEvent || targetEvents.length === 0}
        >
          <option value="">{targetEvents.length === 0 ? "No target events" : "Select event..."}</option>
          {targetEvents.map((event) => (
            <option key={event.event_id} value={event.event_id}>
              {event.label ?? formatDate(event.start_time)}
            </option>
          ))}
        </select>
        <div className={styles.photoEventActions}>
          <button
            type="button"
            className={styles.photoActionButton}
            onClick={onAssignToEvent}
            disabled={isMutatingEvent || !targetEventId}
          >
            Assign
          </button>
          <button
            type="button"
            className={styles.photoActionButton}
            onClick={onRemoveFromEvent}
            disabled={isMutatingEvent}
          >
            Remove
          </button>
        </div>
      </div>
    </article>
  );
}

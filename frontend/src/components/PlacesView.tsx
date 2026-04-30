"use client";

import { forwardRef, useEffect, useMemo, useRef, useState } from "react";
import type { ForwardedRef } from "react";
import type { PlaceSummary, PlaceDetail, PhotoSummary } from "@/types/ui-api";
import { getPlaces, getPlaceDetail, resolveApiUrl, updatePlaceLabel } from "@/lib/api";
import styles from "./places-view.module.css";

interface PlacesViewProps {
  onOpenPhoto: (sha256: string) => void;
}

export default function PlacesView({ onOpenPhoto }: PlacesViewProps) {
  const [places, setPlaces] = useState<PlaceSummary[]>([]);
  const [selectedPlaceId, setSelectedPlaceId] = useState<string | null>(null);
  const [placeDetail, setPlaceDetail] = useState<PlaceDetail | null>(null);
  const [isLoadingPlaces, setIsLoadingPlaces] = useState(false);
  const [isLoadingPlaceDetail, setIsLoadingPlaceDetail] = useState(false);
  const [placesErrorMessage, setPlacesErrorMessage] = useState("");
  const [placeDetailErrorMessage, setPlaceDetailErrorMessage] = useState("");
  const [selectedPhotoId, setSelectedPhotoId] = useState<string | null>(null);
  const [placeSearch, setPlaceSearch] = useState("");
  const [isEditingLabel, setIsEditingLabel] = useState(false);
  const [labelDraft, setLabelDraft] = useState("");
  const [isSavingLabel, setIsSavingLabel] = useState(false);
  const [labelErrorMessage, setLabelErrorMessage] = useState("");
  const placeListRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const photoListRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  const formatCoordinates = (lat: number, lon: number) => {
    return `${lat.toFixed(2)}, ${lon.toFixed(2)}`;
  };

  const visiblePlaces = useMemo(() => {
    const q = placeSearch.trim().toLowerCase();
    if (!q) return places;
    return places.filter((p) => {
      const coordinateText = formatCoordinates(p.latitude, p.longitude).toLowerCase();
      const labelText = p.display_label.toLowerCase();
      const userLabelText = (p.user_label ?? "").toLowerCase();
      const addressText = (p.formatted_address ?? "").toLowerCase();
      return coordinateText.includes(q) || labelText.includes(q) || userLabelText.includes(q) || addressText.includes(q);
    });
  }, [places, placeSearch]);

  // Load places list
  const loadPlaces = async () => {
    setIsLoadingPlaces(true);
    setPlacesErrorMessage("");
    try {
      const response = await getPlaces();
      setPlaces(response.items);
      if (response.items.length > 0 && !selectedPlaceId) {
        setSelectedPlaceId(response.items[0].place_id);
      }
    } catch (err) {
      setPlacesErrorMessage(
        err instanceof Error ? err.message : "Failed to load places"
      );
    } finally {
      setIsLoadingPlaces(false);
    }
  };

  // Load place detail
  const loadPlaceDetail = async (placeId: string) => {
    setIsLoadingPlaceDetail(true);
    setPlaceDetailErrorMessage("");
    try {
      const detail = await getPlaceDetail(placeId);
      setPlaceDetail(detail);
      setSelectedPhotoId(null);
      setIsEditingLabel(false);
      setLabelDraft(detail.user_label ?? "");
      setLabelErrorMessage("");
    } catch (err) {
      setPlaceDetailErrorMessage(
        err instanceof Error ? err.message : "Failed to load place details"
      );
    } finally {
      setIsLoadingPlaceDetail(false);
    }
  };

  // Initial load
  useEffect(() => {
    loadPlaces();
  }, []);

  // Load detail when place selected
  useEffect(() => {
    if (selectedPlaceId) {
      loadPlaceDetail(selectedPlaceId);
      placeListRefs.current.get(selectedPlaceId)?.scrollIntoView({
        behavior: "smooth",
        block: "nearest"
      });
    }
  }, [selectedPlaceId]);

  const geocodedLabel = useMemo(() => {
    if (!placeDetail) return "";
    if (placeDetail.user_label && placeDetail.user_label.trim()) {
      const geoLabel = placeDetail.display_label;
      const fallbackParts = [
        placeDetail.city,
        placeDetail.state,
        placeDetail.country
      ].filter(Boolean) as string[];
      return fallbackParts.join(", ") || placeDetail.formatted_address || geoLabel;
    }
    return placeDetail.formatted_address || "";
  }, [placeDetail]);

  const saveLabel = async () => {
    if (!selectedPlaceId) return;
    setIsSavingLabel(true);
    setLabelErrorMessage("");
    try {
      const updated = await updatePlaceLabel(selectedPlaceId, labelDraft);
      setPlaceDetail(updated);
      setLabelDraft(updated.user_label ?? "");
      setIsEditingLabel(false);
      setPlaces((prev) => prev.map((place) => {
        if (place.place_id !== selectedPlaceId) return place;
        return {
          ...place,
          user_label: updated.user_label,
          display_label: updated.display_label,
          formatted_address: updated.formatted_address,
          city: updated.city,
          county: updated.county,
          state: updated.state,
          country: updated.country,
          geocode_status: updated.geocode_status,
        };
      }));
    } catch (err) {
      setLabelErrorMessage(err instanceof Error ? err.message : "Failed to update place name");
    } finally {
      setIsSavingLabel(false);
    }
  };

  const clearLabel = async () => {
    if (!selectedPlaceId) return;
    setIsSavingLabel(true);
    setLabelErrorMessage("");
    try {
      const updated = await updatePlaceLabel(selectedPlaceId, null);
      setPlaceDetail(updated);
      setLabelDraft("");
      setIsEditingLabel(false);
      setPlaces((prev) => prev.map((place) => {
        if (place.place_id !== selectedPlaceId) return place;
        return {
          ...place,
          user_label: updated.user_label,
          display_label: updated.display_label,
          formatted_address: updated.formatted_address,
          city: updated.city,
          county: updated.county,
          state: updated.state,
          country: updated.country,
          geocode_status: updated.geocode_status,
        };
      }));
    } catch (err) {
      setLabelErrorMessage(err instanceof Error ? err.message : "Failed to clear place name");
    } finally {
      setIsSavingLabel(false);
    }
  };

  // Auto-scroll photo to selected
  useEffect(() => {
    if (selectedPhotoId) {
      photoListRefs.current.get(selectedPhotoId)?.scrollIntoView({
        behavior: "smooth",
        block: "nearest"
      });
    }
  }, [selectedPhotoId]);

  return (
    <div className={styles.container}>
      {/* Place List */}
      <div className={styles.placeList}>
        <div className={styles.header}>
          <h2>Places</h2>
          {isLoadingPlaces && <span className={styles.loading}>Loading...</span>}
        </div>
        {placesErrorMessage && (
          <div className={styles.error}>{placesErrorMessage}</div>
        )}
        {places.length === 0 && !isLoadingPlaces && (
          <div className={styles.noData}>No places found</div>
        )}
        {places.length > 0 && (
          <div className={styles.searchWrapper}>
            <input
              type="search"
              className={styles.searchInput}
              placeholder="Filter by location or coordinates..."
              value={placeSearch}
              onChange={(e) => setPlaceSearch(e.target.value)}
            />
          </div>
        )}
        {visiblePlaces.length === 0 && places.length > 0 && (
          <div className={styles.noData}>No places match your filter.</div>
        )}
        <div className={styles.list}>
          {visiblePlaces.map((place) => (
            <div
              key={place.place_id}
              ref={(el) => {
                if (el) placeListRefs.current.set(place.place_id, el);
              }}
              className={`${styles.placeItem} ${
                selectedPlaceId === place.place_id ? styles.active : ""
              }`}
              onClick={() => setSelectedPlaceId(place.place_id)}
            >
              <PlaceThumb thumbnailUrl={place.thumbnail_url} />
              <div className={styles.placeItemContent}>
                <div className={styles.coordinates}>
                  {place.display_label}
                </div>
                {place.user_label && (
                  <div className={styles.userLabelMeta}>{place.formatted_address ?? formatCoordinates(place.latitude, place.longitude)}</div>
                )}
                <div className={styles.coordinateMeta}>
                  {formatCoordinates(place.latitude, place.longitude)}
                </div>
                <div className={styles.photoCount}>
                  {place.photo_count} {place.photo_count === 1 ? "photo" : "photos"}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Place Detail */}
      <div className={styles.placeDetail}>
        {placeDetail && (
          <>
            <div className={styles.detailHeader}>
              <div>
                <h3>{placeDetail.display_label}</h3>
                {geocodedLabel && <div className={styles.userLabelMeta}>{geocodedLabel}</div>}
                <div className={styles.coordinateMeta}>
                  {formatCoordinates(placeDetail.latitude, placeDetail.longitude)}
                </div>
              </div>
              <div className={styles.detailBadge}>
                {placeDetail.photos.length}{" "}
                {placeDetail.photos.length === 1 ? "photo" : "photos"}
              </div>
            </div>
            <div className={styles.labelEditorRow}>
              {isEditingLabel ? (
                <>
                  <input
                    type="text"
                    maxLength={120}
                    value={labelDraft}
                    onChange={(event) => setLabelDraft(event.target.value)}
                    className={styles.labelInput}
                    placeholder="Place name (e.g., Audrey's House)"
                  />
                  <button type="button" className={styles.labelButtonPrimary} disabled={isSavingLabel} onClick={saveLabel}>Save</button>
                  <button
                    type="button"
                    className={styles.labelButton}
                    disabled={isSavingLabel}
                    onClick={() => {
                      setIsEditingLabel(false);
                      setLabelDraft(placeDetail.user_label ?? "");
                      setLabelErrorMessage("");
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    className={styles.labelButtonDanger}
                    disabled={isSavingLabel}
                    onClick={() => {
                      void clearLabel();
                    }}
                  >
                    Clear
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  className={styles.labelButton}
                  onClick={() => {
                    setIsEditingLabel(true);
                    setLabelDraft(placeDetail.user_label ?? "");
                    setLabelErrorMessage("");
                  }}
                >
                  Edit Name
                </button>
              )}
            </div>
            {labelErrorMessage && <div className={styles.error}>{labelErrorMessage}</div>}
            {isLoadingPlaceDetail && <div className={styles.loading}>Loading photos...</div>}
            {placeDetailErrorMessage && (
              <div className={styles.error}>{placeDetailErrorMessage}</div>
            )}
            <div className={styles.photoGrid}>
              {placeDetail.photos.map((photo) => (
                <PlacePhotoCard
                  key={photo.asset_sha256}
                  photo={photo}
                  isSelected={selectedPhotoId === photo.asset_sha256}
                  isLoadingDetail={isLoadingPlaceDetail}
                  ref={(el) => {
                    if (el) photoListRefs.current.set(photo.asset_sha256, el);
                  }}
                  onClick={() => {
                    setSelectedPhotoId(photo.asset_sha256);
                    onOpenPhoto(photo.asset_sha256);
                  }}
                />
              ))}
            </div>
          </>
        )}
        {!placeDetail && !isLoadingPlaceDetail && selectedPlaceId && (
          <div className={styles.noData}>No photos at this location</div>
        )}
      </div>
    </div>
  );
}

interface PlacePhotoCardProps {
  photo: PhotoSummary;
  isSelected: boolean;
  isLoadingDetail: boolean;
  onClick: () => void;
}

const PlacePhotoCard = forwardRef<HTMLDivElement, PlacePhotoCardProps>(
  ({ photo, isSelected, isLoadingDetail, onClick }, ref: ForwardedRef<HTMLDivElement>) => {
    const [imgError, setImgError] = useState(false);
    const imageUrl = resolveApiUrl(photo.image_url);

    return (
      <div
        ref={ref}
        className={`${styles.photoCard} ${isSelected ? styles.selectedPhoto : ""}`}
        onClick={onClick}
      >
        <div className={styles.photoImage}>
          {imageUrl && !imgError ? (
            <img
              src={imageUrl}
              alt={photo.filename}
              onError={() => setImgError(true)}
            />
          ) : (
            <div className={styles.imagePlaceholder}>?</div>
          )}
        </div>
        <div className={styles.photoInfo}>
          <div className={styles.filename} title={photo.filename}>
            {photo.filename}
          </div>
          {photo.face_count > 0 && (
            <div className={styles.faceCount}>{photo.face_count} faces</div>
          )}
        </div>
      </div>
    );
  }
);
PlacePhotoCard.displayName = "PlacePhotoCard";

interface PlaceThumbProps {
  thumbnailUrl: string | null;
}

function PlaceThumb({ thumbnailUrl }: PlaceThumbProps) {
  const [imgError, setImgError] = useState(false);
  const resolvedUrl = thumbnailUrl ? resolveApiUrl(thumbnailUrl) : null;

  return (
    <div className={styles.placeThumb}>
      {resolvedUrl && !imgError ? (
        <img
          src={resolvedUrl}
          alt=""
          className={styles.placeThumbImg}
          onError={() => setImgError(true)}
        />
      ) : (
        <div className={styles.placeThumbPlaceholder}>📍</div>
      )}
    </div>
  );
}

"use client";

import { forwardRef, useEffect, useMemo, useRef, useState } from "react";
import type { ForwardedRef } from "react";
import type {
  PlaceDetail,
  PlaceObservationSummary,
  PlacePatchRequest,
  PlaceSummary,
  PhotoSummary,
} from "@/types/ui-api";
import {
  addPlaceAlias,
  deletePlaceAlias,
  getPlaceDetail,
  getPlaceObservations,
  getPlaces,
  patchPlace,
  patchPlaceObservation,
  resolveApiUrl,
} from "@/lib/api";
import styles from "./places-view.module.css";

interface PlacesViewProps {
  onOpenPhoto: (sha256: string) => void;
}

interface ApplyDialogState {
  observation: PlaceObservationSummary;
  setUserVerified: boolean;
  setAddressLocked: boolean;
}

const PLACE_TYPE_OPTIONS = [
  "generic",
  "home",
  "personal_place",
  "city",
  "landmark",
  "school",
  "business",
  "park",
  "venue",
  "unknown",
] as const;

export default function PlacesView({ onOpenPhoto }: PlacesViewProps) {
  const [places, setPlaces] = useState<PlaceSummary[]>([]);
  const [selectedPlaceId, setSelectedPlaceId] = useState<string | null>(null);
  const [placeDetail, setPlaceDetail] = useState<PlaceDetail | null>(null);
  const [observations, setObservations] = useState<PlaceObservationSummary[]>([]);
  const [expandedObservationIds, setExpandedObservationIds] = useState<Set<number>>(new Set());
  const [applyDialogState, setApplyDialogState] = useState<ApplyDialogState | null>(null);
  const [isLoadingPlaces, setIsLoadingPlaces] = useState(false);
  const [isLoadingPlaceDetail, setIsLoadingPlaceDetail] = useState(false);
  const [isLoadingObservations, setIsLoadingObservations] = useState(false);
  const [isSavingCanonical, setIsSavingCanonical] = useState(false);
  const [isSavingAlias, setIsSavingAlias] = useState(false);
  const [updatingObservationId, setUpdatingObservationId] = useState<number | null>(null);
  const [placesErrorMessage, setPlacesErrorMessage] = useState("");
  const [placeDetailErrorMessage, setPlaceDetailErrorMessage] = useState("");
  const [observationErrorMessage, setObservationErrorMessage] = useState("");
  const [canonicalErrorMessage, setCanonicalErrorMessage] = useState("");
  const [aliasErrorMessage, setAliasErrorMessage] = useState("");
  const [selectedPhotoId, setSelectedPhotoId] = useState<string | null>(null);
  const [placeSearch, setPlaceSearch] = useState("");
  const [aliasDraft, setAliasDraft] = useState("");
  const [canonicalDraft, setCanonicalDraft] = useState<PlacePatchRequest>({});
  const placeListRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const photoListRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  const formatCoordinates = (lat: number, lon: number) => `${lat.toFixed(2)}, ${lon.toFixed(2)}`;
  const formatCoordinatesFull = (lat: number, lon: number) => `${lat.toFixed(5)}, ${lon.toFixed(5)}`;

  const visiblePlaces = useMemo(() => {
    const q = placeSearch.trim().toLowerCase();
    if (!q) return places;
    return places.filter((p) => {
      const coordinateText = formatCoordinates(p.latitude, p.longitude).toLowerCase();
      const coordinateTextFull = formatCoordinatesFull(p.latitude, p.longitude).toLowerCase();
      const labelText = p.display_label.toLowerCase();
      const userLabelText = (p.user_label ?? "").toLowerCase();
      const addressText = (p.formatted_address ?? "").toLowerCase();
      const placeTypeText = p.place_type.toLowerCase();
      return (
        coordinateText.includes(q)
        || coordinateTextFull.includes(q)
        || labelText.includes(q)
        || userLabelText.includes(q)
        || addressText.includes(q)
        || placeTypeText.includes(q)
      );
    });
  }, [places, placeSearch]);

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
      setPlacesErrorMessage(err instanceof Error ? err.message : "Failed to load places");
    } finally {
      setIsLoadingPlaces(false);
    }
  };

  const syncCanonicalDraft = (detail: PlaceDetail) => {
    setCanonicalDraft({
      user_label: detail.user_label ?? "",
      place_type: detail.place_type,
      formatted_address: detail.formatted_address ?? "",
      street: detail.street ?? "",
      city: detail.city ?? "",
      county: detail.county ?? "",
      state: detail.state ?? "",
      postal_code: detail.postal_code ?? "",
      country: detail.country ?? "",
      notes: detail.notes ?? "",
      user_verified: detail.user_verified,
      address_locked: detail.address_locked,
      address_source: detail.address_source ?? "manual",
    });
  };

  const loadPlaceDetail = async (placeId: string) => {
    setIsLoadingPlaceDetail(true);
    setPlaceDetailErrorMessage("");
    try {
      const detail = await getPlaceDetail(placeId);
      setPlaceDetail(detail);
      syncCanonicalDraft(detail);
      setSelectedPhotoId(null);
      setCanonicalErrorMessage("");
      setAliasErrorMessage("");
    } catch (err) {
      setPlaceDetailErrorMessage(err instanceof Error ? err.message : "Failed to load place details");
    } finally {
      setIsLoadingPlaceDetail(false);
    }
  };

  const loadPlaceObservations = async (placeId: string) => {
    setIsLoadingObservations(true);
    setObservationErrorMessage("");
    try {
      const response = await getPlaceObservations(placeId, 200);
      setObservations(response.items);
    } catch (err) {
      setObservationErrorMessage(err instanceof Error ? err.message : "Failed to load observations");
      setObservations([]);
    } finally {
      setIsLoadingObservations(false);
    }
  };

  const updatePlaceRowFromDetail = (detail: PlaceDetail) => {
    setPlaces((prev) => prev.map((place) => {
      if (place.place_id !== detail.place_id) return place;
      return {
        ...place,
        user_label: detail.user_label,
        display_label: detail.display_label,
        formatted_address: detail.formatted_address,
        city: detail.city,
        county: detail.county,
        state: detail.state,
        postal_code: detail.postal_code,
        country: detail.country,
        place_type: detail.place_type,
        user_verified: detail.user_verified,
        address_locked: detail.address_locked,
        geocode_status: detail.geocode_status,
      };
    }));
  };

  const handleCanonicalSave = async () => {
    if (!selectedPlaceId) return;
    setIsSavingCanonical(true);
    setCanonicalErrorMessage("");
    try {
      const payload: PlacePatchRequest = {
        user_label: canonicalDraft.user_label?.trim() ? canonicalDraft.user_label.trim() : null,
        place_type: canonicalDraft.place_type,
        formatted_address: canonicalDraft.formatted_address?.trim() ? canonicalDraft.formatted_address.trim() : null,
        street: canonicalDraft.street?.trim() ? canonicalDraft.street.trim() : null,
        city: canonicalDraft.city?.trim() ? canonicalDraft.city.trim() : null,
        county: canonicalDraft.county?.trim() ? canonicalDraft.county.trim() : null,
        state: canonicalDraft.state?.trim() ? canonicalDraft.state.trim() : null,
        postal_code: canonicalDraft.postal_code?.trim() ? canonicalDraft.postal_code.trim() : null,
        country: canonicalDraft.country?.trim() ? canonicalDraft.country.trim() : null,
        notes: canonicalDraft.notes?.trim() ? canonicalDraft.notes.trim() : null,
        user_verified: Boolean(canonicalDraft.user_verified),
        address_locked: Boolean(canonicalDraft.address_locked),
        address_source: canonicalDraft.address_source?.trim() ? canonicalDraft.address_source.trim() : "manual",
      };

      const updated = await patchPlace(selectedPlaceId, payload);
      setPlaceDetail(updated);
      syncCanonicalDraft(updated);
      updatePlaceRowFromDetail(updated);
    } catch (err) {
      setCanonicalErrorMessage(err instanceof Error ? err.message : "Failed to save canonical place fields");
    } finally {
      setIsSavingCanonical(false);
    }
  };

  const handleAddAlias = async () => {
    if (!selectedPlaceId || !aliasDraft.trim()) return;
    setIsSavingAlias(true);
    setAliasErrorMessage("");
    try {
      const created = await addPlaceAlias(selectedPlaceId, aliasDraft.trim());
      setPlaceDetail((prev) => {
        if (!prev || prev.place_id !== selectedPlaceId) return prev;
        return { ...prev, aliases: [...prev.aliases, created].sort((a, b) => a.alias.localeCompare(b.alias)) };
      });
      setAliasDraft("");
      setPlaces((prev) => prev.map((place) => (
        place.place_id === selectedPlaceId
          ? { ...place, alias_count: place.alias_count + 1 }
          : place
      )));
    } catch (err) {
      setAliasErrorMessage(err instanceof Error ? err.message : "Failed to add alias");
    } finally {
      setIsSavingAlias(false);
    }
  };

  const handleDeleteAlias = async (aliasId: number) => {
    if (!selectedPlaceId) return;
    setIsSavingAlias(true);
    setAliasErrorMessage("");
    try {
      await deletePlaceAlias(selectedPlaceId, aliasId);
      setPlaceDetail((prev) => {
        if (!prev || prev.place_id !== selectedPlaceId) return prev;
        return { ...prev, aliases: prev.aliases.filter((alias) => alias.id !== aliasId) };
      });
      setPlaces((prev) => prev.map((place) => (
        place.place_id === selectedPlaceId
          ? { ...place, alias_count: Math.max(0, place.alias_count - 1) }
          : place
      )));
    } catch (err) {
      setAliasErrorMessage(err instanceof Error ? err.message : "Failed to delete alias");
    } finally {
      setIsSavingAlias(false);
    }
  };

  const handleObservationStatus = async (
    observationId: number,
    status: "accepted" | "rejected" | "ignored",
    options?: { applyToCanonical?: boolean; setUserVerified?: boolean; setAddressLocked?: boolean },
  ) => {
    if (!selectedPlaceId) return;
    setUpdatingObservationId(observationId);
    setObservationErrorMessage("");
    try {
      const updated = await patchPlaceObservation(selectedPlaceId, observationId, {
        status,
        apply_to_canonical: Boolean(options?.applyToCanonical),
        set_user_verified: Boolean(options?.setUserVerified),
        set_address_locked: Boolean(options?.setAddressLocked),
      });
      setObservations((prev) => prev.map((item) => (item.id === observationId ? updated : item)));
      if (options?.applyToCanonical) {
        const refreshed = await getPlaceDetail(selectedPlaceId);
        setPlaceDetail(refreshed);
        syncCanonicalDraft(refreshed);
        updatePlaceRowFromDetail(refreshed);
      }
    } catch (err) {
      setObservationErrorMessage(err instanceof Error ? err.message : "Failed to update observation");
    } finally {
      setUpdatingObservationId(null);
    }
  };

  useEffect(() => {
    void loadPlaces();
  }, []);

  useEffect(() => {
    if (selectedPlaceId) {
      void loadPlaceDetail(selectedPlaceId);
      void loadPlaceObservations(selectedPlaceId);
      placeListRefs.current.get(selectedPlaceId)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [selectedPlaceId]);

  useEffect(() => {
    if (selectedPhotoId) {
      photoListRefs.current.get(selectedPhotoId)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [selectedPhotoId]);

  const geocodedLabel = useMemo(() => {
    if (!placeDetail) return "";
    const fallbackParts = [placeDetail.city, placeDetail.state, placeDetail.country].filter(Boolean) as string[];
    return fallbackParts.join(", ") || placeDetail.formatted_address || "";
  }, [placeDetail]);

  return (
    <div className={styles.container}>
      <div className={styles.placeList}>
        <div className={styles.header}>
          <h2>Places</h2>
          {isLoadingPlaces && <span className={styles.loading}>Loading...</span>}
        </div>
        {placesErrorMessage && <div className={styles.error}>{placesErrorMessage}</div>}
        {places.length === 0 && !isLoadingPlaces && <div className={styles.noData}>No places found</div>}
        {places.length > 0 && (
          <div className={styles.searchWrapper}>
            <input
              type="search"
              className={styles.searchInput}
              placeholder="Filter by name, type, address, coordinates..."
              value={placeSearch}
              onChange={(e) => setPlaceSearch(e.target.value)}
            />
          </div>
        )}
        {visiblePlaces.length === 0 && places.length > 0 && <div className={styles.noData}>No places match your filter.</div>}
        <div className={styles.list}>
          {visiblePlaces.map((place) => (
            <div
              key={place.place_id}
              ref={(el) => {
                if (el) placeListRefs.current.set(place.place_id, el);
              }}
              className={`${styles.placeItem} ${selectedPlaceId === place.place_id ? styles.active : ""}`}
              onClick={() => setSelectedPlaceId(place.place_id)}
            >
              <PlaceThumb thumbnailUrl={place.thumbnail_url} />
              <div className={styles.placeItemContent}>
                <div className={styles.coordinates}>{place.display_label}</div>
                <div className={styles.userLabelMeta}>{place.formatted_address ?? formatCoordinates(place.latitude, place.longitude)}</div>
                <div className={styles.coordinateMeta}>{formatCoordinates(place.latitude, place.longitude)}</div>
                <div className={styles.badgeRow}>
                  <span className={styles.inlineBadge}>{place.place_type}</span>
                  {place.user_verified && <span className={styles.inlineBadge}>verified</span>}
                  {place.address_locked && <span className={styles.inlineBadge}>locked</span>}
                  {place.alias_count > 0 && <span className={styles.inlineBadge}>{place.alias_count} aliases</span>}
                </div>
                <div className={styles.photoCount}>{place.photo_count} {place.photo_count === 1 ? "photo" : "photos"}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className={styles.placeDetail}>
        {placeDetail && (
          <>
            <div className={styles.detailHeader}>
              <div>
                <h3>{placeDetail.display_label}</h3>
                {geocodedLabel && <div className={styles.userLabelMeta}>{geocodedLabel}</div>}
                <div className={styles.coordinateMeta}>{formatCoordinates(placeDetail.latitude, placeDetail.longitude)}</div>
              </div>
              <div className={styles.detailBadge}>{placeDetail.photos.length} {placeDetail.photos.length === 1 ? "photo" : "photos"}</div>
            </div>

            <div className={styles.section}>
              <div className={styles.sectionTitle}>Canonical Place Information</div>
              <div className={styles.inlineHint}>Verified or locked addresses will not be overwritten automatically by provider results.</div>
              <div className={styles.formGrid}>
                <label className={styles.fieldLabel}>Place Name
                  <input
                    type="text"
                    maxLength={120}
                    className={styles.labelInput}
                    value={canonicalDraft.user_label ?? ""}
                    onChange={(event) => setCanonicalDraft((prev) => ({ ...prev, user_label: event.target.value }))}
                  />
                </label>
                <label className={styles.fieldLabel}>Place Type
                  <select
                    className={styles.selectInput}
                    value={canonicalDraft.place_type ?? "generic"}
                    onChange={(event) => setCanonicalDraft((prev) => ({ ...prev, place_type: event.target.value }))}
                  >
                    {PLACE_TYPE_OPTIONS.map((option) => (
                      <option key={option} value={option}>{option}</option>
                    ))}
                  </select>
                </label>
                <label className={styles.fieldLabelWide}>Formatted Address
                  <input
                    type="text"
                    className={styles.labelInput}
                    value={canonicalDraft.formatted_address ?? ""}
                    onChange={(event) => setCanonicalDraft((prev) => ({ ...prev, formatted_address: event.target.value }))}
                  />
                </label>
                <label className={styles.fieldLabel}>Street
                  <input
                    type="text"
                    className={styles.labelInput}
                    value={canonicalDraft.street ?? ""}
                    onChange={(event) => setCanonicalDraft((prev) => ({ ...prev, street: event.target.value }))}
                  />
                </label>
                <label className={styles.fieldLabel}>City
                  <input
                    type="text"
                    className={styles.labelInput}
                    value={canonicalDraft.city ?? ""}
                    onChange={(event) => setCanonicalDraft((prev) => ({ ...prev, city: event.target.value }))}
                  />
                </label>
                <label className={styles.fieldLabel}>County
                  <input
                    type="text"
                    className={styles.labelInput}
                    value={canonicalDraft.county ?? ""}
                    onChange={(event) => setCanonicalDraft((prev) => ({ ...prev, county: event.target.value }))}
                  />
                </label>
                <label className={styles.fieldLabel}>State
                  <input
                    type="text"
                    className={styles.labelInput}
                    value={canonicalDraft.state ?? ""}
                    onChange={(event) => setCanonicalDraft((prev) => ({ ...prev, state: event.target.value }))}
                  />
                </label>
                <label className={styles.fieldLabel}>Postal Code
                  <input
                    type="text"
                    className={styles.labelInput}
                    value={canonicalDraft.postal_code ?? ""}
                    onChange={(event) => setCanonicalDraft((prev) => ({ ...prev, postal_code: event.target.value }))}
                  />
                </label>
                <label className={styles.fieldLabel}>Country
                  <input
                    type="text"
                    className={styles.labelInput}
                    value={canonicalDraft.country ?? ""}
                    onChange={(event) => setCanonicalDraft((prev) => ({ ...prev, country: event.target.value }))}
                  />
                </label>
                <label className={styles.fieldLabel}>Address Source
                  <input
                    type="text"
                    className={styles.labelInput}
                    value={canonicalDraft.address_source ?? ""}
                    onChange={(event) => setCanonicalDraft((prev) => ({ ...prev, address_source: event.target.value }))}
                  />
                </label>
                <label className={styles.fieldCheckbox}>
                  <input
                    type="checkbox"
                    checked={Boolean(canonicalDraft.user_verified)}
                    onChange={(event) => setCanonicalDraft((prev) => ({ ...prev, user_verified: event.target.checked }))}
                  />
                  User verified
                </label>
                <label className={styles.fieldCheckbox}>
                  <input
                    type="checkbox"
                    checked={Boolean(canonicalDraft.address_locked)}
                    onChange={(event) => setCanonicalDraft((prev) => ({ ...prev, address_locked: event.target.checked }))}
                  />
                  Address locked
                </label>
                <label className={styles.fieldLabelWide}>Notes
                  <textarea
                    className={styles.textAreaInput}
                    value={canonicalDraft.notes ?? ""}
                    onChange={(event) => setCanonicalDraft((prev) => ({ ...prev, notes: event.target.value }))}
                    rows={3}
                  />
                </label>
              </div>
              <div className={styles.rowActions}>
                <button type="button" className={styles.labelButtonPrimary} disabled={isSavingCanonical} onClick={() => { void handleCanonicalSave(); }}>
                  Save Canonical Fields
                </button>
              </div>
              {canonicalErrorMessage && <div className={styles.error}>{canonicalErrorMessage}</div>}
            </div>

            <div className={styles.aliasSection}>
              <div className={styles.aliasHeader}>Aliases</div>
              <div className={styles.aliasEditorRow}>
                <input
                  type="text"
                  value={aliasDraft}
                  onChange={(event) => setAliasDraft(event.target.value)}
                  className={styles.labelInput}
                  placeholder="Add alias (e.g., Home, Audrey's House)"
                  maxLength={255}
                />
                <button
                  type="button"
                  className={styles.labelButtonPrimary}
                  onClick={() => { void handleAddAlias(); }}
                  disabled={isSavingAlias || !aliasDraft.trim()}
                >
                  Add Alias
                </button>
              </div>
              {aliasErrorMessage && <div className={styles.error}>{aliasErrorMessage}</div>}
              <div className={styles.aliasList}>
                {(placeDetail.aliases ?? []).length === 0 && <div className={styles.aliasEmpty}>No aliases yet.</div>}
                {(placeDetail.aliases ?? []).map((alias) => (
                  <div key={alias.id} className={styles.aliasChip}>
                    <span>{alias.alias}</span>
                    <button
                      type="button"
                      className={styles.aliasDeleteButton}
                      onClick={() => { void handleDeleteAlias(alias.id); }}
                      disabled={isSavingAlias}
                      aria-label={`Delete alias ${alias.alias}`}
                    >
                      x
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div className={styles.section}>
              <div className={styles.sectionTitle}>Provider / Source Observations</div>
              {isLoadingObservations && <div className={styles.loading}>Loading observations...</div>}
              {observationErrorMessage && <div className={styles.error}>{observationErrorMessage}</div>}
              {!isLoadingObservations && observations.length === 0 && (
                <div className={styles.aliasEmpty}>No observations for this place yet.</div>
              )}
              <div className={styles.observationList}>
                {observations.map((observation) => {
                  const isExpanded = expandedObservationIds.has(observation.id);
                  const addressText = observation.formatted_address
                    || observation.raw_label
                    || [observation.street, observation.city, observation.state, observation.country].filter(Boolean).join(", ");
                  const canApplyAddress = observation.observation_type === "address";

                  return (
                    <div key={observation.id} className={styles.observationCard}>
                      <div className={styles.observationTop}>
                        <div className={styles.badgeRow}>
                          <span className={styles.inlineBadge}>{observation.source_type}</span>
                          <span className={styles.inlineBadge}>{observation.observation_type}</span>
                          <span className={styles.inlineBadge}>status: {observation.status}</span>
                        </div>
                        <div className={styles.observationAddress}>{addressText || "(No address text)"}</div>
                        <div className={styles.observationMeta}>
                          {observation.confidence !== null && observation.confidence !== undefined ? `confidence: ${observation.confidence}` : ""}
                          {observation.created_at_utc ? `${observation.confidence !== null && observation.confidence !== undefined ? " | " : ""}created: ${new Date(observation.created_at_utc).toLocaleString()}` : ""}
                        </div>
                      </div>
                      <div className={styles.rowActions}>
                        <button
                          type="button"
                          className={styles.labelButtonPrimary}
                          disabled={updatingObservationId === observation.id}
                          onClick={() => { void handleObservationStatus(observation.id, "accepted"); }}
                        >
                          Accept
                        </button>
                        {canApplyAddress && (
                          <button
                            type="button"
                            className={styles.labelButton}
                            disabled={updatingObservationId === observation.id}
                            onClick={() => {
                              setApplyDialogState({
                                observation,
                                setUserVerified: Boolean(placeDetail.user_verified),
                                setAddressLocked: Boolean(placeDetail.address_locked),
                              });
                            }}
                          >
                            Accept + Apply
                          </button>
                        )}
                        <button
                          type="button"
                          className={styles.labelButtonDanger}
                          disabled={updatingObservationId === observation.id}
                          onClick={() => { void handleObservationStatus(observation.id, "rejected"); }}
                        >
                          Reject
                        </button>
                        <button
                          type="button"
                          className={styles.labelButton}
                          disabled={updatingObservationId === observation.id}
                          onClick={() => { void handleObservationStatus(observation.id, "ignored"); }}
                        >
                          Ignore
                        </button>
                        <button
                          type="button"
                          className={styles.aliasDeleteButton}
                          onClick={() => {
                            setExpandedObservationIds((prev) => {
                              const next = new Set(prev);
                              if (next.has(observation.id)) {
                                next.delete(observation.id);
                              } else {
                                next.add(observation.id);
                              }
                              return next;
                            });
                          }}
                        >
                          {isExpanded ? "Hide details" : "Show details"}
                        </button>
                      </div>
                      {isExpanded && (
                        <pre className={styles.observationDetails}>{JSON.stringify({
                          latitude: observation.latitude,
                          longitude: observation.longitude,
                          raw_response_json: observation.raw_response_json,
                        }, null, 2)}</pre>
                      )}
                    </div>
                  );
                })}
              </div>

              {applyDialogState && (
                <div className={styles.applyDialog}>
                  <div className={styles.applyDialogTitle}>Apply observation to canonical address?</div>
                  <div className={styles.applyDialogText}>
                    <strong>Current canonical:</strong> {placeDetail.formatted_address ?? "(empty)"}
                  </div>
                  <div className={styles.applyDialogText}>
                    <strong>Observation:</strong> {applyDialogState.observation.formatted_address ?? applyDialogState.observation.raw_label ?? "(empty)"}
                  </div>
                  <div className={styles.applyDialogText}>
                    <strong>Source:</strong> {applyDialogState.observation.source_type}
                  </div>
                  <label className={styles.fieldCheckbox}>
                    <input
                      type="checkbox"
                      checked={applyDialogState.setUserVerified}
                      onChange={(event) => setApplyDialogState((prev) => prev ? { ...prev, setUserVerified: event.target.checked } : null)}
                    />
                    Mark place as user verified
                  </label>
                  <label className={styles.fieldCheckbox}>
                    <input
                      type="checkbox"
                      checked={applyDialogState.setAddressLocked}
                      onChange={(event) => setApplyDialogState((prev) => prev ? { ...prev, setAddressLocked: event.target.checked } : null)}
                    />
                    Lock address against provider overwrite
                  </label>
                  <div className={styles.rowActions}>
                    <button
                      type="button"
                      className={styles.labelButtonPrimary}
                      disabled={updatingObservationId === applyDialogState.observation.id}
                      onClick={() => {
                        void handleObservationStatus(applyDialogState.observation.id, "accepted", {
                          applyToCanonical: true,
                          setUserVerified: applyDialogState.setUserVerified,
                          setAddressLocked: applyDialogState.setAddressLocked,
                        });
                        setApplyDialogState(null);
                      }}
                    >
                      Confirm Apply
                    </button>
                    <button
                      type="button"
                      className={styles.labelButton}
                      onClick={() => setApplyDialogState(null)}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>

            {isLoadingPlaceDetail && <div className={styles.loading}>Loading photos...</div>}
            {placeDetailErrorMessage && <div className={styles.error}>{placeDetailErrorMessage}</div>}
            <div className={styles.photoGrid}>
              {placeDetail.photos.map((photo) => (
                <PlacePhotoCard
                  key={photo.asset_sha256}
                  photo={photo}
                  isSelected={selectedPhotoId === photo.asset_sha256}
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
        {!placeDetail && !isLoadingPlaceDetail && selectedPlaceId && <div className={styles.noData}>No photos at this location</div>}
      </div>
    </div>
  );
}

interface PlacePhotoCardProps {
  photo: PhotoSummary;
  isSelected: boolean;
  onClick: () => void;
}

const PlacePhotoCard = forwardRef<HTMLDivElement, PlacePhotoCardProps>(
  ({ photo, isSelected, onClick }, ref: ForwardedRef<HTMLDivElement>) => {
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
          {photo.face_count > 0 && <div className={styles.faceCount}>{photo.face_count} faces</div>}
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

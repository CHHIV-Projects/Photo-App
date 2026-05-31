import type {
  AdminDuplicateProcessingActionResponse,
  AdminDuplicateProcessingStatusResponse,
  AdminFaceProcessingActionResponse,
  AdminFaceProcessingStatusResponse,
  AdminHeicPreviewActionResponse,
  AdminHeicPreviewStatusResponse,
  AdminLivePhotoPairingActionResponse,
  AdminLivePhotoPairingStatusResponse,
  AdminPlaceGeocodingActionResponse,
  AdminPlaceGeocodingStatusResponse,
  AdminSummaryResponse,
  SourceIntakeReportDetail,
  SourceIntakeReportsResponse,
  SourceIntakeSourcesResponse,
  SourceCreateRequest,
  SourceCreateResponse,
  SourceIntakeRunRequest,
  SourceIntakeRunResponse,
  SourceIntakeStatusSnapshot,
  SourceIntakeStopResponse,
  SourceReviewCreateAlbumRequest,
  SourceReviewCreateAlbumResponse,
  SourceReviewAddToCollectionRequest,
  SourceReviewAddToCollectionResponse,
  SourceReviewCreateCollectionRequest,
  SourceReviewCreateCollectionResponse,
  SourceReviewCreateEventRequest,
  SourceReviewCreateEventResponse,
  IcloudStagingCleanupRunRequest,
  IcloudStagingCleanupRunResponse,
  IcloudStagingCleanupStatusResponse,
  IcloudAcquisitionStatusResponse,
  IcloudAcquisitionRunRequest,
  IcloudAcquisitionRunResponse,
  IcloudAcquisitionStopResponse,
  AlbumDetail,
  AlbumMembershipSummary,
  AlbumSummary,
  CollectionDetail,
  CollectionAssetMembershipSummaryResponse,
  CollectionSummary,
  VisualEnrichmentCandidatePreviewResponse,
  VisualEnrichmentRunResponse,
  CreatePersonResponse,
  ClusterDetail,
  ClusterSuggestionResponse,
  ClusterListResponse,
  ClusterSummary,
  DuplicateGroupListResponse,
  DuplicateGroupDetail,
  DuplicateAdjudicationResponse,
  EventDetail,
  EventMergeResponse,
  DuplicateLineageMergeResponse,
  DuplicateSuggestionListResponse,
  DuplicateSuggestionRejectResponse,
  DuplicateMergeTargetListResponse,
  PhotoEventMutationResponse,
  PhotoFaceOverlayBatchResponse,
  EventSummary,
  EventUpdateResponse,
  FaceSummary,
  ListResponse,
  PersonSummary,
  PersonAliasSummary,
  PersonWithClusters,
  PhotoDetail,
  PhotoBatchAlbumSummaryResponse,
  PhotoBatchVisibilityResponse,
  PhotoSummary,
  PlaceAliasSummary,
  PlaceDetail,
  GlobalPlaceObservationPatchRequest,
  AcceptObservationAsContextRequest,
  AcceptObservationAsContextResponse,
  AssetContextLabelCreateRequest,
  AssetContextLabelCreateResponse,
  AssetContextLabelSummaryBatchResponse,
  AssetContextLabelSummary,
  ContextLabelPropagationPreviewResponse,
  ContextLabelPropagationRequest,
  ContextLabelPropagationResponse,
  PlaceObservationPatchRequest,
  PlaceObservationCreatePlaceRequest,
  PlaceObservationSummary,
  PlacePatchRequest,
  PlaceSummary,
  SearchPhotoListResponse,
  SourceReviewAssetResponse,
  SourceReviewMatchesResponse,
  TimelineSummaryResponse
} from "@/types/ui-api";

export interface PhotoQueryOptions {
  decade?: number;
  year?: number;
  month?: string;
  date?: string;
  undated?: boolean;
  trust?: Array<"high" | "low" | "unknown">;
}

export interface TimelineQueryOptions extends PhotoQueryOptions {}

export interface ClusterQueryOptions {
  includeIgnored?: boolean;
  status?: "all" | "assigned" | "unassigned" | "ignored";
  personQuery?: string;
  limit?: number;
  offset?: number;
}

export interface SearchPhotoQueryOptions extends PhotoQueryOptions {
  q?: string;
  startDate?: string;
  endDate?: string;
  camera?: string;
  personIds?: string;
  albumId?: number;
  eventId?: number;
  placeQuery?: string;
  provenanceQuery?: string;
  sortBy?: "ingested_desc" | "captured_desc";
  hasLocation?: boolean;
  hasFaces?: boolean;
  hasUnassignedFaces?: boolean;
  visibilityFilter?: "visible" | "demoted" | "all";
  mediaTypeFilter?: "all" | "photos" | "videos";
  includeLivePhotoMotionCompanions?: boolean;
  canonicalFirst?: boolean;
  offset?: number;
  limit?: number;
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || "http://127.0.0.1:8001";

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const errorPayload = (await response.json()) as { detail?: string };
      if (errorPayload.detail) {
        message = errorPayload.detail;
      }
    } catch {
      // Fall back to generic message when no JSON payload is returned.
    }

    throw new Error(message);
  }

  return (await response.json()) as T;
}

export function getClusters(options: ClusterQueryOptions = {}): Promise<ClusterListResponse> {
  const params = new URLSearchParams();
  if (options.includeIgnored !== undefined) {
    params.set("include_ignored", options.includeIgnored ? "true" : "false");
  }
  if (options.status) {
    params.set("status", options.status);
  }
  if (options.personQuery) {
    params.set("person_query", options.personQuery);
  }
  if (options.limit !== undefined) {
    params.set("limit", String(options.limit));
  }
  if (options.offset !== undefined) {
    params.set("offset", String(options.offset));
  }

  const query = params.toString();
  const path = query ? `/api/clusters?${query}` : "/api/clusters";
  return apiRequest<ClusterListResponse>(path);
}

export function getCluster(clusterId: number): Promise<ClusterDetail> {
  return apiRequest<ClusterDetail>(`/api/clusters/${clusterId}`);
}

export function getClusterSuggestions(clusterId: number): Promise<ClusterSuggestionResponse> {
  return apiRequest<ClusterSuggestionResponse>(`/api/clusters/${clusterId}/suggestions`);
}

export function getPeople(): Promise<ListResponse<PersonSummary>> {
  return apiRequest<ListResponse<PersonSummary>>("/api/people");
}

export function getPeopleWithClusters(): Promise<ListResponse<PersonWithClusters>> {
  return apiRequest<ListResponse<PersonWithClusters>>("/api/people-with-clusters");
}

export function getUnassignedFaces(): Promise<ListResponse<FaceSummary>> {
  return apiRequest<ListResponse<FaceSummary>>("/api/faces/unassigned");
}

export function assignPerson(clusterId: number, personId: number): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/api/clusters/${clusterId}/assign-person`, {
    method: "POST",
    body: JSON.stringify({ person_id: personId })
  });
}

export function assignFaceToPerson(faceId: number, personId: number): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/api/faces/${faceId}/assign-person`, {
    method: "POST",
    body: JSON.stringify({ person_id: personId })
  });
}

export function createPerson(displayName: string): Promise<CreatePersonResponse> {
  return apiRequest<CreatePersonResponse>("/api/people", {
    method: "POST",
    body: JSON.stringify({ display_name: displayName })
  });
}

export function getPersonAliases(personId: number): Promise<ListResponse<PersonAliasSummary>> {
  return apiRequest<ListResponse<PersonAliasSummary>>(`/api/people/${personId}/aliases`);
}

export function addPersonAlias(personId: number, alias: string): Promise<PersonSummary> {
  return apiRequest<PersonSummary>(`/api/people/${personId}/aliases`, {
    method: "POST",
    body: JSON.stringify({ alias })
  });
}

export function deletePersonAlias(personId: number, aliasId: number): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/api/people/${personId}/aliases/${aliasId}`, {
    method: "DELETE"
  });
}

export function ignoreCluster(clusterId: number): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/api/clusters/${clusterId}/ignore`, {
    method: "POST"
  });
}

export function removeFaceFromCluster(faceId: number): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/api/faces/${faceId}/remove-from-cluster`, {
    method: "POST"
  });
}

export function moveFace(faceId: number, targetClusterId: number): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/api/faces/${faceId}/move`, {
    method: "POST",
    body: JSON.stringify({ target_cluster_id: targetClusterId })
  });
}

export function createClusterFromFace(faceId: number): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/api/faces/${faceId}/create-cluster`, {
    method: "POST"
  });
}

export function mergeClusters(
  sourceClusterId: number,
  targetClusterId: number
): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>("/api/clusters/merge", {
    method: "POST",
    body: JSON.stringify({
      source_cluster_id: sourceClusterId,
      target_cluster_id: targetClusterId
    })
  });
}

export function resolveApiUrl(path: string | null | undefined): string | null {
  if (!path) {
    return null;
  }

  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }

  const normalizedBase = API_BASE_URL.replace(/\/$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}

export { API_BASE_URL };

function buildQueryString(options: PhotoQueryOptions = {}): string {
  const params = new URLSearchParams();

  if (options.decade !== undefined) params.set("decade", String(options.decade));
  if (options.year !== undefined) params.set("year", String(options.year));
  if (options.month) params.set("month", options.month);
  if (options.date) params.set("date", options.date);
  if (options.undated) params.set("undated", "true");
  for (const trust of options.trust ?? []) {
    params.append("trust", trust);
  }

  const query = params.toString();
  return query ? `?${query}` : "";
}

export function getPhotos(options: PhotoQueryOptions = {}): Promise<ListResponse<PhotoSummary>> {
  return apiRequest<ListResponse<PhotoSummary>>(`/api/photos${buildQueryString(options)}`);
}

export function searchPhotos(options: SearchPhotoQueryOptions = {}): Promise<SearchPhotoListResponse> {
  const params = new URLSearchParams();

  if (options.q?.trim()) params.set("q", options.q.trim());
  if (options.startDate) params.set("start_date", options.startDate);
  if (options.endDate) params.set("end_date", options.endDate);
  if (options.camera?.trim()) params.set("camera", options.camera.trim());
  if (options.personIds) params.set("person_ids", options.personIds);
  if (options.albumId) params.set("album_id", String(options.albumId));
  if (options.eventId) params.set("event_id", String(options.eventId));
  if (options.placeQuery?.trim()) params.set("place_query", options.placeQuery.trim());
  if (options.provenanceQuery?.trim()) params.set("provenance_query", options.provenanceQuery.trim());
  if (options.sortBy) params.set("sort_by", options.sortBy);
  if (options.hasLocation !== undefined) params.set("has_location", String(options.hasLocation));
  if (options.hasFaces !== undefined) params.set("has_faces", String(options.hasFaces));
  if (options.hasUnassignedFaces !== undefined) {
    params.set("has_unassigned_faces", String(options.hasUnassignedFaces));
  }
  if (options.visibilityFilter) params.set("visibility_filter", options.visibilityFilter);
  if (options.mediaTypeFilter) params.set("media_type_filter", options.mediaTypeFilter);
  if (options.includeLivePhotoMotionCompanions !== undefined) {
    params.set("include_live_photo_motion_companions", String(options.includeLivePhotoMotionCompanions));
  }
  if (options.canonicalFirst !== undefined) params.set("canonical_first", String(options.canonicalFirst));
  if (options.offset !== undefined) params.set("offset", String(options.offset));
  if (options.limit !== undefined) params.set("limit", String(options.limit));

  if (options.decade !== undefined) params.set("decade", String(options.decade));
  if (options.year !== undefined) params.set("year", String(options.year));
  if (options.month) params.set("month", options.month);
  if (options.date) params.set("date", options.date);
  if (options.undated) params.set("undated", "true");
  for (const trust of options.trust ?? []) {
    params.append("trust", trust);
  }

  const query = params.toString();
  return apiRequest<SearchPhotoListResponse>(`/api/search/photos${query ? `?${query}` : ""}`);
}

export function getPhotoDetail(sha256: string): Promise<PhotoDetail> {
  return apiRequest<PhotoDetail>(`/api/photos/${sha256}`);
}

export function getSourceReviewAsset(sha256: string): Promise<SourceReviewAssetResponse> {
  return apiRequest<SourceReviewAssetResponse>(`/api/provenance-review/assets/${sha256}`);
}

export function getSourceReviewMatches(options: {
  provenanceId: number;
  levelIndex: number;
  hierarchyMode?: "relative" | "full_source_path";
  limit?: number;
}): Promise<SourceReviewMatchesResponse> {
  const params = new URLSearchParams({
    provenance_id: String(options.provenanceId),
    level_index: String(options.levelIndex),
  });
  if (options.hierarchyMode) {
    params.set("hierarchy_mode", options.hierarchyMode);
  }
  if (options.limit !== undefined) {
    params.set("limit", String(options.limit));
  }

  return apiRequest<SourceReviewMatchesResponse>(`/api/provenance-review/matches?${params.toString()}`);
}

export function createAlbumFromSourceReviewLevel(
  payload: SourceReviewCreateAlbumRequest
): Promise<SourceReviewCreateAlbumResponse> {
  return apiRequest<SourceReviewCreateAlbumResponse>("/api/provenance-review/create-album", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createCollectionFromSourceReviewLevel(
  payload: SourceReviewCreateCollectionRequest
): Promise<SourceReviewCreateCollectionResponse> {
  return apiRequest<SourceReviewCreateCollectionResponse>("/api/provenance-review/create-collection", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function addToCollectionFromSourceReviewLevel(
  payload: SourceReviewAddToCollectionRequest
): Promise<SourceReviewAddToCollectionResponse> {
  return apiRequest<SourceReviewAddToCollectionResponse>("/api/provenance-review/add-to-collection", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createEventFromSourceReviewLevel(
  payload: SourceReviewCreateEventRequest
): Promise<SourceReviewCreateEventResponse> {
  return apiRequest<SourceReviewCreateEventResponse>("/api/provenance-review/create-event", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getPhotoFaceOverlays(assetSha256List: string[]): Promise<PhotoFaceOverlayBatchResponse> {
  return apiRequest<PhotoFaceOverlayBatchResponse>("/api/photos/face-overlays", {
    method: "POST",
    body: JSON.stringify({ asset_sha256_list: assetSha256List })
  });
}

export function getLivePhotoPairingStatus(): Promise<AdminLivePhotoPairingStatusResponse> {
  return apiRequest<AdminLivePhotoPairingStatusResponse>("/api/admin/live-photo-pairing/status");
}

export function runLivePhotoPairing(): Promise<AdminLivePhotoPairingActionResponse> {
  return apiRequest<AdminLivePhotoPairingActionResponse>("/api/admin/live-photo-pairing/run", {
    method: "POST"
  });
}

export function setPhotoRotation(
  sha256: string,
  rotationDegrees: 0 | 90 | 180 | 270
): Promise<{ asset_sha256: string; display_rotation_degrees: 0 | 90 | 180 | 270 }> {
  return apiRequest<{ asset_sha256: string; display_rotation_degrees: 0 | 90 | 180 | 270 }>(
    `/api/photos/${sha256}/rotation`,
    {
      method: "POST",
      body: JSON.stringify({ rotation_degrees: rotationDegrees })
    }
  );
}

export function removePhotoFromEvent(sha256: string): Promise<PhotoEventMutationResponse> {
  return apiRequest<PhotoEventMutationResponse>(`/api/photos/${sha256}/event/remove`, {
    method: "POST"
  });
}

export function assignPhotoToEvent(
  sha256: string,
  eventId: number
): Promise<PhotoEventMutationResponse> {
  return apiRequest<PhotoEventMutationResponse>(`/api/photos/${sha256}/event/assign`, {
    method: "POST",
    body: JSON.stringify({ event_id: eventId })
  });
}

export function getTimelineSummary(
  options: TimelineQueryOptions = {}
): Promise<TimelineSummaryResponse> {
  return apiRequest<TimelineSummaryResponse>(`/api/timeline${buildQueryString(options)}`);
}

export function getEvents(): Promise<ListResponse<EventSummary>> {
  return apiRequest<ListResponse<EventSummary>>("/api/events");
}

export function getEventDetail(eventId: number): Promise<EventDetail> {
  return apiRequest<EventDetail>(`/api/events/${eventId}`);
}

export function updateEventLabel(eventId: number, label: string): Promise<EventUpdateResponse> {
  return apiRequest<EventUpdateResponse>(`/api/events/${eventId}/update`, {
    method: "POST",
    body: JSON.stringify({ label })
  });
}

export function mergeEvents(sourceEventId: number, targetEventId: number): Promise<EventMergeResponse> {
  return apiRequest<EventMergeResponse>("/api/events/merge", {
    method: "POST",
    body: JSON.stringify({ source_event_id: sourceEventId, target_event_id: targetEventId })
  });
}

export function getDuplicateMergeTargets(
  sourceAssetSha256: string,
  query: string,
  limit = 30
): Promise<DuplicateMergeTargetListResponse> {
  const params = new URLSearchParams({ source_asset_sha256: sourceAssetSha256, limit: String(limit) });
  if (query.trim()) {
    params.set("q", query.trim());
  }
  return apiRequest<DuplicateMergeTargetListResponse>(`/api/duplicates/merge-targets?${params.toString()}`);
}

export function getDuplicateSuggestions(
  offset: number = 0,
  limit: number = 50
): Promise<DuplicateSuggestionListResponse> {
  const params = new URLSearchParams({ offset: String(offset), limit: String(limit) });
  return apiRequest<DuplicateSuggestionListResponse>(`/api/duplicates/suggestions?${params.toString()}`);
}

export function confirmDuplicateSuggestion(
  sourceAssetSha256: string,
  targetAssetSha256: string
): Promise<DuplicateLineageMergeResponse> {
  return apiRequest<DuplicateLineageMergeResponse>("/api/duplicates/confirm", {
    method: "POST",
    body: JSON.stringify({
      source_asset_sha256: sourceAssetSha256,
      target_asset_sha256: targetAssetSha256
    })
  });
}

export function rejectDuplicateSuggestion(
  assetSha256A: string,
  assetSha256B: string
): Promise<DuplicateSuggestionRejectResponse> {
  return apiRequest<DuplicateSuggestionRejectResponse>("/api/duplicates/reject", {
    method: "POST",
    body: JSON.stringify({
      asset_sha256_a: assetSha256A,
      asset_sha256_b: assetSha256B
    })
  });
}

export function mergeDuplicateAssets(
  sourceAssetSha256: string,
  targetAssetSha256: string
): Promise<DuplicateLineageMergeResponse> {
  return apiRequest<DuplicateLineageMergeResponse>("/api/duplicates/merge-assets", {
    method: "POST",
    body: JSON.stringify({
      source_asset_sha256: sourceAssetSha256,
      target_asset_sha256: targetAssetSha256
    })
  });
}

export function setDuplicateGroupCanonical(assetSha256: string): Promise<DuplicateAdjudicationResponse> {
  return apiRequest<DuplicateAdjudicationResponse>("/api/duplicates/set-canonical", {
    method: "POST",
    body: JSON.stringify({
      asset_sha256: assetSha256
    })
  });
}

export function removeDuplicateGroupMember(assetSha256: string): Promise<DuplicateAdjudicationResponse> {
  return apiRequest<DuplicateAdjudicationResponse>("/api/duplicates/remove-from-group", {
    method: "POST",
    body: JSON.stringify({
      asset_sha256: assetSha256
    })
  });
}

export function demoteDuplicateGroupMember(assetSha256: string): Promise<DuplicateAdjudicationResponse> {
  return apiRequest<DuplicateAdjudicationResponse>("/api/duplicates/demote", {
    method: "POST",
    body: JSON.stringify({
      asset_sha256: assetSha256
    })
  });
}

export function restoreDuplicateGroupMember(assetSha256: string): Promise<DuplicateAdjudicationResponse> {
  return apiRequest<DuplicateAdjudicationResponse>("/api/duplicates/restore", {
    method: "POST",
    body: JSON.stringify({
      asset_sha256: assetSha256
    })
  });
}

export function getDuplicateGroups(
  query: string = "",
  offset: number = 0,
  limit: number = 50
): Promise<DuplicateGroupListResponse> {
  const params = new URLSearchParams({ offset: String(offset), limit: String(limit) });
  if (query.trim()) {
    params.set("q", query.trim());
  }
  return apiRequest<DuplicateGroupListResponse>(`/api/duplicates/groups?${params.toString()}`);
}

export function getDuplicateGroupDetail(groupId: number): Promise<DuplicateGroupDetail> {
  return apiRequest<DuplicateGroupDetail>(`/api/duplicates/${groupId}`);
}

export function getPlaces(): Promise<ListResponse<PlaceSummary>> {
  return apiRequest<ListResponse<PlaceSummary>>("/api/places");
}

export function getPlaceDetail(placeId: string): Promise<PlaceDetail> {
  return apiRequest<PlaceDetail>(`/api/places/${placeId}`);
}

export function updatePlaceLabel(placeId: string, userLabel: string | null): Promise<PlaceDetail> {
  return apiRequest<PlaceDetail>(`/api/places/${placeId}/label`, {
    method: "POST",
    body: JSON.stringify({ user_label: userLabel })
  });
}

export function patchPlace(placeId: string, payload: PlacePatchRequest): Promise<PlaceDetail> {
  return apiRequest<PlaceDetail>(`/api/places/${placeId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getPlaceAliases(placeId: string): Promise<ListResponse<PlaceAliasSummary>> {
  return apiRequest<ListResponse<PlaceAliasSummary>>(`/api/places/${placeId}/aliases`);
}

export function addPlaceAlias(placeId: string, alias: string): Promise<PlaceAliasSummary> {
  return apiRequest<PlaceAliasSummary>(`/api/places/${placeId}/aliases`, {
    method: "POST",
    body: JSON.stringify({ alias }),
  });
}

export function deletePlaceAlias(placeId: string, aliasId: number): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/api/places/${placeId}/aliases/${aliasId}`, {
    method: "DELETE",
  });
}

export function getPlaceObservations(placeId: string, limit: number = 100): Promise<ListResponse<PlaceObservationSummary>> {
  const params = new URLSearchParams({ limit: String(limit) });
  return apiRequest<ListResponse<PlaceObservationSummary>>(`/api/places/${placeId}/observations?${params.toString()}`);
}

export function patchPlaceObservation(
  placeId: string,
  observationId: number,
  payload: PlaceObservationPatchRequest,
): Promise<PlaceObservationSummary> {
  return apiRequest<PlaceObservationSummary>(`/api/places/${placeId}/observations/${observationId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export interface GlobalPlaceObservationQueryOptions {
  assetSha256?: string;
  sourceType?: string;
  observationType?: string;
  status?: "pending" | "accepted" | "rejected" | "ignored" | "superseded";
  limit?: number;
  offset?: number;
}

export function getGlobalPlaceObservations(
  options: GlobalPlaceObservationQueryOptions = {},
): Promise<ListResponse<PlaceObservationSummary>> {
  const params = new URLSearchParams();
  if (options.assetSha256) {
    params.set("asset_sha256", options.assetSha256);
  }
  if (options.sourceType) {
    params.set("source_type", options.sourceType);
  }
  if (options.observationType) {
    params.set("observation_type", options.observationType);
  }
  if (options.status) {
    params.set("status", options.status);
  }
  params.set("limit", String(options.limit ?? 100));
  params.set("offset", String(options.offset ?? 0));
  return apiRequest<ListResponse<PlaceObservationSummary>>(`/api/place-observations?${params.toString()}`);
}

export function patchGlobalPlaceObservation(
  observationId: number,
  payload: GlobalPlaceObservationPatchRequest,
): Promise<PlaceObservationSummary> {
  return apiRequest<PlaceObservationSummary>(`/api/place-observations/${observationId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function createPlaceFromObservation(
  observationId: number,
  payload: PlaceObservationCreatePlaceRequest,
): Promise<PlaceObservationSummary> {
  return apiRequest<PlaceObservationSummary>(`/api/place-observations/${observationId}/create-place`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface AssetContextLabelQueryOptions {
  assetSha256?: string;
  contextType?: string;
  status?: "active" | "hidden" | "rejected" | "all";
  sourceType?: string;
  limit?: number;
  offset?: number;
}

export function getAssetContextLabels(
  options: AssetContextLabelQueryOptions = {},
): Promise<ListResponse<AssetContextLabelSummary>> {
  const params = new URLSearchParams();
  if (options.assetSha256) {
    params.set("asset_sha256", options.assetSha256);
  }
  if (options.contextType) {
    params.set("context_type", options.contextType);
  }
  if (options.status) {
    params.set("status", options.status);
  }
  if (options.sourceType) {
    params.set("source_type", options.sourceType);
  }
  params.set("limit", String(options.limit ?? 100));
  params.set("offset", String(options.offset ?? 0));
  return apiRequest<ListResponse<AssetContextLabelSummary>>(`/api/asset-context-labels?${params.toString()}`);
}

export function getAssetContextLabelSummaries(
  assetSha256s: string[],
): Promise<AssetContextLabelSummaryBatchResponse> {
  return apiRequest<AssetContextLabelSummaryBatchResponse>("/api/asset-context-labels/summary", {
    method: "POST",
    body: JSON.stringify({ asset_sha256s: assetSha256s }),
  });
}

export function acceptObservationAsContext(
  observationId: number,
  payload: AcceptObservationAsContextRequest,
): Promise<AcceptObservationAsContextResponse> {
  return apiRequest<AcceptObservationAsContextResponse>(`/api/place-observations/${observationId}/accept-as-context`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createAssetContextLabel(
  payload: AssetContextLabelCreateRequest,
): Promise<AssetContextLabelCreateResponse> {
  return apiRequest<AssetContextLabelCreateResponse>("/api/asset-context-labels", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getContextLabelPropagationPreview(
  labelId: number,
): Promise<ContextLabelPropagationPreviewResponse> {
  return apiRequest<ContextLabelPropagationPreviewResponse>(`/api/asset-context-labels/${labelId}/propagation-preview`);
}

export function propagateContextLabel(
  labelId: number,
  payload: ContextLabelPropagationRequest,
): Promise<ContextLabelPropagationResponse> {
  return apiRequest<ContextLabelPropagationResponse>(`/api/asset-context-labels/${labelId}/propagate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getAdminSummary(): Promise<AdminSummaryResponse> {
  return apiRequest<AdminSummaryResponse>("/api/admin/summary");
}

export function getDuplicateProcessingStatus(): Promise<AdminDuplicateProcessingStatusResponse> {
  return apiRequest<AdminDuplicateProcessingStatusResponse>("/api/admin/duplicate-processing/status");
}

export function runDuplicateProcessing(): Promise<AdminDuplicateProcessingActionResponse> {
  return apiRequest<AdminDuplicateProcessingActionResponse>("/api/admin/duplicate-processing/run", {
    method: "POST"
  });
}

export function stopDuplicateProcessing(): Promise<AdminDuplicateProcessingActionResponse> {
  return apiRequest<AdminDuplicateProcessingActionResponse>("/api/admin/duplicate-processing/stop", {
    method: "POST"
  });
}

export function getPlaceGeocodingStatus(): Promise<AdminPlaceGeocodingStatusResponse> {
  return apiRequest<AdminPlaceGeocodingStatusResponse>("/api/admin/place-geocoding/status");
}

export function runPlaceGeocoding(): Promise<AdminPlaceGeocodingActionResponse> {
  return apiRequest<AdminPlaceGeocodingActionResponse>("/api/admin/place-geocoding/run", {
    method: "POST"
  });
}

export function stopPlaceGeocoding(): Promise<AdminPlaceGeocodingActionResponse> {
  return apiRequest<AdminPlaceGeocodingActionResponse>("/api/admin/place-geocoding/stop", {
    method: "POST"
  });
}

export function getFaceProcessingStatus(): Promise<AdminFaceProcessingStatusResponse> {
  return apiRequest<AdminFaceProcessingStatusResponse>("/api/admin/face-processing/status");
}

export function runFaceProcessing(): Promise<AdminFaceProcessingActionResponse> {
  return apiRequest<AdminFaceProcessingActionResponse>("/api/admin/face-processing/run", {
    method: "POST"
  });
}

export function stopFaceProcessing(): Promise<AdminFaceProcessingActionResponse> {
  return apiRequest<AdminFaceProcessingActionResponse>("/api/admin/face-processing/stop", {
    method: "POST"
  });
}

export function getHeicPreviewStatus(): Promise<AdminHeicPreviewStatusResponse> {
  return apiRequest<AdminHeicPreviewStatusResponse>("/api/admin/heic-preview/status");
}

export function runHeicPreviewGeneration(): Promise<AdminHeicPreviewActionResponse> {
  return apiRequest<AdminHeicPreviewActionResponse>("/api/admin/heic-preview/run", {
    method: "POST"
  });
}

export function stopHeicPreviewGeneration(): Promise<AdminHeicPreviewActionResponse> {
  return apiRequest<AdminHeicPreviewActionResponse>("/api/admin/heic-preview/stop", {
    method: "POST"
  });
}

export function getSourceIntakeSources(): Promise<SourceIntakeSourcesResponse> {
  return apiRequest<SourceIntakeSourcesResponse>("/api/admin/source-intake/sources");
}

// ── iCloud Acquisition ────────────────────────────────────────────────────────

export function getIcloudAcquisitionStatus(): Promise<IcloudAcquisitionStatusResponse> {
  return apiRequest<IcloudAcquisitionStatusResponse>("/api/admin/icloud-acquisition/status");
}

export function runIcloudAcquisition(req: IcloudAcquisitionRunRequest): Promise<IcloudAcquisitionRunResponse> {
  return apiRequest<IcloudAcquisitionRunResponse>("/api/admin/icloud-acquisition/run", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function stopIcloudAcquisition(): Promise<IcloudAcquisitionStopResponse> {
  return apiRequest<IcloudAcquisitionStopResponse>("/api/admin/icloud-acquisition/stop", {
    method: "POST",
  });
}

export function getSourceIntakeReports(): Promise<SourceIntakeReportsResponse> {
  return apiRequest<SourceIntakeReportsResponse>("/api/admin/source-intake/reports");
}

export function getSourceIntakeReportDetail(reportFilename: string): Promise<SourceIntakeReportDetail> {
  return apiRequest<SourceIntakeReportDetail>(`/api/admin/source-intake/reports/${encodeURIComponent(reportFilename)}`);
}

export function getAlbums(): Promise<ListResponse<AlbumSummary>> {
  return apiRequest<ListResponse<AlbumSummary>>("/api/albums");
}

export function getAlbumDetail(albumId: number): Promise<AlbumDetail> {
  return apiRequest<AlbumDetail>(`/api/albums/${albumId}`);
}

export function getAlbumsForAsset(sha256: string): Promise<ListResponse<AlbumMembershipSummary>> {
  return apiRequest<ListResponse<AlbumMembershipSummary>>(`/api/albums/by-asset/${sha256}`);
}

export function createAlbum(
  name: string,
  description: string | null = null
): Promise<AlbumSummary> {
  return apiRequest<AlbumSummary>("/api/albums", {
    method: "POST",
    body: JSON.stringify({ name, description })
  });
}

export function updateAlbum(
  albumId: number,
  payload: { name?: string; description?: string | null }
): Promise<AlbumSummary> {
  return apiRequest<AlbumSummary>(`/api/albums/${albumId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function deleteAlbum(albumId: number): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/api/albums/${albumId}`, {
    method: "DELETE"
  });
}

export function addAssetsToAlbum(
  albumId: number,
  assetSha256List: string[]
): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/api/albums/${albumId}/assets`, {
    method: "POST",
    body: JSON.stringify({ asset_sha256_list: assetSha256List })
  });
}

export function removeAssetsFromAlbum(
  albumId: number,
  assetSha256List: string[]
): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/api/albums/${albumId}/assets`, {
    method: "DELETE",
    body: JSON.stringify({ asset_sha256_list: assetSha256List })
  });
}

export function getCollections(): Promise<ListResponse<CollectionSummary>> {
  return apiRequest<ListResponse<CollectionSummary>>("/api/collections");
}

export function getCollectionDetail(collectionId: number): Promise<CollectionDetail> {
  return apiRequest<CollectionDetail>(`/api/collections/${collectionId}`);
}

export function previewVisualEnrichmentCandidates(payload: {
  pool_type: "collection";
  pool_id: number;
  canonical_only: boolean;
  exclude_existing_observations: boolean;
  exclude_existing_context_labels: boolean;
  limit?: number;
}): Promise<VisualEnrichmentCandidatePreviewResponse> {
  return apiRequest<VisualEnrichmentCandidatePreviewResponse>("/api/visual-enrichment/candidates/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function runVisualEnrichmentGoogleVision(payload: {
  asset_sha256s: string[];
  live: boolean;
  mock_provider: boolean;
  feature_landmark: boolean;
  feature_web: boolean;
  feature_label: boolean;
  feature_object: boolean;
}): Promise<VisualEnrichmentRunResponse> {
  return apiRequest<VisualEnrichmentRunResponse>("/api/visual-enrichment/run-google-vision", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createCollection(
  name: string,
  description: string | null = null
): Promise<CollectionSummary> {
  return apiRequest<CollectionSummary>("/api/collections", {
    method: "POST",
    body: JSON.stringify({ name, description })
  });
}

export function addAssetsToCollection(
  collectionId: number,
  assetSha256List: string[]
): Promise<CollectionAssetMembershipSummaryResponse> {
  return apiRequest<CollectionAssetMembershipSummaryResponse>(`/api/collections/${collectionId}/assets`, {
    method: "POST",
    body: JSON.stringify({ asset_sha256_list: assetSha256List })
  });
}

export function addAlbumToCollection(
  collectionId: number,
  albumId: number
): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/api/collections/${collectionId}/albums`, {
    method: "POST",
    body: JSON.stringify({ album_id: albumId })
  });
}

export function removeAlbumFromCollection(
  collectionId: number,
  albumId: number
): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/api/collections/${collectionId}/albums/${albumId}`, {
    method: "DELETE"
  });
}

export function batchUpdatePhotoVisibility(
  assetSha256List: string[],
  action: "demote" | "restore"
): Promise<PhotoBatchVisibilityResponse> {
  return apiRequest<PhotoBatchVisibilityResponse>("/api/photos/batch/visibility", {
    method: "POST",
    body: JSON.stringify({ asset_sha256_list: assetSha256List, action })
  });
}

export function batchAddPhotosToAlbum(
  albumId: number,
  assetSha256List: string[]
): Promise<PhotoBatchAlbumSummaryResponse> {
  return apiRequest<PhotoBatchAlbumSummaryResponse>(`/api/photos/batch/albums/${albumId}/add`, {
    method: "POST",
    body: JSON.stringify({ asset_sha256_list: assetSha256List })
  });
}

export function batchCreateAlbumFromPhotos(
  name: string,
  description: string | null,
  assetSha256List: string[]
): Promise<PhotoBatchAlbumSummaryResponse> {
  return apiRequest<PhotoBatchAlbumSummaryResponse>("/api/photos/batch/albums/create", {
    method: "POST",
    body: JSON.stringify({ name, description, asset_sha256_list: assetSha256List })
  });
}

// ---------------------------------------------------------------------------
// Source Registry
// ---------------------------------------------------------------------------

export function createOrGetIntakeSource(req: SourceCreateRequest): Promise<SourceCreateResponse> {
  return apiRequest<SourceCreateResponse>("/api/admin/source-intake/sources", {
    method: "POST",
    body: JSON.stringify(req)
  });
}

// ---------------------------------------------------------------------------
// Admin-launched Source Intake
// ---------------------------------------------------------------------------

export function startSourceIntake(req: SourceIntakeRunRequest): Promise<SourceIntakeRunResponse> {
  return apiRequest<SourceIntakeRunResponse>("/api/admin/source-intake/run", {
    method: "POST",
    body: JSON.stringify(req)
  });
}

export function getSourceIntakeRunStatus(): Promise<SourceIntakeStatusSnapshot> {
  return apiRequest<SourceIntakeStatusSnapshot>("/api/admin/source-intake/run/status");
}

export function stopSourceIntake(): Promise<SourceIntakeStopResponse> {
  return apiRequest<SourceIntakeStopResponse>("/api/admin/source-intake/run/stop", {
    method: "POST"
  });
}

export function getIcloudStagingCleanupStatus(): Promise<IcloudStagingCleanupStatusResponse> {
  return apiRequest<IcloudStagingCleanupStatusResponse>("/api/admin/icloud-staging-cleanup/status");
}

export function runIcloudStagingCleanup(
  req: IcloudStagingCleanupRunRequest
): Promise<IcloudStagingCleanupRunResponse> {
  return apiRequest<IcloudStagingCleanupRunResponse>("/api/admin/icloud-staging-cleanup/run", {
    method: "POST",
    body: JSON.stringify(req)
  });
}

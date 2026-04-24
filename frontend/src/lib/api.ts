import type {
  AlbumDetail,
  AlbumMembershipSummary,
  AlbumSummary,
  CreatePersonResponse,
  ClusterDetail,
  ClusterSuggestionResponse,
  ClusterSummary,
  DuplicateGroupListResponse,
  DuplicateGroupDetail,
  EventDetail,
  EventMergeResponse,
  DuplicateLineageMergeResponse,
  DuplicateSuggestionListResponse,
  DuplicateSuggestionRejectResponse,
  DuplicateMergeTargetListResponse,
  PhotoEventMutationResponse,
  EventSummary,
  EventUpdateResponse,
  FaceSummary,
  ListResponse,
  PersonSummary,
  PersonWithClusters,
  PhotoDetail,
  PhotoSummary,
  PlaceDetail,
  PlaceSummary,
  SearchPhotoListResponse,
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

export interface SearchPhotoQueryOptions extends PhotoQueryOptions {
  q?: string;
  startDate?: string;
  endDate?: string;
  camera?: string;
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

export function getClusters(): Promise<ListResponse<ClusterSummary>> {
  return apiRequest<ListResponse<ClusterSummary>>("/api/clusters");
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

export function createPerson(displayName: string): Promise<CreatePersonResponse> {
  return apiRequest<CreatePersonResponse>("/api/people", {
    method: "POST",
    body: JSON.stringify({ display_name: displayName })
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

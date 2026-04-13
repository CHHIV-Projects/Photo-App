import type {
  CreatePersonResponse,
  ClusterDetail,
  ClusterSummary,
  EventDetail,
  EventSummary,
  FaceSummary,
  ListResponse,
  PersonSummary,
  PersonWithClusters,
  PhotoDetail,
  PhotoSummary,
  PlaceDetail,
  PlaceSummary,
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

export function getPhotoDetail(sha256: string): Promise<PhotoDetail> {
  return apiRequest<PhotoDetail>(`/api/photos/${sha256}`);
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

export function getPlaces(): Promise<ListResponse<PlaceSummary>> {
  return apiRequest<ListResponse<PlaceSummary>>("/api/places");
}

export function getPlaceDetail(placeId: string): Promise<PlaceDetail> {
  return apiRequest<PlaceDetail>(`/api/places/${placeId}`);
}

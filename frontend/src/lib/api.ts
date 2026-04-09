import type {
  ClusterDetail,
  ClusterSummary,
  ListResponse,
  PersonSummary
} from "@/types/ui-api";

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

export function assignPerson(clusterId: number, personId: number): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/api/clusters/${clusterId}/assign-person`, {
    method: "POST",
    body: JSON.stringify({ person_id: personId })
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

export { API_BASE_URL };

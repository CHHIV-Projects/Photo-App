export interface ClusterSummary {
  cluster_id: number;
  face_count: number;
  person_id: number | null;
  person_name: string | null;
  is_ignored: boolean;
  preview_thumbnail_urls: string[];
}

export interface FaceSummary {
  face_id: number;
  asset_sha256: string;
  thumbnail_url: string | null;
}

export interface ClusterDetail {
  cluster_id: number;
  person_id: number | null;
  person_name: string | null;
  is_ignored: boolean;
  faces: FaceSummary[];
}

export interface PersonSummary {
  person_id: number;
  display_name: string;
}

export interface ClusterAssignmentSummary {
  cluster_id: number;
  face_count: number;
}

export interface PersonWithClusters {
  person_id: number;
  display_name: string;
  clusters: ClusterAssignmentSummary[];
}

export interface CreatePersonRequest {
  display_name: string;
}

export interface CreatePersonResponse {
  success: boolean;
  person: PersonSummary;
}

export interface ListResponse<T> {
  count: number;
  items: T[];
}

export interface BBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface FaceInPhoto {
  face_id: number;
  bbox: BBox;
  cluster_id: number | null;
  person_id: number | null;
  person_name: string | null;
}

export interface PhotoSummary {
  asset_sha256: string;
  filename: string;
  image_url: string;
  face_count: number;
}

export interface PhotoDetail {
  asset_sha256: string;
  filename: string;
  image_url: string;
  faces: FaceInPhoto[];
}

export interface EventSummary {
  event_id: number;
  start_time: string;
  end_time: string;
  photo_count: number;
  face_count: number;
}

export interface EventDetail {
  event_id: number;
  start_time: string;
  end_time: string;
  photos: PhotoSummary[];
}

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

export interface ClusterSuggestionCandidate {
  person_id: number;
  person_name: string;
  confidence_score: number;
  rank: number;
}

export interface ClusterSuggestionResponse {
  cluster_id: number;
  suggestion_state: "high_confidence" | "tentative" | "none" | "ambiguous";
  explanation: string;
  suggested_people: ClusterSuggestionCandidate[];
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
  captured_at: string | null;
  capture_time_trust: "high" | "low" | "unknown";
  face_count: number;
}

export interface TimelineBucketSummary {
  period_key: string;
  label: string;
  level: "decade" | "year" | "month" | "date" | "undated";
  total_assets: number;
  high_trust_count: number;
  low_trust_count: number;
  unknown_trust_count: number;
}

export interface TimelineSummaryResponse {
  level: "decade" | "year" | "month" | "date";
  selected_decade: number | null;
  selected_year: number | null;
  selected_month: string | null;
  selected_date: string | null;
  trust_filter: Array<"high" | "low" | "unknown">;
  items: TimelineBucketSummary[];
  undated_bucket: TimelineBucketSummary | null;
}

export interface AlbumSummary {
  album_id: number;
  name: string;
  description: string | null;
  asset_count: number;
  cover_image_url: string | null;
  updated_at: string;
}

export interface AlbumMembershipSummary {
  album_id: number;
  name: string;
}

export interface AlbumDetail {
  album_id: number;
  name: string;
  description: string | null;
  asset_count: number;
  cover_image_url: string | null;
  created_at: string;
  updated_at: string;
  items: PhotoSummary[];
}

export interface PhotoEventSummary {
  event_id: number;
  label: string | null;
  start_at: string | null;
  end_at: string | null;
}

export interface PhotoLocation {
  latitude: number | null;
  longitude: number | null;
}

export interface PhotoProvenance {
  source_path: string;
  ingested_at: string | null;
  source_hash: string | null;
}

export interface PhotoDetail {
  asset_sha256: string;
  filename: string;
  image_url: string;
  is_scan: boolean;
  capture_type: "digital" | "scan" | "unknown";
  capture_time_trust: "high" | "low" | "unknown";
  event: PhotoEventSummary | null;
  location: PhotoLocation | null;
  provenance: PhotoProvenance[];
  duplicate_group_id: number | null;
  duplicate_group_type: "near" | null;
  is_canonical: boolean;
  quality_score: number | null;
  duplicate_count: number;
  canonical_asset_sha256: string | null;
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

export interface PlaceSummary {
  place_id: string;
  latitude: number;
  longitude: number;
  photo_count: number;
}

export interface PlaceDetail {
  place_id: string;
  latitude: number;
  longitude: number;
  photos: PhotoSummary[];
}

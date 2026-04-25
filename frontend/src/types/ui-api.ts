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

export interface SearchPhotoSummary {
  asset_sha256: string;
  filename: string;
  image_url: string;
  captured_at: string | null;
  camera_make: string | null;
  camera_model: string | null;
  capture_time_trust: "high" | "low" | "unknown";
  face_count: number;
  assigned_face_count: number;
  unassigned_face_count: number;
  duplicate_group_id: number | null;
  is_canonical: boolean;
  visibility_status: "visible" | "demoted";
}

export interface SearchPhotoListResponse {
  total_count: number;
  offset: number;
  limit: number;
  items: SearchPhotoSummary[];
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
  source_label: string | null;
  source_type: string | null;
  source_root_path: string | null;
  source_relative_path: string | null;
  ingestion_source_id: number | null;
  ingestion_run_id: number | null;
  ingested_at: string | null;
  source_hash: string | null;
}

export interface CanonicalMetadataSummary {
  captured_at: string | null;
  camera_make: string | null;
  camera_model: string | null;
  width: number | null;
  height: number | null;
}

export interface PhotoMetadataObservation {
  id: number;
  provenance_id: number | null;
  observation_origin: string;
  observed_source_path: string | null;
  observed_source_type: string | null;
  observed_extension: string | null;
  exif_datetime_original: string | null;
  exif_create_date: string | null;
  captured_at_observed: string | null;
  gps_latitude: number | null;
  gps_longitude: number | null;
  camera_make: string | null;
  camera_model: string | null;
  width: number | null;
  height: number | null;
  is_legacy_seeded: boolean;
  created_at_utc: string | null;
  winner_fields: string[];
}

export interface ContentTagSummary {
  tag: string;
  tag_type: "object" | "scene";
}

export interface PhotoDetail {
  asset_sha256: string;
  filename: string;
  image_url: string;
  display_rotation_degrees: 0 | 90 | 180 | 270;
  is_scan: boolean;
  capture_type: "digital" | "scan" | "unknown";
  capture_time_trust: "high" | "low" | "unknown";
  event: PhotoEventSummary | null;
  location: PhotoLocation | null;
  canonical_metadata: CanonicalMetadataSummary | null;
  metadata_observations: PhotoMetadataObservation[];
  provenance: PhotoProvenance[];
  duplicate_group_id: number | null;
  duplicate_group_type: "near" | null;
  is_canonical: boolean;
  quality_score: number | null;
  duplicate_count: number;
  canonical_asset_sha256: string | null;
  faces: FaceInPhoto[];
  content_tags: ContentTagSummary[];
}

export interface EventSummary {
  event_id: number;
  label: string | null;
  start_time: string;
  end_time: string;
  photo_count: number;
  face_count: number;
}

export interface EventDetail {
  event_id: number;
  label: string | null;
  start_time: string;
  end_time: string;
  photos: PhotoSummary[];
}

export interface EventUpdateResponse {
  event_id: number;
  label: string | null;
  start_time: string;
  end_time: string;
  photo_count: number;
}

export interface EventMergeResponse {
  target_event_id: number;
  removed_event_id: number;
  label: string | null;
  start_time: string;
  end_time: string;
  photo_count: number;
}

export interface EventImpactSummary {
  event_id: number;
  label: string | null;
  start_time: string | null;
  end_time: string | null;
  photo_count: number;
  face_count: number;
}

export interface PhotoEventMutationResponse {
  success: boolean;
  asset_sha256: string;
  event: PhotoEventSummary | null;
  old_event: EventImpactSummary | null;
  new_event: EventImpactSummary | null;
}

export interface DuplicateMergeTargetSummary {
  asset_sha256: string;
  filename: string;
  image_url: string;
  captured_at: string | null;
  duplicate_group_id: number;
  duplicate_count: number;
  is_canonical: boolean;
}

export interface DuplicateMergeTargetListResponse {
  count: number;
  items: DuplicateMergeTargetSummary[];
}

export interface DuplicateLineageAssetSummary {
  asset_sha256: string;
  filename: string;
  captured_at: string | null;
  duplicate_group_id: number | null;
  is_canonical: boolean;
  visibility_status: "visible" | "demoted";
}

export interface DuplicateLineageMergeResponse {
  success: boolean;
  source_asset_sha256: string;
  target_asset_sha256: string;
  resulting_group_id: number;
  resulting_canonical_asset_sha256: string;
  affected_member_count: number;
  affected_assets: DuplicateLineageAssetSummary[];
}

export interface DuplicateSuggestionAssetSummary {
  asset_sha256: string;
  filename: string;
  image_url: string;
  duplicate_group_id: number | null;
  quality_score: number | null;
}

export interface DuplicateSuggestionSummary {
  confidence: "high" | "medium" | "low";
  distance: number;
  asset_a: DuplicateSuggestionAssetSummary;
  asset_b: DuplicateSuggestionAssetSummary;
}

export interface DuplicateSuggestionListResponse {
  total_count: number;
  offset: number;
  limit: number;
  items: DuplicateSuggestionSummary[];
}

export interface DuplicateSuggestionRejectResponse {
  success: boolean;
  created: boolean;
  asset_sha256_a: string;
  asset_sha256_b: string;
}

export interface DuplicateGroupSummary {
  group_id: number;
  member_count: number;
  canonical_asset_sha256: string | null;
  canonical_thumbnail_url: string | null;
  created_at: string;
}

export interface DuplicateGroupListResponse {
  total_count: number;
  items: DuplicateGroupSummary[];
}

export interface DuplicateGroupAssetSummary {
  asset_sha256: string;
  filename: string;
  image_url: string;
  is_canonical: boolean;
  visibility_status: "visible" | "demoted";
  quality_score: number | null;
  capture_type: "digital" | "scan" | "unknown";
  capture_time_trust: "high" | "low" | "unknown";
}

export interface DuplicateGroupDetail {
  group_id: number;
  group_type: "near";
  canonical_asset_sha256: string | null;
  duplicate_count: number;
  assets: DuplicateGroupAssetSummary[];
}

export interface DuplicateAdjudicationResponse {
  success: boolean;
  noop: boolean;
  message: string | null;
  group_id: number | null;
  asset_sha256: string | null;
  affected_assets: DuplicateLineageAssetSummary[];
}

export interface PlaceSummary {
  place_id: string;
  latitude: number;
  longitude: number;
  photo_count: number;
  thumbnail_url: string | null;
  user_label: string | null;
  display_label: string;
  formatted_address: string | null;
  city: string | null;
  county: string | null;
  state: string | null;
  country: string | null;
  geocode_status: string;
}

export interface PlaceDetail {
  place_id: string;
  latitude: number;
  longitude: number;
  user_label: string | null;
  display_label: string;
  formatted_address: string | null;
  city: string | null;
  county: string | null;
  state: string | null;
  country: string | null;
  geocode_status: string;
  photos: PhotoSummary[];
}

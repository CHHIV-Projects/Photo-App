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
  filename?: string | null;
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
  aliases: string[];
}

export interface PersonAliasSummary {
  alias_id: number;
  alias: string;
}

export interface ClusterAssignmentSummary {
  cluster_id: number;
  face_count: number;
}

export interface PersonWithClusters {
  person_id: number;
  display_name: string;
  aliases: string[];
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

export interface ClusterListResponse extends ListResponse<ClusterSummary> {
  total_count: number;
  offset: number;
  limit: number;
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
  cluster_face_count?: number | null;
  person_id: number | null;
  person_name: string | null;
}

export interface PhotoFaceOverlayAsset {
  asset_sha256: string;
  canonical_width: number | null;
  canonical_height: number | null;
  faces: FaceInPhoto[];
}

export interface PhotoFaceOverlayBatchResponse {
  count: number;
  items: PhotoFaceOverlayAsset[];
}

export interface PhotoSummary {
  asset_sha256: string;
  filename: string;
  image_url: string | null;
  display_url: string | null;
  original_url: string | null;
  has_display_preview: boolean;
  display_source: string | null;
  captured_at: string | null;
  capture_time_trust: "high" | "low" | "unknown";
  face_count: number;
  has_live_photo_motion_companion: boolean;
  is_live_photo_motion_companion: boolean;
  live_photo_still_asset_sha256: string | null;
}

export interface SearchPhotoSummary {
  asset_sha256: string;
  filename: string;
  image_url: string | null;
  display_url: string | null;
  original_url: string | null;
  has_display_preview: boolean;
  display_source: string | null;
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
  has_live_photo_motion_companion: boolean;
  is_live_photo_motion_companion: boolean;
  live_photo_still_asset_sha256: string | null;
}

export interface SearchPhotoListResponse {
  total_count: number;
  offset: number;
  limit: number;
  items: SearchPhotoSummary[];
}

export interface PhotoBatchFailureSummary {
  asset_sha256: string;
  reason: string;
}

export interface PhotoBatchVisibilityResponse {
  success: boolean;
  action: "demote" | "restore";
  requested_count: number;
  updated_count: number;
  noop_count: number;
  failed_count: number;
  failures: PhotoBatchFailureSummary[];
}

export interface PhotoBatchAlbumSummaryResponse {
  success: boolean;
  album_id: number;
  album_name: string;
  requested_count: number;
  added_count: number;
  already_in_album_count: number;
  failed_count: number;
  failures: PhotoBatchFailureSummary[];
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

export interface CollectionSummary {
  collection_id: number;
  name: string;
  description: string | null;
  direct_asset_count: number;
  album_count: number;
  created_at: string;
  updated_at: string;
}

export interface CollectionAlbumSummary {
  album_id: number;
  name: string;
  asset_count: number;
}

export interface CollectionDetail {
  collection_id: number;
  name: string;
  description: string | null;
  direct_asset_count: number;
  album_count: number;
  created_at: string;
  updated_at: string;
  direct_assets: PhotoSummary[];
  albums: CollectionAlbumSummary[];
}

export interface CollectionAssetMembershipSummaryResponse {
  success: boolean;
  requested_count: number;
  added_count: number;
  already_present_count: number;
  failed_count: number;
}

export interface VisualEnrichmentCandidatePreviewAsset {
  asset_sha256: string;
  filename: string;
  image_url: string | null;
  display_url: string | null;
  is_canonical: boolean;
  duplicate_group_id: number | null;
  has_landmark_observation: boolean;
  has_landmark_context_label: boolean;
}

export interface VisualEnrichmentCandidatePreviewResponse {
  candidate_count: number;
  excluded_existing_observations_count: number;
  excluded_existing_context_labels_count: number;
  run_count: number;
  showing_count: number;
  assets: VisualEnrichmentCandidatePreviewAsset[];
}

export interface VisualEnrichmentRunResponse {
  requested_count: number;
  processed_count: number;
  provider_calls_attempted: number;
  observations_created_count: number;
  no_landmark_count: number;
  failed_count: number;
  report_path: string;
  mode: "live" | "dry_run";
  features_requested: string[];
  asset_results: VisualEnrichmentAssetRunSummary[];
}

export interface VisualEnrichmentScoredItem {
  description: string;
  score: number | null;
}

export interface VisualEnrichmentObjectItem {
  name: string;
  score: number | null;
}

export interface VisualEnrichmentAssetRunSummary {
  asset_sha256: string;
  filename: string;
  status: string;
  error: string | null;
  landmarks: VisualEnrichmentScoredItem[];
  web_entities: VisualEnrichmentScoredItem[];
  best_guess_labels: string[];
  labels: VisualEnrichmentScoredItem[];
  objects: VisualEnrichmentObjectItem[];
  created_observations: number;
  no_landmark: boolean;
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

export interface PhotoPlaceSummary {
  place_id: number;
  display_label: string;
  geocode_status: string;
  city: string | null;
  state: string | null;
  country: string | null;
  formatted_address: string | null;
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

export interface SourceReviewAssetSummary {
  asset_sha256: string;
  asset_sha_short: string;
  filename: string;
  image_url: string | null;
  display_url: string | null;
  original_url: string | null;
  has_display_preview: boolean;
  display_source: string | null;
  captured_at: string | null;
  provenance_count: number;
}

export interface SourceReviewHierarchyLevel {
  level_index: number;
  level_number: number;
  segment_text: string;
  normalized_prefix: string;
  display_prefix: string;
  is_filename: boolean;
  is_technical_hint: boolean;
}

export interface SourceReviewProvenanceRow {
  provenance_id: number;
  source_path: string;
  source_label: string | null;
  source_type: string | null;
  source_root_path: string | null;
  source_relative_path: string | null;
  ingestion_source_id: number | null;
  ingestion_run_id: number | null;
  ingested_at: string | null;
  source_hash: string | null;
  fallback_reason: string | null;
  parse_mode_used: string;
  parse_mode_options: string[];
  derived_relative_path: string | null;
  normalized_segments_relative: string[];
  normalized_segments_full: string[];
  hierarchy_levels_relative: SourceReviewHierarchyLevel[];
  hierarchy_levels_full: SourceReviewHierarchyLevel[];
  hierarchy_levels: SourceReviewHierarchyLevel[];
}

export interface SourceReviewAssetResponse {
  asset: SourceReviewAssetSummary;
  selected_provenance_id: number | null;
  provenance_rows: SourceReviewProvenanceRow[];
}

export interface AssetLandmarkContextSummary {
  asset_sha256: string;
  landmark_labels: string[];
  count: number;
}

export interface AssetContextLabelSummaryBatchResponse {
  count: number;
  items: AssetLandmarkContextSummary[];
}

export interface AssetContextLabelCreateRequest {
  asset_sha256: string;
  label: string;
  context_type: string;
  source_type: string;
  confidence?: number | null;
}

export interface AssetContextLabelCreateResponse {
  context_label: AssetContextLabelSummary;
  already_present: boolean;
}

export interface VisualEnrichmentWorkingSetAsset {
  asset_sha256: string;
  filename: string;
  image_url: string | null;
  display_url: string | null;
  is_canonical: boolean;
  duplicate_group_id: number | null;
  landmark_labels: string[];
  landmark_count: number;
}

export interface SourceReviewMatchAssetSummary {
  asset_sha256: string;
  filename: string;
  image_url: string | null;
  display_url: string | null;
  original_url: string | null;
  has_display_preview: boolean;
  display_source: string | null;
  captured_at: string | null;
  matched_path_fragment: string | null;
}

export interface SourceReviewMatchesResponse {
  provenance_id: number;
  hierarchy_mode: string;
  selected_level_index: number;
  selected_segment: string;
  selected_prefix: string;
  total_count: number;
  limit: number;
  is_limited: boolean;
  items: SourceReviewMatchAssetSummary[];
}

export interface SourceReviewCreateAlbumRequest {
  provenance_id: number;
  level_index: number;
  hierarchy_mode: "relative" | "full_source_path";
  album_name: string;
  conflict_mode: "ask" | "use_existing";
}

export interface SourceReviewCreateAlbumFailure {
  asset_sha256: string;
  reason: string;
}

export interface SourceReviewCreateAlbumResponse {
  outcome: "created" | "used_existing" | "name_conflict";
  album_id: number;
  album_name: string;
  created_new_album: boolean;
  provenance_id: number;
  hierarchy_mode: string;
  selected_level_index: number;
  selected_segment: string;
  selected_prefix: string;
  matching_asset_count: number;
  requested_count: number;
  added_count: number;
  already_present_count: number;
  failed_count: number;
  failures: SourceReviewCreateAlbumFailure[];
}

export interface SourceReviewCreateCollectionRequest {
  provenance_id: number;
  level_index: number;
  hierarchy_mode: "relative" | "full_source_path";
  collection_name: string;
}

export interface SourceReviewCreateCollectionFailure {
  asset_sha256: string;
  reason: string;
}

export interface SourceReviewCreateCollectionResponse {
  outcome: "created";
  collection_id: number;
  collection_name: string;
  created_new_collection: boolean;
  provenance_id: number;
  hierarchy_mode: string;
  selected_level_index: number;
  selected_segment: string;
  selected_prefix: string;
  matching_asset_count: number;
  requested_count: number;
  added_count: number;
  already_present_count: number;
  failed_count: number;
  failures: SourceReviewCreateCollectionFailure[];
}

export interface SourceReviewAddToCollectionRequest {
  provenance_id: number;
  level_index: number;
  hierarchy_mode: "relative" | "full_source_path";
  collection_id: number;
}

export interface SourceReviewAddToCollectionFailure {
  asset_sha256: string;
  reason: string;
}

export interface SourceReviewAddToCollectionResponse {
  outcome: "added_to_existing";
  collection_id: number;
  collection_name: string;
  provenance_id: number;
  hierarchy_mode: string;
  selected_level_index: number;
  selected_segment: string;
  selected_prefix: string;
  matching_asset_count: number;
  requested_count: number;
  added_count: number;
  already_present_count: number;
  failed_count: number;
  failures: SourceReviewAddToCollectionFailure[];
}

export interface SourceReviewCreateEventRequest {
  provenance_id: number;
  level_index: number;
  hierarchy_mode: "relative" | "full_source_path";
  event_label: string;
  start_at: string | null;
  end_at: string | null;
  existing_event_policy: "skip_existing";
}

export interface SourceReviewCreateEventFailure {
  asset_sha256: string;
  reason: string;
}

export interface SourceReviewCreateEventResponse {
  outcome: "created";
  event_id: number;
  event_label: string | null;
  provenance_id: number;
  hierarchy_mode: string;
  selected_level_index: number;
  selected_segment: string;
  selected_prefix: string;
  existing_event_policy: string;
  date_range_source: "user_input" | "asset_captured_at_fallback" | "asset_created_at_fallback";
  effective_start_at: string;
  effective_end_at: string;
  matching_asset_count: number;
  requested_count: number;
  assigned_count: number;
  already_in_event_count: number;
  skipped_existing_event_count: number;
  failed_count: number;
  failures: SourceReviewCreateEventFailure[];
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
  image_url: string | null;
  display_url: string | null;
  original_url: string | null;
  has_display_preview: boolean;
  display_source: string | null;
  display_rotation_degrees: 0 | 90 | 180 | 270;
  is_scan: boolean;
  capture_type: "digital" | "scan" | "unknown";
  capture_time_trust: "high" | "low" | "unknown";
  event: PhotoEventSummary | null;
  location: PhotoLocation | null;
  place: PhotoPlaceSummary | null;
  canonical_metadata: CanonicalMetadataSummary | null;
  metadata_observations: PhotoMetadataObservation[];
  provenance: PhotoProvenance[];
  duplicate_group_id: number | null;
  duplicate_group_type: "near" | null;
  is_canonical: boolean;
  quality_score: number | null;
  duplicate_count: number;
  canonical_asset_sha256: string | null;
  has_live_photo_motion_companion: boolean;
  live_photo_motion_asset_sha256: string | null;
  is_live_photo_motion_companion: boolean;
  live_photo_still_asset_sha256: string | null;
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
  image_url: string | null;
  display_url: string | null;
  original_url: string | null;
  has_display_preview: boolean;
  display_source: string | null;
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
  image_url: string | null;
  display_url: string | null;
  original_url: string | null;
  has_display_preview: boolean;
  display_source: string | null;
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
  image_url: string | null;
  display_url: string | null;
  original_url: string | null;
  has_display_preview: boolean;
  display_source: string | null;
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
  postal_code: string | null;
  country: string | null;
  geocode_status: string;
  place_type: string;
  user_verified: boolean;
  address_locked: boolean;
  alias_count: number;
}

export interface PlaceAliasSummary {
  id: number;
  place_id: string;
  alias: string;
  alias_normalized: string;
  created_at_utc: string | null;
}

export interface PlaceDetail {
  place_id: string;
  latitude: number;
  longitude: number;
  user_label: string | null;
  display_label: string;
  formatted_address: string | null;
  street: string | null;
  city: string | null;
  county: string | null;
  state: string | null;
  postal_code: string | null;
  country: string | null;
  geocode_status: string;
  place_type: string;
  user_verified: boolean;
  user_verified_at_utc: string | null;
  address_locked: boolean;
  address_source: string | null;
  notes: string | null;
  aliases: PlaceAliasSummary[];
  photos: PhotoSummary[];
}

export interface PlaceObservationSummary {
  id: number;
  place_id: string | null;
  asset_sha256: string | null;
  source_type: string;
  observation_type: string;
  status: string;
  raw_label: string | null;
  formatted_address: string | null;
  street: string | null;
  city: string | null;
  county: string | null;
  state: string | null;
  postal_code: string | null;
  country: string | null;
  latitude: number | null;
  longitude: number | null;
  confidence: number | null;
  raw_response_json: Record<string, unknown> | null;
  created_at_utc: string | null;
  asset: PlaceObservationAssetSummary | null;
  linked_place: PlaceObservationLinkedPlaceSummary | null;
}

export interface PlaceObservationAssetSummary {
  asset_sha256: string;
  filename: string | null;
  image_url: string | null;
  display_url: string | null;
}

export interface PlaceObservationLinkedPlaceSummary {
  place_id: string;
  display_label: string;
  latitude: number;
  longitude: number;
}

export interface PlaceObservationPatchRequest {
  status: "pending" | "accepted" | "rejected" | "ignored" | "superseded";
  apply_to_canonical?: boolean;
  set_user_verified?: boolean;
  set_address_locked?: boolean;
}

export interface GlobalPlaceObservationPatchRequest {
  status: "pending" | "accepted" | "rejected" | "ignored" | "superseded";
  place_id?: string | null;
}

export interface PlaceObservationCreatePlaceRequest {
  user_label: string;
}

export interface AssetContextLabelSummary {
  id: number;
  asset_sha256: string;
  asset_filename: string;
  asset_image_url?: string | null;
  asset_display_url?: string | null;
  duplicate_group_id?: number | null;
  is_canonical?: boolean | null;
  label: string;
  label_normalized: string;
  context_type: string;
  source_type: string;
  source_observation_id: number | null;
  status: string;
  confidence: number | null;
  created_at_utc: string;
}

export interface AcceptObservationAsContextRequest {
  label?: string;
}

export interface AcceptObservationAsContextResponse {
  context_label: AssetContextLabelSummary;
  observation_status: string;
  already_present: boolean;
}

export interface ContextLabelPropagationTargetSummary {
  asset_sha256: string;
  asset_filename: string;
  image_url: string | null;
  display_url: string | null;
  duplicate_group_id: number;
  is_canonical: boolean;
  already_has_label: boolean;
  selectable: boolean;
  default_selected: boolean;
}

export interface ContextLabelPropagationPreviewResponse {
  source_label: AssetContextLabelSummary;
  duplicate_group_id: number | null;
  eligible_target_count: number;
  targets: ContextLabelPropagationTargetSummary[];
  message: string | null;
}

export interface ContextLabelPropagationRequest {
  target_asset_sha256s: string[];
}

export interface ContextLabelPropagationResponse {
  source_label_id: number;
  requested_count: number;
  added_count: number;
  already_present_count: number;
  skipped_count: number;
  failed_count: number;
}

export interface PlacePatchRequest {
  user_label?: string | null;
  place_type?: string;
  formatted_address?: string | null;
  street?: string | null;
  city?: string | null;
  county?: string | null;
  state?: string | null;
  postal_code?: string | null;
  country?: string | null;
  user_verified?: boolean;
  address_locked?: boolean;
  address_source?: string | null;
  notes?: string | null;
}

export interface AdminDuplicateTypeCount {
  group_type: string;
  count: number;
}

export interface AdminAssetsSummary {
  total: number;
  visible: number;
  demoted: number;
}

export interface AdminDuplicatesSummary {
  total_groups: number;
  by_type: AdminDuplicateTypeCount[];
}

export interface AdminFacesSummary {
  total: number;
  unassigned: number;
}

export interface AdminPlacesSummary {
  total: number;
  with_user_label: number;
  without_user_label: number;
  linked_to_assets: number;
  empty: number;
}

export interface AdminSummaryResponse {
  generated_at: string;
  assets: AdminAssetsSummary;
  duplicates: AdminDuplicatesSummary;
  faces: AdminFacesSummary;
  places: AdminPlacesSummary;
}

export interface AdminDuplicateProcessingRunStatus {
  run_id: number | null;
  status: "idle" | "running" | "stop_requested" | "completed" | "failed" | "stopped";
  started_at: string | null;
  finished_at: string | null;
  elapsed_seconds: number | null;
  total_items: number;
  processed_items: number;
  current_stage: string | null;
  error_message: string | null;
  stop_requested: boolean;
  workset_cutoff: string | null;
  last_successful_cutoff: string | null;
}

export interface AdminDuplicateProcessingStatusResponse {
  generated_at: string;
  pending_items: number;
  current: AdminDuplicateProcessingRunStatus;
}

export interface AdminDuplicateProcessingActionResponse {
  accepted: boolean;
  message: string;
  status: AdminDuplicateProcessingRunStatus;
}

export interface AdminPlaceGeocodingRunStatus {
  run_id: number | null;
  status: "idle" | "running" | "stop_requested" | "completed" | "failed" | "stopped";
  started_at: string | null;
  finished_at: string | null;
  elapsed_seconds: number | null;
  total_places: number;
  processed_places: number;
  succeeded_places: number;
  failed_places: number;
  current_place_id: number | null;
  last_error: string | null;
  last_run_summary: string | null;
  stop_requested: boolean;
}

export interface AdminPlaceGeocodingStatusResponse {
  generated_at: string;
  pending_places: number;
  current: AdminPlaceGeocodingRunStatus;
}

export interface AdminPlaceGeocodingActionResponse {
  accepted: boolean;
  message: string;
  status: AdminPlaceGeocodingRunStatus;
}

export interface AdminFaceProcessingRunStatus {
  run_id: number | null;
  status: "idle" | "running" | "stop_requested" | "completed" | "failed" | "stopped";
  started_at: string | null;
  finished_at: string | null;
  elapsed_seconds: number | null;
  assets_pending_detection: number;
  assets_processed_detection: number;
  faces_pending_embedding: number;
  faces_processed_embedding: number;
  faces_pending_clustering: number;
  faces_processed_clustering: number;
  crops_pending: number;
  crops_generated: number;
  current_stage: string | null;
  last_error: string | null;
  last_run_summary: string | null;
  stop_requested: boolean;
}

export interface AdminFaceProcessingStatusResponse {
  generated_at: string;
  pending_detection: number;
  pending_embedding: number;
  pending_clustering: number;
  pending_crops: number;
  current: AdminFaceProcessingRunStatus;
}

export interface AdminFaceProcessingActionResponse {
  accepted: boolean;
  message: string;
  status: AdminFaceProcessingRunStatus;
}

export interface AdminHeicPreviewRunStatus {
  run_id: number | null;
  status: "idle" | "running" | "stop_requested" | "completed" | "failed" | "stopped";
  started_at: string | null;
  finished_at: string | null;
  elapsed_seconds: number | null;
  assets_pending: number;
  assets_processed: number;
  assets_succeeded: number;
  assets_failed: number;
  last_error: string | null;
  last_run_summary: string | null;
  stop_requested: boolean;
}

export interface AdminHeicPreviewStatusResponse {
  generated_at: string;
  pending_previews: number;
  current: AdminHeicPreviewRunStatus;
}

export interface AdminHeicPreviewActionResponse {
  accepted: boolean;
  message: string;
  status: AdminHeicPreviewRunStatus;
}

export interface AdminLivePhotoPairingRunStatus {
  status: "idle" | "running" | "completed" | "failed";
  started_at: string | null;
  finished_at: string | null;
  elapsed_seconds: number | null;
  scanned_rows: number;
  candidate_groups: number;
  pairs_created: number;
  already_paired: number;
  updated: number;
  removed_stale: number;
  skipped_missing_source: number;
  skipped_ambiguous: number;
  skipped_suspicious_delta: number;
  last_report_path: string | null;
  last_error: string | null;
}

export interface AdminLivePhotoPairingStatusResponse {
  generated_at: string;
  current: AdminLivePhotoPairingRunStatus;
}

export interface AdminLivePhotoPairingActionResponse {
  accepted: boolean;
  message: string;
  status: AdminLivePhotoPairingRunStatus;
}

// Source Intake visibility types (12.24)

export interface SourceIntakeReportCounts {
  total_files_scanned: number | null;
  skipped_already_known: number | null;
  eligible_unknown_files: number | null;
  selected_for_session: number | null;
  staged_to_dropzone: number | null;
  processed_new_unique: number | null;
  failed_or_rejected: number | null;
  deferred_unready_count: number | null;
  remaining_unknown_eligible: number | null;
}

export interface SourceIntakeSourceSummary {
  source_id: number;
  source_label: string;
  source_type: string;
  source_root_path: string | null;
  account_username: string | null;
  first_seen_at: string | null;
  last_run_at: string | null;
  latest_report_filename: string | null;
  latest_counts: SourceIntakeReportCounts | null;
  source_complete: boolean | null;
}

export interface SourceIntakeSourcesResponse {
  generated_at: string;
  sources: SourceIntakeSourceSummary[];
}

export type SourceProfileStatus =
  | "active"
  | "inactive"
  | "archived"
  | "test"
  | "deprecated";

export type SourceProfileType =
  | "local_folder"
  | "external_drive"
  | "removable_media"
  | "optical_media"
  | "cloud_export"
  | "scan_batch"
  | "other";

export type SourceCloudProvider =
  | "icloud"
  | "onedrive"
  | "google_photos"
  | "dropbox"
  | "other";

export type SourceAcquisitionMethod =
  | "icloudpd"
  | "folder_scan"
  | "manual_export"
  | "none";

export interface SourceProfileSummary {
  source_id: number;
  source_label: string;
  source_type: SourceProfileType;
  source_root_path: string | null;
  endpoint_relative_root: string | null;
  endpoint_id: number | null;
  endpoint_alias: string | null;
  endpoint_source_type: SourceIdentityProbeSourceType | null;
  profile_status: SourceProfileStatus;
  cloud_provider: SourceCloudProvider | null;
  acquisition_method: SourceAcquisitionMethod | null;
  managed_staging_path: string | null;
  account_username_masked: string | null;
  account_username: string | null;
  first_seen_at: string | null;
  last_run_at: string | null;
  provenance_count: number | null;
  ingestion_runs_count: number | null;
  source_intake_runs_count: number | null;
  icloud_acquisition_runs_count: number | null;
}

export interface SourceProfileDetail extends SourceProfileSummary {
  normalized_label: string;
  effective_path: string | null;
  effective_path_kind: "source_root_path" | "managed_staging_path" | "none";
  expected_acquisition_path: string | null;
  source_root_path_relative: string | null;
  managed_staging_path_relative: string | null;
  effective_path_relative: string | null;
  is_referenced: boolean;
  has_path_divergence: boolean;
  warnings: string[];
}

export interface IcloudReadinessReason {
  code: string;
  message: string;
}

export interface IcloudReadinessOperationConflicts {
  icloud_acquisition_active: boolean;
  source_intake_active: boolean;
  icloud_cleanup_active: boolean;
  source_intake_active_for_this_source: boolean | null;
  icloud_cleanup_active_for_this_source: boolean | null;
}

export interface IcloudReadinessLastAcquisition {
  status: string;
  started_at: string | null;
  finished_at: string | null;
  downloaded_count: number;
  skipped_count: number;
  failed_count: number;
  error_code: string | null;
  report_path: string | null;
}

export interface IcloudSourceReadiness {
  source_id: number;
  is_icloud_profile: boolean;
  readiness_status: "ready" | "warning" | "not_ready" | "unknown";
  profile_status: string;
  source_label: string;
  source_type: string;
  cloud_provider: string | null;
  account_username_masked: string | null;
  source_root_path: string | null;
  managed_staging_path: string | null;
  expected_acquisition_path: string | null;
  effective_path: string | null;
  approved_root_status: "ok" | "blocked" | "unknown";
  staging_folder_status: "exists" | "missing" | "unsafe" | "unknown";
  path_alignment_status: "matched" | "mismatch" | "unknown";
  source_root_alignment_status: "matched" | "mismatch" | "unknown";
  source_registration_status: "matched" | "mismatch" | "unknown";
  auth_status: "unknown" | "action_required";
  last_auth_error_code: string | null;
  operation_conflicts: IcloudReadinessOperationConflicts;
  last_acquisition: IcloudReadinessLastAcquisition | null;
  blocking_reasons: IcloudReadinessReason[];
  warnings: IcloudReadinessReason[];
  recommended_action: string;
}

export interface SourceProfilePathCheckResponse {
  source_id: number;
  path: string | null;
  path_relative: string | null;
  path_kind: "source_root_path" | "managed_staging_path";
  exists: boolean;
  is_directory: boolean;
  checked_at: string;
}

export interface SourceProfileStagingFolderCreateResponse {
  source_id: number;
  path: string;
  path_relative: string | null;
  created: boolean;
  exists: boolean;
  checked_at: string;
}

export type SourceProfileReadinessStatus =
  | "ready"
  | "path_only"
  | "needs_review"
  | "blocked"
  | "provider_specific"
  | "unknown";

export type SourceProfileIdentityMatchStatus =
  | "not_enrolled"
  | "matched"
  | "needs_review"
  | "mismatch"
  | "unavailable"
  | "unsupported"
  | "provider_specific"
  | "ambiguous"
  | "unknown";

export interface ReadinessMessage {
  code: string;
  message: string;
}

export type SourceDurableIdentityStatus =
  | "verified"
  | "not_verified"
  | "provider_specific"
  | "unknown";

export interface SourceProfileReadinessResponse {
  source_profile_id: number;
  source_label: string | null;
  source_type: string | null;
  profile_status: string | null;
  cloud_provider: string | null;
  endpoint_id: number | null;
  endpoint_alias: string | null;
  endpoint_source_type: string | null;
  durable_identity_status: SourceDurableIdentityStatus;
  durable_identity_reason: string | null;
  durable_identity_identifier_type: string | null;
  durable_identity_identifier: string | null;
  durable_identity_evidence: string[];
  readiness_status: SourceProfileReadinessStatus;
  identity_match_status: SourceProfileIdentityMatchStatus;
  can_run_source_intake: boolean;
  requires_operator_acknowledgment: boolean;
  hard_block: boolean;
  operator_message: string;
  recommended_next_action: string;
  warnings: ReadinessMessage[];
  blockers: ReadinessMessage[];
  checked_at: string;
  probe_summary: Record<string, unknown>;
  observed_path_summary: Record<string, unknown>;
  access_node_summary: Record<string, unknown>;
  advanced_details: Record<string, unknown>;
}

export type SourceSelectionResult = "selected" | "not_selected";
export type SourceSelectionAvailability = "available" | "unavailable" | "needs_attention";
export type SourceSelectionWorkflowKind = "filesystem_source_intake" | "icloud_intake";

export interface SourceSelectionRequest {
  source_profile_id: number;
}

export interface SelectedSourceContext {
  source_profile_id: number;
  source_endpoint_id: number | null;
  source_type: string | null;
  friendly_source_type: string;
  device_label: string;
  source_name: string;
  profile_status: string;
  endpoint_status: string | null;
  endpoint_relative_root: string | null;
  configured_source_root: string | null;
  resolved_source_root: string | null;
  resolved_endpoint_path: string | null;
  root_display: string;
  durable_identity_status: SourceDurableIdentityStatus;
  identity_match_status: string;
  availability: SourceSelectionAvailability;
  workflow_kind: SourceSelectionWorkflowKind;
  provider_context: Record<string, unknown> | null;
  selected_at: string;
  selection_version: string;
  selection_fingerprint: string | null;
}

export interface SourceSelectionResponse {
  result: SourceSelectionResult;
  availability: SourceSelectionAvailability;
  workflow_kind: SourceSelectionWorkflowKind | null;
  selected_source_context: SelectedSourceContext | null;
  message: string;
  retry_guidance: string | null;
  advanced_details: Record<string, unknown>;
}

export interface SourceProfilesResponse {
  generated_at: string;
  profiles: SourceProfileSummary[];
}

export interface SourceProfileCreateRequest {
  source_label: string;
  source_type: SourceProfileType;
  source_root_path?: string | null;
  profile_status: SourceProfileStatus;
  cloud_provider?: SourceCloudProvider | null;
  account_username?: string | null;
  acquisition_method?: SourceAcquisitionMethod | null;
  managed_staging_path?: string | null;
}

export interface SourceProfileCreateResponse {
  already_exists: boolean;
  profile: SourceProfileSummary;
}

export type SourceIdentityProbeSourceType =
  | "local"
  | "external_device"
  | "removable_media"
  | "optical_media"
  | "nas"
  | "cloud";

export interface SourceIdentityProbeRequest {
  source_type: SourceIdentityProbeSourceType;
  observed_path?: string | null;
  probe_mode?: "setup_probe" | "readiness_probe" | "run_launch_verification" | "diagnostic_probe";
  intended_use?: string | null;
  os_family?: "windows" | "linux" | "macos" | "unknown";
}

export interface SourceIdentityProbeEvidenceItem {
  category: string;
  code: string;
  status: string;
  durability: string;
  privacy_level: string;
  display_value: string | null;
  masked_value: string | null;
  message: string | null;
}

export interface SourceIdentityProbeResponse {
  probe_status: "completed" | "completed_with_warnings" | "blocked" | "unavailable" | "unsupported_provider" | "provider_error";
  source_type: SourceIdentityProbeSourceType;
  observed_path: string | null;
  normalized_observed_path: string | null;
  source_root_candidate: {
    path: string | null;
    is_valid_source_root_candidate: boolean;
    filesystem_boundary_type: string;
    root_reason: string;
  };
  evidence_items: SourceIdentityProbeEvidenceItem[];
  blockers: SourceIdentityProbeEvidenceItem[];
  warnings: SourceIdentityProbeEvidenceItem[];
  next_safe_actions: string[];
}

export interface EnrollmentMessage {
  code: string;
  message: string;
}

export interface SourceEndpointEnrollmentCandidate {
  source_type: string;
  observed_path: string | null;
  normalized_observed_path: string | null;
  source_root_candidate_path: string | null;
  filesystem_boundary_type: string;
  is_valid_source_root_candidate: boolean;
  probe_status: string;
  confidence_tier: string;
  safe_to_run: string;
  provider_name: string;
  provider_version: string;
  access_node_label: string;
  access_node_os_family: string;
  identity_fingerprint_hash: string | null;
  identity_fingerprint_version: string | null;
  identity_fingerprint_strength: "strong" | "medium" | "weak" | "unavailable";
}

export interface SourceEndpointEnrollmentMatch {
  source_endpoint_id: number;
  alias: string;
  source_type: string;
  match_strength: string;
  match_reason: string;
  identity_confidence: string;
}

export interface SourceEndpointEnrollmentPlanRequest {
  source_profile_id: number;
  probe_request: SourceIdentityProbeRequest;
  proposed_alias?: string | null;
  selected_existing_endpoint_id?: number | null;
  operator_review_acknowledged?: boolean;
}

export interface SourceEndpointEnrollmentPlanResponse {
  generated_at: string;
  plan_status:
    | "ready"
    | "needs_review"
    | "blocked"
    | "alias_conflict"
    | "duplicate_match"
    | "source_profile_already_linked";
  source_profile_id: number;
  source_profile_label: string | null;
  existing_source_endpoint_id: number | null;
  endpoint_action: "create_new_endpoint" | "link_existing_endpoint" | "none";
  source_profile_action: "link_existing_profile" | "none";
  proposed_alias: string | null;
  alias_normalized: string | null;
  plan_fingerprint: string;
  durable_identity_status: SourceDurableIdentityStatus;
  durable_identity_reason: string | null;
  durable_identity_identifier_type: string | null;
  durable_identity_identifier: string | null;
  durable_identity_evidence: string[];
  candidate: SourceEndpointEnrollmentCandidate | null;
  possible_matches: SourceEndpointEnrollmentMatch[];
  blockers: EnrollmentMessage[];
  warnings: EnrollmentMessage[];
  required_confirmations: EnrollmentMessage[];
}

export interface SourceEndpointEnrollmentConfirmRequest {
  source_profile_id: number;
  probe_request: SourceIdentityProbeRequest;
  confirmed_alias?: string | null;
  selected_existing_endpoint_id?: number | null;
  plan_fingerprint?: string | null;
  operator_confirmed: boolean;
  operator_review_acknowledged?: boolean;
}

export interface SourceEndpointEnrollmentConfirmResponse {
  generated_at: string;
  enrollment_status: "completed" | "blocked" | "failed";
  source_profile_id: number;
  source_endpoint_id: number | null;
  source_profile_endpoint_id: number | null;
  endpoint_action: "create_new_endpoint" | "link_existing_endpoint" | "none";
  source_profile_action: "link_existing_profile" | "none";
  already_linked: boolean;
  created_endpoint: boolean;
  created_access_node: boolean;
  created_observed_path: boolean;
  observed_path_id: number | null;
  plan_fingerprint: string | null;
  durable_identity_status: SourceDurableIdentityStatus;
  durable_identity_reason: string | null;
  durable_identity_identifier_type: string | null;
  durable_identity_identifier: string | null;
  durable_identity_evidence: string[];
  blockers: EnrollmentMessage[];
  warnings: EnrollmentMessage[];
}

export type SourceCreationType = "local" | "external" | "removable" | "optical" | "nas";
export type SourceCreationNameAction = "create_new" | "use_existing" | "rename_existing" | "cancel";
export type SourceCreationRecognitionStatus =
  | "new_device"
  | "existing_device"
  | "existing_device_type_mismatch"
  | "existing_source_active"
  | "existing_source_inactive"
  | "existing_legacy_source"
  | "multiple_source_matches"
  | "identity_needs_review"
  | "location_blocked";

export interface SourceCreationMessage {
  code: string;
  message: string;
}

export interface SourceCreationEndpointMatch {
  source_endpoint_id: number;
  alias: string;
  source_type: string;
  match_strength: "strong" | "legacy_review";
  match_reason: string;
  identity_confidence: string;
}

export interface SourceCreationSourceMatch {
  source_profile_id: number;
  source_label: string;
  source_type: string;
  profile_status: string;
  source_root_path: string | null;
  source_endpoint_id: number | null;
  endpoint_alias: string | null;
  endpoint_relative_root: string | null;
  match_kind: "modern_exact" | "legacy_exact";
  classification: string;
  provenance_count: number;
  ingestion_runs_count: number;
  source_intake_runs_count: number;
  asset_count: number;
  has_protected_history: boolean;
  recommended_action: string | null;
  allowed_actions: string[];
  selected_for_action: boolean;
  conflict_reason: string | null;
}

export interface SourceCreationPlanRequest {
  source_type: SourceCreationType;
  observed_path: string;
  source_name?: string | null;
  device_name?: string | null;
  naming_action?: SourceCreationNameAction | null;
  selected_existing_endpoint_id?: number | null;
  selected_canonical_source_id?: number | null;
  duplicate_source_ids_to_inactivate?: number[];
  use_registered_source_type?: boolean;
  operator_review_acknowledged?: boolean;
}

export interface SourceCreationPlanResponse {
  generated_at: string;
  plan_status: "ready" | "needs_review" | "blocked" | "source_exists";
  plan_fingerprint: string;
  recognition_status: SourceCreationRecognitionStatus;
  recognition_title: string;
  recognition_message: string;
  source_type: SourceCreationType;
  recognized_source_type: SourceCreationType;
  registered_endpoint_source_type: string | null;
  source_type_mismatch: boolean;
  persisted_source_type: string;
  requested_device_name: string;
  device_name: string;
  naming_action: SourceCreationNameAction | null;
  name_decision_required: boolean;
  observed_path: string;
  canonical_source_root_path: string;
  endpoint_relative_root: string;
  entire_endpoint: boolean;
  entire_endpoint_label: string | null;
  suggested_source_name: string;
  requested_source_name: string | null;
  source_name_suggested_alternative: string | null;
  source_display_name: string;
  durable_identity_status: SourceDurableIdentityStatus;
  durable_identity_reason: string | null;
  durable_identity_identifier_type: string | null;
  durable_identity_identifier: string | null;
  durable_identity_evidence: string[];
  endpoint_action:
    | "create_new_endpoint"
    | "reuse_existing_endpoint"
    | "upgrade_legacy_endpoint"
    | "rename_existing_endpoint"
    | "upgrade_and_rename_endpoint"
    | "none";
  source_action:
    | "create_new_source"
    | "reuse_existing_source"
    | "reactivate_existing_source"
    | "adopt_legacy_source"
    | "adopt_and_reactivate_source"
    | "canonicalize_existing_source"
    | "canonicalize_and_reactivate_source"
    | "none";
  selected_existing_endpoint_id: number | null;
  selected_canonical_source_id: number | null;
  existing_source_profile_id: number | null;
  existing_source_status: string | null;
  duplicate_source_ids_to_inactivate: number[];
  possible_matches: SourceCreationEndpointMatch[];
  exact_source_matches: SourceCreationSourceMatch[];
  conflicting_source_profile_ids: number[];
  final_action_label: string;
  blockers: SourceCreationMessage[];
  warnings: SourceCreationMessage[];
  required_confirmations: SourceCreationMessage[];
  advanced_details: Record<string, unknown>;
}

export interface SourceCreationConfirmRequest extends SourceCreationPlanRequest {
  plan_fingerprint: string;
  operator_confirmed: boolean;
}

export interface SourceCreationConfirmResponse {
  generated_at: string;
  creation_status: "completed" | "blocked";
  plan_fingerprint: string | null;
  source_profile_id: number | null;
  source_endpoint_id: number | null;
  observed_path_id: number | null;
  alias_event_id: number | null;
  source_type: SourceCreationType;
  recognized_source_type: SourceCreationType;
  persisted_source_type: string;
  device_name: string;
  observed_path: string;
  canonical_source_root_path: string;
  endpoint_relative_root: string;
  entire_endpoint: boolean;
  entire_endpoint_label: string | null;
  suggested_source_name: string;
  requested_source_name: string | null;
  source_display_name: string;
  durable_identity_status: SourceDurableIdentityStatus;
  durable_identity_reason: string | null;
  durable_identity_identifier_type: string | null;
  durable_identity_identifier: string | null;
  durable_identity_evidence: string[];
  endpoint_action: SourceCreationPlanResponse["endpoint_action"];
  source_action: SourceCreationPlanResponse["source_action"];
  created_endpoint: boolean;
  reused_endpoint: boolean;
  upgraded_legacy_endpoint: boolean;
  renamed_endpoint: boolean;
  created_source: boolean;
  reused_source: boolean;
  reactivated_source: boolean;
  adopted_legacy_source: boolean;
  canonicalized_source: boolean;
  inactivated_duplicate_source_ids: number[];
  created_observed_path: boolean;
  blockers: SourceCreationMessage[];
  warnings: SourceCreationMessage[];
  advanced_details: Record<string, unknown>;
}

export interface SourceProfileMetadataUpdateRequest {
  source_label?: string;
  profile_status?: SourceProfileStatus;
  cloud_provider?: SourceCloudProvider | null;
  account_username?: string | null;
  acquisition_method?: SourceAcquisitionMethod | null;
  managed_staging_path?: string | null;
}

// ── iCloud Acquisition (Milestone 12.42/12.43) ──────────────────────────────

export interface IcloudAcquisitionRunStatus {
  run_id: number | null;
  status:
    | "idle"
    | "running"
    | "stop_requested"
    | "completed"
    | "completed_with_warnings"
    | "failed"
    | "stopped";
  source_label: string | null;
  source_type: string | null;
  source_root_path: string | null;
  acquisition_mode: "standard" | "list_first_non_repeat";
  source_registration_status: string | null;
  username: string | null;
  staging_path: string | null;
  recent_count: number | null;
  resolved_executable: string | null;
  icloudpd_version: string | null;
  started_at: string | null;
  completed_at: string | null;
  elapsed_seconds: number | null;
  downloaded_count: number;
  skipped_existing_count: number;
  failed_count: number;
  stdout_tail: string | null;
  stderr_tail: string | null;
  report_path: string | null;
  error_code: string | null;
  error_message: string | null;
  stop_requested: boolean;
  file_inventory_count: number | null;
  recommended_source_intake_command: string | null;
}

export interface IcloudAcquisitionStatusResponse {
  generated_at: string;
  current: IcloudAcquisitionRunStatus;
}

export interface IcloudAcquisitionRunRequest {
  source_label: string;
  username: string;
  recent_count: number;
  source_type?: string;
  acquisition_mode?: "standard" | "list_first_non_repeat";
}

export interface IcloudAcquisitionRunResponse {
  status: string;
  message: string;
  current: IcloudAcquisitionRunStatus;
}

export interface IcloudAcquisitionStopResponse {
  status: string;
  message: string;
  current: IcloudAcquisitionRunStatus;
}

export interface SourceIntakeReportSummary {
  report_filename: string;
  generated_at_utc: string | null;
  source_label: string | null;
  source_path: string | null;
  ingestion_source_id: number | null;
  ingestion_run_id: number | null;
  ingest_source_limit: number | null;
  ingest_batch_size: number | null;
  source_complete: boolean | null;
  counts: SourceIntakeReportCounts | null;
}

export interface SourceIntakeReportsResponse {
  generated_at: string;
  reports: SourceIntakeReportSummary[];
}

export interface SourceIntakeReportDetail {
  report_filename: string;
  raw: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Source Registry
// ---------------------------------------------------------------------------

export interface SourceCreateRequest {
  source_label: string;
  source_type: string;
  source_root_path: string;
  account_username?: string | null;
  create_new_label?: boolean;
}

export interface SourceCreateResponse {
  ingestion_source_id: number;
  source_label: string;
  source_type: string;
  source_root_path: string | null;
  account_username: string | null;
  created_at: string;
  was_existing: boolean;
}

// ---------------------------------------------------------------------------
// Admin-launched Source Intake
// ---------------------------------------------------------------------------

export interface SourceIntakeRunRequest {
  ingestion_source_id: number;
  source_intake_limit: number | null;
  ingest_batch_size: number;
  readiness_acknowledged?: boolean;
}

export interface SourceIntakeReadinessRejectionPayload {
  detail?: string;
  error_code?: string;
  source_profile_id?: number;
  source_label?: string | null;
  source_type?: string | null;
  profile_status?: string | null;
  cloud_provider?: string | null;
  endpoint_id?: number | null;
  endpoint_alias?: string | null;
  endpoint_source_type?: string | null;
  readiness_status?: SourceProfileReadinessStatus;
  identity_match_status?: SourceProfileIdentityMatchStatus;
  can_run_source_intake?: boolean;
  requires_operator_acknowledgment?: boolean;
  hard_block?: boolean;
  operator_message?: string;
  recommended_next_action?: string;
  warnings?: ReadinessMessage[];
  blockers?: ReadinessMessage[];
  checked_at?: string;
  readiness?: Partial<SourceProfileReadinessResponse>;
  current?: SourceIntakeStatusSnapshot;
}

export interface SourceIntakeStatusSnapshot {
  run_id: number | null;
  status: string;
  ingestion_run_id: number | null;
  source_label: string | null;
  source_type: string | null;
  source_root_path: string | null;
  source_intake_limit: number | null;
  ingest_batch_size: number | null;
  started_at: string | null;
  finished_at: string | null;
  elapsed_seconds: number | null;
  files_scanned: number;
  skipped_known: number;
  selected: number;
  staged: number;
  processed_new_unique: number;
  failed_or_rejected: number;
  remaining_unknown: number;
  report_path: string | null;
  error_message: string | null;
  stop_requested: boolean;
}

export interface SourceIntakeRunResponse {
  status: string;
  message: string;
  current: SourceIntakeStatusSnapshot;
}

export interface SourceIntakeStopResponse {
  status: string;
  message: string;
  current: SourceIntakeStatusSnapshot;
}

export interface IcloudStagingCleanupRunRequest {
  source_id: number;
  dry_run: boolean;
}

export interface IcloudStagingCleanupExecuteRequest {
  source_id: number;
  dry_run_run_id: number;
  explicit_confirmation: string;
}

export interface IcloudStagingCleanupEligibleFile {
  relative_path: string;
  size_bytes: number | null;
  asset_sha256: string | null;
  staged_sha256: string | null;
  verification_state: string;
  asset_id: number | null;
}

export interface IcloudStagingCleanupRunStatus {
  run_id: number | null;
  status: string;
  source_id: number | null;
  source_label: string | null;
  source_root_path: string | null;
  dry_run: boolean;
  started_at: string | null;
  finished_at: string | null;
  elapsed_seconds: number | null;
  eligible_count: number;
  deleted_count: number;
  skipped_count: number;
  total_bytes_eligible: number;
  total_bytes_deleted: number;
  total_files: number;
  processed_files: number;
  current_stage: string | null;
  protected_count: number;
  verification_failed_count: number;
  file_missing_count: number;
  delete_failed_count: number;
  manifest_fingerprint: string | null;
  planner_version: string | null;
  preview_expires_at: string | null;
  authorized_dry_run_id: number | null;
  authorization_consumed_at: string | null;
  skipped_reasons: Record<string, number>;
  skipped_samples: Record<string, string[]>;
  eligible_files: IcloudStagingCleanupEligibleFile[];
  report_path: string | null;
  error_message: string | null;
}

export interface IcloudStagingCleanupStatusResponse {
  generated_at: string;
  current: IcloudStagingCleanupRunStatus;
}

export interface IcloudStagingCleanupRunResponse {
  status: string;
  message: string;
  current: IcloudStagingCleanupRunStatus;
}

export interface IcloudStagingCleanupReadinessResponse {
  generated_at: string;
  source_id: number;
  readiness_status: "ready" | "blocked";
  canonical_staging_path: string | null;
  blocking_reasons: IcloudReadinessReason[];
  latest_dry_run: IcloudStagingCleanupRunStatus;
}

export interface IcloudBackfillInventoryScanRequest {
  source_id: number;
  max_candidates: number;
}

export interface IcloudBackfillInventoryStatus {
  source_id: number;
  status: string;
  last_inventory_scan_at: string | null;
  last_scan_candidate_count: number;
  last_scan_created_count: number;
  last_scan_updated_count: number;
  inventory_total_count: number;
  eligible_metadata_count: number;
  unsupported_or_ambiguous_count: number;
  backfill_completed_count: number;
  unresolved_eligible_count: number;
  acquirable_pending_count: number;
  retryable_failed_count: number;
  ambiguous_or_unsupported_count: number;
  deferred_current_count: number;
  deferred_adjusted_resource_count: number;
  deferred_ambiguous_count: number;
  deferred_unsupported_count: number;
  deferred_new_since_last_scan_count: number;
  deferred_changed_since_last_scan_count: number;
  source_exhausted: boolean;
  scan_limit_reached: boolean;
  stop_reason: string | null;
}

export interface IcloudBackfillInventoryScanResponse {
  status: string;
  message: string;
  current: IcloudBackfillInventoryStatus;
}

export interface IcloudBackfillStatusResponse {
  generated_at: string;
  current: IcloudBackfillInventoryStatus;
}

export interface IcloudBackfillAcquirePreviewRequest {
  source_id: number;
  acquire_limit: number;
  max_listing_candidates: number;
  include_items: boolean;
}

export interface IcloudBackfillAcquirePreviewItem {
  inventory_id: number;
  logical_resource_count: number;
  is_live_photo: boolean;
  primary_relative_path: string | null;
}

export interface IcloudBackfillAcquirePreviewResponse {
  source_id: number;
  status: string;
  selected_inventory_count: number;
  matched_listing_count: number;
  preview_selected_logical_count: number;
  preview_selected_resource_count: number;
  skipped_stale_count: number;
  skipped_known_count: number;
  skipped_unsupported_count: number;
  skipped_ambiguous_count: number;
  skipped_missing_identity_count: number;
  skipped_pending_classification_count: number;
  skipped_completed_count: number;
  unsafe_manifest_count: number;
  acquire_limit: number;
  max_listing_candidates: number;
  stop_reason: string;
  next_safe_action: string;
  preview_items: IcloudBackfillAcquirePreviewItem[];
}

export interface IcloudBackfillAcquireRequest {
  source_id: number;
  acquire_limit: number;
  max_listing_candidates: number;
  dry_run: boolean;
  auto_run_source_intake: boolean;
  include_items: boolean;
}

export interface IcloudBackfillAcquireItem {
  inventory_id: number;
  acquisition_state: string | null;
  backfill_completed: boolean;
  backfill_resolution_state: string | null;
  logical_resource_count: number | null;
  is_live_photo: boolean | null;
  primary_relative_path: string | null;
}

export interface IcloudBackfillAcquireResponse {
  source_id: number;
  status: string;
  dry_run: boolean;
  auto_run_source_intake: boolean;
  selected_inventory_count: number;
  matched_listing_count: number;
  selected_logical_count: number;
  selected_resource_count: number;
  downloaded_logical_count: number;
  downloaded_resource_count: number;
  source_intake_attempted: boolean;
  source_intake_succeeded: boolean;
  source_intake_run_id: number | null;
  acquisition_run_id: number | null;
  acquisition_batch_id: number | null;
  backfill_completed_count: number;
  skipped_stale_count: number;
  skipped_known_count: number;
  skipped_unsupported_count: number;
  skipped_ambiguous_count: number;
  skipped_missing_identity_count: number;
  skipped_pending_classification_count: number;
  skipped_completed_count: number;
  failed_retryable_count: number;
  failed_terminal_count: number;
  stop_reason: string;
  next_safe_action: string;
  acquired_resource_paths: string[];
  items: IcloudBackfillAcquireItem[];
}

export interface SourceProfileDeferredAssetItem {
  id: number;
  inventory_id: number | null;
  source_profile_id: number;
  primary_relative_path: string | null;
  filename: string | null;
  extension: string | null;
  content_type: string | null;
  resource_count: number;
  is_live_photo: boolean;
  grouping: string | null;
  deferred_category: string;
  deferred_reason_code: string;
  deferred_reason_human: string;
  policy_status: string;
  current_state: string;
  first_seen_at: string;
  last_seen_at: string;
  observation_count: number;
}

export interface SourceProfileDeferredAssetsResponse {
  source_id: number;
  limit: number;
  category: string | null;
  reason_code: string | null;
  state: string | null;
  items: SourceProfileDeferredAssetItem[];
}

export interface IcloudHistoricalRoutineStatus {
  source_id: number;
  source_label: string | null;
  total_imported_from_source: number;
  inventory_total_logical: number;
  backfill_completed_logical: number;
  eligible_pending_logical: number;
  available_inventory: "yes" | "no" | "unknown";
  logical_candidates_ready: number;
  latest_prepare_run_id: number | null;
  prepare_status: string | null;
  prepare_expires_at: string | null;
  target_logical_candidates: number;
  new_deferred_this_prepare: number;
  source_exhaustion_state: string;
  provider_records_scanned: number;
  scan_depth_used: number;
  deferred_current_logical: number;
  deferred_adjusted_resource_logical: number;
  deferred_ambiguous_logical: number;
  deferred_unsupported_logical: number;
  retryable_failed_logical: number;
  last_inventory_scan_at: string | null;
  last_inventory_refresh_at: string | null;
  last_historical_run_at: string | null;
  last_historical_run_id: number | null;
  last_cleanup_run_id: number | null;
  local_staging_file_count: number;
  partial_file_count: number;
  backfill_execute_file_count: number;
  operator_message: string;
}

export interface IcloudHistoricalRoutineStatusResponse {
  generated_at: string;
  current: IcloudHistoricalRoutineStatus;
}

export interface IcloudHistoricalRoutineRefreshRequest {
  source_id: number;
  max_candidates?: number;
}

export interface IcloudHistoricalRoutineRefreshResponse {
  status: string;
  message: string;
  source_id: number;
  prepare_run_id: number;
  inventory_total_logical: number;
  created_logical: number;
  updated_logical: number;
  eligible_pending_logical: number;
  available_inventory: "yes" | "no" | "unknown";
  target_logical_candidates: number;
  logical_candidates_ready: number;
  new_deferred_this_prepare: number;
  deferred_current_logical: number;
  deferred_adjusted_resource_logical: number;
  source_exhausted: boolean;
  scan_limit_reached: boolean;
  source_exhaustion_state: string;
  provider_records_scanned: number;
  scan_depth_used: number;
  expires_at: string;
  scanned_at: string;
  scan_limit_note: string;
  operator_message: string;
}

export interface IcloudHistoricalRoutineRunRequest {
  source_id: number;
  target_logical_assets?: number;
  internal_batch_size?: number;
}

export interface IcloudHistoricalRoutineChunk {
  chunk_index: number;
  requested_logical_assets: number;
  imported_logical_assets: number;
  imported_resources: number;
  cleaned_local_staging_files: number;
  acquisition_run_id: number | null;
  acquisition_batch_id: number | null;
  source_intake_run_id: number | null;
  cleanup_dry_run_id: number | null;
  cleanup_execution_run_id: number | null;
  cleanup_report_path: string | null;
  status: string;
  stop_reason: string | null;
  operator_message: string;
}

export interface IcloudHistoricalRoutineRunResponse {
  status: string;
  source_id: number;
  prepare_run_id: number | null;
  requested_logical_assets: number;
  logical_candidates: number;
  internal_batch_size: number;
  imported_logical_assets: number;
  logical_imported: number;
  imported_resources: number;
  files_resources_imported: number;
  cleaned_local_staging_files: number;
  local_staging_files_cleaned: number;
  new_deferred_this_run: number;
  execution_failed_this_run: number;
  eligible_remaining_logical: number;
  deferred_current_logical: number;
  deferred_adjusted_resource_logical: number;
  available_inventory: "yes" | "no" | "unknown";
  operator_message: string;
  stop_reason: string | null;
  chunks: IcloudHistoricalRoutineChunk[];
}

export interface IcloudIntakeImportStartRequest {
  source_id: number;
  target_logical_assets?: number;
  internal_batch_size?: number;
}

export interface IcloudIntakeImportAdvanceRequest {
  source_id: number;
  import_run_id?: number | null;
}

export interface IcloudIntakeImportResumeRequest {
  source_id: number;
  import_run_id?: number | null;
}

export interface IcloudIntakeImportChunkStatus {
  id: number;
  chunk_index: number;
  status: string;
  candidate_start_index: number;
  candidate_end_index: number;
  logical_candidates: number;
  logical_imported: number;
  files_resources_imported: number;
  local_staging_files_cleaned: number;
  new_deferred_this_chunk: number;
  execution_failed_retryable_count: number;
  execution_failed_terminal_count: number;
  source_intake_failed_count: number;
  cleanup_failed_count: number;
  acquisition_run_id: number | null;
  acquisition_batch_id: number | null;
  source_intake_run_id: number | null;
  cleanup_dry_run_id: number | null;
  cleanup_execution_run_id: number | null;
  cleanup_report_path: string | null;
  cleanup_eligible_count: number;
  cleanup_skipped_count: number;
  cleanup_protected_count: number;
  cleanup_verification_failed_count: number;
  cleanup_file_missing_count: number;
  cleanup_delete_failed_count: number;
  chunk_total_seconds: number | null;
  candidate_load_seconds: number | null;
  fresh_resolution_seconds: number | null;
  download_stage_seconds: number | null;
  source_intake_seconds: number | null;
  cleanup_dry_run_seconds: number | null;
  cleanup_execute_seconds: number | null;
  db_state_update_seconds: number | null;
  inter_chunk_gap_seconds: number | null;
  started_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  operator_message: string | null;
  stop_reason: string | null;
  timing_note: string | null;
}

export interface IcloudIntakeImportStatus {
  source_id: number;
  source_label: string | null;
  total_imported_from_source: number;
  last_inventory_refresh_at: string | null;
  available_inventory: "yes" | "no" | "unknown";
  logical_candidates_ready: number;
  latest_prepare_run_id: number | null;
  prepare_status: string | null;
  prepare_expires_at: string | null;
  import_run_id: number | null;
  import_status: string | null;
  import_operator_message: string;
  import_stop_reason: string | null;
  target_logical_candidates: number;
  logical_candidates_total: number;
  logical_imported: number;
  files_resources_imported: number;
  local_staging_files_cleaned: number;
  new_deferred_this_run: number;
  execution_failed_retryable_count: number;
  execution_failed_terminal_count: number;
  source_intake_failed_count: number;
  cleanup_failed_count: number;
  current_chunk_index: number;
  total_chunks: number;
  internal_batch_size: number;
  pending_chunk_count: number;
  completed_chunk_count: number;
  remaining_logical_candidates: number;
  resume_available: boolean;
  can_start_import: boolean;
  can_resume_import: boolean;
  can_advance_import: boolean;
  current_phase: string | null;
  last_chunk_duration_seconds: number | null;
  last_inter_chunk_gap_seconds: number | null;
  started_at: string | null;
  last_progress_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  interrupted_at: string | null;
  resumed_at: string | null;
  report_path: string | null;
  local_staging_file_count: number;
  partial_file_count: number;
  backfill_execute_file_count: number;
  chunks: IcloudIntakeImportChunkStatus[];
}

export interface IcloudIntakeImportStatusResponse {
  generated_at: string;
  current: IcloudIntakeImportStatus;
}

export type InternalIcloudMediaScope =
  | "ordinary_stills"
  | "stills_with_live_photo_pairs"
  | "videos_only"
  | "all_supported_media";

export type InternalIcloudCountOrStatus = number | "not_available" | "deferred" | "not_applicable" | "unknown";
export type InternalIcloudAssetScope = "ordinary_stills_only" | "all_supported_assets";

export interface InternalIcloudRunRequest {
  source_id: number;
  batch_size: number;
  total_limit: number;
  candidate_search_cap: number;
  media_scope: InternalIcloudMediaScope;
  auto_cleanup_if_safe: boolean;
}

export interface InternalIcloudRunStatus {
  run_id: number | null;
  status: string;
  stop_reason: string | null;
  failure_reason: string | null;
  current_phase: string | null;
  source_id: number;
  source_label: string | null;
  batch_size: number;
  total_limit: number;
  candidate_search_cap: number;
  requested_media_scope: InternalIcloudMediaScope;
  effective_media_scope: InternalIcloudMediaScope | null;
  requested_asset_scope: InternalIcloudAssetScope | null;
  effective_asset_scope: InternalIcloudAssetScope | null;
  auto_cleanup_if_safe: boolean;
  dry_run_performed: boolean;
  execution_performed: boolean;
  cleanup_performed: boolean;
  cleanup_recovery_used: boolean;
  final_verification_passed: boolean;
  next_safe_action: string | null;
  report_path: string | null;
  orchestration_report_path: string | null;
  cleanup_dry_run_id: number | null;
  cleanup_execution_run_id: number | null;
  final_cleanup_verification_run_id: number | null;
  acquisition_run_ids: number[];
  acquisition_batch_ids: number[];
  source_intake_run_ids: number[];
  ingestion_run_ids: number[];
  cleanup_dry_run_ids: number[];
  cleanup_execution_run_ids: number[];
  final_cleanup_verification_run_ids: number[];
  logical_assets_selected: InternalIcloudCountOrStatus;
  resources_selected: InternalIcloudCountOrStatus;
  candidates_considered: InternalIcloudCountOrStatus;
  safe_unknown_supported_count: InternalIcloudCountOrStatus;
  already_known_count: InternalIcloudCountOrStatus;
  ambiguous_skipped_count: InternalIcloudCountOrStatus;
  unsupported_skipped_count: InternalIcloudCountOrStatus;
  selected_count: InternalIcloudCountOrStatus;
  execution_decision_reason: string | null;
  ordinary_still_logical_count: InternalIcloudCountOrStatus;
  ordinary_still_resource_count: InternalIcloudCountOrStatus;
  video_logical_count: InternalIcloudCountOrStatus;
  video_resource_count: InternalIcloudCountOrStatus;
  ordinary_still_count: InternalIcloudCountOrStatus;
  live_photo_logical_count: InternalIcloudCountOrStatus;
  live_photo_still_resource_count: InternalIcloudCountOrStatus;
  live_photo_motion_resource_count: InternalIcloudCountOrStatus;
  video_count: InternalIcloudCountOrStatus;
  unsupported_or_blocked_count: InternalIcloudCountOrStatus;
  ambiguous_count: InternalIcloudCountOrStatus;
  acquired_resource_count: InternalIcloudCountOrStatus;
  source_intake_count: InternalIcloudCountOrStatus;
  ingestion_count: InternalIcloudCountOrStatus;
  cleanup_eligible_count: InternalIcloudCountOrStatus;
  cleanup_completed_deleted_count: InternalIcloudCountOrStatus;
  cleanup_failed_count: InternalIcloudCountOrStatus;
  orphaned_companion_count: InternalIcloudCountOrStatus;
  pairing_warning_count: InternalIcloudCountOrStatus;
  final_staging_clean: boolean | null;
  drop_zone_clean: boolean | null;
  partial_workspace_clean: boolean | null;
  cloud_deletion_occurred: boolean;
  normal_ui_exposure_added: boolean;
  normal_admin_api_exposure_added: boolean;
  mixed_media_supported_for_execution: boolean;
}

export interface InternalIcloudRunResponse {
  status: string;
  message: string;
  current: InternalIcloudRunStatus;
}

export interface InternalIcloudRunStatusResponse {
  generated_at: string;
  current: InternalIcloudRunStatus;
}

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

export interface SourceProfileSummary {
  source_id: number;
  source_label: string;
  source_type: string;
  source_root_path: string | null;
  profile_status: SourceProfileStatus;
  cloud_provider: string | null;
  acquisition_method: string | null;
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

export interface SourceProfilesResponse {
  generated_at: string;
  profiles: SourceProfileSummary[];
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
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  raw: Record<string, any>;
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
  skipped_reasons: Record<string, number>;
  skipped_samples: Record<string, string[]>;
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

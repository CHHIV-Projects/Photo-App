"use client";

import { useEffect, useState } from "react";
import styles from "@/components/duplicate-groups-view.module.css";
import {
  demoteDuplicateGroupMember,
  getDuplicateGroups,
  getDuplicateGroupDetail,
  removeDuplicateGroupMember,
  resolveApiUrl,
  restoreDuplicateGroupMember,
  setDuplicateGroupCanonical,
} from "@/lib/api";
import type {
  DuplicateGroupSummary,
  DuplicateGroupDetail,
} from "@/types/ui-api";

interface DuplicateGroupsViewProps {
  onOpenPhoto: (sha256: string) => void;
  focusGroupId?: number | null;
}

export function DuplicateGroupsView({ onOpenPhoto, focusGroupId = null }: DuplicateGroupsViewProps) {
  const [groups, setGroups] = useState<DuplicateGroupSummary[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null);
  const [groupDetail, setGroupDetail] = useState<DuplicateGroupDetail | null>(null);
  const [isLoadingGroups, setIsLoadingGroups] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [groupsErrorMessage, setGroupsErrorMessage] = useState<string | null>(null);
  const [detailErrorMessage, setDetailErrorMessage] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(0);
  const [totalCount, setTotalCount] = useState(0);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [busyAssetSha256, setBusyAssetSha256] = useState<string | null>(null);

  const PAGE_SIZE = 50;

  useEffect(() => {
    void loadGroups(0, searchQuery);
  }, []);

  useEffect(() => {
    if (focusGroupId === null) {
      return;
    }
    setSelectedGroupId(focusGroupId);
    void loadGroupDetail(focusGroupId);
  }, [focusGroupId]);

  async function loadGroups(offset: number, query: string = ""): Promise<void> {
    setIsLoadingGroups(true);
    setGroupsErrorMessage(null);

    try {
      const response = await getDuplicateGroups(query, offset, PAGE_SIZE);
      console.log("Duplicate groups response:", response);
      setGroups(response.items);
      setTotalCount(response.total_count);
      setCurrentPage(offset / PAGE_SIZE);
    } catch (error) {
      console.error("Error loading groups:", error);
      setGroupsErrorMessage(getErrorMessage(error, "Failed to load duplicate groups."));
    } finally {
      setIsLoadingGroups(false);
    }
  }

  async function loadGroupDetail(groupId: number, options?: { clearActionMessage?: boolean }): Promise<void> {
    setIsLoadingDetail(true);
    setDetailErrorMessage(null);
    if (options?.clearActionMessage ?? true) {
      setActionMessage(null);
    }

    try {
      const response = await getDuplicateGroupDetail(groupId);
      setGroupDetail(response);
    } catch (error) {
      setDetailErrorMessage(getErrorMessage(error, "Failed to load group detail."));
      setGroupDetail(null);
    } finally {
      setIsLoadingDetail(false);
    }
  }

  function handleSelectGroup(groupId: number): void {
    setSelectedGroupId(groupId);
    void loadGroupDetail(groupId, { clearActionMessage: true });
  }

  async function handleSearch(query: string): Promise<void> {
    setSearchQuery(query);
    setCurrentPage(0);
    await loadGroups(0, query);
  }

  async function handleNextPage(): Promise<void> {
    const nextOffset = (currentPage + 1) * PAGE_SIZE;
    if (nextOffset < totalCount) {
      await loadGroups(nextOffset, searchQuery);
    }
  }

  async function handlePrevPage(): Promise<void> {
    if (currentPage > 0) {
      const prevOffset = (currentPage - 1) * PAGE_SIZE;
      await loadGroups(prevOffset, searchQuery);
    }
  }

  function handleOpenAssetDetail(sha256: string): void {
    onOpenPhoto(sha256);
  }

  async function handleSetCanonical(assetSha256: string): Promise<void> {
    if (selectedGroupId === null) return;
    setBusyAssetSha256(assetSha256);
    try {
      const response = await setDuplicateGroupCanonical(assetSha256);
      setActionMessage(response.message ?? "Canonical asset updated.");
      await loadGroupDetail(selectedGroupId, { clearActionMessage: false });
    } catch (error) {
      setDetailErrorMessage(getErrorMessage(error, "Failed to set canonical asset."));
    } finally {
      setBusyAssetSha256(null);
    }
  }

  async function handleRemoveFromGroup(assetSha256: string): Promise<void> {
    if (selectedGroupId === null) return;
    setBusyAssetSha256(assetSha256);
    try {
      const response = await removeDuplicateGroupMember(assetSha256);
      setActionMessage(response.message ?? "Asset removed from group.");
      await loadGroupDetail(selectedGroupId, { clearActionMessage: false });
      await loadGroups(currentPage * PAGE_SIZE, searchQuery);
    } catch (error) {
      setDetailErrorMessage(getErrorMessage(error, "Failed to remove asset from group."));
    } finally {
      setBusyAssetSha256(null);
    }
  }

  async function handleDemote(assetSha256: string): Promise<void> {
    if (selectedGroupId === null) return;
    setBusyAssetSha256(assetSha256);
    try {
      const response = await demoteDuplicateGroupMember(assetSha256);
      setActionMessage(response.message ?? "Asset demoted.");
      await loadGroupDetail(selectedGroupId, { clearActionMessage: false });
    } catch (error) {
      setDetailErrorMessage(getErrorMessage(error, "Failed to demote asset."));
    } finally {
      setBusyAssetSha256(null);
    }
  }

  async function handleRestore(assetSha256: string): Promise<void> {
    if (selectedGroupId === null) return;
    setBusyAssetSha256(assetSha256);
    try {
      const response = await restoreDuplicateGroupMember(assetSha256);
      setActionMessage(response.message ?? "Asset restored.");
      await loadGroupDetail(selectedGroupId, { clearActionMessage: false });
    } catch (error) {
      setDetailErrorMessage(getErrorMessage(error, "Failed to restore asset."));
    } finally {
      setBusyAssetSha256(null);
    }
  }

  if (isLoadingGroups) {
    return (
      <div className={styles.container}>
        <div className={styles.loadingMessage}>Loading duplicate groups...</div>
      </div>
    );
  }

  if (groupsErrorMessage) {
    return (
      <div className={styles.container}>
        <div className={styles.errorMessage}>{groupsErrorMessage}</div>
      </div>
    );
  }

  if (groups.length === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.emptyState}>
          No duplicate groups found. Your assets are all unique!
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.layout}>
        {/* List view */}
        <div className={styles.listPane}>
          <div className={styles.searchBar}>
            <input
              type="text"
              placeholder="Search by filename..."
              value={searchQuery}
              onChange={(e) => {
                void handleSearch(e.target.value);
              }}
              className={styles.searchInput}
            />
          </div>

          <div className={styles.groupList}>
            {groups.map((group) => (
              <div
                key={group.group_id}
                className={`${styles.groupListItem} ${selectedGroupId === group.group_id ? styles.groupListItemActive : ""}`}
                onClick={() => handleSelectGroup(group.group_id)}
              >
                {group.canonical_thumbnail_url && (
                  <img
                    src={resolveApiUrl(group.canonical_thumbnail_url) ?? ""}
                    alt={`Group ${group.group_id}`}
                    className={styles.groupThumbnail}
                  />
                )}
                <div className={styles.groupInfo}>
                  <div className={styles.groupId}>Group #{group.group_id}</div>
                  <div className={styles.memberCount}>
                    {group.member_count} member{group.member_count !== 1 ? "s" : ""}
                  </div>
                  <div className={styles.createdAt}>
                    {new Date(group.created_at).toLocaleDateString()}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className={styles.pagination}>
            <button
              type="button"
              disabled={currentPage === 0 || isLoadingGroups}
              onClick={() => {
                void handlePrevPage();
              }}
              className={styles.paginationButton}
            >
              ← Previous
            </button>
            <span className={styles.paginationInfo}>
              Page {currentPage + 1} of {Math.ceil(totalCount / PAGE_SIZE)} ({totalCount} total)
            </span>
            <button
              type="button"
              disabled={(currentPage + 1) * PAGE_SIZE >= totalCount || isLoadingGroups}
              onClick={() => {
                void handleNextPage();
              }}
              className={styles.paginationButton}
            >
              Next →
            </button>
          </div>
        </div>

        {/* Detail view */}
        {selectedGroupId !== null && (
          <div className={styles.detailPane}>
            {isLoadingDetail ? (
              <div className={styles.loadingMessage}>Loading group detail...</div>
            ) : detailErrorMessage ? (
              <div className={styles.errorMessage}>{detailErrorMessage}</div>
            ) : groupDetail ? (
              <div className={styles.groupDetail}>
                <div className={styles.groupDetailHeader}>
                  <h2>Duplicate Group #{groupDetail.group_id}</h2>
                  <div className={styles.groupStats}>
                    <span>{groupDetail.duplicate_count} assets</span>
                    <span>Type: {groupDetail.group_type}</span>
                  </div>
                  {actionMessage && <div className={styles.successMessage}>{actionMessage}</div>}
                </div>

                <div className={styles.groupMembers}>
                  {groupDetail.assets.map((asset) => (
                    <div
                      key={asset.asset_sha256}
                      className={`${styles.memberCard} ${asset.is_canonical ? styles.memberCardCanonical : ""}`}
                    >
                      {asset.image_url && (
                        <img
                          src={resolveApiUrl(asset.image_url) ?? ""}
                          alt={asset.filename}
                          className={styles.memberImage}
                        />
                      )}
                      <div className={styles.memberInfo}>
                        <div className={styles.memberFilename}>{asset.filename}</div>
                        <div className={styles.memberBadges}>
                          {asset.is_canonical && (
                            <div className={styles.canonicalBadge}>Canonical</div>
                          )}
                          {asset.visibility_status === "demoted" && (
                            <div className={styles.demotedBadge}>Demoted</div>
                          )}
                        </div>
                        <div className={styles.memberMeta}>
                          <span>Quality: {asset.quality_score?.toFixed(2) ?? "unknown"}</span>
                          <span>Type: {asset.capture_type}</span>
                          <span>Trust: {asset.capture_time_trust}</span>
                        </div>
                      </div>
                      <div className={styles.memberActions}>
                        <button
                          type="button"
                          onClick={() => handleOpenAssetDetail(asset.asset_sha256)}
                          className={styles.viewButton}
                        >
                          View Details
                        </button>
                        {!asset.is_canonical && (
                          <button
                            type="button"
                            disabled={busyAssetSha256 === asset.asset_sha256}
                            onClick={() => {
                              void handleSetCanonical(asset.asset_sha256);
                            }}
                            className={styles.actionButton}
                          >
                            Set Canonical
                          </button>
                        )}
                        {asset.visibility_status === "visible" && !asset.is_canonical && (
                          <button
                            type="button"
                            disabled={busyAssetSha256 === asset.asset_sha256}
                            onClick={() => {
                              void handleDemote(asset.asset_sha256);
                            }}
                            className={styles.actionButton}
                          >
                            Demote
                          </button>
                        )}
                        {asset.visibility_status === "demoted" && (
                          <button
                            type="button"
                            disabled={busyAssetSha256 === asset.asset_sha256}
                            onClick={() => {
                              void handleRestore(asset.asset_sha256);
                            }}
                            className={styles.actionButton}
                          >
                            Restore
                          </button>
                        )}
                        <button
                          type="button"
                          disabled={busyAssetSha256 === asset.asset_sha256}
                          onClick={() => {
                            void handleRemoveFromGroup(asset.asset_sha256);
                          }}
                          className={styles.actionButtonDanger}
                        >
                          Remove From Group
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}

function getErrorMessage(error: unknown, fallbackMessage: string) {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallbackMessage;
}

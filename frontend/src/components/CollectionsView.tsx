"use client";

import { useEffect, useState } from "react";

import {
  addAlbumToCollection,
  createCollection,
  getAlbums,
  getCollectionDetail,
  getCollections,
  removeAlbumFromCollection,
  resolveApiUrl,
} from "@/lib/api";
import type { AlbumSummary, CollectionDetail, CollectionSummary } from "@/types/ui-api";
import styles from "./collections-view.module.css";

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

export function CollectionsView() {
  const [collections, setCollections] = useState<CollectionSummary[]>([]);
  const [albums, setAlbums] = useState<AlbumSummary[]>([]);
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(null);
  const [collectionDetail, setCollectionDetail] = useState<CollectionDetail | null>(null);
  const [newCollectionName, setNewCollectionName] = useState("");
  const [newCollectionDescription, setNewCollectionDescription] = useState("");
  const [selectedAlbumToLink, setSelectedAlbumToLink] = useState<number | null>(null);
  const [isLoadingCollections, setIsLoadingCollections] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    void loadCollections();
    void loadAlbums();
  }, []);

  useEffect(() => {
    if (selectedCollectionId === null) {
      setCollectionDetail(null);
      return;
    }
    void loadCollectionDetail(selectedCollectionId);
  }, [selectedCollectionId]);

  async function loadCollections(preferredCollectionId?: number | null) {
    setIsLoadingCollections(true);
    setErrorMessage(null);

    try {
      const response = await getCollections();
      setCollections(response.items);

      if (response.items.length === 0) {
        setSelectedCollectionId(null);
        return;
      }

      const nextId = preferredCollectionId ?? selectedCollectionId;
      const matching = response.items.find((item) => item.collection_id === nextId);
      setSelectedCollectionId(matching ? matching.collection_id : response.items[0].collection_id);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Failed to load collections."));
      setSelectedCollectionId(null);
    } finally {
      setIsLoadingCollections(false);
    }
  }

  async function loadCollectionDetail(collectionId: number) {
    setIsLoadingDetail(true);
    setErrorMessage(null);

    try {
      const detail = await getCollectionDetail(collectionId);
      setCollectionDetail(detail);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Failed to load collection detail."));
      setCollectionDetail(null);
    } finally {
      setIsLoadingDetail(false);
    }
  }

  async function loadAlbums() {
    try {
      const response = await getAlbums();
      setAlbums(response.items);
    } catch {
      setAlbums([]);
    }
  }

  async function handleCreateCollection() {
    const name = newCollectionName.trim();
    if (!name) {
      setErrorMessage("Collection name is required.");
      return;
    }

    setIsSaving(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const created = await createCollection(name, newCollectionDescription.trim() || null);
      setNewCollectionName("");
      setNewCollectionDescription("");
      await loadCollections(created.collection_id);
      setSuccessMessage(`Created collection: ${created.name}`);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Failed to create collection."));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleLinkAlbum() {
    if (!collectionDetail || !selectedAlbumToLink) {
      return;
    }

    setIsSaving(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      await addAlbumToCollection(collectionDetail.collection_id, selectedAlbumToLink);
      await Promise.all([
        loadCollectionDetail(collectionDetail.collection_id),
        loadCollections(collectionDetail.collection_id),
      ]);
      setSelectedAlbumToLink(null);
      setSuccessMessage("Album linked to collection.");
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Failed to link album to collection."));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleUnlinkAlbum(albumId: number) {
    if (!collectionDetail) {
      return;
    }

    setIsSaving(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      await removeAlbumFromCollection(collectionDetail.collection_id, albumId);
      await Promise.all([
        loadCollectionDetail(collectionDetail.collection_id),
        loadCollections(collectionDetail.collection_id),
      ]);
      setSuccessMessage("Album unlinked from collection.");
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Failed to unlink album from collection."));
    } finally {
      setIsSaving(false);
    }
  }

  const linkedAlbumIds = new Set(collectionDetail?.albums.map((item) => item.album_id) ?? []);
  const availableAlbums = albums.filter((album) => !linkedAlbumIds.has(album.album_id));

  return (
    <div className={styles.layout}>
      <aside className={styles.sidebar}>
        <section className={styles.panel}>
          <h2 className={styles.panelTitle}>Collections</h2>
          <div className={styles.createGrid}>
            <input
              value={newCollectionName}
              onChange={(event) => setNewCollectionName(event.target.value)}
              className={styles.input}
              placeholder="Collection name"
            />
            <textarea
              value={newCollectionDescription}
              onChange={(event) => setNewCollectionDescription(event.target.value)}
              className={styles.textarea}
              placeholder="Optional description"
              rows={3}
            />
            <button type="button" className={styles.primaryButton} onClick={handleCreateCollection} disabled={isSaving}>
              Create Collection
            </button>
          </div>
        </section>

        <section className={styles.panel}>
          {isLoadingCollections ? (
            <p className={styles.message}>Loading collections...</p>
          ) : collections.length === 0 ? (
            <p className={styles.message}>No collections yet.</p>
          ) : (
            <div className={styles.collectionList}>
              {collections.map((collection) => (
                <button
                  key={collection.collection_id}
                  type="button"
                  className={`${styles.collectionItem} ${selectedCollectionId === collection.collection_id ? styles.collectionItemActive : ""}`.trim()}
                  onClick={() => setSelectedCollectionId(collection.collection_id)}
                >
                  <span className={styles.collectionName}>{collection.name}</span>
                  <span className={styles.collectionMeta}>
                    {collection.direct_asset_count} assets | {collection.album_count} albums
                  </span>
                </button>
              ))}
            </div>
          )}
        </section>
      </aside>

      <section className={styles.detailPane}>
        {errorMessage ? <p className={styles.error}>{errorMessage}</p> : null}
        {successMessage ? <p className={styles.success}>{successMessage}</p> : null}

        {!collectionDetail || selectedCollectionId === null ? (
          <div className={styles.panel}>
            <p className={styles.message}>Select a collection to view details.</p>
          </div>
        ) : isLoadingDetail ? (
          <div className={styles.panel}>
            <p className={styles.message}>Loading collection...</p>
          </div>
        ) : (
          <>
            <div className={styles.panel}>
              <h3 className={styles.sectionTitle}>Collection Details</h3>
              <p className={styles.metaText}>Name: {collectionDetail.name}</p>
              <p className={styles.metaText}>Direct assets: {collectionDetail.direct_asset_count}</p>
              <p className={styles.metaText}>Albums: {collectionDetail.album_count}</p>
              <p className={styles.metaText}>Created: {new Date(collectionDetail.created_at).toLocaleString()}</p>
            </div>

            <div className={styles.panel}>
              <h3 className={styles.sectionTitle}>Associate Album</h3>
              <div className={styles.addRow}>
                <select
                  value={selectedAlbumToLink ?? ""}
                  onChange={(event) => setSelectedAlbumToLink(event.target.value ? Number(event.target.value) : null)}
                  className={styles.select}
                >
                  <option value="">Select album</option>
                  {availableAlbums.map((album) => (
                    <option key={album.album_id} value={album.album_id}>{album.name}</option>
                  ))}
                </select>
                <button type="button" className={styles.primaryButton} onClick={handleLinkAlbum} disabled={!selectedAlbumToLink || isSaving}>
                  Link Album
                </button>
              </div>
            </div>

            <div className={styles.panel}>
              <h3 className={styles.sectionTitle}>Associated Albums</h3>
              {collectionDetail.albums.length === 0 ? (
                <p className={styles.message}>No albums linked yet.</p>
              ) : (
                <ul className={styles.linkedList}>
                  {collectionDetail.albums.map((album) => (
                    <li key={album.album_id} className={styles.linkedRow}>
                      <span>{album.name} ({album.asset_count} assets)</span>
                      <button
                        type="button"
                        className={styles.secondaryButton}
                        disabled={isSaving}
                        onClick={() => void handleUnlinkAlbum(album.album_id)}
                      >
                        Remove
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className={styles.panel}>
              <h3 className={styles.sectionTitle}>Direct Assets</h3>
              {collectionDetail.direct_assets.length === 0 ? (
                <p className={styles.message}>No direct assets in this collection.</p>
              ) : (
                <div className={styles.assetGrid}>
                  {collectionDetail.direct_assets.slice(0, 30).map((asset) => (
                    <article key={asset.asset_sha256} className={styles.assetCard}>
                      <div className={styles.assetThumbWrap}>
                        {resolveApiUrl(asset.image_url) ? (
                          <img
                            src={resolveApiUrl(asset.image_url) ?? ""}
                            alt={asset.filename}
                            className={styles.assetThumb}
                          />
                        ) : (
                          <div className={styles.assetThumbPlaceholder}>No preview</div>
                        )}
                      </div>
                      <p className={styles.assetFilename}>{asset.filename}</p>
                    </article>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </section>
    </div>
  );
}

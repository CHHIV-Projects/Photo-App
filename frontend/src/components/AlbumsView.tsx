"use client";

import { useEffect, useMemo, useState } from "react";

import {
  addAssetsToAlbum,
  createAlbum,
  deleteAlbum,
  getAlbumDetail,
  getAlbums,
  getPhotos,
  removeAssetsFromAlbum,
  resolveApiUrl,
  updateAlbum
} from "@/lib/api";
import type { AlbumDetail, AlbumSummary, PhotoSummary } from "@/types/ui-api";
import styles from "./albums-view.module.css";

interface Props {
  onOpenPhoto?: (sha256: string) => void;
}

export function AlbumsView({ onOpenPhoto }: Props) {
  const [albums, setAlbums] = useState<AlbumSummary[]>([]);
  const [selectedAlbumId, setSelectedAlbumId] = useState<number | null>(null);
  const [albumDetail, setAlbumDetail] = useState<AlbumDetail | null>(null);
  const [allPhotos, setAllPhotos] = useState<PhotoSummary[]>([]);

  const [newAlbumName, setNewAlbumName] = useState("");
  const [newAlbumDescription, setNewAlbumDescription] = useState("");
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [selectedAssetToAdd, setSelectedAssetToAdd] = useState("");

  const [isLoadingAlbums, setIsLoadingAlbums] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    void loadAlbums();
    void loadPhotos();
  }, []);

  useEffect(() => {
    if (selectedAlbumId === null) {
      setAlbumDetail(null);
      return;
    }
    void loadAlbumDetail(selectedAlbumId);
  }, [selectedAlbumId]);

  useEffect(() => {
    if (!albumDetail) return;
    setEditName(albumDetail.name);
    setEditDescription(albumDetail.description ?? "");
  }, [albumDetail]);

  const availablePhotosForAdd = useMemo(() => {
    if (!albumDetail) return allPhotos;
    const existing = new Set(albumDetail.items.map((item) => item.asset_sha256));
    return allPhotos.filter((photo) => !existing.has(photo.asset_sha256));
  }, [allPhotos, albumDetail]);

  async function loadAlbums(preferredAlbumId?: number | null) {
    setIsLoadingAlbums(true);
    setErrorMessage(null);

    try {
      const response = await getAlbums();
      setAlbums(response.items);

      if (response.items.length === 0) {
        setSelectedAlbumId(null);
        return;
      }

      const nextId = preferredAlbumId ?? selectedAlbumId;
      const matching = response.items.find((item) => item.album_id === nextId);
      setSelectedAlbumId(matching ? matching.album_id : response.items[0].album_id);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Failed to load albums."));
      setSelectedAlbumId(null);
    } finally {
      setIsLoadingAlbums(false);
    }
  }

  async function loadAlbumDetail(albumId: number) {
    setIsLoadingDetail(true);
    setErrorMessage(null);

    try {
      const detail = await getAlbumDetail(albumId);
      setAlbumDetail(detail);
      if (!selectedAssetToAdd && detail.items.length > 0) {
        setSelectedAssetToAdd("");
      }
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Failed to load album detail."));
      setAlbumDetail(null);
    } finally {
      setIsLoadingDetail(false);
    }
  }

  async function loadPhotos() {
    try {
      const response = await getPhotos();
      setAllPhotos(response.items);
    } catch {
      // Keep add-photo interaction available with manual fallback in future iterations.
    }
  }

  async function handleCreateAlbum() {
    const name = newAlbumName.trim();
    if (!name) {
      setErrorMessage("Album name is required.");
      return;
    }

    setIsSaving(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const created = await createAlbum(name, newAlbumDescription.trim() || null);
      setNewAlbumName("");
      setNewAlbumDescription("");
      await loadAlbums(created.album_id);
      setSuccessMessage(`Created album: ${created.name}`);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Failed to create album."));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleSaveAlbumMetadata() {
    if (!albumDetail) return;

    setIsSaving(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      await updateAlbum(albumDetail.album_id, {
        name: editName,
        description: editDescription || null
      });
      await Promise.all([
        loadAlbums(albumDetail.album_id),
        loadAlbumDetail(albumDetail.album_id)
      ]);
      setSuccessMessage("Album updated.");
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Failed to update album."));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDeleteAlbum() {
    if (!albumDetail) return;

    setIsSaving(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      await deleteAlbum(albumDetail.album_id);
      await loadAlbums();
      setSuccessMessage("Album deleted.");
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Failed to delete album."));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleAddPhotoToAlbum() {
    if (!albumDetail || !selectedAssetToAdd) return;

    setIsSaving(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      await addAssetsToAlbum(albumDetail.album_id, [selectedAssetToAdd]);
      await Promise.all([
        loadAlbums(albumDetail.album_id),
        loadAlbumDetail(albumDetail.album_id)
      ]);
      setSelectedAssetToAdd("");
      setSuccessMessage("Photo added to album.");
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Failed to add photo to album."));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleRemovePhotoFromAlbum(assetSha256: string) {
    if (!albumDetail) return;

    setIsSaving(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      await removeAssetsFromAlbum(albumDetail.album_id, [assetSha256]);
      await Promise.all([
        loadAlbums(albumDetail.album_id),
        loadAlbumDetail(albumDetail.album_id)
      ]);
      setSuccessMessage("Photo removed from album.");
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Failed to remove photo from album."));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className={styles.layout}>
      <aside className={styles.sidebar}>
        <section className={styles.panel}>
          <h2 className={styles.panelTitle}>Albums</h2>
          <div className={styles.createGrid}>
            <input
              value={newAlbumName}
              onChange={(event) => setNewAlbumName(event.target.value)}
              className={styles.input}
              placeholder="Album name"
            />
            <textarea
              value={newAlbumDescription}
              onChange={(event) => setNewAlbumDescription(event.target.value)}
              className={styles.textarea}
              placeholder="Optional description"
              rows={3}
            />
            <button type="button" className={styles.primaryButton} onClick={handleCreateAlbum} disabled={isSaving}>
              Create Album
            </button>
          </div>
        </section>

        <section className={styles.panel}>
          {isLoadingAlbums ? (
            <p className={styles.message}>Loading albums…</p>
          ) : albums.length === 0 ? (
            <p className={styles.message}>No albums yet.</p>
          ) : (
            <div className={styles.albumList}>
              {albums.map((album) => (
                <button
                  key={album.album_id}
                  type="button"
                  className={`${styles.albumItem} ${selectedAlbumId === album.album_id ? styles.albumItemActive : ""}`.trim()}
                  onClick={() => setSelectedAlbumId(album.album_id)}
                >
                  <span className={styles.albumName}>{album.name}</span>
                  <span className={styles.albumMeta}>{album.asset_count} photos</span>
                </button>
              ))}
            </div>
          )}
        </section>
      </aside>

      <section className={styles.detailPane}>
        {errorMessage ? <p className={styles.error}>{errorMessage}</p> : null}
        {successMessage ? <p className={styles.success}>{successMessage}</p> : null}

        {!albumDetail || selectedAlbumId === null ? (
          <div className={styles.panel}>
            <p className={styles.message}>Select an album to view details.</p>
          </div>
        ) : isLoadingDetail ? (
          <div className={styles.panel}>
            <p className={styles.message}>Loading album…</p>
          </div>
        ) : (
          <>
            <div className={styles.panel}>
              <h3 className={styles.sectionTitle}>Album Details</h3>
              <div className={styles.detailGrid}>
                <input
                  value={editName}
                  onChange={(event) => setEditName(event.target.value)}
                  className={styles.input}
                  placeholder="Album name"
                />
                <textarea
                  value={editDescription}
                  onChange={(event) => setEditDescription(event.target.value)}
                  className={styles.textarea}
                  rows={3}
                />
                <div className={styles.buttonRow}>
                  <button type="button" className={styles.primaryButton} onClick={handleSaveAlbumMetadata} disabled={isSaving}>
                    Save
                  </button>
                  <button type="button" className={styles.dangerButton} onClick={handleDeleteAlbum} disabled={isSaving}>
                    Delete Album
                  </button>
                </div>
                <p className={styles.metaText}>{albumDetail.asset_count} photos in album</p>
              </div>
            </div>

            <div className={styles.panel}>
              <h3 className={styles.sectionTitle}>Add Photo</h3>
              <div className={styles.addRow}>
                <select
                  value={selectedAssetToAdd}
                  onChange={(event) => setSelectedAssetToAdd(event.target.value)}
                  className={styles.select}
                >
                  <option value="">Select a photo</option>
                  {availablePhotosForAdd.map((photo) => (
                    <option key={photo.asset_sha256} value={photo.asset_sha256}>
                      {photo.filename}
                    </option>
                  ))}
                </select>
                <button type="button" className={styles.primaryButton} onClick={handleAddPhotoToAlbum} disabled={!selectedAssetToAdd || isSaving}>
                  Add
                </button>
              </div>
            </div>

            <div className={styles.panel}>
              <h3 className={styles.sectionTitle}>Album Photos</h3>
              {albumDetail.items.length === 0 ? (
                <p className={styles.message}>This album is empty.</p>
              ) : (
                <div className={styles.photoGrid}>
                  {albumDetail.items.map((photo) => (
                    <article key={photo.asset_sha256} className={styles.photoCard}>
                      <img
                        src={resolveApiUrl(photo.image_url) ?? ""}
                        alt={photo.filename}
                        className={styles.photoThumb}
                      />
                      <div className={styles.photoText}>
                        <p className={styles.photoName}>{photo.filename}</p>
                      </div>
                      <div className={styles.buttonRow}>
                        {onOpenPhoto ? (
                          <button type="button" className={styles.secondaryButton} onClick={() => onOpenPhoto(photo.asset_sha256)}>
                            Open
                          </button>
                        ) : null}
                        <button
                          type="button"
                          className={styles.secondaryButton}
                          onClick={() => handleRemovePhotoFromAlbum(photo.asset_sha256)}
                          disabled={isSaving}
                        >
                          Remove
                        </button>
                      </div>
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

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

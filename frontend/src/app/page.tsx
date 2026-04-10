"use client";

import { useEffect, useState } from "react";

import { ClusterDetail } from "@/components/ClusterDetail";
import { ClusterList } from "@/components/ClusterList";
import { PeopleView } from "@/components/PeopleView";
import { PhotosView } from "@/components/PhotosView";
import { UnassignedFacesView } from "@/components/UnassignedFacesView";
import styles from "@/components/review-screen.module.css";
import {
  assignPerson,
  createPerson,
  getCluster,
  getClusters,
  getPeople,
  getPeopleWithClusters,
  getPhotoDetail,
  getPhotos,
  getUnassignedFaces,
  ignoreCluster,
  mergeClusters,
  moveFace,
  removeFaceFromCluster
} from "@/lib/api";
import type {
  ClusterDetail as ClusterDetailType,
  ClusterSummary,
  FaceSummary,
  PersonSummary,
  PersonWithClusters,
  PhotoDetail,
  PhotoSummary
} from "@/types/ui-api";

type ViewMode = "review" | "people" | "unassigned" | "photos";

export default function HomePage() {
  const [viewMode, setViewMode] = useState<ViewMode>("review");
  const [clusters, setClusters] = useState<ClusterSummary[]>([]);
  const [people, setPeople] = useState<PersonSummary[]>([]);
  const [peopleWithClusters, setPeopleWithClusters] = useState<PersonWithClusters[]>([]);
  const [unassignedFaces, setUnassignedFaces] = useState<FaceSummary[]>([]);
  const [selectedClusterId, setSelectedClusterId] = useState<number | null>(null);
  const [clusterDetail, setClusterDetail] = useState<ClusterDetailType | null>(null);
  const [isLoadingClusters, setIsLoadingClusters] = useState(true);
  const [isLoadingPeople, setIsLoadingPeople] = useState(true);
  const [isLoadingPeopleView, setIsLoadingPeopleView] = useState(true);
  const [isLoadingUnassignedFaces, setIsLoadingUnassignedFaces] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isAssigning, setIsAssigning] = useState(false);
  const [isIgnoringCluster, setIsIgnoringCluster] = useState(false);
  const [isMergingCluster, setIsMergingCluster] = useState(false);
  const [isCreatingPerson, setIsCreatingPerson] = useState(false);
  const [clusterErrorMessage, setClusterErrorMessage] = useState<string | null>(null);
  const [peopleErrorMessage, setPeopleErrorMessage] = useState<string | null>(null);
  const [peopleViewErrorMessage, setPeopleViewErrorMessage] = useState<string | null>(null);
  const [unassignedFacesErrorMessage, setUnassignedFacesErrorMessage] = useState<string | null>(null);
  const [detailErrorMessage, setDetailErrorMessage] = useState<string | null>(null);
  const [assignErrorMessage, setAssignErrorMessage] = useState<string | null>(null);
  const [actionErrorMessage, setActionErrorMessage] = useState<string | null>(null);
  const [unassignedActionErrorMessage, setUnassignedActionErrorMessage] = useState<string | null>(null);
  const [createPersonErrorMessage, setCreatePersonErrorMessage] = useState<string | null>(null);
  const [photos, setPhotos] = useState<PhotoSummary[]>([]);
  const [selectedPhotoSha256, setSelectedPhotoSha256] = useState<string | null>(null);
  const [photoDetail, setPhotoDetail] = useState<PhotoDetail | null>(null);
  const [isLoadingPhotos, setIsLoadingPhotos] = useState(true);
  const [isLoadingPhotoDetail, setIsLoadingPhotoDetail] = useState(false);
  const [photosErrorMessage, setPhotosErrorMessage] = useState<string | null>(null);
  const [photoDetailErrorMessage, setPhotoDetailErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    void loadClusters();
    void loadPeople();
    void loadPeopleWithClusters();
    void loadUnassignedFaces();
    void loadPhotos();
  }, []);

  useEffect(() => {
    if (selectedClusterId === null) {
      setClusterDetail(null);
      return;
    }

    void loadClusterDetail(selectedClusterId);
  }, [selectedClusterId]);

  async function loadClusters(preferredClusterId?: number | null): Promise<number | null> {
    setIsLoadingClusters(true);
    setClusterErrorMessage(null);

    try {
      const response = await getClusters();
      setClusters(response.items);

      if (response.items.length === 0) {
        setSelectedClusterId(null);
        return null;
      }

      const nextSelectedClusterId = preferredClusterId ?? selectedClusterId;
      const matchingCluster = response.items.find(
        (cluster) => cluster.cluster_id === nextSelectedClusterId
      );
      const resolvedSelectedClusterId = matchingCluster
        ? matchingCluster.cluster_id
        : response.items[0].cluster_id;

      setSelectedClusterId(resolvedSelectedClusterId);
      return resolvedSelectedClusterId;
    } catch (error) {
      setClusterErrorMessage(getErrorMessage(error, "Failed to load clusters."));
      setSelectedClusterId(null);
      return null;
    } finally {
      setIsLoadingClusters(false);
    }
  }

  async function loadPeople() {
    setIsLoadingPeople(true);
    setPeopleErrorMessage(null);

    try {
      const response = await getPeople();
      setPeople(response.items);
    } catch (error) {
      setPeopleErrorMessage(getErrorMessage(error, "Failed to load people."));
    } finally {
      setIsLoadingPeople(false);
    }
  }

  async function loadPeopleWithClusters() {
    setIsLoadingPeopleView(true);
    setPeopleViewErrorMessage(null);

    try {
      const response = await getPeopleWithClusters();
      setPeopleWithClusters(response.items);
    } catch (error) {
      setPeopleViewErrorMessage(getErrorMessage(error, "Failed to load people."));
    } finally {
      setIsLoadingPeopleView(false);
    }
  }

  async function loadClusterDetail(clusterId: number) {
    setIsLoadingDetail(true);
    setDetailErrorMessage(null);

    try {
      const response = await getCluster(clusterId);
      setClusterDetail(response);
    } catch (error) {
      setDetailErrorMessage(getErrorMessage(error, "Failed to load cluster detail."));
      setClusterDetail(null);
    } finally {
      setIsLoadingDetail(false);
    }
  }

  async function loadUnassignedFaces() {
    setIsLoadingUnassignedFaces(true);
    setUnassignedFacesErrorMessage(null);

    try {
      const response = await getUnassignedFaces();
      setUnassignedFaces(response.items);
    } catch (error) {
      setUnassignedFacesErrorMessage(getErrorMessage(error, "Failed to load unassigned faces."));
    } finally {
      setIsLoadingUnassignedFaces(false);
    }
  }

  async function loadPhotos() {
    setIsLoadingPhotos(true);
    setPhotosErrorMessage(null);

    try {
      const response = await getPhotos();
      setPhotos(response.items);
    } catch (error) {
      setPhotosErrorMessage(getErrorMessage(error, "Failed to load photos."));
    } finally {
      setIsLoadingPhotos(false);
    }
  }

  async function loadPhotoDetail(sha256: string) {
    setIsLoadingPhotoDetail(true);
    setPhotoDetailErrorMessage(null);

    try {
      const response = await getPhotoDetail(sha256);
      setPhotoDetail(response);
    } catch (error) {
      setPhotoDetailErrorMessage(getErrorMessage(error, "Failed to load photo detail."));
      setPhotoDetail(null);
    } finally {
      setIsLoadingPhotoDetail(false);
    }
  }

  function handleSelectPhoto(sha256: string) {
    setSelectedPhotoSha256(sha256);
    void loadPhotoDetail(sha256);
  }

  async function handleAssign(personId: number) {
    if (selectedClusterId === null) {
      return;
    }

    setIsAssigning(true);
    setActionErrorMessage(null);
    setAssignErrorMessage(null);

    try {
      await assignPerson(selectedClusterId, personId);
      await refreshAfterClusterMutation(selectedClusterId);
    } catch (error) {
      setAssignErrorMessage(getErrorMessage(error, "Failed to assign person."));
    } finally {
      setIsAssigning(false);
    }
  }

  async function handleIgnoreCluster() {
    if (selectedClusterId === null) {
      return;
    }

    setIsIgnoringCluster(true);
    setActionErrorMessage(null);

    try {
      await ignoreCluster(selectedClusterId);
      await refreshAfterClusterMutation(selectedClusterId);
    } catch (error) {
      setActionErrorMessage(getErrorMessage(error, "Failed to ignore cluster."));
    } finally {
      setIsIgnoringCluster(false);
    }
  }

  async function handleRemoveFace(faceId: number): Promise<boolean> {
    if (selectedClusterId === null) {
      return false;
    }

    setActionErrorMessage(null);

    try {
      await removeFaceFromCluster(faceId);
      await refreshAfterClusterMutation(selectedClusterId);
      return true;
    } catch (error) {
      setActionErrorMessage(getErrorMessage(error, "Failed to remove face from cluster."));
      return false;
    }
  }

  async function handleMoveFace(faceId: number, targetClusterId: number): Promise<boolean> {
    if (selectedClusterId === null) {
      return false;
    }

    if (targetClusterId === selectedClusterId) {
      setActionErrorMessage("Target cluster must be different from the selected cluster.");
      return false;
    }

    setActionErrorMessage(null);

    try {
      await moveFace(faceId, targetClusterId);
      await refreshAfterClusterMutation(selectedClusterId);
      return true;
    } catch (error) {
      setActionErrorMessage(getErrorMessage(error, "Failed to move face."));
      return false;
    }
  }

  async function handleMergeClusters(targetClusterId: number): Promise<boolean> {
    if (selectedClusterId === null) {
      return false;
    }

    if (targetClusterId === selectedClusterId) {
      setActionErrorMessage("Cannot merge a cluster into itself.");
      return false;
    }

    setIsMergingCluster(true);
    setActionErrorMessage(null);

    try {
      await mergeClusters(selectedClusterId, targetClusterId);
      await Promise.all([
        refreshAfterClusterMutation(targetClusterId),
        loadPeople(),
        loadPeopleWithClusters()
      ]);
      return true;
    } catch (error) {
      const detail = getErrorMessage(error, "Unknown error.");
      setActionErrorMessage(`Failed to merge clusters: ${detail}`);
      return false;
    } finally {
      setIsMergingCluster(false);
    }
  }

  async function refreshAfterClusterMutation(previousClusterId: number) {
    const selectedPhoto = selectedPhotoSha256;
    const resolvedSelectedClusterId = await loadClusters(previousClusterId);

    if (resolvedSelectedClusterId === null) {
      setClusterDetail(null);
      const refreshTasks: Promise<unknown>[] = [
        loadPeopleWithClusters(),
        loadUnassignedFaces(),
        loadPhotos(),
      ];
      if (selectedPhoto) {
        refreshTasks.push(loadPhotoDetail(selectedPhoto));
      }
      await Promise.all(refreshTasks);
      return;
    }

    const refreshTasks: Promise<unknown>[] = [
      loadClusterDetail(resolvedSelectedClusterId),
      loadPeopleWithClusters(),
      loadUnassignedFaces(),
      loadPhotos(),
    ];
    if (selectedPhoto) {
      refreshTasks.push(loadPhotoDetail(selectedPhoto));
    }
    await Promise.all(refreshTasks);
  }

  function handleSelectClusterFromPeople(clusterId: number) {
    setViewMode("review");
    setSelectedClusterId(clusterId);
  }

  async function handleMoveUnassignedFace(faceId: number, targetClusterId: number): Promise<boolean> {
    const selectedPhoto = selectedPhotoSha256;
    setUnassignedActionErrorMessage(null);

    try {
      await moveFace(faceId, targetClusterId);

      const preferredClusterId = selectedClusterId;
      const resolvedSelectedClusterId = await loadClusters(preferredClusterId);

      const refreshTasks: Promise<unknown>[] = [
        loadUnassignedFaces(),
        loadPeopleWithClusters(),
        loadPhotos(),
      ];
      if (selectedPhoto) {
        refreshTasks.push(loadPhotoDetail(selectedPhoto));
      }
      await Promise.all(refreshTasks);

      if (resolvedSelectedClusterId !== null && resolvedSelectedClusterId === targetClusterId) {
        await loadClusterDetail(resolvedSelectedClusterId);
      }

      return true;
    } catch (error) {
      const detail = getErrorMessage(error, "Unknown error.");
      setUnassignedActionErrorMessage(`Failed to move face: ${detail}`);
      return false;
    }
  }

  async function handleCreatePerson(displayName: string): Promise<boolean> {
    setIsCreatingPerson(true);
    setCreatePersonErrorMessage(null);

    try {
      await createPerson(displayName);
      await Promise.all([loadPeople(), loadPeopleWithClusters()]);
      return true;
    } catch (error) {
      setCreatePersonErrorMessage(getErrorMessage(error, "Failed to create person."));
      return false;
    } finally {
      setIsCreatingPerson(false);
    }
  }

  return (
    <main className={styles.page}>
      <div className={styles.shell}>
        <header className={styles.header}>
          <p className={styles.kicker}>Milestone 10.10</p>
          <h1 className={styles.title}>Face Cluster Review</h1>
          <p className={styles.subtitle}>
            Review, correct, and merge clusters while keeping people assignments in sync.
          </p>

          <div className={styles.viewSwitch}>
            <button
              type="button"
              className={`${styles.viewButton} ${viewMode === "review" ? styles.viewButtonActive : ""}`.trim()}
              onClick={() => setViewMode("review")}
            >
              Review
            </button>
            <button
              type="button"
              className={`${styles.viewButton} ${viewMode === "people" ? styles.viewButtonActive : ""}`.trim()}
              onClick={() => setViewMode("people")}
            >
              People
            </button>
            <button
              type="button"
              className={`${styles.viewButton} ${viewMode === "unassigned" ? styles.viewButtonActive : ""}`.trim()}
              onClick={() => setViewMode("unassigned")}
            >
              Unassigned Faces
            </button>
            <button
              type="button"
              className={`${styles.viewButton} ${viewMode === "photos" ? styles.viewButtonActive : ""}`.trim()}
              onClick={() => setViewMode("photos")}
            >
              Photos
            </button>
          </div>
        </header>

        {viewMode === "review" ? (
          <div className={styles.layout}>
            <ClusterList
              clusters={clusters}
              selectedClusterId={selectedClusterId}
              isLoading={isLoadingClusters}
              errorMessage={clusterErrorMessage}
              onSelectCluster={setSelectedClusterId}
            />

            <ClusterDetail
              clusterDetail={clusterDetail}
              isLoadingDetail={isLoadingDetail}
              detailErrorMessage={detailErrorMessage}
              people={people}
              isLoadingPeople={isLoadingPeople}
              assignErrorMessage={assignErrorMessage ?? peopleErrorMessage}
              actionErrorMessage={actionErrorMessage}
              isAssigning={isAssigning}
              isIgnoringCluster={isIgnoringCluster}
              isMergingCluster={isMergingCluster}
              onAssign={handleAssign}
              onIgnoreCluster={handleIgnoreCluster}
              onMergeClusters={handleMergeClusters}
              onMergeValidationError={setActionErrorMessage}
              onRemoveFace={handleRemoveFace}
              onMoveFace={handleMoveFace}
              clusters={clusters}
              selectedClusterId={selectedClusterId}
              onSelectCluster={setSelectedClusterId}
            />
          </div>
        ) : viewMode === "people" ? (
          <PeopleView
            people={peopleWithClusters}
            isLoadingPeople={isLoadingPeopleView}
            peopleErrorMessage={peopleViewErrorMessage}
            createErrorMessage={createPersonErrorMessage}
            isCreatingPerson={isCreatingPerson}
            onCreatePerson={handleCreatePerson}
            onSelectCluster={handleSelectClusterFromPeople}
          />
        ) : viewMode === "unassigned" ? (
          <UnassignedFacesView
            faces={unassignedFaces}
            isLoading={isLoadingUnassignedFaces}
            errorMessage={unassignedFacesErrorMessage}
            actionErrorMessage={unassignedActionErrorMessage}
            onMoveFace={handleMoveUnassignedFace}
            onValidationError={setUnassignedActionErrorMessage}
          />
        ) : (
          <PhotosView
            photos={photos}
            isLoading={isLoadingPhotos}
            errorMessage={photosErrorMessage}
            selectedPhotoSha256={selectedPhotoSha256}
            photoDetail={photoDetail}
            isLoadingDetail={isLoadingPhotoDetail}
            photoDetailErrorMessage={photoDetailErrorMessage}
            onSelectPhoto={handleSelectPhoto}
          />
        )}
      </div>
    </main>
  );
}

function getErrorMessage(error: unknown, fallbackMessage: string) {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallbackMessage;
}

"use client";

import { useEffect, useState } from "react";

import { ClusterDetail } from "@/components/ClusterDetail";
import { ClusterList } from "@/components/ClusterList";
import styles from "@/components/review-screen.module.css";
import {
  assignPerson,
  getCluster,
  getClusters,
  getPeople,
  ignoreCluster,
  moveFace,
  removeFaceFromCluster
} from "@/lib/api";
import type { ClusterDetail as ClusterDetailType, ClusterSummary, PersonSummary } from "@/types/ui-api";

export default function HomePage() {
  const [clusters, setClusters] = useState<ClusterSummary[]>([]);
  const [people, setPeople] = useState<PersonSummary[]>([]);
  const [selectedClusterId, setSelectedClusterId] = useState<number | null>(null);
  const [clusterDetail, setClusterDetail] = useState<ClusterDetailType | null>(null);
  const [isLoadingClusters, setIsLoadingClusters] = useState(true);
  const [isLoadingPeople, setIsLoadingPeople] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isAssigning, setIsAssigning] = useState(false);
  const [isIgnoringCluster, setIsIgnoringCluster] = useState(false);
  const [clusterErrorMessage, setClusterErrorMessage] = useState<string | null>(null);
  const [peopleErrorMessage, setPeopleErrorMessage] = useState<string | null>(null);
  const [detailErrorMessage, setDetailErrorMessage] = useState<string | null>(null);
  const [assignErrorMessage, setAssignErrorMessage] = useState<string | null>(null);
  const [actionErrorMessage, setActionErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    void loadClusters();
    void loadPeople();
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

  async function refreshAfterClusterMutation(previousClusterId: number) {
    const resolvedSelectedClusterId = await loadClusters(previousClusterId);

    if (resolvedSelectedClusterId === null) {
      setClusterDetail(null);
      return;
    }

    await loadClusterDetail(resolvedSelectedClusterId);
  }

  return (
    <main className={styles.page}>
      <div className={styles.shell}>
        <header className={styles.header}>
          <p className={styles.kicker}>Milestone 10.3</p>
          <h1 className={styles.title}>Face Cluster Review</h1>
          <p className={styles.subtitle}>
            Review clusters, assign people, and apply core correction actions directly from the same screen.
          </p>
        </header>

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
            onAssign={handleAssign}
            onIgnoreCluster={handleIgnoreCluster}
            onRemoveFace={handleRemoveFace}
            onMoveFace={handleMoveFace}
          />
        </div>
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

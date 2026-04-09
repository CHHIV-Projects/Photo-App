import { useState } from "react";

import styles from "@/components/review-screen.module.css";
import type { PersonWithClusters } from "@/types/ui-api";

interface PeopleViewProps {
  people: PersonWithClusters[];
  isLoadingPeople: boolean;
  peopleErrorMessage: string | null;
  createErrorMessage: string | null;
  isCreatingPerson: boolean;
  onCreatePerson: (displayName: string) => Promise<boolean>;
  onSelectCluster: (clusterId: number) => void;
}

export function PeopleView({
  people,
  isLoadingPeople,
  peopleErrorMessage,
  createErrorMessage,
  isCreatingPerson,
  onCreatePerson,
  onSelectCluster
}: PeopleViewProps) {
  const [draftDisplayName, setDraftDisplayName] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const displayName = draftDisplayName.trim();
    if (!displayName) {
      setValidationError("Person name is required.");
      return;
    }

    setValidationError(null);
    const created = await onCreatePerson(displayName);
    if (created) {
      setDraftDisplayName("");
    }
  };

  return (
    <section className={styles.panel}>
      <header className={styles.panelHeader}>
        <div className={styles.panelTitleRow}>
          <h2 className={styles.panelTitle}>People</h2>
          <span className={styles.panelMeta}>{people.length} loaded</span>
        </div>
      </header>

      <div className={styles.panelBody}>
        <form className={styles.peopleForm} onSubmit={handleSubmit}>
          <input
            type="text"
            className={styles.peopleInput}
            placeholder="New person display name"
            value={draftDisplayName}
            onChange={(event) => setDraftDisplayName(event.target.value)}
            disabled={isCreatingPerson}
          />
          <button className={styles.assignButton} type="submit" disabled={isCreatingPerson}>
            {isCreatingPerson ? "Creating..." : "Create Person"}
          </button>
        </form>

        {validationError ? <div className={styles.errorMessage}>{validationError}</div> : null}
        {createErrorMessage ? <div className={styles.errorMessage}>{createErrorMessage}</div> : null}
        {isLoadingPeople ? <div className={styles.message}>Loading people...</div> : null}
        {peopleErrorMessage ? <div className={styles.errorMessage}>{peopleErrorMessage}</div> : null}

        {!isLoadingPeople && !peopleErrorMessage && people.length === 0 ? (
          <div className={styles.emptyState}>No people found.</div>
        ) : null}

        {!isLoadingPeople && !peopleErrorMessage && people.length > 0 ? (
          <div className={styles.peopleList}>
            {people.map((person) => (
              <article key={person.person_id} className={styles.peopleCard}>
                <div className={styles.peopleHeader}>
                  <h3 className={styles.peopleName}>{person.display_name}</h3>
                  <p className={styles.peopleMeta}>Person #{person.person_id}</p>
                </div>

                <p className={styles.peopleMeta}>Clusters: {person.clusters.length}</p>
                {person.clusters.length > 0 ? (
                  <ul className={styles.clusterAssignmentsList}>
                    {person.clusters.map((cluster) => (
                      <li key={cluster.cluster_id} className={styles.clusterAssignmentItem}>
                        <button
                          type="button"
                          className={styles.clusterAssignmentButton}
                          onClick={() => onSelectCluster(cluster.cluster_id)}
                        >
                          <span>Cluster #{cluster.cluster_id}</span>
                          <span>{cluster.face_count} faces</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className={styles.emptyState}>No assigned clusters.</div>
                )}
              </article>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}

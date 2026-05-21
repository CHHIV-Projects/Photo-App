import { useEffect, useMemo, useState } from "react";

import styles from "@/components/review-screen.module.css";
import { getPersonAliases } from "@/lib/api";
import type { PersonAliasSummary, PersonWithClusters } from "@/types/ui-api";

interface PeopleViewProps {
  people: PersonWithClusters[];
  isLoadingPeople: boolean;
  peopleErrorMessage: string | null;
  createErrorMessage: string | null;
  isCreatingPerson: boolean;
  onCreatePerson: (displayName: string) => Promise<boolean>;
  onAddAlias: (personId: number, alias: string) => Promise<void>;
  onRemoveAlias: (personId: number, aliasId: number) => Promise<void>;
  onSelectCluster: (clusterId: number) => void;
}

function personMatchesQuery(person: PersonWithClusters, queryLower: string): boolean {
  if (person.display_name.toLowerCase().includes(queryLower)) {
    return true;
  }
  return person.aliases.some((alias) => alias.toLowerCase().includes(queryLower));
}

export function PeopleView({
  people,
  isLoadingPeople,
  peopleErrorMessage,
  createErrorMessage,
  isCreatingPerson,
  onCreatePerson,
  onAddAlias,
  onRemoveAlias,
  onSelectCluster
}: PeopleViewProps) {
  const [draftDisplayName, setDraftDisplayName] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [aliasesByPersonId, setAliasesByPersonId] = useState<Record<number, PersonAliasSummary[]>>({});
  const [aliasDraftByPersonId, setAliasDraftByPersonId] = useState<Record<number, string>>({});
  const [aliasErrorByPersonId, setAliasErrorByPersonId] = useState<Record<number, string | null>>({});
  const [aliasBusyByPersonId, setAliasBusyByPersonId] = useState<Record<number, boolean>>({});
  const [aliasSuccessMessage, setAliasSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    let isCancelled = false;

    async function loadAliases() {
      if (people.length === 0) {
        setAliasesByPersonId({});
        return;
      }

      const entries = await Promise.all(
        people.map(async (person) => {
          const response = await getPersonAliases(person.person_id);
          return [person.person_id, response.items] as const;
        })
      );
      if (isCancelled) {
        return;
      }

      const next: Record<number, PersonAliasSummary[]> = {};
      for (const [personId, aliases] of entries) {
        next[personId] = aliases;
      }
      setAliasesByPersonId(next);
    }

    void loadAliases().catch(() => {
      if (!isCancelled) {
        setAliasesByPersonId({});
      }
    });

    return () => {
      isCancelled = true;
    };
  }, [people]);

  const visiblePeople = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return people;
    return people.filter((p) => personMatchesQuery(p, q));
  }, [people, searchQuery]);

  async function refreshAliasesForPerson(personId: number): Promise<void> {
    const response = await getPersonAliases(personId);
    setAliasesByPersonId((current) => ({
      ...current,
      [personId]: response.items,
    }));
  }

  async function handleAddAlias(personId: number): Promise<void> {
    const draft = (aliasDraftByPersonId[personId] ?? "").trim();
    if (!draft) {
      setAliasErrorByPersonId((current) => ({ ...current, [personId]: "Alias is required." }));
      return;
    }

    setAliasBusyByPersonId((current) => ({ ...current, [personId]: true }));
    setAliasErrorByPersonId((current) => ({ ...current, [personId]: null }));
    setAliasSuccessMessage(null);

    try {
      await onAddAlias(personId, draft);
      await refreshAliasesForPerson(personId);
      setAliasDraftByPersonId((current) => ({ ...current, [personId]: "" }));
      setAliasSuccessMessage("Alias added.");
    } catch (error) {
      const message = error instanceof Error && error.message ? error.message : "Failed to add alias.";
      setAliasErrorByPersonId((current) => ({ ...current, [personId]: message }));
    } finally {
      setAliasBusyByPersonId((current) => ({ ...current, [personId]: false }));
    }
  }

  async function handleRemoveAlias(personId: number, aliasId: number): Promise<void> {
    setAliasBusyByPersonId((current) => ({ ...current, [personId]: true }));
    setAliasErrorByPersonId((current) => ({ ...current, [personId]: null }));
    setAliasSuccessMessage(null);

    try {
      await onRemoveAlias(personId, aliasId);
      await refreshAliasesForPerson(personId);
      setAliasSuccessMessage("Alias removed.");
    } catch (error) {
      const message = error instanceof Error && error.message ? error.message : "Failed to remove alias.";
      setAliasErrorByPersonId((current) => ({ ...current, [personId]: message }));
    } finally {
      setAliasBusyByPersonId((current) => ({ ...current, [personId]: false }));
    }
  }

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
        {aliasSuccessMessage ? <div className={styles.message}>{aliasSuccessMessage}</div> : null}
        {isLoadingPeople ? <div className={styles.message}>Loading people...</div> : null}
        {peopleErrorMessage ? <div className={styles.errorMessage}>{peopleErrorMessage}</div> : null}

        {!isLoadingPeople && !peopleErrorMessage && people.length > 0 ? (
          <input
            type="search"
            className={styles.searchInput}
            placeholder="Search people..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        ) : null}

        {!isLoadingPeople && !peopleErrorMessage && visiblePeople.length === 0 && people.length > 0 ? (
          <div className={styles.emptyState}>No people match your search.</div>
        ) : null}
        {!isLoadingPeople && !peopleErrorMessage && people.length === 0 ? (
          <div className={styles.emptyState}>No people found.</div>
        ) : null}

        {!isLoadingPeople && !peopleErrorMessage && visiblePeople.length > 0 ? (
          <div className={styles.peopleList}>
            {visiblePeople.map((person) => (
              <article key={person.person_id} className={styles.peopleCard}>
                <div className={styles.peopleHeader}>
                  <h3 className={styles.peopleName}>{person.display_name}</h3>
                  <p className={styles.peopleMeta}>Person #{person.person_id}</p>
                </div>

                <p className={styles.peopleMeta}>Clusters: {person.clusters.length}</p>
                <div className={styles.aliasSection}>
                  <p className={styles.peopleMeta}>Aliases</p>
                  <div className={styles.aliasList}>
                    {(aliasesByPersonId[person.person_id] ?? []).map((alias) => (
                      <span key={alias.alias_id} className={styles.aliasChip}>
                        {alias.alias}
                        <button
                          type="button"
                          className={styles.aliasRemoveButton}
                          onClick={() => {
                            void handleRemoveAlias(person.person_id, alias.alias_id);
                          }}
                          disabled={aliasBusyByPersonId[person.person_id] ?? false}
                          aria-label={`Remove alias ${alias.alias}`}
                        >
                          x
                        </button>
                      </span>
                    ))}
                    {(aliasesByPersonId[person.person_id] ?? []).length === 0 ? (
                      <span className={styles.peopleMeta}>No aliases</span>
                    ) : null}
                  </div>
                  <div className={styles.aliasAddRow}>
                    <input
                      type="text"
                      className={styles.peopleInput}
                      placeholder="Add alias"
                      value={aliasDraftByPersonId[person.person_id] ?? ""}
                      onChange={(event) =>
                        setAliasDraftByPersonId((current) => ({
                          ...current,
                          [person.person_id]: event.target.value,
                        }))
                      }
                      disabled={aliasBusyByPersonId[person.person_id] ?? false}
                    />
                    <button
                      type="button"
                      className={styles.assignButton}
                      onClick={() => {
                        void handleAddAlias(person.person_id);
                      }}
                      disabled={aliasBusyByPersonId[person.person_id] ?? false}
                    >
                      Add
                    </button>
                  </div>
                  {aliasErrorByPersonId[person.person_id] ? (
                    <div className={styles.errorMessage}>{aliasErrorByPersonId[person.person_id]}</div>
                  ) : null}
                </div>
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

import { useEffect, useMemo, useState } from "react";

import styles from "@/components/review-screen.module.css";
import type { PersonSummary } from "@/types/ui-api";

interface PersonAssignFormProps {
  people: PersonSummary[];
  selectedPersonId: number | null;
  isLoadingPeople: boolean;
  isSubmitting: boolean;
  errorMessage: string | null;
  onAssign: (personId: number) => Promise<void>;
}

export function PersonAssignForm({
  people,
  selectedPersonId,
  isLoadingPeople,
  isSubmitting,
  errorMessage,
  onAssign
}: PersonAssignFormProps) {
  const [draftPersonId, setDraftPersonId] = useState<string>(selectedPersonId ? String(selectedPersonId) : "");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    setDraftPersonId(selectedPersonId ? String(selectedPersonId) : "");
  }, [selectedPersonId]);

  const filteredPeople = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) {
      return people;
    }
    return people.filter((person) => {
      if (person.display_name.toLowerCase().includes(q)) {
        return true;
      }
      return person.aliases.some((alias) => alias.toLowerCase().includes(q));
    });
  }, [people, searchQuery]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!draftPersonId) {
      return;
    }

    await onAssign(Number(draftPersonId));
  };

  return (
    <div className={styles.detailGrid}>
      {isLoadingPeople ? <div className={styles.message}>Loading people...</div> : null}
      {errorMessage ? <div className={styles.errorMessage}>{errorMessage}</div> : null}
      {!isLoadingPeople && people.length === 0 ? (
        <div className={styles.emptyState}>No people available to assign.</div>
      ) : null}
      {!isLoadingPeople && people.length > 0 ? (
        <form className={styles.assignForm} onSubmit={handleSubmit}>
          <input
            type="search"
            className={styles.searchInput}
            placeholder="Search person or alias..."
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            disabled={isSubmitting}
          />
          <select
            className={styles.select}
            value={draftPersonId}
            onChange={(event) => setDraftPersonId(event.target.value)}
            disabled={isSubmitting}
          >
            <option value="">Select person</option>
            {filteredPeople.map((person) => (
              <option key={person.person_id} value={person.person_id}>
                {person.aliases.length > 0
                  ? `${person.display_name} (${person.aliases.join(", ")})`
                  : person.display_name}
              </option>
            ))}
          </select>
          <button className={styles.assignButton} type="submit" disabled={!draftPersonId || isSubmitting}>
            {isSubmitting ? "Assigning..." : "Assign"}
          </button>
        </form>
      ) : null}
    </div>
  );
}

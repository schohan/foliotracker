export type ListVisibilityMode =
  | "first-run"
  | "held-only"
  | "watched-only"
  | "both";

/** Derive which list sections to show from membership counts. */
export function listVisibility(
  heldCount: number,
  watchedCount: number,
): ListVisibilityMode {
  if (heldCount === 0 && watchedCount === 0) return "first-run";
  if (heldCount > 0 && watchedCount === 0) return "held-only";
  if (heldCount === 0 && watchedCount > 0) return "watched-only";
  return "both";
}

export function showListSections(mode: ListVisibilityMode): boolean {
  return mode !== "first-run";
}

export function emptySiblingCopy(
  kind: "held" | "watched",
): string {
  if (kind === "held") {
    return "Nothing held yet. Add a ticker as Held when you own it.";
  }
  return "Nothing watched yet. Add a ticker as Watched to research it.";
}

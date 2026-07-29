export const RESEARCH_WAIT_LINE =
  "Researching — fundamentals, news, filings, thesis…";

/** Static honest stage line while a ticker is refreshing. No fake rotating stages. */
export function researchWaitCopy(isRefreshing: boolean): string | null {
  return isRefreshing ? RESEARCH_WAIT_LINE : null;
}

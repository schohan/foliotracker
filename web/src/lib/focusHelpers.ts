/** Whether a keyboard event should close the detail panel. */
export function shouldCloseOnEscape(key: string): boolean {
  return key === "Escape";
}

/** Stable id for returning focus to the row that opened detail. */
export function rowFocusId(ticker: string): string {
  return `ticker-row-${ticker}`;
}

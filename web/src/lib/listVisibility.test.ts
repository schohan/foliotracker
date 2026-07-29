import { describe, expect, it } from "vitest";
import {
  emptySiblingCopy,
  listVisibility,
  showListSections,
} from "./listVisibility";

describe("listVisibility", () => {
  it("returns first-run when both counts are zero", () => {
    expect(listVisibility(0, 0)).toBe("first-run");
  });

  it("returns held-only when only held has rows", () => {
    expect(listVisibility(2, 0)).toBe("held-only");
  });

  it("returns watched-only when only watched has rows", () => {
    expect(listVisibility(0, 3)).toBe("watched-only");
  });

  it("returns both when each list has rows", () => {
    expect(listVisibility(1, 1)).toBe("both");
  });
});

describe("showListSections", () => {
  it("hides sections on first-run only", () => {
    expect(showListSections("first-run")).toBe(false);
    expect(showListSections("held-only")).toBe(true);
    expect(showListSections("watched-only")).toBe(true);
    expect(showListSections("both")).toBe(true);
  });
});

describe("emptySiblingCopy", () => {
  it("returns warm held copy", () => {
    expect(emptySiblingCopy("held")).toContain("Held");
  });

  it("returns warm watched copy", () => {
    expect(emptySiblingCopy("watched")).toContain("Watched");
  });
});

import { beforeEach, describe, expect, it } from "vitest";
import {
  clearGuestHomeCache,
  readGuestHomeCache,
  writeGuestHomeCache,
  type StudentHomeSnapshot,
} from "../lib/chat/home-cache";

const home: StudentHomeSnapshot = {
  resume: null,
  minutesLeft: 15,
  current: {
    chapter: {
      id: "linear-equations",
      title: "Linear equations",
      live: true,
      status: "learning",
      recommended: true,
      skills_total: 12,
      skills_can_do_it: 1,
    },
    skill: "Use inverse operations",
  },
  started: true,
  due: 2,
  topics: [{ id: "linear-equations", title: "Linear equations", percent: 8 }],
};

describe("guest home cache", () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
  });

  it("keeps a snapshot in session storage, separated by guest", () => {
    writeGuestHomeCache("guest-a", home);

    expect(readGuestHomeCache("guest-a")).toEqual(home);
    expect(readGuestHomeCache("guest-b")).toBeNull();
    expect(localStorage.length).toBe(0);
  });

  it("clears the snapshot for a guest", () => {
    writeGuestHomeCache("guest-a", home);
    clearGuestHomeCache("guest-a");

    expect(readGuestHomeCache("guest-a")).toBeNull();
  });

  it("rejects malformed or outdated snapshots", () => {
    sessionStorage.setItem("yt_guest_home_v1:guest-a", JSON.stringify({ started: true }));

    expect(readGuestHomeCache("guest-a")).toBeNull();
  });
});

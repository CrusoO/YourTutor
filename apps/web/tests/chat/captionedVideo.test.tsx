import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CaptionedVideo } from "@/components/chat/CaptionedVideo";

const TRACK = { src: "blob:vtt", lang: "en-IN" };

beforeEach(() => {
  window.localStorage.clear();
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("CaptionedVideo", () => {
  it("renders a native captions track and an ON toggle by default", async () => {
    const { container } = render(<CaptionedVideo captions={TRACK} src="x.mp4" controls />);
    const track = container.querySelector("track")!;
    expect(track.getAttribute("kind")).toBe("captions");
    expect(track.getAttribute("srclang")).toBe("en-IN");
    expect(track.getAttribute("src")).toBe("blob:vtt");
    expect(track.hasAttribute("default")).toBe(true);
    const btn = await screen.findByTestId("captions-toggle");
    expect(btn.getAttribute("aria-pressed")).toBe("true");
    expect(btn.textContent).toContain("Captions");
    expect(btn.className).toContain("min-h-11");
  });

  it("toggles with the keyboard, flips aria-pressed and remembers the choice", async () => {
    const user = userEvent.setup();
    const { unmount } = render(<CaptionedVideo captions={TRACK} src="x.mp4" />);
    const btn = screen.getByTestId("captions-toggle");
    btn.focus();
    await user.keyboard("{Enter}");
    expect(btn.getAttribute("aria-pressed")).toBe("false");
    expect(window.localStorage.getItem("yt_captions")).toBe("off");
    unmount();
    render(<CaptionedVideo captions={TRACK} src="x.mp4" />);
    expect((await screen.findByTestId("captions-toggle")).getAttribute("aria-pressed")).toBe("false");
    await user.click(screen.getByTestId("captions-toggle"));
    expect(window.localStorage.getItem("yt_captions")).toBe("on");
  });

  it("is hidden and adds no track when there is no sidecar", () => {
    const { container } = render(<CaptionedVideo src="x.mp4" controls />);
    expect(screen.queryByTestId("captions-toggle")).toBeNull();
    expect(container.querySelector("track")).toBeNull();
    expect(container.querySelector("video")).not.toBeNull();
  });

  it("still works with storage blocked", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    const user = userEvent.setup();
    render(<CaptionedVideo captions={TRACK} src="x.mp4" />);
    const btn = screen.getByTestId("captions-toggle");
    expect(btn.getAttribute("aria-pressed")).toBe("true");
    await user.click(btn);
    expect(btn.getAttribute("aria-pressed")).toBe("false");
  });
});

import { cleanup, render, renderHook, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ShareLesson } from "@/components/chat/lesson/ShareLesson";
import { lessonLink } from "@/lib/chat/share";
import { useLinkStart } from "@/lib/chat/useLinkStart";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.history.replaceState({}, "", "/");
});

describe("ShareLesson", () => {
  beforeEach(() => {
    Object.defineProperty(navigator, "share", { value: undefined, configurable: true });
  });

  it("copies a link that carries only the question, and says so", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    render(<ShareLesson prompt="what is quantum tunnelling?" />);
    expect(screen.getByTestId("share-status")).toHaveTextContent("only the question");
    await userEvent.click(screen.getByTestId("share-button"));
    await waitFor(() => expect(screen.getByTestId("share-status")).toHaveTextContent("Link copied"));
    expect(writeText).toHaveBeenCalledWith(lessonLink(window.location.origin, "what is quantum tunnelling?"));
  });

  it("uses the device share sheet when there is one", async () => {
    const share = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "share", { value: share, configurable: true });
    render(<ShareLesson prompt="slope" />);
    await userEvent.click(screen.getByTestId("share-button"));
    await waitFor(() => expect(screen.getByTestId("share-status")).toHaveTextContent("Shared."));
    expect(share.mock.calls[0]![0].url).toBe(lessonLink(window.location.origin, "slope"));
  });

  it("says plainly when it can do neither", async () => {
    Object.defineProperty(navigator, "clipboard", { value: undefined, configurable: true });
    render(<ShareLesson prompt="slope" />);
    await userEvent.click(screen.getByTestId("share-button"));
    await waitFor(() => expect(screen.getByTestId("share-status")).toHaveTextContent("Couldn't share the link"));
  });
});

describe("useLinkStart", () => {
  const ready: { role: string; identityReady: boolean; contextReady: unknown; lessonOpen: boolean } = {
    role: "visitor",
    identityReady: true,
    contextReady: {},
    lessonOpen: false,
  };

  it("starts a lesson on the question in the address, once, and cleans the address", () => {
    window.history.replaceState({}, "", "/brownie-chat?topic=why%20is%20the%20sky%20blue%3F");
    const submitText = vi.fn();
    const { rerender } = renderHook((props) => useLinkStart(props), { initialProps: { ...ready, submitText } });
    expect(submitText).toHaveBeenCalledTimes(1);
    expect(submitText).toHaveBeenCalledWith("why is the sky blue?");
    expect(window.location.search).toBe("");
    rerender({ ...ready, submitText });
    rerender({ ...ready, lessonOpen: true, submitText });
    expect(submitText).toHaveBeenCalledTimes(1);
  });

  it("waits until the page can actually start a lesson", () => {
    window.history.replaceState({}, "", "/brownie-chat?topic=slope");
    const submitText = vi.fn();
    const { rerender } = renderHook((props) => useLinkStart(props), {
      initialProps: { ...ready, identityReady: false, submitText },
    });
    rerender({ ...ready, identityReady: true, contextReady: null, submitText });
    expect(submitText).not.toHaveBeenCalled();
    expect(window.location.search).toBe("?topic=slope"); // not cleaned until it has started
    rerender({ ...ready, submitText });
    expect(submitText).toHaveBeenCalledWith("slope");
  });

  it("does nothing for a signed-in student, a teacher or a parent, or when a lesson is already open", () => {
    for (const props of [
      { ...ready, role: "student" },
      { ...ready, role: "teacher" },
      { ...ready, role: "parent" },
      { ...ready, lessonOpen: true },
    ]) {
      window.history.replaceState({}, "", "/brownie-chat?topic=slope");
      const submitText = vi.fn();
      renderHook(() => useLinkStart({ ...props, submitText }));
      expect(submitText).not.toHaveBeenCalled();
    }
  });

  it("does nothing when the address has no usable question", () => {
    for (const search of ["", "?topic=", "?topic=a", "?other=1"]) {
      window.history.replaceState({}, "", "/brownie-chat" + search);
      const submitText = vi.fn();
      renderHook(() => useLinkStart({ ...ready, submitText }));
      expect(submitText).not.toHaveBeenCalled();
    }
  });

  it("also starts for a guest", () => {
    window.history.replaceState({}, "", "/brownie-chat?topic=slope");
    const submitText = vi.fn();
    renderHook(() => useLinkStart({ ...ready, role: "guest", submitText }));
    expect(submitText).toHaveBeenCalledWith("slope");
  });
});

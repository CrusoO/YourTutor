import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@assistant-ui/react", () => ({
  ComposerPrimitive: {
    Root: ({ children }: { children: React.ReactNode }) => <form>{children}</form>,
    Input: () => <textarea data-testid="composer-input" />,
  },
}));
vi.mock("@/components/chat/ChatProvider", () => ({
  MODES_BY_ROLE: { visitor: ["learn"] },
  useChatApi: () => ({
    copy: new Proxy({}, { get: (_t, k) => String(k) }),
    role: "visitor",
    mode: "learn",
    setMode: vi.fn(),
    busy: false,
    ctx: null,
    dispatch: vi.fn(),
  }),
}));

import { Composer } from "@/components/chat/Composer";

afterEach(() => {
  cleanup();
  vi.unstubAllEnvs();
});

describe("the composer mic", () => {
  it("is not rendered by default", () => {
    render(<Composer />);
    expect(screen.queryByTestId("composer-mic")).toBeNull();
    expect(screen.getByTestId("composer-send")).toBeTruthy();
  });

  it("is not rendered when the flag is anything but true", () => {
    vi.stubEnv("NEXT_PUBLIC_VOICE_ENABLED", "1");
    render(<Composer />);
    expect(screen.queryByTestId("composer-mic")).toBeNull();
  });

  it("appears only when NEXT_PUBLIC_VOICE_ENABLED is true", () => {
    vi.stubEnv("NEXT_PUBLIC_VOICE_ENABLED", "true");
    render(<Composer />);
    expect(screen.getByTestId("composer-mic")).toBeTruthy();
  });
});

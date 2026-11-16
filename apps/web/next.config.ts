import type { NextConfig } from "next";

// Phone preview: hosts (no scheme or port) allowed to load dev resources, e.g. "192.168.1.20".
const allowedDevOrigins = (process.env.NEXT_ALLOWED_DEV_ORIGINS || "")
  .split(",")
  .map((host) => host.trim())
  .filter(Boolean);

// The /dev preview pages live in files named page.dev.tsx. They are routes only when NEXT_PUBLIC_DEV_TOOLS is on or
// the server is not a production build, so a production build without the flag does not contain them at all.
const devToolsOn = process.env.NEXT_PUBLIC_DEV_TOOLS === "true" || process.env.NODE_ENV !== "production";

const nextConfig: NextConfig = {
  pageExtensions: devToolsOn ? ["tsx", "ts", "jsx", "js", "dev.tsx"] : ["tsx", "ts", "jsx", "js"],
  allowedDevOrigins,
  async headers() {
    return [
      {
        source: "/checkpoints/:path*",
        headers: [{ key: "Referrer-Policy", value: "no-referrer" }],
      },
    ];
  },
};

export default nextConfig;

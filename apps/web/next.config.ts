import type { NextConfig } from "next";

// Phone preview: hosts (no scheme or port) allowed to load dev resources, e.g. "192.168.1.20".
const allowedDevOrigins = (process.env.NEXT_ALLOWED_DEV_ORIGINS || "")
  .split(",")
  .map((host) => host.trim())
  .filter(Boolean);

const nextConfig: NextConfig = {
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

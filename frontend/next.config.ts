import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Docker 部署：生成独立运行目录（.next/standalone），无需完整 node_modules
  output: "standalone",
  allowedDevOrigins: ["127.0.0.1", "localhost"],
};

export default nextConfig;

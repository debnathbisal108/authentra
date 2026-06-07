/** @type {import('next').NextConfig} */
const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000";
const nextConfig = {
  output: "standalone",
  experimental: {
    serverActions: {
      allowedOrigins: ["localhost:3000"],
    },
  },
  async rewrites() {
    console.log("API URL:", process.env.NEXT_PUBLIC_API_URL);
    return [
      {
        source: "/api/:path*",
        // destination: `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`,
        destination: `${API_URL}/api/:path*`
      },
    ];
  },
};

module.exports = nextConfig;

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",

  async rewrites() {
    let backendUrl =
      process.env.API_INTERNAL_URL ||
      "https://authentra-oeft.onrender.com";

    if (backendUrl && !backendUrl.startsWith("http")) {
      backendUrl = `http://${backendUrl}`;
    }

    console.log("[next.config] Proxying /api/* to:", backendUrl);

    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",

  async rewrites() {
    let backendUrl =
      process.env.API_INTERNAL_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      "http://backend:8000";

    console.log("API_INTERNAL_URL =", process.env.API_INTERNAL_URL);
    console.log("NEXT_PUBLIC_API_URL =", process.env.NEXT_PUBLIC_API_URL);
    console.log("backendUrl =", backendUrl);
    
    if (backendUrl && !backendUrl.startsWith("http")) {
      backendUrl = `http://${backendUrl}`;
    }

    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;

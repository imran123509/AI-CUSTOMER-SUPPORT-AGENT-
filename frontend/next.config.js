/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  experimental: {
    serverActions: { allowedOrigins: ["*"] },
  },
  async rewrites() {
    const api = process.env.NEXT_PUBLIC_API_URL || "http://backend:8000";
    return [
      { source: "/api/:path*", destination: `${api}/api/:path*` },
    ];
  },
};
module.exports = nextConfig;

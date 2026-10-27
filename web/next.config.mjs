/** @type {import('next').NextConfig} */
const apiUrl = process.env.API_URL ?? "http://localhost:8000";

const nextConfig = {
  // The browser only talks to the Next.js origin; /api/* is forwarded to FastAPI.
  // Same origin = httpOnly cookies work without CORS.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiUrl}/api/:path*` }];
  },
};

export default nextConfig;

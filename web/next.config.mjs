/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // INTERNAL_API_URL is a server-only Vercel env var pointing at the Railway
    // backend. Proxying /api/v1/* through Next.js makes the session cookie
    // first-party to peacewayonline.com — Safari and Chrome block cross-origin
    // cookies even with SameSite=None, which caused the post-registration loop.
    const internal = process.env.INTERNAL_API_URL;
    if (!internal) return [];
    return [
      {
        source: "/api/v1/:path*",
        destination: `${internal}/:path*`,
      },
    ];
  },
};

export default nextConfig;

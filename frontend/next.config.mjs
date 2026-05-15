/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // The frontend image runs in a containerized environment behind Docker
  // networking; allow image optimization to be a no-op for now.
  images: {
    unoptimized: true,
  },
  // Suppress source-map generation in production for a smaller image.
  productionBrowserSourceMaps: false,
};

export default nextConfig;

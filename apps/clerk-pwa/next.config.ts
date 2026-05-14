import type { NextConfig } from 'next';

const config: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ['@aura/ui', '@aura/consent', '@aura/api-client', '@aura/types'],
};

export default config;

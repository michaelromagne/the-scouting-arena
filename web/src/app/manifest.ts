import { MetadataRoute } from 'next';

/**
 * Web app manifest for PWA support and better mobile experience.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'The Scouting Arena - Football Analytics',
    short_name: 'Scouting Arena',
    description: 'Advanced football player analytics and scouting platform with 5,000+ players from top European leagues',
    start_url: '/',
    display: 'standalone',
    background_color: '#0B1B3F',
    theme_color: '#00FF88',
    icons: [
      {
        src: '/favicon.svg',
        sizes: 'any',
        type: 'image/svg+xml',
      },
    ],
  };
}

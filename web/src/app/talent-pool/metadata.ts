import { Metadata } from 'next';
import { generateSEO } from '@/lib/seo';

export const metadata: Metadata = generateSEO({
  title: 'Talent Pool - Player Database & Search',
  description: 'Browse and search through 5,000+ football players from top European leagues. Filter by position, league, nationality, and performance metrics to find the perfect player.',
  keywords: [
    'player database',
    'football talent pool',
    'player search',
    'football player finder',
    'scouting database',
    'player profiles',
  ],
  url: '/talent-pool',
});

import { Metadata } from 'next';
import { generateSEO } from '@/lib/seo';

export const metadata: Metadata = generateSEO({
  title: 'Player Similarity Search',
  description: 'Find similar football players using advanced analytics. Discover players with comparable playing styles, statistics, and performance metrics across multiple leagues.',
  keywords: [
    'similar players',
    'player similarity',
    'football player finder',
    'playing style comparison',
    'player alternatives',
    'scouting tool',
  ],
  url: '/similarity-search',
});

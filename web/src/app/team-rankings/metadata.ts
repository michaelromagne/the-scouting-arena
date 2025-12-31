import { Metadata } from 'next';
import { generateSEO } from '@/lib/seo';

export const metadata: Metadata = generateSEO({
  title: 'Team Rankings & League Standings',
  description: 'View comprehensive team rankings and performance metrics across European football leagues. Compare teams by various statistical categories and performance indicators.',
  keywords: [
    'team rankings',
    'league standings',
    'team statistics',
    'football league tables',
    'team performance rankings',
    'European football teams',
  ],
  url: '/team-rankings',
});

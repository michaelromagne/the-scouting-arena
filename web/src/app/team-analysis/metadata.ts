import { Metadata } from 'next';
import { generateSEO } from '@/lib/seo';

export const metadata: Metadata = generateSEO({
  title: 'Team Analysis & Squad Statistics',
  description: 'Analyze football team performance with detailed squad statistics, player distributions, and comparative metrics across Premier League, La Liga, Serie A, Bundesliga, and more.',
  keywords: [
    'team analysis',
    'squad statistics',
    'team performance',
    'football team stats',
    'squad depth analysis',
    'team comparison',
  ],
  url: '/team-analysis',
});

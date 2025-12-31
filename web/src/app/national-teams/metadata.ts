import { Metadata } from 'next';
import { generateSEO } from '@/lib/seo';

export const metadata: Metadata = generateSEO({
  title: 'National Team Statistics & Analysis',
  description: 'Explore national team player pools, statistics, and performance metrics. Analyze international football talent across different countries and competitions.',
  keywords: [
    'national team stats',
    'international football',
    'national team players',
    'country football statistics',
    'international player pool',
    'national team analysis',
  ],
  url: '/national-teams',
});

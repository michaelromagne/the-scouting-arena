import { Metadata } from 'next';
import { generateSEO } from '@/lib/seo';

export const metadata: Metadata = generateSEO({
  title: 'Face-to-Face Player Comparison',
  description: 'Compare two football players head-to-head with interactive scatter plots, detailed radar charts, and comprehensive performance analysis across all metrics from top European leagues.',
  keywords: [
    'player comparison',
    'head to head',
    'football player vs',
    'soccer comparison tool',
    'player stats comparison',
    'radar chart comparison',
  ],
  url: '/face-to-face',
});

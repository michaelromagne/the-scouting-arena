import { MetadataRoute } from 'next';

/**
 * Generate sitemap for search engines.
 *
 * This sitemap includes all static pages and can be extended to include
 * dynamic player profiles and team pages.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://thescoutingarena.com';

  const routes = [
    '',
    '/face-to-face',
    '/similarity-search',
    '/team-analysis',
    '/team-rankings',
    '/national-teams',
    '/talent-pool',
  ];

  return routes.map((route) => ({
    url: `${baseUrl}${route}`,
    lastModified: new Date(),
    changeFrequency: route === '' ? 'daily' : 'weekly',
    priority: route === '' ? 1.0 : 0.8,
  }));
}

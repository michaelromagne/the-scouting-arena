import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Formats a compact season code (e.g., "2425") into a readable format (e.g., "2024-2025").
 * If the input doesn't match the expected format, returns it unchanged.
 *
 * @param season - Compact season code (e.g., "2425", "2526")
 * @returns Formatted season string (e.g., "2024-2025", "2025-2026")
 */
export function formatSeason(season: string): string {
  // Match 4-digit season codes like "2425", "2526"
  const match = season.match(/^(\d{2})(\d{2})$/);

  if (match) {
    const startYear = `20${match[1]}`;
    const endYear = `20${match[2]}`;
    return `${startYear}-${endYear}`;
  }

  // Return unchanged if it doesn't match the pattern
  return season;
}

import { z } from "zod";

// Legacy API_BASE_URL - now using /api/ proxy routes
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

// Response schemas
const PlayerSchema = z.object({
  player_id: z.number(),
  player_name: z.string(),
  team_name: z.string().nullable(),
  league_name: z.string().nullable(),
  season_label: z.string().nullable(),
  position: z.string().nullable(),
  minutes: z.number().nullable(),
  image_url: z.string().nullable(),
  market_value_eur: z.number().nullable(),
  nationality: z.string().nullable(),
  birth_date: z.string().nullable(),
});

const MetricDefinitionSchema = z.object({
  code: z.string(),
  name: z.string(),
  category: z.string().optional(),
  description: z.string().optional(),
  direction: z.enum(["higher_is_better", "lower_is_better"]),
});

const RankingItemSchema = z.object({
  player_id: z.number(),
  player_name: z.string(),
  team_name: z.string(),
  league_name: z.string(),
  season_label: z.string(),
  value: z.number(),
  percentile: z.number().nullable(),
  image_url: z.string().nullable().optional(),
});

const ScatterPointSchema = z.object({
  player_id: z.number(),
  player_name: z.string(),
  team_name: z.string(),
  league_name: z.string(),
  season_label: z.string(),
  position: z.string().optional(),
  x: z.number(),
  y: z.number(),
});

const PlayerMetricSchema = z.object({
  code: z.string(),
  name: z.string(),
  category: z.string().nullable(),
  quantile_value: z.number().nullable(),
});

const PlayerDetailSchema = z.object({
  player_id: z.number(),
  player_name: z.string(),
  team_name: z.string().nullable(),
  league_name: z.string().nullable(),
  season_label: z.string().nullable(),
  minutes: z.number().nullable(),
  position: z.string().nullable(),
  value_m_eur: z.number().nullable(),
  image_url: z.string().nullable(),
  nationality: z.string().nullable(),
  birth_date: z.string().nullable(), // ISO date string (YYYY-MM-DD)
  metrics: z.array(PlayerMetricSchema),
});

// API response types
export type Player = z.infer<typeof PlayerSchema>;
export type MetricDefinition = z.infer<typeof MetricDefinitionSchema>;
export type RankingItem = z.infer<typeof RankingItemSchema>;
export type ScatterPoint = z.infer<typeof ScatterPointSchema>;
export type PlayerMetric = z.infer<typeof PlayerMetricSchema>;
export type PlayerDetail = z.infer<typeof PlayerDetailSchema>;

// ============================================================================
// USER FEATURES (Bookmarks / Watchlists)
// ============================================================================

const BookmarkSchema = z.object({
  bookmark_id: z.number(),
  notes: z.string().nullable().optional(),
  tags: z.array(z.string()).nullable().optional(),
  created_at: z.string().nullable().optional(),
  player_season_id: z.number(),
  player_id: z.number(),
  player_name: z.string(),
  position_primary: z.string().nullable().optional(),
  position: z.string().nullable().optional(),
  minutes: z.number().nullable().optional(),
  market_value_eur: z.number().nullable().optional(),
  birth_date: z.string().nullable().optional(),
  nationality: z.string().nullable().optional(),
  image_url: z.string().nullable().optional(),
  team_name: z.string().nullable().optional(),
  league_name: z.string().nullable().optional(),
  season_label: z.string().nullable().optional(),
});

const BookmarksResponseSchema = z.object({
  bookmarks: z.array(BookmarkSchema),
});

export type Bookmark = z.infer<typeof BookmarkSchema>;

const WatchlistSchema = z.object({
  id: z.number(),
  name: z.string(),
  description: z.string().nullable().optional(),
  is_public: z.boolean().nullable().optional(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
});

const WatchlistsResponseSchema = z.object({
  watchlists: z.array(WatchlistSchema),
});

export type Watchlist = z.infer<typeof WatchlistSchema>;

export async function fetchBookmarks(): Promise<Bookmark[]> {
  const response = await fetch("/api/bookmarks");
  if (!response.ok) {
    throw new Error(`Failed to fetch bookmarks: ${response.statusText}`);
  }
  const data = await response.json();
  return BookmarksResponseSchema.parse(data).bookmarks;
}

export async function fetchWatchlists(): Promise<Watchlist[]> {
  const response = await fetch("/api/watchlists");
  if (!response.ok) {
    throw new Error(`Failed to fetch watchlists: ${response.statusText}`);
  }
  const data = await response.json();
  return WatchlistsResponseSchema.parse(data).watchlists;
}

export async function createWatchlist(input: {
  name: string;
  description?: string;
}): Promise<Watchlist> {
  const response = await fetch("/api/watchlists", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Failed to create watchlist: ${text || response.statusText}`);
  }
  const data = await response.json();
  return WatchlistSchema.parse(data.watchlist);
}

export async function deleteWatchlist(watchlistId: number): Promise<void> {
  const response = await fetch(`/api/watchlists?watchlist_id=${watchlistId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Failed to delete watchlist: ${text || response.statusText}`);
  }
}

export interface PaginatedResponse<T> {
  total: number;
  items: T[];
}

export interface RankingsResponse {
  metric: string;
  direction: "higher_is_better" | "lower_is_better";
  total: number;
  items: RankingItem[];
}

export interface ScatterResponse {
  x_metric: string;
  y_metric: string;
  total: number;
  items: ScatterPoint[];
}

export interface PlayerRankResponse {
  player_id: number;
  player_name: string;
  team_name: string | null;
  league_name: string | null;
  season_label: string | null;
  quantile_value: number;
  image_url: string | null;
  nationality: string | null;
  birth_date: string | null;
  value_m_eur: number | null;
  rank: number;
  total: number;
  metric: string;
  direction: "higher_is_better" | "lower_is_better";
}


// API functions
export async function fetchPlayers(params: {
  q?: string;
  league?: string;
  season?: string;
  team?: string;
  position?: string;
  page?: number;
  limit?: number;
}): Promise<PaginatedResponse<Player>> {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) {
      searchParams.set(key, value.toString());
    }
  });

  const url = `/api/players?${searchParams}`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch players: ${response.statusText}`);
  }

  return response.json();
}

export async function fetchMetrics(params: {
  q?: string;
  category?: string;
  page?: number;
  limit?: number;
} = {}): Promise<PaginatedResponse<MetricDefinition>> {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) {
      searchParams.set(key, value.toString());
    }
  });

  const response = await fetch(`/api/metrics?${searchParams}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch metrics: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchRankings(params: {
  metric: string;
  league?: string;
  season?: string;
  limit?: number;
  min_minutes?: number;
}): Promise<RankingsResponse> {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) {
      searchParams.set(key, value.toString());
    }
  });

  const response = await fetch(`/api/rankings?${searchParams}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch rankings: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchScatter(params: {
  x: string;
  y: string;
  league?: string;
  season?: string;
  position?: string;
  min_minutes?: number;
}): Promise<ScatterResponse> {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) {
      searchParams.set(key, value.toString());
    }
  });

  const response = await fetch(`/api/scatter?${searchParams}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch scatter data: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchPlayerRank(params: {
  playerId: number;
  metric: string;
  league?: string;
  season?: string;
  pos?: string;
  team?: string;
  nation?: string;
  min_minutes?: number;
  min_value?: number;
  max_value?: number;
  min_age?: number;
  max_age?: number;
}): Promise<PlayerRankResponse> {
  const searchParams = new URLSearchParams({
    metric: params.metric,
  });

  if (params.league) searchParams.set('league', params.league);
  if (params.season) searchParams.set('season', params.season);
  if (params.pos) searchParams.set('pos', params.pos);
  if (params.team) searchParams.set('team', params.team);
  if (params.nation) searchParams.set('nation', params.nation);
  if (params.min_minutes !== undefined) searchParams.set('min_minutes', params.min_minutes.toString());
  if (params.min_value !== undefined) searchParams.set('min_value', params.min_value.toString());
  if (params.max_value !== undefined) searchParams.set('max_value', params.max_value.toString());
  if (params.min_age !== undefined) searchParams.set('min_age', params.min_age.toString());
  if (params.max_age !== undefined) searchParams.set('max_age', params.max_age.toString());

  const response = await fetch(`/api/players/${params.playerId}/rank?${searchParams}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch player rank: ${response.statusText}`);
  }
  return response.json();
}

// Fetch available leagues and seasons
export async function fetchLeagues(): Promise<string[]> {
  // Use a broad query to get all available leagues (API limit is 200)
  const response = await fetch(`/api/rankings?metric=finishing&limit=200&min_minutes=0`);
  if (!response.ok) {
    throw new Error(`Failed to fetch leagues: ${response.statusText}`);
  }

  const data = await response.json();
  const leagues = Array.from(new Set(data.items.map((item: RankingItem) => item.league_name).filter(Boolean))) as string[];

  // Add "Big 5 European Leagues" as a special filter option at the top
  const sortedLeagues = leagues.sort();

  // Insert "Big 5 European Leagues" after "Aggregated (All Leagues)" if it exists
  const aggregatedIndex = sortedLeagues.indexOf("Aggregated (All Leagues)");
  if (aggregatedIndex !== -1) {
    sortedLeagues.splice(aggregatedIndex + 1, 0, "Big 5 European Leagues");
  } else {
    // If no aggregated league, add at the beginning
    sortedLeagues.unshift("Big 5 European Leagues");
  }

  return sortedLeagues;
}

export async function fetchSeasons(): Promise<string[]> {
  // Use a broad query to get all available seasons (API limit is 200)
  const response = await fetch(`/api/rankings?metric=finishing&limit=200&min_minutes=0`);
  if (!response.ok) {
    throw new Error(`Failed to fetch seasons: ${response.statusText}`);
  }

  const data = await response.json();
  const seasons = Array.from(new Set(data.items.map((item: RankingItem) => item.season_label).filter(Boolean))) as string[];
  return seasons.sort().reverse(); // Most recent first
}

export async function fetchPlayerLeagues(playerId: number): Promise<string[]> {
  const response = await fetch(`/api/players/${playerId}/leagues`);
  if (!response.ok) {
    throw new Error(`Failed to fetch player leagues: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchTeams(): Promise<string[]> {
  const response = await fetch(`/api/teams`);
  if (!response.ok) {
    throw new Error(`Failed to fetch teams: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchNations(): Promise<string[]> {
  const response = await fetch(`/api/nations`);
  if (!response.ok) {
    throw new Error(`Failed to fetch nations: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchPositions(): Promise<string[]> {
  // Try to fetch from a dedicated positions endpoint first
  try {
    const response = await fetch(`/api/positions`);
    if (response.ok) {
      return response.json();
    }
  } catch (error) {
    console.warn('Positions endpoint not available, using fallback');
  }

  // Fallback: return common football positions
  // This should be replaced with a proper API endpoint once positions table is integrated
  const positions = [
    'GK',      // Goalkeeper
    'DF',      // Defender
    'MF',      // Midfielder
    'FW',      // Forward
    'DF,MF',   // Defender/Midfielder
    'FW,MF',   // Winger
    'DF,FW',   // Fullback
  ];

  return positions;
}

// Player detail
export async function fetchPlayer(playerId: number, season?: string, league?: string): Promise<PlayerDetail> {
  const url = new URL(`/api/players/${playerId}`, window.location.origin);
  if (season) {
    url.searchParams.set('season', season);
  }
  if (league) {
    url.searchParams.set('league', league);
  }

  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error(`Failed to fetch player: ${response.statusText}`);
  }

  const data = await response.json();
  return PlayerDetailSchema.parse(data);
}

// Chart URL builders
export function buildRankingsChartUrl(params: {
  metric: string;
  league?: string;
  season?: string;
  limit?: number;
  min_minutes?: number;
}): string {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) {
      searchParams.set(key, value.toString());
    }
  });
  return `/api/charts/rankings/bar?${searchParams}`;
}

export function buildScatterChartUrl(params: {
  x: string;
  y: string;
  league?: string;
  season?: string;
  position?: string;
  min_minutes?: number;
}): string {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) {
      searchParams.set(key, value.toString());
    }
  });
  return `/api/charts/scatter/metrics?${searchParams}`;
}

// Similar players types
export interface SimilarPlayer {
  player_id: number;
  player_name: string;
  team_name: string;
  league_name: string;
  season_label: string;
  position: string;
  similarity_score: number;
  image_url?: string;
  value_m_eur?: number | null;
  nationality?: string | null;
  birth_date?: string | null;  // ISO date string (YYYY-MM-DD)
}

export interface SimilarPlayersResponse {
  player_id: number;
  player_name: string;
  similar_players: SimilarPlayer[];
}

// Fetch similar players
export async function fetchSimilarPlayers({
  playerId,
  season = "2526",  // Default to current season (matches DEFAULT_FILTERS.season)
  league = "Aggregated (All Leagues)",
  k = 20,
  min_minutes = 0,
  pos,
  nation,
  min_value,
  max_value
}: {
  playerId: number;
  season?: string;
  league?: string;
  k?: number;
  min_minutes?: number;
  pos?: string;
  nation?: string;
  min_value?: number;
  max_value?: number;
}): Promise<SimilarPlayersResponse> {
  const params = new URLSearchParams({
    season,
    league,
    k: k.toString(),
    min_minutes: min_minutes.toString()
  });

  if (pos) params.append("pos", pos);
  if (nation) params.append("nation", nation);
  if (min_value !== undefined) params.append("min_value", min_value.toString());
  if (max_value !== undefined) params.append("max_value", max_value.toString());

  const response = await fetch(`/api/players/${playerId}/similar?${params}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch similar players: ${response.statusText}`);
  }

  return response.json();
}

// ============================================================================
// TEAM ANALYSIS API
// ============================================================================

export interface Team {
  id: number;
  name: string;
  league_name: string | null;
  league_id: number | null;
}

export interface TeamMetricValue {
  quantile_value: number;
}

export interface TeamStats {
  team_id: number;
  team_name: string;
  league_name: string | null;
  season_label: string | null;
  games_played: number | null;
  metrics: Record<string, TeamMetricValue>;
}

export interface TopPlayer {
  player_id: number;
  player_name: string;
  position: string | null;
  quantile_value: number;
  image_url: string | null;
}

export interface ElitePlayer {
  player_id: number;
  player_name: string;
  position: string | null;
  image_url: string | null;
  team_name?: string | null;
  market_value_eur?: number | null;
  birth_date?: string | null;  // ISO date string
  minutes?: number | null;
  elite_categories: Record<string, number>;  // Category -> quantile value (e.g., {"Finishing": 98.5})
  max_quantile: number;  // Highest quantile value
}

export interface TeamComparison {
  team1: TeamStats;
  team2: TeamStats;
  elite_players_team1: ElitePlayer[];
  elite_players_team2: ElitePlayer[];
  top_value_team1: ElitePlayer[];
  top_value_team2: ElitePlayer[];
}

export interface NationalTeam {
  nationality: string;
  season_label: string;
  elite_players: ElitePlayer[];
  top_value_players: ElitePlayer[];
}

export async function fetchNationalTeam(
  nationality: string,
  season: string = "2526",
  limit: number = 10
): Promise<NationalTeam> {
  const params = new URLSearchParams({
    season,
    limit: limit.toString(),
  });
  const response = await fetch(`/api/national-teams/${encodeURIComponent(nationality)}?${params}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch national team: ${response.statusText}`);
  }

  return response.json();
}

export async function fetchTeamsList({
  league,
  season,
}: {
  league?: string;
  season?: string;
} = {}): Promise<Team[]> {
  const params = new URLSearchParams();
  if (league) params.append("league", league);
  if (season) params.append("season", season);

  const response = await fetch(`/api/teams/list?${params}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch teams list: ${response.statusText}`);
  }

  return response.json();
}

export async function fetchTeamStats({
  teamId,
  season = "2526",
}: {
  teamId: number;
  season?: string;
}): Promise<TeamStats> {
  const params = new URLSearchParams({ season });
  const response = await fetch(`/api/teams/${teamId}/stats?${params}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch team stats: ${response.statusText}`);
  }

  return response.json();
}

export async function fetchTeamComparison({
  team1Id,
  team2Id,
  season1 = "2526",
  season2 = "2526",
  topN = 3,
}: {
  team1Id: number;
  team2Id: number;
  season1?: string;
  season2?: string;
  topN?: number;
}): Promise<TeamComparison> {
  const params = new URLSearchParams({
    team1_id: team1Id.toString(),
    team2_id: team2Id.toString(),
    season1,
    season2,
    top_n: topN.toString(),
  });

  const response = await fetch(`/api/teams/compare?${params}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch team comparison: ${response.statusText}`);
  }

  return response.json();
}

export async function fetchTeamTopPlayers({
  teamId,
  season = "2526",
  category,
  limit = 3,
}: {
  teamId: number;
  season?: string;
  category: string;
  limit?: number;
}): Promise<TopPlayer[]> {
  const params = new URLSearchParams({
    season,
    category,
    limit: limit.toString(),
  });

  const response = await fetch(`/api/teams/${teamId}/top-players?${params}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch team top players: ${response.statusText}`);
  }

  return response.json();
}

// Re-export fetchMetricCategories from api-client
export { fetchMetricCategories, type MetricCategory } from "./api-client";

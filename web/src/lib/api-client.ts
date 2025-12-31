const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export interface Metric {
  code: string;
  name: string;
  category?: string;
  description?: string;
  direction: string;
  scale?: string;
}

export interface PaginatedMetrics {
  total: number;
  items: Metric[];
}

export interface League {
  id: number;
  name: string;
}

export interface Season {
  id: number;
  label: string;
  start_year?: number;
  end_year?: number;
}

export interface PlayerItem {
  player_id: number;
  player_name: string;
  team_name?: string;
  league_name?: string;
  season_label?: string;
  minutes?: number;
  position?: string;
}

export interface PaginatedPlayers {
  total: number;
  items: PlayerItem[];
}

export interface RankingItem {
  player_id: number;
  player_name: string;
  team_name?: string;
  league_name?: string;
  season_label?: string;
  value: number;
  percentile?: number;
}

export interface RankingsResponse {
  metric: string;
  direction: string;
  total: number;
  items: RankingItem[];
}

export interface ScatterPoint {
  player_id: number;
  player_name: string;
  team_name?: string;
  league_name?: string;
  season_label?: string;
  position?: string;
  x: number;
  y: number;
}

export interface ScatterResponse {
  x: string;
  y: string;
  total: number;
  items: ScatterPoint[];
}

export interface PlayerMetricOut {
  code: string;
  name: string;
  category?: string;
  value?: number;
  percentile?: number;
}

export interface PlayerDetail {
  player_id: number;
  player_name: string;
  team_name?: string;
  league_name?: string;
  season_label?: string;
  minutes?: number;
  position?: string;
  value_m_eur?: number;
  metrics: PlayerMetricOut[];
}

// Metrics API
export const fetchMetrics = async (params?: {
  q?: string;
  offset?: number;
  limit?: number;
}): Promise<PaginatedMetrics> => {
  const searchParams = new URLSearchParams();
  if (params?.q) searchParams.append('q', params.q);
  if (params?.offset !== undefined) searchParams.append('offset', params.offset.toString());
  if (params?.limit !== undefined) searchParams.append('limit', params.limit.toString());

  const url = `${API_BASE_URL}/metrics${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch metrics: ${response.statusText}`);
  }

  return response.json();
};

// Get all metrics (fetches all pages)
export const fetchAllMetrics = async (): Promise<Metric[]> => {
  const allMetrics: Metric[] = [];
  let offset = 0;
  const limit = 100;

  while (true) {
    const page = await fetchMetrics({ offset, limit });
    allMetrics.push(...page.items);

    if (page.items.length < limit) {
      break; // No more pages
    }
    offset += limit;
  }

  return allMetrics;
};

export interface MetricCategory {
  category: string;
  description?: string;
  metric_count: number;
  sample_metrics: string[];
  isGoalkeeper: boolean;
}

// Get metric categories with rich descriptions from FBREF statistics
export const fetchMetricCategories = async (): Promise<MetricCategory[]> => {
  // Static list of metric categories organized by field players vs goalkeepers
  return [
    // Field player metrics
    { category: "Finishing", isGoalkeeper: false, description: "Goal scoring ability", metric_count: 5, sample_metrics: ["finishing"] },
    { category: "Dribbling", isGoalkeeper: false, description: "Dribbling and ball carrying", metric_count: 7, sample_metrics: ["dribbling"] },
    { category: "Passing", isGoalkeeper: false, description: "Key passes and assists", metric_count: 8, sample_metrics: ["passing"] },
    { category: "Defense", isGoalkeeper: false, description: "Defensive actions", metric_count: 10, sample_metrics: ["defense"] },
    { category: "Aerial", isGoalkeeper: false, description: "Aerial duels", metric_count: 5, sample_metrics: ["aerial"] },
    { category: "Penalty", isGoalkeeper: false, description: "Penalty taking", metric_count: 3, sample_metrics: ["penalty"] },

    // Goalkeeper metrics
    { category: "Reflexes & Saves", isGoalkeeper: true, description: "Shot stopping ability", metric_count: 8, sample_metrics: ["reflexes_&_saves"] },
    { category: "Penalty Specialist", isGoalkeeper: true, description: "Penalty saving", metric_count: 3, sample_metrics: ["penalty_specialist"] },
    { category: "Footwork & Distribution", isGoalkeeper: true, description: "Ball distribution", metric_count: 6, sample_metrics: ["footwork_&_distribution"] },
    { category: "Air Dominance", isGoalkeeper: true, description: "Aerial ability", metric_count: 4, sample_metrics: ["air_dominance"] },
    { category: "Sweeper Play", isGoalkeeper: true, description: "Playing out from the back", metric_count: 5, sample_metrics: ["sweeper_play"] },
  ];
};

// Get metrics grouped by category
export const fetchMetricsByCategory = async (): Promise<Record<string, Metric[]>> => {
  const metrics = await fetchAllMetrics();
  const grouped: Record<string, Metric[]> = {};

  metrics.forEach(metric => {
    const category = metric.category || 'Other';
    if (!grouped[category]) {
      grouped[category] = [];
    }
    grouped[category].push(metric);
  });

  return grouped;
};

// Players API
export const fetchPlayers = async (params?: {
  q?: string;
  league?: string;
  season?: string;
  team?: string;
  offset?: number;
  limit?: number;
}): Promise<PaginatedPlayers> => {
  const searchParams = new URLSearchParams();
  if (params?.q) searchParams.append('q', params.q);
  if (params?.league) searchParams.append('league', params.league);
  if (params?.season) searchParams.append('season', params.season);
  if (params?.team) searchParams.append('team', params.team);
  if (params?.offset !== undefined) searchParams.append('offset', params.offset.toString());
  if (params?.limit !== undefined) searchParams.append('limit', params.limit.toString());

  const url = `${API_BASE_URL}/players${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch players: ${response.statusText}`);
  }

  return response.json();
};

// Get player details
export const fetchPlayerDetail = async (
  playerId: number,
  params?: {
    season?: string;
    league?: string;
  }
): Promise<PlayerDetail> => {
  const searchParams = new URLSearchParams();
  if (params?.season) searchParams.append('season', params.season);
  if (params?.league) searchParams.append('league', params.league);

  const url = `${API_BASE_URL}/players/${playerId}${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch player detail: ${response.statusText}`);
  }

  return response.json();
};

// Rankings API
export const fetchRankings = async (params: {
  metric: string;
  league?: string;
  season?: string;
  pos?: string;
  team?: string;
  nation?: string;
  min_minutes?: number;
  limit?: number;
}): Promise<RankingsResponse> => {
  const searchParams = new URLSearchParams();
  searchParams.append('metric', params.metric);
  if (params.league) searchParams.append('league', params.league);
  if (params.season) searchParams.append('season', params.season);
  if (params.pos) searchParams.append('pos', params.pos);
  if (params.team) searchParams.append('team', params.team);
  if (params.nation) searchParams.append('nation', params.nation);
  if (params.min_minutes !== undefined) searchParams.append('min_minutes', params.min_minutes.toString());
  if (params.limit !== undefined) searchParams.append('limit', params.limit.toString());

  const url = `${API_BASE_URL}/rankings?${searchParams.toString()}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch rankings: ${response.statusText}`);
  }

  return response.json();
};

// Scatter API
export const fetchScatter = async (params: {
  x: string;
  y: string;
  league?: string;
  season?: string;
  pos?: string;
  team?: string;
  nation?: string;
  min_minutes?: number;
  limit?: number;
}): Promise<ScatterResponse> => {
  const searchParams = new URLSearchParams();
  searchParams.append('x', params.x);
  searchParams.append('y', params.y);
  if (params.league) searchParams.append('league', params.league);
  if (params.season) searchParams.append('season', params.season);
  if (params.pos) searchParams.append('pos', params.pos);
  if (params.team) searchParams.append('team', params.team);
  if (params.nation) searchParams.append('nation', params.nation);
  if (params.min_minutes !== undefined) searchParams.append('min_minutes', params.min_minutes.toString());
  if (params.limit !== undefined) searchParams.append('limit', params.limit.toString());

  const url = `${API_BASE_URL}/scatter?${searchParams.toString()}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch scatter data: ${response.statusText}`);
  }

  return response.json();
};

// Teams API
export const fetchTeams = async (): Promise<string[]> => {
  const response = await fetch(`${API_BASE_URL}/teams`);

  if (!response.ok) {
    throw new Error(`Failed to fetch teams: ${response.statusText}`);
  }

  return response.json();
};

// Legacy functions that need to be implemented or removed
export const fetchLeagues = async (): Promise<string[]> => {
  // This would need to be implemented in the API or derived from teams data
  throw new Error('fetchLeagues not implemented in API yet');
};

export const fetchSeasons = async (): Promise<string[]> => {
  // This would need to be implemented in the API
  throw new Error('fetchSeasons not implemented in API yet');
};

export const fetchPositions = async (): Promise<string[]> => {
  // This would need to be implemented in the API or derived from player data
  throw new Error('fetchPositions not implemented in API yet');
};

export const fetchNations = async (): Promise<string[]> => {
  // This would need to be implemented in the API or derived from player data
  throw new Error('fetchNations not implemented in API yet');
};

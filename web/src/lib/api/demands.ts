/**
 * API client for club demands and demand matching
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

// TypeScript interfaces

export interface MatchCounts {
  suggested: number;
  proposed: number;
  interested: number;
  rejected: number;
  signed: number;
}

export interface DemandSummary {
  id: number;
  club_name: string;
  position: string[];
  status: "open" | "closed";
  priority: "low" | "medium" | "high";
  deadline: string | null;
  created_date: string;
  match_counts: MatchCounts;
}

export interface DemandDetail {
  id: number;
  club_name: string;
  club_contact_name: string | null;
  club_contact_email: string | null;
  created_date: string;
  deadline: string | null;
  status: "open" | "closed";
  priority: "low" | "medium" | "high";
  position: string[];
  age_min: number | null;
  age_max: number | null;
  nationality_preferences: string[] | null;
  budget_min: number | null;
  budget_max: number | null;
  metrics_requirements: Record<string, { min?: number; max?: number }> | null;
  playing_style_notes: string | null;
  default_season: string;
  internal_notes: string | null;
  match_counts: MatchCounts;
}

export interface PlayerInfo {
  id: number;
  name: string;
  team: string | null;
  league: string | null;
  season: string | null;
  position: string | null;
  age: number | null;
  nationality: string | null;
  image_url: string | null;
  market_value: number | null;
  key_metrics: Record<string, number>;
}

export interface DemandMatch {
  id: number;
  demand_id: number;
  player_season_id: number;
  match_score: number;
  status: "suggested" | "proposed" | "interested" | "rejected" | "signed";
  added_date: string;
  status_updated_date: string;
  notes: string | null;
  player: PlayerInfo;
}

export interface CreateDemandRequest {
  club_name: string;
  club_contact_name?: string;
  club_contact_email?: string;
  deadline?: string;
  priority?: "low" | "medium" | "high";
  position: string[];
  age_min?: number;
  age_max?: number;
  nationality_preferences?: string[];
  budget_min?: number;
  budget_max?: number;
  metrics_requirements?: Record<string, { min?: number; max?: number }>;
  playing_style_notes?: string;
  default_season: string;
  internal_notes?: string;
}

export interface UpdateDemandRequest {
  club_name?: string;
  club_contact_name?: string;
  club_contact_email?: string;
  deadline?: string;
  status?: "open" | "closed";
  priority?: "low" | "medium" | "high";
  position?: string[];
  age_min?: number;
  age_max?: number;
  nationality_preferences?: string[];
  budget_min?: number;
  budget_max?: number;
  metrics_requirements?: Record<string, { min?: number; max?: number }>;
  playing_style_notes?: string;
  default_season?: string;
  internal_notes?: string;
}

export interface UpdateMatchRequest {
  status?: "suggested" | "proposed" | "interested" | "rejected" | "signed";
  notes?: string;
}

export interface RunMatchingRequest {
  season?: string;
  limit?: number;
}

// API functions

/**
 * Create a new club demand
 */
export async function createDemand(
  data: CreateDemandRequest
): Promise<DemandDetail> {
  const response = await fetch(`${API_BASE_URL}/demands`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to create demand");
  }

  return response.json();
}

/**
 * List all demands with optional filters
 */
export async function listDemands(params?: {
  status?: "open" | "closed";
  club_name?: string;
  position?: string;
  date_from?: string;
  date_to?: string;
}): Promise<DemandSummary[]> {
  const query = new URLSearchParams();
  if (params?.status) query.append("status", params.status);
  if (params?.club_name) query.append("club_name", params.club_name);
  if (params?.position) query.append("position", params.position);
  if (params?.date_from) query.append("date_from", params.date_from);
  if (params?.date_to) query.append("date_to", params.date_to);

  const url = `${API_BASE_URL}/demands${query.toString() ? `?${query}` : ""}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error("Failed to fetch demands");
  }

  return response.json();
}

/**
 * Get demand detail
 */
export async function getDemand(demandId: number): Promise<DemandDetail> {
  const response = await fetch(`${API_BASE_URL}/demands/${demandId}`);

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("Demand not found");
    }
    throw new Error("Failed to fetch demand");
  }

  return response.json();
}

/**
 * Update a demand
 */
export async function updateDemand(
  demandId: number,
  data: UpdateDemandRequest
): Promise<DemandDetail> {
  const response = await fetch(`${API_BASE_URL}/demands/${demandId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to update demand");
  }

  return response.json();
}

/**
 * Delete a demand
 */
export async function deleteDemand(demandId: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/demands/${demandId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error("Failed to delete demand");
  }
}

/**
 * Run matching algorithm for a demand
 */
export async function runMatching(
  demandId: number,
  params?: RunMatchingRequest
): Promise<DemandMatch[]> {
  const response = await fetch(`${API_BASE_URL}/demands/${demandId}/match`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(params || {}),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to run matching");
  }

  return response.json();
}

/**
 * Get all matched players for a demand
 */
export async function getDemandMatches(
  demandId: number,
  params?: {
    status?: "suggested" | "proposed" | "interested" | "rejected" | "signed";
    sort_by?: "match_score" | "added_date";
  }
): Promise<DemandMatch[]> {
  const query = new URLSearchParams();
  if (params?.status) query.append("status", params.status);
  if (params?.sort_by) query.append("sort_by", params.sort_by);

  const url = `${API_BASE_URL}/demands/${demandId}/matches${
    query.toString() ? `?${query}` : ""
  }`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error("Failed to fetch demand matches");
  }

  return response.json();
}

/**
 * Update match status and/or notes
 */
export async function updateMatch(
  demandId: number,
  playerSeasonId: number,
  data: UpdateMatchRequest
): Promise<DemandMatch> {
  const response = await fetch(
    `${API_BASE_URL}/demands/${demandId}/matches/${playerSeasonId}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to update match");
  }

  return response.json();
}

/**
 * Propose a player to the club (shortcut to set status to proposed)
 */
export async function proposeMatch(
  demandId: number,
  playerSeasonId: number
): Promise<DemandMatch> {
  const response = await fetch(
    `${API_BASE_URL}/demands/${demandId}/matches/${playerSeasonId}/propose`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to propose match");
  }

  return response.json();
}

/**
 * Remove a player from demand matches
 */
export async function deleteMatch(
  demandId: number,
  playerSeasonId: number
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/demands/${demandId}/matches/${playerSeasonId}`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    throw new Error("Failed to delete match");
  }
}

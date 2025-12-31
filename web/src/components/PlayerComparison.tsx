"use client";

import { useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Chart as ChartJS, RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend } from 'chart.js';
import { Radar } from 'react-chartjs-2';
import { useQuery } from "@tanstack/react-query";
import { fetchSimilarPlayers, type SimilarPlayer } from "@/lib/api";
import { POSITION_MAPPING } from '@/lib/constants';
import { formatSeason } from '@/lib/utils';


ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

interface Player {
  player_id: number;
  player_name: string;
  team_name: string | null;
  position: string | null;
  x: number;
  y: number;
}

interface PlayerMetric {
  code: string;
  name: string;
  category?: string;
  value?: number;
  percentile?: number;
}

interface PlayerStats {
  player_id: number;
  player_name: string;
  team_name: string;
  position: string;
  season_label: string;
  minutes: number;
  image_url?: string;
  value_m_eur?: number | null;
  nationality?: string | null;
  birth_date?: string | null;
  metrics: PlayerMetric[];
  // Parsed metric categories - updated to match new categories
  aerial?: number;
  passing?: number;
  defense?: number;
  discipline?: number;
  finishing?: number;
  penalty?: number;
  dribbling?: number;
  // Goalkeeper categories
  penalty_specialist?: number;
  reflexes_saves?: number;
  sweeper_play?: number;
  footwork_distribution?: number;
  air_dominance?: number;
}

interface PlayerComparisonProps {
  player1: Player;
  player2: Player;
  season: string;
  league?: string;
  onClear: () => void;
  onReplacePlayer1?: (newPlayer: { player_id: number; player_name: string; team_name: string | null; league_name: string; season_label: string; position: string | null }) => void;
  onReplacePlayer2?: (newPlayer: { player_id: number; player_name: string; team_name: string | null; league_name: string; season_label: string; position: string | null }) => void;
  onSearchPlayer1?: (query: string) => void;
  onSearchPlayer2?: (query: string) => void;
  player1SearchQuery?: string;
  player2SearchQuery?: string;
  player1SearchResults?: any[];
  player2SearchResults?: any[];
  onSelectPlayer1?: (player: any) => void;
  onSelectPlayer2?: (player: any) => void;
  isSearching1?: boolean;
  isSearching2?: boolean;
}

// Use shared position mapping
const positionMapping = POSITION_MAPPING;

// Metric categories for radar chart - updated to match new categories (filtered out penalty and discipline)
const FIELD_PLAYER_CATEGORIES = [
  { key: 'aerial', label: 'Aerial' },
  { key: 'passing', label: 'Passing' },
  { key: 'defense', label: 'Defense' },
  { key: 'finishing', label: 'Finishing' },
  { key: 'dribbling', label: 'Dribbling' },
];

const GOALKEEPER_CATEGORIES = [
  { key: 'penalty_specialist', label: 'Penalty Specialist' },
  { key: 'reflexes_saves', label: 'Reflexes & Saves' },
  { key: 'sweeper_play', label: 'Sweeper Play' },
  { key: 'footwork_distribution', label: 'Footwork & Distribution' },
  { key: 'air_dominance', label: 'Air Dominance' },
];

// Parse API response metrics into component format
const parsePlayerStats = (apiResponse: any): PlayerStats => {
  const parsedStats: PlayerStats = {
    player_id: apiResponse.player_id,
    player_name: apiResponse.player_name,
    team_name: apiResponse.team_name || '',
    position: apiResponse.position || '',
    season_label: apiResponse.season_label || '',
    minutes: apiResponse.minutes || 0,
    image_url: apiResponse.image_url,
    value_m_eur: apiResponse.value_m_eur,
    nationality: apiResponse.nationality,
    birth_date: apiResponse.birth_date,
    metrics: apiResponse.metrics || [],
  };

  // Convert metrics array to direct properties
  if (apiResponse.metrics) {
    console.log(`🔍 Processing ${apiResponse.metrics.length} metrics for ${parsedStats.player_name}:`,
      apiResponse.metrics.map((m: any) => `${m.code}=${m.quantile_value ?? m.value}`).join(', '));

    for (const metric of apiResponse.metrics) {
      // Use quantile_value if available, fallback to value for backward compatibility
      const metricValue = metric.quantile_value ?? metric.value;
      if (metric.code && metricValue !== null && metricValue !== undefined) {
        console.log(`📊 Mapping metric: ${metric.code} = ${metricValue}`);
        // Map metric codes to component properties - updated for new categories
        switch (metric.code) {
          // Field player categories
          case 'aerial':
            parsedStats.aerial = metricValue;
            break;
          case 'passing':
            parsedStats.passing = metricValue;
            break;
          case 'defense':
            parsedStats.defense = metricValue;
            break;
          case 'discipline':
            parsedStats.discipline = metricValue;
            break;
          case 'finishing':
            parsedStats.finishing = metricValue;
            break;
          case 'penalty':
            parsedStats.penalty = metricValue;
            break;
          case 'dribbling':
            parsedStats.dribbling = metricValue;
            break;
          // Goalkeeper categories
          case 'penalty_specialist':
            parsedStats.penalty_specialist = metricValue;
            break;
          case 'reflexes_&_saves':
            parsedStats.reflexes_saves = metricValue;
            break;
          case 'sweeper_play':
            parsedStats.sweeper_play = metricValue;
            break;
          case 'footwork_&_distribution':
            parsedStats.footwork_distribution = metricValue;
            break;
          case 'air_dominance':
            parsedStats.air_dominance = metricValue;
            break;
        }
      }
    }
  }

  console.log(`✅ Final parsed stats for ${parsedStats.player_name}:`, {
    aerial: parsedStats.aerial,
    defense: parsedStats.defense,
    discipline: parsedStats.discipline,
    passing: parsedStats.passing,
    finishing: parsedStats.finishing,
    penalty: parsedStats.penalty,
    dribbling: parsedStats.dribbling,
  });

  return parsedStats;
};

export function PlayerComparison({
  player1,
  player2,
  season,
  league,
  onClear,
  onReplacePlayer1,
  onReplacePlayer2,
  onSearchPlayer1,
  onSearchPlayer2,
  player1SearchQuery = "",
  player2SearchQuery = "",
  player1SearchResults = [],
  player2SearchResults = [],
  onSelectPlayer1,
  onSelectPlayer2,
  isSearching1 = false,
  isSearching2 = false
}: PlayerComparisonProps) {
  const [player1Stats, setPlayer1Stats] = useState<PlayerStats | null>(null);
  const [player2Stats, setPlayer2Stats] = useState<PlayerStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);



  // Fetch player statistics
  useEffect(() => {
    const fetchPlayerStats = async () => {
      setLoading(true);
      setError(null);

      try {
        console.log('🔄 Fetching stats for players:', player1.player_name, player2.player_name);

        // Fetch both players' stats via Next.js API proxy
        const [response1, response2] = await Promise.all([
          fetch(`/api/players/${player1.player_id}?season=${season}`),
          fetch(`/api/players/${player2.player_id}?season=${season}`)
        ]);

        console.log('🔗 API URLs:',
          `/api/players/${player1.player_id}?season=${season}`,
          `/api/players/${player2.player_id}?season=${season}`
        );

        if (!response1.ok || !response2.ok) {
          throw new Error('Failed to fetch player statistics');
        }

        const rawStats1 = await response1.json();
        const rawStats2 = await response2.json();

        console.log('📊 Raw Player 1 stats:', rawStats1);
        console.log('📊 Raw Player 2 stats:', rawStats2);

        // Parse the API response into the format expected by the component
        const parsedStats1 = parsePlayerStats(rawStats1);
        const parsedStats2 = parsePlayerStats(rawStats2);

        console.log('✅ Parsed Player 1 stats:', parsedStats1);
        console.log('✅ Parsed Player 2 stats:', parsedStats2);

        setPlayer1Stats(parsedStats1);
        setPlayer2Stats(parsedStats2);
      } catch (err) {
        console.error('❌ Error fetching player stats:', err);
        setError(err instanceof Error ? err.message : 'Failed to load player statistics');
      } finally {
        setLoading(false);
      }
    };

    fetchPlayerStats();
  }, [player1.player_id, player2.player_id, season]);

  // Fetch similar players for both players
  const { data: player1Similar } = useQuery({
    queryKey: ["similar-players", player1.player_id, season],
    queryFn: () => fetchSimilarPlayers({
      playerId: player1.player_id,
      season,
      k: 5
    }),
    enabled: !!player1.player_id,
    staleTime: 1000 * 60 * 10, // 10 minutes
  });

  const { data: player2Similar } = useQuery({
    queryKey: ["similar-players", player2.player_id, season],
    queryFn: () => fetchSimilarPlayers({
      playerId: player2.player_id,
      season,
      k: 5
    }),
    enabled: !!player2.player_id,
    staleTime: 1000 * 60 * 10, // 10 minutes
  });



  // Prepare radar chart data
  const getRadarData = () => {
    if (!player1Stats || !player2Stats) return null;

    // Determine if either player is a goalkeeper
    const isKeeper1 = player1Stats.position?.includes('GK');
    const isKeeper2 = player2Stats.position?.includes('GK');
    const categories = (isKeeper1 || isKeeper2) ? GOALKEEPER_CATEGORIES : FIELD_PLAYER_CATEGORIES;

    const labels = categories.map(cat => cat.label);
    const player1Data = categories.map(cat => {
      const value = player1Stats[cat.key as keyof PlayerStats];
      // Convert negative values to 0 for radar display
      return typeof value === 'number' ? Math.max(0, value) : 0;
    });
    const player2Data = categories.map(cat => {
      const value = player2Stats[cat.key as keyof PlayerStats];
      // Convert negative values to 0 for radar display
      return typeof value === 'number' ? Math.max(0, value) : 0;
    });

    // Calculate dynamic scaling based on actual data (like Python implementation)
    const allValues = [...player1Data, ...player2Data].filter(val => val > 0);
    const minValue = Math.min(...allValues);
    const maxValue = Math.max(...allValues);

    // Dynamic scaling similar to Python radar: range from min-1 to max+1
    let dynamicMin: number;
    let dynamicMax: number;

    if (allValues.length === 0) {
      // Fallback if no valid data
      dynamicMax = 100;
      dynamicMin = 0;
    } else {
      // Always start from 0 but scale the max to show variation
      dynamicMin = 0;

      // Scale max based on data range (similar to Python: max + 1)
      if (maxValue <= 1) {
        dynamicMax = Math.ceil(maxValue * 1.2);
      } else if (maxValue <= 10) {
        dynamicMax = Math.ceil(maxValue + 1);
      } else if (maxValue <= 100) {
        dynamicMax = Math.ceil(maxValue + Math.max(1, maxValue * 0.1));
      } else {
        dynamicMax = Math.ceil(maxValue + 1);
      }

      // Ensure minimum meaningful range (allow very small ranges for precise scaling)
      if (dynamicMax - dynamicMin < 0.5) {
        dynamicMax = Math.max(0.5, maxValue + 0.1);
      }
    }

    console.log('🎯 Radar comparison scaling:', {
      player1Data,
      player2Data,
      minValue,
      maxValue,
      dynamicMin,
      dynamicMax,
      scalingRange: `${dynamicMin} to ${dynamicMax}`,
      note: 'Negative values displayed as 0'
    });

    return {
      labels,
      datasets: [
        {
          label: `${player1Stats.player_name} (${player1Stats.team_name})`,
          data: player1Data,
          borderColor: '#4d8ef7',
          backgroundColor: 'rgba(77, 142, 247, 0.2)',
          borderWidth: 2.5,
          pointRadius: 3, // Smaller, more modern points
          pointBackgroundColor: '#4d8ef7',
        },
        {
          label: `${player2Stats.player_name} (${player2Stats.team_name})`,
          data: player2Data,
          borderColor: '#ed5a5d',
          backgroundColor: 'rgba(237, 90, 93, 0.2)',
          borderWidth: 2.5,
          pointRadius: 3, // Smaller, more modern points
          pointBackgroundColor: '#ed5a5d',
        },
      ],
      dynamicMin,
      dynamicMax,
    };
  };

  const radarData = getRadarData();

  const radarOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: {
        beginAtZero: true,
        min: radarData?.dynamicMin || 0,
        max: radarData?.dynamicMax || 100,
        ticks: {
          stepSize: Math.max(0.1, Math.ceil((radarData?.dynamicMax || 100) / 5 * 10) / 10),
          font: {
            size: 10,
          },
          color: 'rgba(0, 0, 0, 0.6)',
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.1)',
        },
        angleLines: {
          color: 'rgba(0, 0, 0, 0.1)',
        },
        pointLabels: {
          font: {
            size: 12,
            weight: 'bold' as const,
          },
          color: 'rgba(0, 0, 0, 0.8)',
        },
      },
    },
    plugins: {
      legend: {
        position: 'bottom' as const,
        labels: {
          font: {
            size: 12,
          },
          padding: 20,
        },
      },
      tooltip: {
        callbacks: {
          label: function(context: any) {
            return `${context.dataset.label}: ${context.parsed.r.toFixed(1)}`;
          },
        },
      },
    },
  };

  if (loading) {
    return (
      <Card className="mt-6 border-2 border-accent/20 shadow-lg">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <span className="text-2xl">⚔️</span>
              Player Comparison
            </CardTitle>
            <Button variant="outline" size="sm" onClick={onClear}>
              Clear Comparison
            </Button>
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Loading state with same layout as full comparison */}
          <div className="grid grid-cols-2 gap-4">
            {/* Player 1 Skeleton */}
            <div className="text-center p-4 bg-blue-50 rounded-lg border border-blue-200">
              <div className="w-16 h-16 rounded-full bg-gray-300 animate-pulse mx-auto mb-3 border-2 border-blue-300"></div>
              <div className="h-4 bg-gray-300 animate-pulse rounded mb-2 mx-auto w-24"></div>
              <div className="h-3 bg-gray-300 animate-pulse rounded mx-auto w-16"></div>
            </div>
            {/* Player 2 Skeleton */}
            <div className="text-center p-4 bg-red-50 rounded-lg border border-red-200">
              <div className="w-16 h-16 rounded-full bg-gray-300 animate-pulse mx-auto mb-3 border-2 border-red-300"></div>
              <div className="h-4 bg-gray-300 animate-pulse rounded mb-2 mx-auto w-24"></div>
              <div className="h-3 bg-gray-300 animate-pulse rounded mx-auto w-16"></div>
            </div>
          </div>

          {/* Performance Radar Skeleton */}
          <div className="bg-gradient-to-r from-gray-50 to-slate-50 p-6 rounded-lg border">
            <div className="h-6 bg-gray-300 animate-pulse rounded mb-6 mx-auto w-48"></div>
            <div className="h-96 bg-gray-300 animate-pulse rounded-lg"></div>
          </div>

          {/* Stats Table Skeleton */}
          <div className="bg-gradient-to-r from-slate-50 to-gray-50 p-6 rounded-lg border">
            <div className="h-6 bg-gray-300 animate-pulse rounded mb-6 mx-auto w-32"></div>
            <div className="space-y-3">
              {[1, 2, 3, 4, 5, 6, 7].map((i) => (
                <div key={i} className="grid grid-cols-3 gap-4 items-center py-2">
                  <div className="h-4 bg-gray-300 animate-pulse rounded w-16"></div>
                  <div className="h-4 bg-gray-300 animate-pulse rounded w-12 mx-auto"></div>
                  <div className="h-4 bg-gray-300 animate-pulse rounded w-16 ml-auto"></div>
                </div>
              ))}
            </div>
          </div>

          {/* Similar Players Skeleton */}
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
              <div className="h-5 bg-gray-300 animate-pulse rounded mb-3 w-32"></div>
              <div className="space-y-2">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="flex items-center gap-3 p-2">
                    <div className="w-8 h-8 rounded-full bg-gray-300 animate-pulse"></div>
                    <div className="flex-1">
                      <div className="h-3 bg-gray-300 animate-pulse rounded mb-1 w-20"></div>
                      <div className="h-2 bg-gray-300 animate-pulse rounded w-16"></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-red-50 p-4 rounded-lg border border-red-200">
              <div className="h-5 bg-gray-300 animate-pulse rounded mb-3 w-32"></div>
              <div className="space-y-2">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="flex items-center gap-3 p-2">
                    <div className="w-8 h-8 rounded-full bg-gray-300 animate-pulse"></div>
                    <div className="flex-1">
                      <div className="h-3 bg-gray-300 animate-pulse rounded mb-1 w-20"></div>
                      <div className="h-2 bg-gray-300 animate-pulse rounded w-16"></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Loading text */}
          <div className="text-center py-4">
            <div className="flex items-center justify-center gap-2">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
              <span className="text-gray-600 text-sm">Loading player comparison...</span>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="mt-6 border-red-200">
        <CardContent className="pt-6">
          <div className="text-center py-8 text-red-600">
            <div className="mb-2">❌ {error}</div>
            <Button variant="outline" size="sm" onClick={onClear}>
              Try Again
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!player1Stats || !player2Stats) {
    return null;
  }

  return (
    <Card className="mt-6 border-2 border-accent/20 shadow-lg">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <span className="text-2xl">⚔️</span>
            Player Comparison
          </CardTitle>
          <Button variant="outline" size="sm" onClick={onClear}>
            Clear Comparison
          </Button>
        </div>


      </CardHeader>

      <CardContent className="space-y-6">
        {/* Player Info Row with Search */}
        <div className="grid grid-cols-2 gap-6">
          {/* Player 1 */}
          <div className="p-4 bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg border-2 border-blue-200 shadow-sm">
            {/* Search Bar for Player 1 */}
            <div className="mb-4 relative">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-semibold text-blue-700">🔍 Replace Player 1</span>
              </div>
              <Input
                type="text"
                placeholder={`Search in ${formatSeason(season)}${league && league !== "Aggregated (All Leagues)" ? ` - ${league}` : ""}...`}
                value={player1SearchQuery}
                onChange={(e) => onSearchPlayer1?.(e.target.value)}
                className="w-full h-9 text-sm border-blue-300 focus:border-blue-500 focus:ring-blue-500"
              />
              {isSearching1 && (
                <div className="absolute right-3 top-8">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
                </div>
              )}

              {/* Search Results Dropdown for Player 1 */}
              {player1SearchResults.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-blue-200 rounded-lg shadow-lg z-50 max-h-48 overflow-y-auto">
                  {player1SearchResults.map((player) => (
                    <div
                      key={player.player_id}
                      onClick={() => onSelectPlayer1?.(player)}
                      className="px-3 py-2 hover:bg-blue-50 cursor-pointer border-b border-blue-100 last:border-b-0 transition-colors"
                    >
                      <div className="font-medium text-sm text-primary">{player.player_name}</div>
                      <div className="text-xs text-muted-foreground flex items-center gap-2">
                        <span>{player.team_name}</span>
                        {player.position && (
                          <Badge variant="secondary" className="text-xs px-1 py-0">
                            {positionMapping[player.position] || player.position}
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Player 1 Info */}
            <div className="text-center">
              <div className="w-20 h-20 rounded-full overflow-hidden mx-auto mb-3 border-3 border-blue-400 shadow-md">
                <img
                  src={player1Stats.image_url || "https://via.placeholder.com/80x80/3b82f6/ffffff?text=👤"}
                  alt={player1Stats.player_name}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    e.currentTarget.src = "https://via.placeholder.com/80x80/3b82f6/ffffff?text=👤";
                  }}
                />
              </div>
              <h3 className="font-bold text-xl text-navy mb-1">{player1Stats.player_name}</h3>
              <p className="text-sm text-blue-700 font-medium mb-2">{player1Stats.team_name}</p>
              <div className="flex justify-center gap-1.5 flex-wrap">
                <Badge className="bg-blue-600 text-white text-xs px-2 py-1">
                  {positionMapping[player1Stats.position] || player1Stats.position}
                </Badge>
                <Badge className="bg-blue-600 text-white text-xs px-2 py-1">
                  {player1Stats.minutes}min
                </Badge>
                {(() => {
                  if (!player1Stats.birth_date) return null;
                  const birth = new Date(player1Stats.birth_date);
                  const today = new Date();
                  let age = today.getFullYear() - birth.getFullYear();
                  const monthDiff = today.getMonth() - birth.getMonth();
                  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
                    age--;
                  }
                  return age > 0 ? (
                    <Badge className="bg-blue-500 text-white text-xs px-2 py-1">
                      {age} yo
                    </Badge>
                  ) : null;
                })()}
                {player1Stats.nationality && (
                  <Badge className="bg-purple-500 text-white text-xs px-2 py-1">
                    🌍 {player1Stats.nationality}
                  </Badge>
                )}
                {player1Stats.value_m_eur !== null && player1Stats.value_m_eur !== undefined && player1Stats.value_m_eur > 0 && (
                  <Badge className="bg-emerald-500 text-white text-xs px-2 py-1 font-semibold">
                    💰 €{player1Stats.value_m_eur.toFixed(1)}M
                  </Badge>
                )}
              </div>
            </div>
          </div>

          {/* Player 2 */}
          <div className="p-4 bg-gradient-to-br from-red-50 to-red-100 rounded-lg border-2 border-red-200 shadow-sm">
            {/* Search Bar for Player 2 */}
            <div className="mb-4 relative">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-semibold text-red-700">🔍 Replace Player 2</span>
              </div>
              <Input
                type="text"
                placeholder={`Search in ${formatSeason(season)}${league && league !== "Aggregated (All Leagues)" ? ` - ${league}` : ""}...`}
                value={player2SearchQuery}
                onChange={(e) => onSearchPlayer2?.(e.target.value)}
                className="w-full h-9 text-sm border-red-300 focus:border-red-500 focus:ring-red-500"
              />
              {isSearching2 && (
                <div className="absolute right-3 top-8">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-red-500"></div>
                </div>
              )}

              {/* Search Results Dropdown for Player 2 */}
              {player2SearchResults.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-red-200 rounded-lg shadow-lg z-50 max-h-48 overflow-y-auto">
                  {player2SearchResults.map((player) => (
                    <div
                      key={player.player_id}
                      onClick={() => onSelectPlayer2?.(player)}
                      className="px-3 py-2 hover:bg-red-50 cursor-pointer border-b border-red-100 last:border-b-0 transition-colors"
                    >
                      <div className="font-medium text-sm text-primary">{player.player_name}</div>
                      <div className="text-xs text-muted-foreground flex items-center gap-2">
                        <span>{player.team_name}</span>
                        {player.position && (
                          <Badge variant="secondary" className="text-xs px-1 py-0">
                            {positionMapping[player.position] || player.position}
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Player 2 Info */}
            <div className="text-center">
              <div className="w-20 h-20 rounded-full overflow-hidden mx-auto mb-3 border-3 border-red-400 shadow-md">
                <img
                  src={player2Stats.image_url || "https://via.placeholder.com/80x80/ed5a5d/ffffff?text=👤"}
                  alt={player2Stats.player_name}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    e.currentTarget.src = "https://via.placeholder.com/80x80/ed5a5d/ffffff?text=👤";
                  }}
                />
              </div>
              <h3 className="font-bold text-xl text-navy mb-1">{player2Stats.player_name}</h3>
              <p className="text-sm text-red-700 font-medium mb-2">{player2Stats.team_name}</p>
              <div className="flex justify-center gap-1.5 flex-wrap">
                <Badge className="bg-red-600 text-white text-xs px-2 py-1">
                  {positionMapping[player2Stats.position] || player2Stats.position}
                </Badge>
                <Badge className="bg-red-600 text-white text-xs px-2 py-1">
                  {player2Stats.minutes}min
                </Badge>
                {(() => {
                  if (!player2Stats.birth_date) return null;
                  const birth = new Date(player2Stats.birth_date);
                  const today = new Date();
                  let age = today.getFullYear() - birth.getFullYear();
                  const monthDiff = today.getMonth() - birth.getMonth();
                  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
                    age--;
                  }
                  return age > 0 ? (
                    <Badge className="bg-red-500 text-white text-xs px-2 py-1">
                      {age} yo
                    </Badge>
                  ) : null;
                })()}
                {player2Stats.nationality && (
                  <Badge className="bg-purple-500 text-white text-xs px-2 py-1">
                    🌍 {player2Stats.nationality}
                  </Badge>
                )}
                {player2Stats.value_m_eur !== null && player2Stats.value_m_eur !== undefined && player2Stats.value_m_eur > 0 && (
                  <Badge className="bg-emerald-500 text-white text-xs px-2 py-1 font-semibold">
                    💰 €{player2Stats.value_m_eur.toFixed(1)}M
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Statistics Comparison Table - VS Style */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-semibold mb-4 text-center">📊 Key Statistics Comparison</h4>

          {/* Header Row */}
          <div className="grid grid-cols-3 gap-4 mb-3 text-sm">
            <div className="font-bold text-center text-blue-600 bg-blue-50 py-2 rounded-lg border border-blue-200">
              {player1Stats.player_name.split(' ')[0]}
            </div>
            <div className="font-bold text-center text-gray-700 bg-white py-2 rounded-lg border border-gray-300 shadow-sm">
              Metric
            </div>
            <div className="font-bold text-center text-red-600 bg-red-50 py-2 rounded-lg border border-red-200">
              {player2Stats.player_name.split(' ')[0]}
            </div>
          </div>

          {/* Stats Rows - VS Format */}
          <div className="space-y-2">
            {(player1Stats.position?.includes('GK') || player2Stats.position?.includes('GK') ? GOALKEEPER_CATEGORIES : FIELD_PLAYER_CATEGORIES).map(({ key, label }) => {
              const player1Value = player1Stats[key as keyof PlayerStats];
              const player2Value = player2Stats[key as keyof PlayerStats];
              const player1Val = typeof player1Value === 'number' ? player1Value : 0;
              const player2Val = typeof player2Value === 'number' ? player2Value : 0;
              const player1Better = player1Val > player2Val;

              return (
                <div key={key} className="grid grid-cols-3 gap-4 items-center text-sm">
                  {/* Player 1 Value */}
                  <div className={`text-center py-2 px-3 rounded-lg font-bold transition-all duration-200 ${
                    player1Better
                      ? "bg-blue-100 border-2 border-blue-300 text-blue-800 shadow-sm scale-105"
                      : "bg-blue-50 border border-blue-200 text-blue-700"
                  }`}>
                    {player1Val.toFixed(1)}
                  </div>

                  {/* Metric Name - Centered */}
                  <div className="text-center py-2 px-3 font-medium text-gray-700 bg-white rounded-lg border border-gray-200 shadow-sm">
                    {label}
                  </div>

                  {/* Player 2 Value */}
                  <div className={`text-center py-2 px-3 rounded-lg font-bold transition-all duration-200 ${
                    !player1Better
                      ? "bg-red-100 border-2 border-red-300 text-red-800 shadow-sm scale-105"
                      : "bg-red-50 border border-red-200 text-red-700"
                  }`}>
                    {player2Val.toFixed(1)}
                  </div>
                </div>
              );
            })}
          </div>

          {/* VS Indicator */}
          <div className="flex items-center justify-center mt-4 pt-3 border-t border-gray-200">
            <div className="bg-gradient-to-r from-blue-500 via-gray-400 to-red-500 text-white px-4 py-1 rounded-full text-sm font-bold shadow-md">
              VS
            </div>
          </div>
        </div>

        {/* Radar Chart */}
        <div className="bg-white rounded-lg border p-4">
          <h4 className="font-semibold mb-4 text-center">📈 Performance Radar</h4>
          <div className="h-96">
            {radarData && (
              <Radar data={radarData} options={radarOptions} />
            )}
          </div>
        </div>

        {/* Similar Players Section */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Player 1 Similar Players */}
          <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
            <h4 className="font-semibold mb-3 text-blue-800 flex items-center gap-2">
              <span>🔍</span>
              Similar to {player1Stats?.player_name?.split(' ')[0]}
            </h4>
            {player1Similar?.similar_players ? (
              <div className="space-y-2">
                {player1Similar.similar_players.map((similarPlayer: SimilarPlayer, index: number) => (
                  <div key={`player1-${similarPlayer.player_id}`} className="flex items-center gap-3 p-2 bg-white rounded border border-blue-100 hover:border-blue-300 transition-colors">
                    <div className="w-8 h-8 rounded-full overflow-hidden border border-blue-200">
                      <img
                        src={similarPlayer.image_url || "https://via.placeholder.com/32x32/3b82f6/ffffff?text=👤"}
                        alt={similarPlayer.player_name}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          e.currentTarget.src = "https://via.placeholder.com/32x32/3b82f6/ffffff?text=👤";
                        }}
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm text-blue-900 truncate">
                        {similarPlayer.player_name}
                      </div>
                      <div className="text-xs text-blue-600 truncate">
                        {similarPlayer.team_name}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="text-right">
                        <div className="text-sm font-bold text-blue-700">
                          {Math.round(similarPlayer.similarity_score * 100)}%
                        </div>
                        <div className="text-xs text-blue-500">
                          #{index + 1}
                        </div>
                      </div>
                      <div className="flex flex-col gap-1">
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-6 px-2 text-xs bg-blue-500 text-white border-blue-500 hover:bg-blue-600 hover:border-blue-600"
                          onClick={(e) => {
                            e.stopPropagation();
                            onReplacePlayer1?.({
                              player_id: similarPlayer.player_id,
                              player_name: similarPlayer.player_name,
                              team_name: similarPlayer.team_name,
                              league_name: similarPlayer.league_name || "Aggregated (All Leagues)",
                              season_label: season,
                              position: similarPlayer.position
                            });
                          }}
                        >
                          vs {player2Stats?.player_name?.split(' ')[0] || 'Player 2'}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-6 px-2 text-xs bg-red-500 text-white border-red-500 hover:bg-red-600 hover:border-red-600"
                          onClick={(e) => {
                            e.stopPropagation();
                            onReplacePlayer2?.({
                              player_id: similarPlayer.player_id,
                              player_name: similarPlayer.player_name,
                              team_name: similarPlayer.team_name,
                              league_name: similarPlayer.league_name || "Aggregated (All Leagues)",
                              season_label: season,
                              position: similarPlayer.position
                            });
                          }}
                        >
                          vs {player1Stats?.player_name?.split(' ')[0] || 'Player 1'}
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-4 text-blue-600 text-sm">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto mb-2"></div>
                Loading similar players...
              </div>
            )}
          </div>

          {/* Player 2 Similar Players */}
          <div className="bg-red-50 p-4 rounded-lg border border-red-200">
            <h4 className="font-semibold mb-3 text-red-800 flex items-center gap-2">
              <span>🔍</span>
              Similar to {player2Stats?.player_name?.split(' ')[0]}
            </h4>
            {player2Similar?.similar_players ? (
              <div className="space-y-2">
                {player2Similar.similar_players.map((similarPlayer: SimilarPlayer, index: number) => (
                  <div key={`player2-${similarPlayer.player_id}`} className="flex items-center gap-3 p-2 bg-white rounded border border-red-100 hover:border-red-300 transition-colors">
                    <div className="w-8 h-8 rounded-full overflow-hidden border border-red-200">
                      <img
                        src={similarPlayer.image_url || "https://via.placeholder.com/32x32/ed5a5d/ffffff?text=👤"}
                        alt={similarPlayer.player_name}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          e.currentTarget.src = "https://via.placeholder.com/32x32/ed5a5d/ffffff?text=👤";
                        }}
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm text-red-900 truncate">
                        {similarPlayer.player_name}
                      </div>
                      <div className="text-xs text-red-600 truncate">
                        {similarPlayer.team_name}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="text-right">
                        <div className="text-sm font-bold text-red-700">
                          {Math.round(similarPlayer.similarity_score * 100)}%
                        </div>
                        <div className="text-xs text-red-500">
                          #{index + 1}
                        </div>
                      </div>
                      <div className="flex flex-col gap-1">
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-6 px-2 text-xs bg-blue-500 text-white border-blue-500 hover:bg-blue-600 hover:border-blue-600"
                          onClick={(e) => {
                            e.stopPropagation();
                            onReplacePlayer1?.({
                              player_id: similarPlayer.player_id,
                              player_name: similarPlayer.player_name,
                              team_name: similarPlayer.team_name,
                              league_name: similarPlayer.league_name || "Aggregated (All Leagues)",
                              season_label: season,
                              position: similarPlayer.position
                            });
                          }}
                        >
                          vs {player2Stats?.player_name?.split(' ')[0] || 'Player 2'}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-6 px-2 text-xs bg-red-500 text-white border-red-500 hover:bg-red-600 hover:border-red-600"
                          onClick={(e) => {
                            e.stopPropagation();
                            onReplacePlayer2?.({
                              player_id: similarPlayer.player_id,
                              player_name: similarPlayer.player_name,
                              team_name: similarPlayer.team_name,
                              league_name: similarPlayer.league_name || "Aggregated (All Leagues)",
                              season_label: season,
                              position: similarPlayer.position
                            });
                          }}
                        >
                          vs {player1Stats?.player_name?.split(' ')[0] || 'Player 1'}
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-4 text-red-600 text-sm">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-red-500 mx-auto mb-2"></div>
                Loading similar players...
              </div>
            )}
          </div>
        </div>

      </CardContent>
    </Card>
  );
}

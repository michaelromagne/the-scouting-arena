"use client";

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter, notFound } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { fetchPlayer, PlayerDetail, PlayerMetric, fetchPlayerLeagues, fetchSimilarPlayers, fetchSeasons } from "@/lib/api";
import { PlayerRadarChart } from "@/components/PlayerRadarChart";
import { POSITION_MAPPING, DEFAULT_FILTERS } from "@/lib/constants";
import { formatSeason } from "@/lib/utils";
import { Info } from "lucide-react";

// Simple tooltip component
function Tooltip({ children, content }: { children: React.ReactNode; content: string }) {
  return (
    <div className="group relative">
      {children}
      <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-10 max-w-xs text-center">
        {content}
        <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
      </div>
    </div>
  );
}

// Modern spinner component with visible blue rotating animation
function ModernSpinner() {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="spinner-loading rounded-full h-12 w-12 border-4 border-gray-200 border-t-blue-500"></div>
      <div className="mt-4 text-slate-600 font-medium animate-pulse">
        Analyzing similarity patterns...
      </div>
      <div className="text-sm text-slate-400 mt-1">
        Comparing across 1000+ performance metrics
      </div>
    </div>
  );
}

// Helper function to get quantile text from percentile
function getQuantileText(percentile: number | null): string {
  if (percentile === null || percentile === 0) return "";

  const rounded = Math.round(percentile);
  const topPercentage = Math.max(1, 100 - rounded);

  if (rounded >= 90) return `Elite (Top ${topPercentage}%)`;
  if (rounded >= 75) return `Excellent (Top ${topPercentage}%)`;
  if (rounded >= 50) return `Good (Top ${topPercentage}%)`;
  if (rounded >= 25) return `Below Average (Top ${topPercentage}%)`;
  return `Poor (Top ${topPercentage}%)`;
}

// Helper function to get the main category scores with quantiles
// Returns different categories based on player position (field player vs goalkeeper)
function getCategoryScores(metrics: PlayerMetric[], position: string | null) {
  // Goalkeeper categories (codes match database: lowercase with underscores)
  const goalkeeperCategories = [
    { name: "Reflexes & Saves", code: "reflexes_&_saves", emoji: "🧤", description: "Shot-stopping quality and handling" },
    { name: "Air Dominance", code: "air_dominance", emoji: "✈️", description: "Command of high balls and the box" },
    { name: "Sweeper Play", code: "sweeper_play", emoji: "🏃‍♂️", description: "Proactive interventions off the line" },
    { name: "Footwork & Distribution", code: "footwork_&_distribution", emoji: "🦶", description: "Quality of footwork and distribution" },
    { name: "Penalty Specialist", code: "penalty_specialist", emoji: "🎯", description: "Reading and stopping penalties" }
  ];

  // Field player categories
  const fieldPlayerCategories = [
    { name: "Finishing", code: "finishing", emoji: "⚽", description: "Goal threat and shot efficiency" },
    { name: "Passing", code: "passing", emoji: "🎯", description: "Creating chances for teammates through passing" },
    { name: "Dribbling", code: "dribbling", emoji: "🏃", description: "Dribbling and carrying that advances play" },
    { name: "Defense", code: "defense", emoji: "🛡️", description: "Ball winning and preventing danger" },
    { name: "Aerial", code: "aerial", emoji: "🦅", description: "Effectiveness in the air" }
  ];

  // Determine if player is a goalkeeper
  const isGoalkeeper = position?.toUpperCase() === "GK" || position?.toLowerCase() === "goalkeeper";
  const categories = isGoalkeeper ? goalkeeperCategories : fieldPlayerCategories;

  return categories.map(category => {
    // Look for the category score metric (e.g., "finishing", "reflexes_&_saves")
    const categoryScoreMetric = metrics.find(m =>
      m.code.toLowerCase() === category.code.toLowerCase()
    );

    // Look for the quantile metric (e.g., "quantile_category_scores_finishing", "quantile_category_scores_reflexes_&_saves")
    const quantileMetric = metrics.find(m =>
      m.code.toLowerCase() === `quantile_category_scores_${category.code.toLowerCase()}`
    );

    // The category score value (actual score like 6.00)
    const scoreValue = categoryScoreMetric?.quantile_value || 0;

    // The quantile/percentile (0-100, where 90 = top 10%)
    const percentileValue = quantileMetric?.quantile_value || 0;

    return {
      ...category,
      value: scoreValue,
      percentile: percentileValue,
      metric: categoryScoreMetric || quantileMetric,
      hasQuantile: !!quantileMetric
    };
  }).filter(cat => cat.metric); // Only include categories that have data
}

interface PlayerHeaderProps {
  player: PlayerDetail;
}

// Helper function to get top per_90 metrics that have quantile values
function getTopPerNinetyMetricsWithQuantiles(metrics: PlayerMetric[]): Array<PlayerMetric & { displayName: string; description: string; quantileValue: number | null; category: string }> {
  const foundMetrics: Array<PlayerMetric & { displayName: string; description: string; quantileValue: number | null; category: string }> = [];

  // Key metrics to highlight (most important per_90 stats based on available data)
  const keyMetrics = [
    { code: "ast_per_90", category: "Attacking", name: "Assists per 90", description: "Assists provided per 90 minutes of play" },
    { code: "1_per_3_per_90", category: "Playmaking", name: "Final Third Passes per 90", description: "Passes into final third per 90 minutes" },
    { code: "aerial_duels_won_per_90", category: "Physical", name: "Aerial Duels Won per 90", description: "Aerial duels won per 90 minutes of play" },
    { code: "aerial_duels_wonpct_per_90", category: "Physical", name: "Aerial Duel Win % per 90", description: "Percentage of aerial duels won per 90 minutes" },
    { code: "blocks_sh_per_90", category: "Defending", name: "Shot Blocks per 90", description: "Opponent shots blocked per 90 minutes of play" },
    { code: "carries_carries_per_90", category: "Possession", name: "Ball Carries per 90", description: "Times the player carried the ball per 90 minutes" },
    { code: "carries_1_per_3_per_90", category: "Possession", name: "Carries into Final Third per 90", description: "Ball carries into final third per 90 minutes" },
    { code: "carries_cpa_per_90", category: "Possession", name: "Carries into Penalty Area per 90", description: "Ball carries into penalty area per 90 minutes" },
    { code: "crdy_per_90", category: "Discipline", name: "Yellow Cards per 90", description: "Yellow cards received per 90 minutes of play" },
    { code: "fld_per_90", category: "Physical", name: "Fouls Drawn per 90", description: "Fouls drawn per 90 minutes of play" },
    { code: "fls_per_90", category: "Discipline", name: "Fouls Committed per 90", description: "Fouls committed per 90 minutes of play" },
    { code: "recov_per_90", category: "Defending", name: "Ball Recoveries per 90", description: "Ball recoveries made per 90 minutes of play" }
  ];

  // Find metrics that match our key codes and have quantile values
  for (const keyMetric of keyMetrics) {
    const metric = metrics.find(m =>
      m.code.toLowerCase() === keyMetric.code.toLowerCase()
    );

    if (metric && metric.quantile_value !== null) {
      // Look for corresponding quantile metric
      const quantileMetric = metrics.find(m =>
        m.code.toLowerCase() === `quantile_league_${metric.code.toLowerCase()}`
      );

      // Only include if quantile exists
      if (quantileMetric) {
        foundMetrics.push({
          ...metric,
          displayName: keyMetric.name,
          description: keyMetric.description,
          category: keyMetric.category,
          quantileValue: quantileMetric.quantile_value
        });
      }
    }
  }

  // Sort by quantile value (best performers first)
  return foundMetrics.sort((a, b) => (b.quantileValue || 0) - (a.quantileValue || 0));
}

function PlayerHeader({ player }: PlayerHeaderProps) {
  const {
    player_name,
    team_name,
    league_name,
    season_label,
    position,
    minutes,
    value_m_eur,
    nationality,
    birth_date,
  } = player;

  // Use shared position mapping
  const positionMapping = POSITION_MAPPING;

  // Calculate age from birth_date
  const calculateAge = (birthDate: string | null): number | null => {
    if (!birthDate) return null;
    const today = new Date();
    const birth = new Date(birthDate);
    let age = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
      age--;
    }
    return age;
  };

  const age = calculateAge(birth_date);

  return (
    <div className="bg-navy text-white py-12">
      <div className="container mx-auto px-4">
        <div className="space-y-8">
          {/* Player Basic Info */}
          <div className="flex flex-col md:flex-row md:justify-between md:items-start gap-6">
            <div className="flex items-center gap-6">
              {/* Player Photo */}
              <div className="w-24 h-24 md:w-32 md:h-32 rounded-full overflow-hidden border-4 border-white/20 shadow-xl">
                <img
                  src={player.image_url || "https://via.placeholder.com/128x128/0B1B3F/ffffff?text=👤"}
                  alt={player_name}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    // Fallback to letter avatar if image fails to load
                    const target = e.target as HTMLImageElement;
                    target.style.display = 'none';
                    const fallback = target.nextElementSibling as HTMLElement;
                    if (fallback) fallback.style.display = 'flex';
                  }}
                />
                {/* Fallback letter avatar */}
                <div className="w-full h-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center text-white text-4xl font-bold" style={{ display: 'none' }}>
                  {player_name.charAt(0).toUpperCase()}
                </div>
              </div>

              <div className="flex-1">
                <h1 className="text-3xl md:text-4xl font-bold mb-2 text-white">
                  {player_name}
                </h1>
                <div className="flex flex-wrap items-center gap-3">
                  {season_label && (
                    <Badge className="bg-orange-500 hover:bg-orange-600 text-white">
                      Season {formatSeason(season_label)}
                    </Badge>
                  )}
                  {value_m_eur !== null && (
                    <Badge className="bg-green-500 hover:bg-green-600 text-white font-semibold">
                      €{value_m_eur.toFixed(1)}M
                    </Badge>
                  )}
                </div>
              </div>
            </div>

            {/* Fixed grid layout to prevent shifting */}
            <div className="grid grid-cols-2 md:grid-cols-6 gap-6">
              {/* Team - always show, use placeholder if empty */}
              <div className="space-y-2">
                <span className="text-blue-200 text-sm font-semibold uppercase tracking-wider">Team</span>
                <div className="text-white font-medium text-base min-h-[1.5rem]">
                  {team_name || "—"}
                </div>
              </div>

              {/* League - always show, use placeholder if empty */}
              <div className="space-y-2">
                <span className="text-blue-200 text-sm font-semibold uppercase tracking-wider">League</span>
                <div className="text-white font-medium text-base min-h-[1.5rem]">
                  {league_name || "—"}
                </div>
              </div>

              {/* Position - always show, use placeholder if empty */}
              <div className="space-y-2">
                <span className="text-blue-200 text-sm font-semibold uppercase tracking-wider">Position</span>
                <div className="text-white font-medium text-base min-h-[1.5rem]">
                  {position ? (positionMapping[position] || position) : "—"}
                </div>
              </div>

              {/* Age - always show, use placeholder if empty */}
              <div className="space-y-2">
                <span className="text-blue-200 text-sm font-semibold uppercase tracking-wider">Age</span>
                <div className="text-white font-medium text-base min-h-[1.5rem]">
                  {age !== null ? `${age} years` : "—"}
                </div>
              </div>

              {/* Nationality - always show, use placeholder if empty */}
              <div className="space-y-2">
                <span className="text-blue-200 text-sm font-semibold uppercase tracking-wider">Nationality</span>
                <div className="text-white font-medium text-base min-h-[1.5rem]">
                  {nationality || "—"}
                </div>
              </div>

              {/* Market Value - always show, use placeholder if empty */}
              <div className="space-y-2">
                <span className="text-blue-200 text-sm font-semibold uppercase tracking-wider">💰 Value</span>
                <div className="text-green-300 font-bold text-base min-h-[1.5rem]">
                  {value_m_eur !== null ? `€${value_m_eur.toFixed(1)}M` : "—"}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function PlayerProfilePage() {
  const params = useParams();
  const router = useRouter();
  const playerId = parseInt(params.id as string);

  // State for league and season selectors - start with undefined to let API return player's actual data
  const [selectedLeague, setSelectedLeague] = useState<string | undefined>(undefined);
  const [selectedSeason, setSelectedSeason] = useState<string | undefined>(undefined);
  const [hasTriedFallback, setHasTriedFallback] = useState(false);
  const [showFallbackNotice, setShowFallbackNotice] = useState(false);

  if (isNaN(playerId)) {
    notFound();
  }

  // Fetch available seasons
  const { data: seasons = [] } = useQuery({
    queryKey: ["seasons"],
    queryFn: fetchSeasons,
    staleTime: 1000 * 60 * 10, // 10 minutes
    retry: 1,
  });

  // Fetch leagues where this player has played
  const { data: leagues = [] } = useQuery({
    queryKey: ["playerLeagues", playerId],
    queryFn: () => fetchPlayerLeagues(playerId),
    staleTime: 1000 * 60 * 10, // 10 minutes
    retry: 1,
  });

  const { data: player, isLoading, error, refetch } = useQuery({
    queryKey: ["player", playerId, selectedSeason, selectedLeague],
    queryFn: () => fetchPlayer(playerId, selectedSeason, selectedLeague),
    staleTime: 1000 * 60 * 5, // 5 minutes
    retry: false, // Don't retry - we'll handle fallback manually
  });

  // Handle 404 errors by falling back to "Aggregated (All Leagues)"
  // This happens when a player transferred leagues and the selected league doesn't match the season
  useEffect(() => {
    console.log('🔍 Fallback check:', {
      hasError: !!error,
      hasTriedFallback,
      selectedLeague,
      isAggregated: selectedLeague === "Aggregated (All Leagues)"
    });

    if (error && !hasTriedFallback) {
      // Only fallback if we're not already on "Aggregated (All Leagues)"
      if (selectedLeague && selectedLeague !== "Aggregated (All Leagues)") {
        console.log(`⚠️ Player not found in ${selectedLeague} for season ${selectedSeason}, falling back to Aggregated (All Leagues)`);

        setSelectedLeague("Aggregated (All Leagues)");
        setHasTriedFallback(true);
        setShowFallbackNotice(true);

        // Hide notice after 5 seconds
        setTimeout(() => setShowFallbackNotice(false), 5000);
      } else if (!selectedLeague) {
        // If no league is selected yet, set it to aggregated
        console.log(`⚠️ Player not found with no league selected, setting to Aggregated (All Leagues)`);
        setSelectedLeague("Aggregated (All Leagues)");
        setHasTriedFallback(true);
      }
    }
  }, [error, hasTriedFallback, selectedLeague, selectedSeason]);

  // Reset fallback flag when season or league changes successfully
  useEffect(() => {
    if (player && hasTriedFallback) {
      setHasTriedFallback(false);
    }
  }, [player, hasTriedFallback]);

  // Once player data loads, set the actual league and season if not already set
  if (player && !selectedLeague && !selectedSeason) {
    if (player.league_name) setSelectedLeague(player.league_name);
    if (player.season_label) setSelectedSeason(player.season_label);
  }

  // Fetch similar players - pass selected season for proper matching
  const { data: similarPlayers, isLoading: similarLoading } = useQuery({
    queryKey: ["similarPlayers", playerId, selectedSeason, selectedLeague],
    queryFn: () => fetchSimilarPlayers({ playerId, season: selectedSeason, league: selectedLeague, k: 9 }),
    enabled: !!player, // Only run after player data is loaded
    staleTime: 1000 * 60 * 10, // 10 minutes (more stable)
    retry: 1,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-pulse text-lg text-navy">Loading player...</div>
        </div>
      </div>
    );
  }

  // Only show error if we've already tried the fallback
  if (error && hasTriedFallback) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-navy mb-4">Player Not Found</h1>
          <p className="text-gray-600 mb-4">
            The player you&apos;re looking for doesn&apos;t exist or isn&apos;t available for the selected season.
          </p>
          <Button onClick={() => router.back()} className="bg-navy hover:bg-navy/90">
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  if (!player) {
    notFound();
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Player Header */}
      <PlayerHeader player={player} />

      {/* Fallback Notice Banner */}
      {showFallbackNotice && (
        <div className="bg-orange-50 border-l-4 border-orange-400 p-4">
          <div className="container mx-auto px-4">
            <div className="flex items-center gap-3 max-w-6xl mx-auto">
              <Info className="w-5 h-5 text-orange-600 flex-shrink-0" />
              <p className="text-sm text-orange-800">
                Player data not found in the selected league for this season. Showing aggregated data across all leagues instead.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Season & League Selector Section */}
      <div className="bg-white py-8 border-b">
        <div className="container mx-auto px-4">
          <div className="max-w-6xl mx-auto">
            {/* Season and League Selectors */}
            <div className="mb-8">
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6">
                {/* Season Selector */}
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-gray-700">Season:</span>
                  <Select
                    value={selectedSeason}
                    onValueChange={(newSeason) => {
                      setSelectedSeason(newSeason);
                      setHasTriedFallback(false); // Reset fallback when season changes
                    }}
                  >
                    <SelectTrigger className="w-32">
                      <SelectValue placeholder="Select season" />
                    </SelectTrigger>
                    <SelectContent>
                      {seasons.map((season) => (
                        <SelectItem key={season} value={season}>
                          {formatSeason(season)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* League Selector */}
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-gray-700">League:</span>
                  <Select
                    value={selectedLeague}
                    onValueChange={(newLeague) => {
                      setSelectedLeague(newLeague);
                      setHasTriedFallback(false); // Reset fallback when league changes manually
                      setShowFallbackNotice(false); // Hide notice when user manually changes league
                    }}
                  >
                    <SelectTrigger className="w-64">
                      <SelectValue placeholder="Select league" />
                    </SelectTrigger>
                    <SelectContent>
                      {leagues.map((league) => (
                        <SelectItem key={league} value={league}>
                          {league}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="text-sm text-gray-500">
                  <span className="font-medium">Tip:</span> Switch seasons to see historical data
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Performance Overview Section - Separated from header */}
      <div className="bg-white py-12">
        <div className="container mx-auto px-4">
          <div className="bg-navy rounded-xl p-8 shadow-lg max-w-7xl mx-auto">
            <div className="text-center mb-8">
              <h3 className="text-2xl font-bold text-white mb-2">Performance Overview</h3>
              <p className="text-blue-200">Key metrics with season quantile rankings and overall performance profile</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
              {/* Category Scores - Left Side */}
              <div>
                <h4 className="text-xl font-bold text-white mb-6 text-center">Performance Categories</h4>
                <div className="grid grid-cols-2 gap-4">
                  {getCategoryScores(player.metrics, player.position).map((category) => {
                    // Performance level classification based on percentile
                    const isElite = category.percentile >= 90;
                    const isExcellent = category.percentile >= 75;
                    const isGood = category.percentile >= 50;
                    const isBelowAverage = category.percentile >= 25;

                    // Get performance level text
                    const getPerformanceLevel = () => {
                      if (isElite) return 'Elite';
                      if (isExcellent) return 'Excellent';
                      if (isGood) return 'Good';
                      if (isBelowAverage) return 'Below Average';
                      return 'Poor';
                    };

                    // Get colors based on performance
                    const getColors = () => {
                      if (isElite) return {
                        bg: 'bg-emerald-500/20',
                        text: 'text-emerald-300',
                        bar: 'bg-gradient-to-r from-emerald-400 to-emerald-500',
                        badge: 'bg-emerald-500/30 text-emerald-200'
                      };
                      if (isExcellent) return {
                        bg: 'bg-green-500/20',
                        text: 'text-green-300',
                        bar: 'bg-gradient-to-r from-green-400 to-green-500',
                        badge: 'bg-green-500/30 text-green-200'
                      };
                      if (isGood) return {
                        bg: 'bg-blue-500/20',
                        text: 'text-blue-300',
                        bar: 'bg-gradient-to-r from-blue-400 to-blue-500',
                        badge: 'bg-blue-500/30 text-blue-200'
                      };
                      if (isBelowAverage) return {
                        bg: 'bg-yellow-500/20',
                        text: 'text-yellow-300',
                        bar: 'bg-gradient-to-r from-yellow-400 to-yellow-500',
                        badge: 'bg-yellow-500/30 text-yellow-200'
                      };
                      return {
                        bg: 'bg-orange-500/20',
                        text: 'text-orange-300',
                        bar: 'bg-gradient-to-r from-orange-400 to-orange-500',
                        badge: 'bg-orange-500/30 text-orange-200'
                      };
                    };

                    const colors = getColors();
                    const quantileText = getQuantileText(category.percentile);

                    return (
                      <Tooltip key={category.code} content={category.description}>
                        <div className="group hover:scale-105 transition-all duration-300 cursor-help">
                          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4 h-full border border-white/10 hover:border-white/20">
                            {/* Category Header */}
                            <div className="flex justify-between items-center mb-3">
                              <div className="text-sm text-white font-semibold flex items-center gap-2">
                                <span className="text-lg">{category.emoji}</span>
                                <span>{category.name}</span>
                              </div>
                              <div className={`text-xs font-medium px-2 py-1 rounded-full ${colors.badge}`}>
                                {quantileText || `${category.percentile.toFixed(0)}th`}
                              </div>
                            </div>

                            {/* Main Score */}
                            <div className={`text-xl md:text-2xl font-bold mb-2 ${colors.text}`}>
                              {category.value?.toFixed(2) || "N/A"}
                            </div>

                            {/* Performance Level */}
                            <div className="text-xs text-white/80 font-medium mb-2">
                              {getPerformanceLevel()} ({category.percentile.toFixed(0)}th percentile)
                            </div>

                            {/* Quantile Bar */}
                            <div className="w-full bg-white/10 rounded-full h-3 mb-2">
                              <div
                                className={`h-3 rounded-full transition-all duration-700 shadow-sm ${colors.bar}`}
                                style={{ width: `${Math.max(3, category.percentile)}%` }}
                              />
                            </div>

                            {/* Quantile indicators */}
                            <div className="flex justify-between text-xs text-white/60">
                              <span>0th</span>
                              <span>100th</span>
                            </div>
                          </div>
                        </div>
                      </Tooltip>
                    );
                  })}
                </div>
              </div>

              {/* Radar Chart - Right Side */}
              <div className="flex flex-col h-full">
                <h4 className="text-xl font-bold text-white mb-6 text-center">Performance Radar</h4>
                <div className="bg-white/5 backdrop-blur-sm rounded-lg p-6 border border-white/10 flex-1 flex flex-col justify-center">
                  <div style={{ height: '400px' }}>
                    <PlayerRadarChart
                      playerId={playerId}
                      season={selectedSeason}
                      league={selectedLeague}
                    />
                  </div>

                  {/* Arena Challenge Button */}
                  <div className="mt-6 text-center">
                    <Button
                      size="lg"
                      className="bg-orange text-white hover:bg-orange/90 font-bold px-6 py-3 shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105"
                      onClick={() => router.push(`/?player=${encodeURIComponent(player.player_name)}&playerId=${player.player_id}#arena-section`)}
                    >
                      ⚔️ Face {player.player_name.split(' ')[0]} in the Arena!
                    </Button>
                    <p className="text-white/70 text-xs mt-2">
                      Challenge this player head-to-head with interactive comparisons
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Similar Players Section - Moved up for prominence */}
      <div className="bg-white py-12">
        <div className="container mx-auto px-4">
          <div className="max-w-6xl mx-auto">
            <Card className="shadow-lg border-0 bg-gradient-to-r from-blue-50 to-indigo-50">
              <CardHeader className="text-center pb-8">
                <CardTitle className="text-slate-900 text-2xl flex items-center justify-center gap-3">
                  <div className="w-2 h-8 bg-blue-500 rounded-full"></div>
                  Similar Players
                  <div className="w-2 h-8 bg-blue-500 rounded-full"></div>
                </CardTitle>
                <CardDescription className="text-slate-600 text-lg mt-2">
                  Discover players with similar performance profiles and playing styles
                </CardDescription>
              </CardHeader>
              <CardContent>
                {similarLoading ? (
                  <ModernSpinner />
                ) : similarPlayers?.similar_players?.length ? (
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {similarPlayers.similar_players.map((similar) => (
                      <div
                        key={similar.player_id}
                        className="bg-white rounded-lg border border-gray-100 p-4 hover:shadow-md transition-all duration-200 cursor-pointer group"
                        onClick={() => window.location.href = `/talent-pool/${similar.player_id}`}
                      >
                        <div className="flex justify-between items-start mb-3">
                          <div className="flex-1">
                            <h4 className="font-semibold text-slate-900 group-hover:text-blue-600 transition-colors">
                              {similar.player_name}
                            </h4>
                            <div className="text-sm text-slate-500 space-y-1">
                              {similar.team_name && (
                                <div>{similar.team_name}</div>
                              )}
                              <div className="flex flex-wrap gap-1 mt-1">
                                {similar.position && (
                                  <Badge variant="outline" className="text-xs">
                                    {similar.position}
                                  </Badge>
                                )}
                                {(() => {
                                  if (!similar.birth_date) return null;
                                  const birth = new Date(similar.birth_date);
                                  const today = new Date();
                                  let age = today.getFullYear() - birth.getFullYear();
                                  const monthDiff = today.getMonth() - birth.getMonth();
                                  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
                                    age--;
                                  }
                                  return age > 0 ? (
                                    <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-500">
                                      {age} yo
                                    </Badge>
                                  ) : null;
                                })()}
                                {similar.nationality && (
                                  <Badge variant="outline" className="text-xs bg-purple-50 text-purple-700 border-purple-500">
                                    🌍 {similar.nationality}
                                  </Badge>
                                )}
                                {similar.value_m_eur !== null && similar.value_m_eur !== undefined && similar.value_m_eur > 0 && (
                                  <Badge variant="outline" className="text-xs bg-emerald-50 text-emerald-700 border-emerald-600 font-semibold">
                                    💰 €{similar.value_m_eur.toFixed(1)}M
                                  </Badge>
                                )}
                              </div>
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="text-sm font-semibold text-green-600">
                              {(similar.similarity_score * 100).toFixed(1)}%
                            </div>
                            <div className="text-xs text-slate-400">similarity</div>
                          </div>
                        </div>
                        <div className="w-full bg-gray-100 rounded-full h-2">
                          <div
                            className="bg-gradient-to-r from-green-400 to-green-500 h-2 rounded-full transition-all duration-500"
                            style={{ width: `${similar.similarity_score * 100}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <div className="mb-6">
                      <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6-4h6m2 5.291A7.962 7.962 0 0112 15c-2.34 0-4.47-.881-6.08-2.33" />
                        </svg>
                      </div>
                      <p className="text-slate-600">
                        No similar players found with the current criteria.
                      </p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

    </div>
  );
}

"use client";

import { useState, useRef, useLayoutEffect, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Podium } from "@/components/Podium";
import { InlineFeedback } from "@/components/InlineFeedback";
import { fetchLeagues, fetchSeasons, fetchPositions, fetchTeams, fetchNations, fetchPlayerRank } from "@/lib/api";
import { fetchMetricCategories, type MetricCategory } from "@/lib/api-client";
import { POSITION_MAPPING, DEFAULT_FILTERS, getCountryName, getPositionDisplayName } from "@/lib/constants";
import { formatSeason } from "@/lib/utils";

// Search Result Display Component
function SearchResultDisplay({
  playerId,
  selectedMetric,
  categoryToMetricCode,
  selectedLeague,
  selectedSeason,
  selectedTeam,
  selectedNation,
  selectedPosition,
  minMinutes,
  minValue,
  maxValue,
  minAge,
  maxAge,
  onViewProfile,
}: {
  playerId?: number;
  selectedMetric: string;
  categoryToMetricCode: Record<string, string>;
  selectedLeague: string;
  selectedSeason: string;
  selectedTeam: string;
  selectedNation: string;
  selectedPosition: string;
  minMinutes: string;
  minValue: string;
  maxValue: string;
  minAge: string;
  maxAge: string;
  onViewProfile: (playerId: number) => void;
}) {
  // Fetch full player details to get all category scores
  const { data: playerDetail, isLoading: isLoadingDetail } = useQuery({
    queryKey: ["player-detail", playerId, selectedLeague, selectedSeason],
    queryFn: async () => {
      if (!playerId) return null;
      try {
        const response = await fetch(`/api/players/${playerId}?season=${selectedSeason}&league=${selectedLeague}`);
        if (!response.ok) return null;
        return await response.json();
      } catch (error) {
        console.error("Error fetching player detail:", error);
        return null;
      }
    },
    enabled: !!playerId,
    staleTime: 1000 * 60 * 5,
  });

  // Fetch ranks for all categories
  const categoryCodesForRanks = playerDetail?.position === "GK"
    ? ["reflexes_&_saves", "penalty_specialist", "footwork_&_distribution", "air_dominance", "sweeper_play"]
    : ["finishing", "passing", "dribbling", "defense", "aerial", "penalty"];

  const { data: allCategoryRanks, isLoading: isLoadingRanks } = useQuery({
    queryKey: ["all-category-ranks", playerId, selectedLeague, selectedSeason, playerDetail?.position, selectedTeam, selectedNation, selectedPosition, minMinutes, minValue, maxValue, minAge, maxAge],
    queryFn: async () => {
      if (!playerId || !playerDetail) return null;

      try {
        // Fetch ranks for all categories in parallel
        const rankPromises = categoryCodesForRanks.map(async (metricCode) => {
          try {
            const rank = await fetchPlayerRank({
              playerId,
              metric: metricCode,
              league: selectedLeague,
              season: selectedSeason,
              pos: selectedPosition !== "All Positions" ? selectedPosition : undefined,
              team: selectedTeam !== "All Teams" ? selectedTeam : undefined,
              nation: selectedNation !== "All Nations" ? selectedNation : undefined,
              min_minutes: parseInt(minMinutes) || 0,
              min_value: minValue ? parseFloat(minValue) : undefined,
              max_value: maxValue ? parseFloat(maxValue) : undefined,
              min_age: minAge ? parseInt(minAge) : undefined,
              max_age: maxAge ? parseInt(maxAge) : undefined,
            });
            return { metricCode, rank };
          } catch (error) {
            console.error(`Error fetching rank for ${metricCode}:`, error);
            return { metricCode, rank: null };
          }
        });

        const results = await Promise.all(rankPromises);

        // Convert to a map for easy lookup
        const ranksMap: Record<string, any> = {};
        results.forEach(({ metricCode, rank }) => {
          if (rank) ranksMap[metricCode] = rank;
        });

        return ranksMap;
      } catch (error) {
        console.error("Error fetching category ranks:", error);
        return null;
      }
    },
    enabled: !!playerId && !!playerDetail,
    staleTime: 1000 * 60 * 5,
  });

  const isLoading = isLoadingDetail || isLoadingRanks;

  if (!playerId) return null;

  if (isLoading) {
    return (
      <div className="py-6 text-center">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-green"></div>
        <p className="mt-2 text-sm text-gray-600">Loading player data...</p>
      </div>
    );
  }

  if (!playerDetail || !allCategoryRanks) {
    return (
      <div className="py-4 px-4 bg-yellow-50 border border-yellow-300 rounded-lg">
        <p className="text-sm text-gray-700 text-center">
          Player not found in current rankings. Try adjusting filters or selecting a different metric.
        </p>
      </div>
    );
  }

  // Get the rank info for the selected metric to determine overall tier
  const selectedMetricCode = categoryToMetricCode[selectedMetric] || selectedMetric;
  const selectedMetricRank = allCategoryRanks[selectedMetricCode];

  const age = playerDetail.birth_date
    ? new Date().getFullYear() - new Date(playerDetail.birth_date).getFullYear()
    : null;

  const percentile = selectedMetricRank?.quantile_value || 0;
  const isTopTier = percentile >= 90;
  const isHighTier = percentile >= 75 && percentile < 90;
  const isMidTier = percentile >= 50 && percentile < 75;

  // Extract category scores from player metrics
  const isGoalkeeper = playerDetail.position === "GK";
  const categoryMetrics = playerDetail.metrics.filter((m: any) =>
    m.code.startsWith("quantile_category_scores_")
  );

  // Define category order and icons
  const fieldPlayerCategories = [
    { code: "finishing", label: "Finishing", icon: "⚽" },
    { code: "passing", label: "Passing", icon: "🎨" },
    { code: "dribbling", label: "Dribbling", icon: "⚡" },
    { code: "defense", label: "Defense", icon: "🛡️" },
    { code: "aerial", label: "Aerial", icon: "🦅" },
    { code: "penalty", label: "Penalty", icon: "🎯" },
  ];

  const goalkeeperCategories = [
    { code: "reflexes_&_saves", label: "Reflexes & Saves", icon: "🧤" },
    { code: "penalty_specialist", label: "Penalty Specialist", icon: "🥅" },
    { code: "footwork_&_distribution", label: "Footwork & Distribution", icon: "👟" },
    { code: "air_dominance", label: "Air Dominance", icon: "🪂" },
    { code: "sweeper_play", label: "Sweeper Play", icon: "🏃" },
  ];

  const categories = isGoalkeeper ? goalkeeperCategories : fieldPlayerCategories;

  // Map metrics to categories
  const categoryScores = categories.map(cat => {
    const metric = categoryMetrics.find((m: any) =>
      m.code === `quantile_category_scores_${cat.code}`
    );
    return {
      ...cat,
      value: metric?.quantile_value ?? null,
    };
  }).filter(cat => cat.value !== null);

  return (
    <div className={`p-4 rounded-lg border-2 ${
      isTopTier ? "border-green bg-green/5" :
      isHighTier ? "border-blue-400 bg-blue-50" :
      isMidTier ? "border-orange bg-orange/5" :
      "border-gray-300 bg-gray-50"
    }`}>
      <div className="mb-3">
        <h4 className="text-sm font-semibold text-gray-700">📊 Player Ranking Result</h4>
      </div>
      <div className="flex items-center gap-4">
          {/* Player Image */}
          <div className="flex-shrink-0">
            {playerDetail.image_url ? (
              <img
                src={playerDetail.image_url}
                alt={playerDetail.player_name}
                className="w-20 h-20 rounded-full object-cover border-4 border-green shadow-md"
              />
            ) : (
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-green to-blue-400 flex items-center justify-center text-white font-bold text-2xl border-4 border-green shadow-md">
                {playerDetail.player_name.charAt(0)}
              </div>
            )}
          </div>

          {/* Player Info */}
          <div className="flex-1">
            <h3 className="text-xl font-bold text-gray-900 mb-1">
              {playerDetail.player_name}
            </h3>

            <div className="flex flex-wrap gap-2 text-sm text-gray-600 mb-2">
              {playerDetail.team_name && (
                <span className="font-medium">{playerDetail.team_name}</span>
              )}
              {playerDetail.team_name && playerDetail.league_name && <span>•</span>}
              {playerDetail.league_name && (
                <span>{playerDetail.league_name}</span>
              )}
            </div>

            <div className="flex flex-wrap gap-2 mb-3">
              {age && age > 0 && (
                <Badge variant="outline" className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 border-blue-500">
                  {age} years old
                </Badge>
              )}
              {playerDetail.nationality && (
                <Badge variant="outline" className="text-xs px-2 py-0.5 bg-purple-50 text-purple-700 border-purple-500">
                  🌍 {getCountryName(playerDetail.nationality)}
                </Badge>
              )}
              {playerDetail.value_m_eur !== null && playerDetail.value_m_eur !== undefined && playerDetail.value_m_eur > 0 && (
                <Badge variant="outline" className="text-xs px-2 py-0.5 bg-emerald-50 text-emerald-700 border-emerald-600 font-semibold">
                  💰 €{playerDetail.value_m_eur.toFixed(1)}M
                </Badge>
              )}
            </div>

            {/* All Category Scores */}
            <div className="space-y-2">

              {/* Compact grid of all category scores */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {categoryScores.map((cat) => {
                  const catPercentile = cat.value || 0;
                  const catRank = allCategoryRanks[cat.code];
                  const isElite = catPercentile >= 90;
                  const isHigh = catPercentile >= 75 && catPercentile < 90;
                  const isMid = catPercentile >= 50 && catPercentile < 75;

                  return (
                    <div
                      key={cat.code}
                      className={`p-2 rounded-lg border ${
                        isElite ? "border-green bg-green/5" :
                        isHigh ? "border-blue-400 bg-blue-50" :
                        isMid ? "border-orange bg-orange/5" :
                        "border-gray-300 bg-gray-50"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium text-gray-700 flex items-center gap-1">
                          <span>{cat.icon}</span>
                          <span className="truncate">{cat.label}</span>
                        </span>
                        {catRank ? (
                          <Badge className={`${
                            isElite ? "bg-green text-navy" :
                            isHigh ? "bg-blue-500 text-white" :
                            isMid ? "bg-orange text-white" :
                            "bg-gray-500 text-white"
                          } font-bold px-1.5 py-0 text-xs whitespace-nowrap`}>
                            #{catRank.rank} / {catRank.total.toLocaleString()}
                          </Badge>
                        ) : (
                          <span className="text-xs text-gray-400">N/A</span>
                        )}
                      </div>
                      {/* Mini progress bar */}
                      <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${
                            isElite ? "bg-green" :
                            isHigh ? "bg-blue-500" :
                            isMid ? "bg-orange" :
                            "bg-gray-400"
                          }`}
                          style={{ width: `${catPercentile}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* View Profile Button */}
            <Button
              onClick={() => onViewProfile(playerId)}
              className="mt-3 w-full bg-navy text-white hover:bg-navy/90"
              size="sm"
            >
              View Full Profile →
            </Button>
          </div>
        </div>
    </div>
  );
}

export default function Home() {
  const router = useRouter();

  // --- Rankings Section State ---
  const anchorRef = useRef<HTMLDivElement>(null);
  const preTopRef = useRef<number | null>(null);

  const snapshotAnchor = () => {
    const el = anchorRef.current;
    if (el) preTopRef.current = el.getBoundingClientRect().top;
  };

  const restoreToAnchor = () => {
    const el = anchorRef.current;
    if (!el || preTopRef.current === null) return;
    const after = el.getBoundingClientRect().top;
    const delta = after - preTopRef.current;
    if (delta !== 0) window.scrollBy(0, delta);
    preTopRef.current = null;
  };

  // Use position mapping from shared constants
  const positionMapping = POSITION_MAPPING;

  // Rankings filters
  const [selectedMetric, setSelectedMetric] = useState("finishing");
  const [selectedLeague, setSelectedLeague] = useState(DEFAULT_FILTERS.league);
  const [selectedSeason, setSelectedSeason] = useState(DEFAULT_FILTERS.season);
  const [selectedTeam, setSelectedTeam] = useState(DEFAULT_FILTERS.team);
  const [selectedNation, setSelectedNation] = useState(DEFAULT_FILTERS.nation);
  const [selectedPosition, setSelectedPosition] = useState(DEFAULT_FILTERS.position);
  const [minMinutes, setMinMinutes] = useState(DEFAULT_FILTERS.minMinutes);
  const [minValue, setMinValue] = useState("");
  const [maxValue, setMaxValue] = useState("");
  const [minAge, setMinAge] = useState("");
  const [maxAge, setMaxAge] = useState("");

  // Set initial filter visibility based on screen size (only on mount, not on resize/scroll)
  const [showFilters, setShowFilters] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth >= 600;
    }
    return true;
  });

  // Player search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [showSearchResults, setShowSearchResults] = useState(false);

  // Rankings display limit
  const [rankingsLimit, setRankingsLimit] = useState(20);

  // Map category names to metric codes for API calls
  const categoryToMetricCode: Record<string, string> = {
    "finishing": "finishing",
    "penalty": "penalty",
    "passing": "passing",
    "defense": "defense",
    "discipline": "discipline",
    "dribbling": "dribbling",
    "aerial": "aerial",
    "reflexes & saves": "reflexes_&_saves",
    "penalty specialist": "penalty_specialist",
    "footwork & distribution": "footwork_&_distribution",
    "air dominance": "air_dominance",
    "sweeper play": "sweeper_play",
    "shooting": "finishing",
    "goalkeeping": "reflexes_&_saves",
    "possession": "dribbling",
    "misc": "aerial"
  };

  // Available metric categories - fetch dynamically from API
  const { data: availableMetricCategories = [] } = useQuery<MetricCategory[]>({
    queryKey: ["metric-categories"],
    queryFn: fetchMetricCategories,
    staleTime: 1000 * 60 * 10, // 10 minutes - categories don't change often
  });

  // Data fetching
  const { data: leagues = [] } = useQuery({
    queryKey: ["leagues"],
    queryFn: fetchLeagues,
  });

  const { data: seasons = [] } = useQuery({
    queryKey: ["seasons"],
    queryFn: fetchSeasons,
  });

  const { data: positions = [] } = useQuery({
    queryKey: ["positions"],
    queryFn: fetchPositions,
  });

  const { data: teams = [] } = useQuery({
    queryKey: ["teams"],
    queryFn: fetchTeams,
  });

  const { data: nations = [] } = useQuery({
    queryKey: ["nations"],
    queryFn: fetchNations,
  });

  // Team filtering logic
  const uniqueTeams = Array.from(new Set(
    teams.flatMap(team =>
      team.split(' & ').map(t => t.trim())
    )
  )).sort();

  // Rankings restore after filter changes
  useLayoutEffect(() => {
    restoreToAnchor();
  }, [selectedMetric, selectedLeague, selectedSeason, selectedTeam, selectedNation, selectedPosition, minMinutes, minValue, maxValue, minAge, maxAge]);

  // Reset rankings limit when filters change
  useLayoutEffect(() => {
    setRankingsLimit(20);
  }, [selectedMetric, selectedLeague, selectedSeason, selectedTeam, selectedNation, selectedPosition, minMinutes, minValue, maxValue, minAge, maxAge]);

  // Player search functionality
  const handleSearchChange = async (query: string) => {
    setSearchQuery(query);

    if (query.length < 2) {
      setSearchResults([]);
      setShowSearchResults(false);
      return;
    }

    try {
      const params = new URLSearchParams({
        q: query,
        league: selectedLeague,
        season: selectedSeason,
        limit: "10",
      });

      const response = await fetch(`/api/players?${params.toString()}`);
      if (!response.ok) throw new Error("Failed to search players");

      const data = await response.json();
      setSearchResults(data.items || []);
      setShowSearchResults(true);
    } catch (error) {
      console.error("Search error:", error);
      setSearchResults([]);
    }
  };

  // Fetch rankings data (always fetch 50, display based on rankingsLimit)
  const {
    data: rankingsData,
    isLoading: isLoadingRankings,
    error: rankingsError,
  } = useQuery({
    queryKey: [
      "rankings",
      selectedMetric,
      selectedLeague,
      selectedSeason,
      selectedTeam,
      selectedNation,
      selectedPosition,
      minMinutes,
      minValue,
      maxValue,
      minAge,
      maxAge,
    ],
    queryFn: async () => {
      const params = new URLSearchParams({
        metric: categoryToMetricCode[selectedMetric] || selectedMetric,
        league: selectedLeague,
        season: selectedSeason,
        limit: "50", // Always fetch 50 players
        min_minutes: minMinutes,
      });

      if (selectedTeam !== "All Teams") params.append("team", selectedTeam);
      if (selectedNation !== "All Nations") params.append("nation", selectedNation);
      if (selectedPosition !== "All Positions") params.append("pos", selectedPosition);
      if (minValue) params.append("min_value", minValue);
      if (maxValue) params.append("max_value", maxValue);
      if (minAge) params.append("min_age", minAge);
      if (maxAge) params.append("max_age", maxAge);

      const response = await fetch(`/api/rankings?${params.toString()}`);
      if (!response.ok) throw new Error("Failed to fetch rankings");
      const data = await response.json();
      // API returns { metric, direction, total, items: [...] }
      return data.items || [];
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <section className="bg-navy text-white py-12 relative">
        <div className="container mx-auto px-4">
          <div className="text-center px-4">
            <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold mb-4 text-white">
              The Scouting Arena <span className="text-green">Dashboard</span>
            </h1>
          <p className="text-base sm:text-lg text-gray-200 max-w-2xl mx-auto mb-6 px-4">
            Advanced analytics across <strong>5,000+ players</strong> from top leagues
          </p>

          {/* Platform Stats */}
          <div className="grid grid-cols-3 gap-4 sm:gap-8 mb-8 text-center max-w-2xl mx-auto px-4">
            <div>
              <div className="text-xl sm:text-2xl font-bold text-green mb-1">5,000+</div>
              <div className="text-gray-300 text-xs sm:text-sm">Active Players</div>
            </div>
            <div>
              <div className="text-xl sm:text-2xl font-bold text-orange mb-1">12</div>
              <div className="text-gray-300 text-xs sm:text-sm">Leagues</div>
            </div>
            <div>
              <div className="text-xl sm:text-2xl font-bold text-blue-400 mb-1">24/7</div>
              <div className="text-gray-300 text-xs sm:text-sm">Real-time Updates</div>
            </div>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-3 gap-2 sm:gap-3 max-w-4xl mx-auto px-2 sm:px-4">
            <Button
              onClick={() => {
                const element = document.getElementById('rankings-section');
                if (element) {
                  const offsetTop = element.offsetTop - 60; // Account for navbar height
                  window.scrollTo({ top: offsetTop, behavior: 'smooth' });
                }
              }}
              size="lg"
              className="bg-green text-navy hover:bg-green/90 font-semibold px-2 sm:px-4 py-3 text-xs sm:text-base w-full"
            >
              Player Rankings
            </Button>
            <Button
              asChild
              size="lg"
              className="bg-orange text-white hover:bg-orange/90 font-semibold px-2 sm:px-4 py-3 text-xs sm:text-base w-full"
            >
              <Link href="/face-to-face">Face-to-Face</Link>
            </Button>
            <Button
              asChild
              size="lg"
              className="bg-gradient-to-r from-emerald-600 to-teal-600 text-white hover:from-emerald-600/90 hover:to-teal-600/90 font-semibold px-2 sm:px-4 py-3 text-xs sm:text-base w-full"
            >
              <Link href="/similarity-search">Similarity</Link>
            </Button>
            <Button
              asChild
              size="lg"
              className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-600/90 hover:to-indigo-600/90 font-semibold px-2 sm:px-4 py-3 text-xs sm:text-base w-full"
            >
              <Link href="/team-analysis">Team Analysis</Link>
            </Button>
            <Button
              asChild
              size="lg"
              className="bg-gradient-to-r from-slate-600 to-cyan-600 text-white hover:from-slate-600/90 hover:to-cyan-600/90 font-semibold px-2 sm:px-4 py-3 text-xs sm:text-base w-full"
            >
              <Link href="/team-rankings">Team Rankings</Link>
            </Button>
            <Button
              asChild
              size="lg"
              className="bg-gradient-to-r from-purple-600 to-pink-600 text-white hover:from-purple-600/90 hover:to-pink-600/90 font-semibold px-2 sm:px-4 py-3 text-xs sm:text-base w-full"
            >
              <Link href="/national-teams">National Teams</Link>
            </Button>
          </div>
          </div>
        </div>
      </section>

      {/* Rankings Section */}
      <section id="rankings-section" className="py-12 bg-white">
        <div className="container mx-auto px-4 max-w-6xl">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold text-navy mb-4">Player Rankings</h2>
            <p className="text-xl text-gray-600">Find the top performers across different metrics and leagues</p>
          </div>

          {/* Rankings Filters */}
          <Card className="mb-6 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <CardTitle className="text-sm">🔎 Rankings filters</CardTitle>
                  {!showFilters && (selectedLeague !== DEFAULT_FILTERS.league || selectedSeason !== DEFAULT_FILTERS.season || selectedTeam !== DEFAULT_FILTERS.team || selectedNation !== "All Nations" || selectedPosition !== "All Positions" || minMinutes !== "0" || minValue || maxValue || minAge || maxAge) && (
                    <Badge variant="secondary" className="text-xs px-2 py-0">
                      Active
                    </Badge>
                  )}
                </div>
                <CardDescription className="text-xs">
                  {showFilters ? "Customize your ranking view" : "Click 'Show Filters' to customize"}
                </CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowFilters(!showFilters)}
                  className="px-3 h-8 text-xs whitespace-nowrap"
                >
                  {showFilters ? "🔼 Hide" : "🔽 Show"}
                </Button>
                {(selectedLeague !== DEFAULT_FILTERS.league || selectedSeason !== DEFAULT_FILTERS.season || selectedTeam !== DEFAULT_FILTERS.team || selectedNation !== "All Nations" || selectedPosition !== "All Positions" || minMinutes !== "0" || minValue || maxValue || minAge || maxAge) && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      snapshotAnchor();
                      setSelectedMetric("finishing");
                      setSelectedLeague(DEFAULT_FILTERS.league);
                      setSelectedSeason(DEFAULT_FILTERS.season);
                      setSelectedTeam(DEFAULT_FILTERS.team);
                      setSelectedNation("All Nations");
                      setSelectedPosition("All Positions");
                      setMinMinutes("0");
                      setMinValue("");
                      setMaxValue("");
                      setMinAge("");
                      setMaxAge("");
                    }}
                    className="px-3 h-8 text-xs whitespace-nowrap"
                  >
                    🔄 Reset
                  </Button>
                )}
              </div>
            </CardHeader>
            {showFilters && (
              <CardContent className="pt-0 pb-4">
              {/* First row: Main filters */}
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-3">
                {/* League Filter */}
                <div className="space-y-1.5">
                  <div className="flex items-center gap-1">
                    <span className="text-sm">🏆</span>
                    <label className="text-xs font-medium text-primary">League</label>
                  </div>
                  <Select
                    value={selectedLeague}
                    onValueChange={(value) => {
                      snapshotAnchor();
                      setSelectedLeague(value);
                    }}
                  >
                    <SelectTrigger className="w-full h-8 text-xs bg-white text-gray-900 border-gray-300 hover:border-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                      <SelectValue placeholder="Select league" />
                    </SelectTrigger>
                    <SelectContent>
                      {leagues.map((league) => (
                        <SelectItem key={league} value={league}>
                          {league.replace("Aggregated (All Leagues)", "All Leagues")}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Season Filter */}
                <div className="space-y-1.5">
                  <div className="flex items-center gap-1">
                    <span className="text-sm">📅</span>
                    <label className="text-xs font-medium text-primary">Season</label>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {seasons.map((season) => (
                      <Badge
                        key={season}
                        variant={selectedSeason === season ? "default" : "outline"}
                        className={`cursor-pointer px-2 py-0.5 text-xs transition-all duration-200 ${
                          selectedSeason === season
                            ? "bg-navy text-white"
                            : "hover:bg-navy hover:text-white"
                        }`}
                        onClick={() => {
                          snapshotAnchor();
                          setSelectedSeason(season);
                        }}
                      >
                        {formatSeason(season)}
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* Team Filter */}
                <div className="space-y-1.5">
                  <div className="flex items-center gap-1">
                    <span className="text-sm">🏟️</span>
                    <label className="text-xs font-medium text-primary">Team</label>
                  </div>
                  <div className="space-y-1">
                    <Select
                      value={selectedTeam}
                      onValueChange={(value) => {
                        snapshotAnchor();
                        setSelectedTeam(value);
                      }}
                    >
                      <SelectTrigger className="w-full h-8 text-xs bg-white text-gray-900 border-gray-300 hover:border-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                        <SelectValue placeholder="Select team..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="All Teams" className="text-xs">
                          All Teams
                        </SelectItem>
                        {uniqueTeams.map((team) => (
                          <SelectItem key={team} value={team} className="text-xs">
                            {team}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Nation Filter */}
                <div className="space-y-1.5">
                  <div className="flex items-center gap-1">
                    <span className="text-sm">🌍</span>
                    <label className="text-xs font-medium text-primary">Nation</label>
                  </div>
                  <div>
                    <Select
                      value={selectedNation}
                      onValueChange={(value) => {
                        snapshotAnchor();
                        setSelectedNation(value);
                      }}
                    >
                      <SelectTrigger className="w-full h-8 text-xs bg-white text-gray-900 border-gray-300 hover:border-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                        <SelectValue placeholder="Select nation" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="All Nations">All Nations</SelectItem>
                        {nations.filter((nation) => nation !== "0").map((nation) => (
                          <SelectItem key={nation} value={nation}>
                            {getCountryName(nation)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Market Value Filter */}
                <div className="space-y-1.5">
                  <div className="flex items-center gap-1">
                    <span className="text-sm">💰</span>
                    <label className="text-xs font-medium text-primary">Market Value (M€)</label>
                  </div>
                  <div className="space-y-1" suppressHydrationWarning>
                    <Input
                      type="number"
                      value={minValue}
                      onChange={(e) => {
                        snapshotAnchor();
                        setMinValue(e.target.value);
                      }}
                      placeholder="Min"
                      className="w-full h-8 text-xs"
                      suppressHydrationWarning
                    />
                    <Input
                      type="number"
                      value={maxValue}
                      onChange={(e) => {
                        snapshotAnchor();
                        setMaxValue(e.target.value);
                      }}
                      placeholder="Max"
                      className="w-full h-8 text-xs"
                      suppressHydrationWarning
                    />
                  </div>
                </div>

                {/* Age Filter */}
                <div className="space-y-1.5">
                  <div className="flex items-center gap-1">
                    <span className="text-sm">🎂</span>
                    <label className="text-xs font-medium text-primary">Age</label>
                  </div>
                  <div className="space-y-1">
                    <Input
                      type="number"
                      value={minAge}
                      onChange={(e) => {
                        snapshotAnchor();
                        setMinAge(e.target.value);
                      }}
                      placeholder="Min"
                      min="15"
                      max="50"
                      className="w-full h-8 text-xs"
                    />
                    <Input
                      type="number"
                      value={maxAge}
                      onChange={(e) => {
                        snapshotAnchor();
                        setMaxAge(e.target.value);
                      }}
                      placeholder="Max"
                      min="15"
                      max="50"
                      className="w-full h-8 text-xs"
                    />
                  </div>
                </div>
              </div>

              {/* Second row: Position Filter */}
              <div className="space-y-1.5">
                <div className="flex items-center gap-1">
                  <span className="text-sm">🎯</span>
                  <label className="text-xs font-medium text-primary">Position</label>
                </div>
                <div className="flex flex-wrap gap-1">
                  <Badge
                    variant={selectedPosition === "All Positions" ? "default" : "outline"}
                    className={`cursor-pointer px-2 py-0.5 text-xs transition-all duration-200 ${
                      selectedPosition === "All Positions"
                        ? "bg-navy text-white"
                        : "hover:bg-navy hover:text-white"
                    }`}
                    onClick={() => {
                      snapshotAnchor();
                      setSelectedPosition("All Positions");
                    }}
                  >
                    All
                  </Badge>
                  {positions.slice(0, 4).map((position) => (
                    <Badge
                      key={position}
                      variant={selectedPosition === position ? "default" : "outline"}
                      className={`cursor-pointer px-2 py-0.5 text-xs transition-all duration-200 ${
                        selectedPosition === position
                          ? "bg-navy text-white"
                          : "hover:bg-navy hover:text-white"
                      }`}
                      onClick={() => {
                        snapshotAnchor();
                        setSelectedPosition(position);
                      }}
                    >
                      {positionMapping[position] || position}
                    </Badge>
                  ))}
                </div>
              </div>
            </CardContent>
            )}
          </Card>

          {/* Metric Selector */}
          <Card className="bg-gradient-to-r from-slate-50 to-white border border-slate-200 mb-6">
            <CardContent className="pt-4 pb-3">
              {/* Field Player Metrics */}
              <div className="mb-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-sm font-semibold text-primary">⚽ Field Players</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {availableMetricCategories.filter(c => !c.isGoalkeeper && c.category !== "Discipline").map((category) => (
                    <button
                      key={category.category}
                      type="button"
                      onMouseDown={snapshotAnchor}
                      onClick={() => setSelectedMetric(category.category.toLowerCase())}
                      className={`
                        px-3 py-2 md:px-4 md:py-2 rounded-lg font-medium text-xs md:text-sm transition-all duration-200 transform hover:scale-105 hover:shadow-md
                        ${
                          selectedMetric === category.category.toLowerCase()
                            ? "bg-gradient-to-r from-accent to-green-400 text-white shadow-md scale-105 ring-1 ring-accent ring-opacity-50"
                            : "bg-white text-primary border border-slate-200 hover:border-accent hover:bg-accent hover:text-white hover:shadow-sm"
                        }
                      `}
                    >
                      <div className="flex items-center gap-1">
                        <span className="text-sm md:text-base">
                          {category.category === "Finishing" && "⚽"}
                          {category.category === "Dribbling" && "⚡"}
                          {category.category === "Passing" && "🎨"}
                          {category.category === "Defense" && "🛡️"}
                          {category.category === "Aerial" && "🦅"}
                          {category.category === "Penalty" && "🎯"}
                        </span>
                        <span className="hidden sm:inline">{category.category}</span>
                        <span className="sm:hidden">{category.category.split(" ")[0]}</span>
                        {selectedMetric === category.category.toLowerCase() && <span className="ml-0.5 text-xs">✨</span>}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Goalkeeper Metrics */}
              <div className="pt-4 border-t border-slate-200">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-sm font-semibold text-primary">🧤 Goalkeepers</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {availableMetricCategories.filter(c => c.isGoalkeeper).map((category) => (
                    <button
                      key={category.category}
                      type="button"
                      onMouseDown={snapshotAnchor}
                      onClick={() => setSelectedMetric(category.category.toLowerCase())}
                      className={`
                        px-3 py-2 md:px-4 md:py-2 rounded-lg font-medium text-xs md:text-sm transition-all duration-200 transform hover:scale-105 hover:shadow-md
                        ${
                          selectedMetric === category.category.toLowerCase()
                            ? "bg-gradient-to-r from-accent to-green-400 text-white shadow-md scale-105 ring-1 ring-accent ring-opacity-50"
                            : "bg-white text-primary border border-slate-200 hover:border-accent hover:bg-accent hover:text-white hover:shadow-sm"
                        }
                      `}
                    >
                      <div className="flex items-center gap-1">
                        <span className="text-sm md:text-base">
                          {category.category === "Penalty Specialist" && "🥅"}
                          {category.category === "Reflexes & Saves" && "🧤"}
                          {category.category === "Sweeper Play" && "🏃"}
                          {category.category === "Footwork & Distribution" && "👟"}
                          {category.category === "Air Dominance" && "🪂"}
                        </span>
                        <span className="hidden sm:inline">{category.category}</span>
                        <span className="sm:hidden">{category.category.split(" ")[0]}</span>
                        {selectedMetric === category.category.toLowerCase() && <span className="ml-0.5 text-xs">✨</span>}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>


          {/* Player Search */}
          <Card className="mb-6 shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">🔍 Search Player</CardTitle>
              <CardDescription className="text-xs">
                Search for a specific player to see their ranking on {selectedMetric}
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-0 pb-4">
              <div className="relative">
                <Input
                  type="text"
                  placeholder="Enter player name..."
                  value={searchQuery}
                  onChange={(e) => handleSearchChange(e.target.value)}
                  onFocus={() => searchResults.length > 0 && setShowSearchResults(true)}
                  className="w-full"
                />

                {/* Search Results Dropdown */}
                {showSearchResults && searchResults.length > 0 && (
                  <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-96 overflow-y-auto">
                    {searchResults.map((player) => {
                      const age = player.birth_date
                        ? new Date().getFullYear() - new Date(player.birth_date).getFullYear()
                        : null;

                      return (
                        <div
                          key={player.player_id}
                          className="p-3 hover:bg-gray-50 cursor-pointer border-b last:border-b-0 transition-colors"
                          onClick={() => {
                            setShowSearchResults(false);
                            setSearchQuery(player.player_name);

                            // Scroll to the search result section
                            setTimeout(() => {
                              const element = document.getElementById('search-result');
                              if (element) {
                                element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                              }
                            }, 100);
                          }}
                        >
                          <div className="flex items-center gap-3">
                            {/* Player Image */}
                            <div className="flex-shrink-0">
                              {player.image_url ? (
                                <img
                                  src={player.image_url}
                                  alt={player.player_name}
                                  className="w-10 h-10 rounded-full object-cover border-2 border-green"
                                />
                              ) : (
                                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-green to-blue-400 flex items-center justify-center text-white font-bold text-sm border-2 border-green">
                                  {player.player_name.charAt(0)}
                                </div>
                              )}
                            </div>

                            {/* Player Info */}
                            <div className="flex-1 min-w-0">
                              <h4 className="text-sm font-semibold text-gray-900 truncate">
                                {player.player_name}
                              </h4>
                              <div className="flex flex-wrap gap-1 text-xs text-gray-600">
                                {player.team_name && (
                                  <span className="truncate">{player.team_name}</span>
                                )}
                                {player.team_name && player.league_name && <span>•</span>}
                                {player.league_name && (
                                  <span className="truncate">{player.league_name}</span>
                                )}
                              </div>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {age && age > 0 && (
                                  <Badge variant="outline" className="text-xs px-1.5 py-0 bg-blue-50 text-blue-700 border-blue-500">
                                    {age} yo
                                  </Badge>
                                )}
                                {player.position && (
                                  <Badge variant="outline" className="text-xs px-1.5 py-0 bg-gray-50 text-gray-700 border-gray-500">
                                    {player.position}
                                  </Badge>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* No Results */}
                {showSearchResults && searchQuery.length >= 2 && searchResults.length === 0 && (
                  <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg p-4">
                    <p className="text-sm text-gray-600 text-center">No players found</p>
                  </div>
                )}
              </div>

              {/* Close search results when clicking outside */}
              {showSearchResults && (
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setShowSearchResults(false)}
                />
              )}

              {/* Search Result Display - Integrated */}
              {searchQuery && (
                <div id="search-result" className="mt-4 pt-4 border-t border-gray-200">
                  <SearchResultDisplay
                    playerId={searchResults.find(p => p.player_name === searchQuery)?.player_id}
                    selectedMetric={selectedMetric}
                    categoryToMetricCode={categoryToMetricCode}
                    selectedLeague={selectedLeague}
                    selectedSeason={selectedSeason}
                    selectedTeam={selectedTeam}
                    selectedNation={selectedNation}
                    selectedPosition={selectedPosition}
                    minMinutes={minMinutes}
                    minValue={minValue}
                    maxValue={maxValue}
                    minAge={minAge}
                    maxAge={maxAge}
                    onViewProfile={(playerId: number) => router.push(`/talent-pool/${playerId}`)}
                  />
                </div>
              )}
            </CardContent>
          </Card>

          {/* Anchor for scroll restoration */}
          <div ref={anchorRef} />

          {/* Podium for Top 3 Players */}
          {rankingsData && rankingsData.length >= 3 && (
            <Podium
              players={rankingsData.slice(0, 3).map((p: any) => ({
                player_id: p.player_id,
                player_name: p.player_name,
                value: p.quantile_value,
                team_name: p.team_name,
                image_url: p.image_url,
              }))}
              metricName={selectedMetric.charAt(0).toUpperCase() + selectedMetric.slice(1)}
            />
          )}

          {/* Rankings List */}
          <Card>
            <CardHeader>
              <CardTitle>{selectedMetric.charAt(0).toUpperCase() + selectedMetric.slice(1)} Rankings</CardTitle>
              <CardDescription>
                {selectedLeague} • {formatSeason(selectedSeason)} • Top {rankingsLimit} players
                {parseInt(minMinutes) > 0 && ` • Players with ${minMinutes}+ minutes played`}
                {selectedPosition !== "All Positions" && ` • ${positionMapping[selectedPosition] || selectedPosition}`}
                {(minValue || maxValue) && ` • Market value: ${minValue || "0"}M€ - ${maxValue || "∞"}M€`}
                {(minAge || maxAge) && ` • Age: ${minAge || "15"} - ${maxAge || "50"}`}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoadingRankings && (
                <div className="text-center py-12">
                  <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-green"></div>
                  <p className="mt-4 text-gray-600">Loading rankings...</p>
                </div>
              )}

              {rankingsError && (
                <div className="text-center py-8">
                  <p className="text-red-600">Error loading rankings: {(rankingsError as Error).message}</p>
                </div>
              )}

              {rankingsData && !isLoadingRankings && (
                <>
                  {rankingsData.length > 0 ? (
                    <div className="space-y-3">
                      {rankingsData.slice(0, rankingsLimit).map((player: any, index: number) => {
                        const age = player.birth_date
                          ? new Date().getFullYear() - new Date(player.birth_date).getFullYear()
                          : null;

                        return (
                          <Card
                            key={player.player_id}
                            className="shadow-sm border border-blue-200 hover:shadow-md transition-all cursor-pointer hover:border-green"
                            onClick={() => router.push(`/talent-pool/${player.player_id}`)}
                          >
                            <CardContent className="py-2 px-3">
                              <div className="flex items-center gap-2.5">
                                {/* Rank Badge */}
                                <div className="flex-shrink-0">
                                  <div
                                    className={`w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold ${
                                      index === 0
                                        ? "bg-gradient-to-br from-yellow-400 to-yellow-600 text-white"
                                        : index === 1
                                        ? "bg-gradient-to-br from-gray-300 to-gray-500 text-white"
                                        : index === 2
                                        ? "bg-gradient-to-br from-orange-400 to-orange-600 text-white"
                                        : "bg-gradient-to-br from-gray-700 to-gray-900 text-white"
                                    }`}
                                  >
                                    {index + 1}
                                  </div>
                                </div>

                                {/* Player Image */}
                                <div className="flex-shrink-0">
                                  {player.image_url ? (
                                    <img
                                      src={player.image_url}
                                      alt={player.player_name}
                                      className="w-11 h-11 rounded-full object-cover border-2 border-green"
                                    />
                                  ) : (
                                    <div className="w-11 h-11 rounded-full bg-gradient-to-br from-green to-blue-400 flex items-center justify-center text-white font-bold text-base border-2 border-green">
                                      {player.player_name.charAt(0)}
                                    </div>
                                  )}
                                </div>

                                {/* Player Info */}
                                <div className="flex-1 min-w-0">
                                  <h3 className="text-base font-bold text-gray-900 mb-0 leading-tight truncate">
                                    {player.player_name}
                                  </h3>

                                  {/* Player Details */}
                                  <div className="flex flex-wrap gap-1 text-sm text-gray-600 leading-tight mb-1">
                                    {player.team_name && (
                                      <span className="truncate max-w-[120px]">{player.team_name}</span>
                                    )}
                                    {player.league_name && player.team_name && (
                                      <span>•</span>
                                    )}
                                    {player.league_name && (
                                      <span className="truncate max-w-[100px]">{player.league_name}</span>
                                    )}
                                  </div>

                                  {/* Additional Info Badges */}
                                  <div className="flex flex-wrap gap-1">
                                    {age && age > 0 && (
                                      <Badge variant="outline" className="text-xs px-1.5 py-0 bg-blue-50 text-blue-700 border-blue-500">
                                        {age} yo
                                      </Badge>
                                    )}
                                    {player.nationality && (
                                      <Badge variant="outline" className="text-xs px-1.5 py-0 bg-purple-50 text-purple-700 border-purple-500">
                                        🌍 {getCountryName(player.nationality)}
                                      </Badge>
                                    )}
                                    {player.value_m_eur !== null && player.value_m_eur !== undefined && player.value_m_eur > 0 && (
                                      <Badge variant="outline" className="text-xs px-1.5 py-0 bg-emerald-50 text-emerald-700 border-emerald-600 font-semibold">
                                        💰 €{player.value_m_eur.toFixed(1)}M
                                      </Badge>
                                    )}
                                  </div>
                                </div>

                                {/* Score Badge */}
                                <div className="flex-shrink-0">
                                  <Badge className="bg-green text-navy font-bold px-2.5 py-1 text-sm whitespace-nowrap">
                                    {player.quantile_value.toFixed(2)}
                                  </Badge>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <p className="text-gray-600 text-lg mb-2">No players found</p>
                      <p className="text-sm text-gray-500">
                        Try adjusting your filters to see more results
                      </p>
                    </div>
                  )}

                  {/* Show More Button - only show if there are more than 20 players */}
                  {rankingsData && rankingsData.length > 20 && rankingsLimit === 20 && (
                    <div className="mt-6 text-center">
                      <Button
                        onClick={() => {
                          snapshotAnchor();
                          setRankingsLimit(50);
                        }}
                        variant="outline"
                        size="lg"
                        className="bg-white hover:bg-navy hover:text-white border-2 border-navy text-navy font-semibold px-8 py-3 transition-all duration-200"
                      >
                        Show More ({Math.min(rankingsData.length, 50)} players)
                      </Button>
                    </div>
                  )}

                  {/* Show Less Button */}
                  {rankingsData && rankingsData.length > 20 && rankingsLimit === 50 && (
                    <div className="mt-6 text-center">
                      <Button
                        onClick={() => {
                          snapshotAnchor();
                          setRankingsLimit(20);
                        }}
                        variant="outline"
                        size="lg"
                        className="bg-white hover:bg-navy hover:text-white border-2 border-navy text-navy font-semibold px-8 py-3 transition-all duration-200"
                      >
                        Show Less (20 players)
                      </Button>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Call to Action & Feedback Section - Side by Side */}
      <section className="py-10 bg-gradient-to-br from-orange-50 via-red-50 to-pink-50">
        <div className="container mx-auto px-4">
          <div className="max-w-6xl mx-auto">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Face-to-Face CTA */}
              <Card className="border-2 border-orange-200 shadow-xl">
                <CardContent className="pt-6 pb-6 px-4 sm:pt-7 sm:pb-7 sm:px-6">
                  <div className="text-center">
                    <h2 className="text-xl sm:text-2xl font-bold text-navy mb-3 px-2">
                      Ready for Face-to-Face Comparison?
                    </h2>
                    <p className="text-sm sm:text-base text-gray-600 mb-4 sm:mb-5 px-2">
                      Compare two players head-to-head with interactive scatter plots,
                      detailed radar charts, and comprehensive performance analysis across all metrics.
                    </p>

                    <Button
                      asChild
                      size="lg"
                      className="bg-red-500 text-white hover:bg-red-600 font-bold px-4 sm:px-5 py-3 sm:py-4 text-sm sm:text-base shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 w-full sm:w-auto"
                    >
                      <Link href="/face-to-face">
                        Start Face-to-Face Comparison
                      </Link>
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Inline Feedback */}
              <InlineFeedback context="rankings" />
            </div>
          </div>
        </div>
      </section>

    </div>
  );
}

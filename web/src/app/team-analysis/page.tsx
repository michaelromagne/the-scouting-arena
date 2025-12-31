"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { InlineFeedback } from "@/components/InlineFeedback";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  fetchTeamsList,
  fetchTeamComparison,
  fetchLeagues,
  fetchSeasons,
  fetchMetricCategories,
  type Team,
  type TeamComparison,
  type MetricCategory,
} from "@/lib/api";
import { getPositionDisplayName } from "@/lib/constants";
import { formatSeason } from "@/lib/utils";
import { Radar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from "chart.js";

// Register Chart.js components
ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

export default function TeamAnalysisPage() {
  // Team 1 filters
  const [team1League, setTeam1League] = useState<string>("Aggregated (All Leagues)");
  const [team1Season, setTeam1Season] = useState<string>("2526");
  const [team1Id, setTeam1Id] = useState<number | null>(null);

  // Team 2 filters
  const [team2League, setTeam2League] = useState<string>("Aggregated (All Leagues)");
  const [team2Season, setTeam2Season] = useState<string>("2526");
  const [team2Id, setTeam2Id] = useState<number | null>(null);

  // Helper function to format quantile as "Top X%"
  const formatQuantile = (quantile: number): string => {
    const topPercent = 100 - quantile;
    if (topPercent < 1) {
      return "Top 1%";
    }
    return `Top ${Math.round(topPercent)}%`;
  };

  // Fetch leagues and filter to domestic leagues only (exclude European cups and aggregated)
  const { data: allLeagues = [] } = useQuery({
    queryKey: ["leagues"],
    queryFn: fetchLeagues,
  });


  // Fetch seasons
  const { data: seasons = [] } = useQuery({
    queryKey: ["seasons"],
    queryFn: fetchSeasons,
  });

  // Fetch metric categories
  const { data: metricCategories = [] } = useQuery<MetricCategory[]>({
    queryKey: ["metric-categories"],
    queryFn: fetchMetricCategories,
  });

  // Fetch teams for Team 1
  const { data: teams1 = [], isLoading: teams1Loading } = useQuery({
    queryKey: ["teams", team1League, team1Season],
    queryFn: () =>
      fetchTeamsList({
        league: team1League,
        season: team1Season,
      }),
    enabled: !!team1League && !!team1Season,
  });

  // Fetch teams for Team 2
  const { data: teams2 = [], isLoading: teams2Loading } = useQuery({
    queryKey: ["teams", team2League, team2Season],
    queryFn: () =>
      fetchTeamsList({
        league: team2League,
        season: team2Season,
      }),
    enabled: !!team2League && !!team2Season,
  });

  // Fetch comparison when both teams selected
  const {
    data: comparison,
    isLoading: comparisonLoading,
    error: comparisonError,
  } = useQuery({
    queryKey: ["teamComparison", team1Id, team2Id, team1Season, team2Season],
    queryFn: async () => {
      return fetchTeamComparison({
        team1Id: team1Id!,
        team2Id: team2Id!,
        season1: team1Season,
        season2: team2Season,
        topN: 3,
      });
    },
    enabled: !!team1Id && !!team2Id,
  });

  // Get team names for display
  const team1Name = teams1.find((t) => t.id === team1Id)?.name || "Team 1";
  const team2Name = teams2.find((t) => t.id === team2Id)?.name || "Team 2";

  // Prepare radar chart data using actual metric categories
  const getRadarData = (comparison: TeamComparison | undefined) => {
    if (!comparison || !metricCategories.length) return null;

    // Filter out goalkeeper and discipline categories for team comparison
    const relevantCategories = metricCategories.filter(
      (cat) => !cat.isGoalkeeper && cat.category.toLowerCase() !== "discipline"
    );

    const labels = relevantCategories.map((cat) => cat.category);

    // Calculate percentile per category for each team
    // The percentiles are stored in metrics with "quantile_" prefix
    // e.g., "quantile_finishing", "quantile_passing", etc.
    const team1Data = labels.map((category) => {
      const categoryLower = category.toLowerCase().replace(/\s+/g, "_");
      const quantileKey = `quantile_${categoryLower}`;
      const metric = comparison.team1.metrics[quantileKey];
      // The quantile value is stored in the 'quantile_value' field
      return metric?.quantile_value || 0;
    });

    const team2Data = labels.map((category) => {
      const categoryLower = category.toLowerCase().replace(/\s+/g, "_");
      const quantileKey = `quantile_${categoryLower}`;
      const metric = comparison.team2.metrics[quantileKey];
      // The quantile value is stored in the 'quantile_value' field
      return metric?.quantile_value || 0;
    });

    return {
      labels,
      datasets: [
        {
          label: `${team1Name} (${formatSeason(team1Season)})`,
          data: team1Data,
          backgroundColor: "rgba(59, 130, 246, 0.2)", // blue
          borderColor: "rgba(59, 130, 246, 1)",
          borderWidth: 2,
          pointBackgroundColor: "rgba(59, 130, 246, 1)",
          pointBorderColor: "#fff",
          pointHoverBackgroundColor: "#fff",
          pointHoverBorderColor: "rgba(59, 130, 246, 1)",
        },
        {
          label: `${team2Name} (${formatSeason(team2Season)})`,
          data: team2Data,
          backgroundColor: "rgba(239, 68, 68, 0.2)", // red
          borderColor: "rgba(239, 68, 68, 1)",
          borderWidth: 2,
          pointBackgroundColor: "rgba(239, 68, 68, 1)",
          pointBorderColor: "#fff",
          pointHoverBackgroundColor: "#fff",
          pointHoverBorderColor: "rgba(239, 68, 68, 1)",
        },
      ],
    };
  };

  const radarData = getRadarData(comparison);

  const handleReset = () => {
    setTeam1League("Aggregated (All Leagues)");
    setTeam1Season("2526");
    setTeam1Id(null);
    setTeam2League("Aggregated (All Leagues)");
    setTeam2Season("2526");
    setTeam2Id(null);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <section className="bg-navy text-white py-12 relative">
        <div className="container mx-auto px-4 text-center">
          <h1 className="text-3xl md:text-4xl font-bold mb-4 text-white">
            Team <span className="text-blue-400">Analysis</span>
          </h1>
          <p className="text-lg text-gray-200 max-w-2xl mx-auto mb-6">
            Compare two teams head-to-head with radar charts and discover their key players
          </p>
          <p className="text-sm text-gray-400 max-w-xl mx-auto">
            💡 Compare teams across different leagues and seasons
          </p>
        </div>
      </section>

      {/* Filters Section */}
      <section className="py-6 bg-white border-b">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 max-w-7xl mx-auto">
            {/* Team 1 Filter Card */}
            <Card className="shadow-lg border-2 border-blue-200">
              <CardHeader className="bg-gradient-to-r from-blue-50 to-blue-100/50 pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <span className="text-2xl">🔵</span>
                  <span>Team 1</span>
                </CardTitle>
                <CardDescription className="text-xs">Select league, season, and team</CardDescription>
              </CardHeader>
              <CardContent className="pt-4 pb-4">
                <div className="space-y-3">
                  {/* League */}
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-1">
                      <span className="text-sm">🏆</span>
                      <label className="text-xs font-medium text-primary">League</label>
                    </div>
                    <Select value={team1League} onValueChange={(val) => {
                      setTeam1League(val);
                      setTeam1Id(null); // Reset team when league changes
                    }}>
                      <SelectTrigger className="w-full h-9 text-xs bg-white text-gray-900 border-blue-300 focus:ring-blue-500">
                        <SelectValue placeholder="Select league" />
                      </SelectTrigger>
                      <SelectContent>
                        {allLeagues.map((league) => (
                          <SelectItem key={league} value={league}>
                            {league}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Season */}
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-1">
                      <span className="text-sm">📅</span>
                      <label className="text-xs font-medium text-primary">Season</label>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {seasons.map((season) => (
                        <Badge
                          key={season}
                          variant={team1Season === season ? "default" : "outline"}
                          className={`cursor-pointer px-2 py-1 text-xs transition-all duration-200 ${
                            team1Season === season
                              ? "bg-blue-600 text-white hover:bg-blue-700"
                              : "hover:bg-blue-100 hover:text-blue-700 border-blue-300"
                          }`}
                          onClick={() => {
                            setTeam1Season(season);
                            setTeam1Id(null); // Reset team when season changes
                          }}
                        >
                          {formatSeason(season)}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  {/* Team */}
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-1">
                      <span className="text-sm">⚽</span>
                      <label className="text-xs font-medium text-primary">Team</label>
                    </div>
                    <Select
                      value={team1Id?.toString() || ""}
                      onValueChange={(val) => setTeam1Id(Number(val))}
                      disabled={teams1Loading}
                    >
                      <SelectTrigger className="w-full h-9 text-xs bg-white text-gray-900 border-blue-300 focus:ring-blue-500">
                        <SelectValue placeholder={teams1Loading ? "Loading teams..." : "Select team"} />
                      </SelectTrigger>
                      <SelectContent>
                        {teams1.map((team) => (
                          <SelectItem key={team.id} value={team.id.toString()}>
                            {team.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {team1Id && (
                    <div className="pt-2 text-center">
                      <Badge className="bg-blue-600 text-white px-3 py-1">
                        ✓ {team1Name}
                      </Badge>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Team 2 Filter Card */}
            <Card className="shadow-lg border-2 border-red-200">
              <CardHeader className="bg-gradient-to-r from-red-50 to-red-100/50 pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <span className="text-2xl">🔴</span>
                  <span>Team 2</span>
                </CardTitle>
                <CardDescription className="text-xs">Select league, season, and team</CardDescription>
              </CardHeader>
              <CardContent className="pt-4 pb-4">
                <div className="space-y-3">
                  {/* League */}
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-1">
                      <span className="text-sm">🏆</span>
                      <label className="text-xs font-medium text-primary">League</label>
                    </div>
                    <Select value={team2League} onValueChange={(val) => {
                      setTeam2League(val);
                      setTeam2Id(null); // Reset team when league changes
                    }}>
                      <SelectTrigger className="w-full h-9 text-xs bg-white text-gray-900 border-red-300 focus:ring-red-500">
                        <SelectValue placeholder="Select league" />
                      </SelectTrigger>
                      <SelectContent>
                        {allLeagues.map((league) => (
                          <SelectItem key={league} value={league}>
                            {league}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Season */}
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-1">
                      <span className="text-sm">📅</span>
                      <label className="text-xs font-medium text-primary">Season</label>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {seasons.map((season) => (
                        <Badge
                          key={season}
                          variant={team2Season === season ? "default" : "outline"}
                          className={`cursor-pointer px-2 py-1 text-xs transition-all duration-200 ${
                            team2Season === season
                              ? "bg-red-600 text-white hover:bg-red-700"
                              : "hover:bg-red-100 hover:text-red-700 border-red-300"
                          }`}
                          onClick={() => {
                            setTeam2Season(season);
                            setTeam2Id(null); // Reset team when season changes
                          }}
                        >
                          {formatSeason(season)}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  {/* Team */}
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-1">
                      <span className="text-sm">⚽</span>
                      <label className="text-xs font-medium text-primary">Team</label>
                    </div>
                    <Select
                      value={team2Id?.toString() || ""}
                      onValueChange={(val) => setTeam2Id(Number(val))}
                      disabled={teams2Loading}
                    >
                      <SelectTrigger className="w-full h-9 text-xs bg-white text-gray-900 border-red-300 focus:ring-red-500">
                        <SelectValue placeholder={teams2Loading ? "Loading teams..." : "Select team"} />
                      </SelectTrigger>
                      <SelectContent>
                        {teams2.map((team) => (
                          <SelectItem key={team.id} value={team.id.toString()}>
                            {team.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {team2Id && (
                    <div className="pt-2 text-center">
                      <Badge className="bg-red-600 text-white px-3 py-1">
                        ✓ {team2Name}
                      </Badge>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Reset Button */}
          <div className="text-center mt-4">
            <Button
              variant="outline"
              size="sm"
              onClick={handleReset}
              className="px-4 h-9 text-xs"
            >
              🔄 Reset All Filters
            </Button>
          </div>

          {/* Cross-season warning */}
          {team1Id && team2Id && team1Season !== team2Season && (
            <div className="mt-4 max-w-2xl mx-auto">
              <Card className="bg-amber-50 border-amber-300">
                <CardContent className="pt-4 pb-4">
                  <div className="flex items-start gap-3">
                    <span className="text-2xl">⚠️</span>
                    <div>
                      <p className="text-sm font-medium text-amber-900">
                        Cross-Season Comparison
                      </p>
                      <p className="text-xs text-amber-700 mt-1">
                        You're comparing teams from different seasons ({formatSeason(team1Season)} vs {formatSeason(team2Season)}).
                        Stats are normalized within each season, so percentiles are relative to their respective seasons.
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </section>

      {/* Results Section */}
      {team1Id && team2Id ? (
        <section className="py-12 bg-gradient-to-br from-blue-50 via-slate-50 to-indigo-100/50">
          <div className="container mx-auto px-4 max-w-7xl">
            {comparisonLoading && (
              <Card className="shadow-lg">
                <CardContent className="pt-8 pb-8">
                  <p className="text-center text-gray-600">Loading comparison...</p>
                </CardContent>
              </Card>
            )}

            {comparisonError && (
              <Card className="bg-red-50 border-red-200 shadow-lg">
                <CardContent className="pt-8 pb-8">
                  <p className="text-center text-red-600">
                    Error loading comparison. Please try again.
                  </p>
                </CardContent>
              </Card>
            )}

            {comparison && (
              <div className="space-y-8">
                {/* Radar Chart */}
                {radarData && (
                  <Card className="shadow-lg">
                    <CardHeader>
                      <CardTitle className="text-center text-xl">
                        📊 Performance Comparison : {team1Name} season {formatSeason(team1Season)} vs {team2Name} season {formatSeason(team2Season)}
                      </CardTitle>
                      <CardDescription className="text-center">
                        Percentile rankings across key performance categories
                        {team1Season !== team2Season && (
                          <span className="block text-amber-600 text-xs mt-1">
                            ⚠️ Comparing {formatSeason(team1Season)} vs {formatSeason(team2Season)} seasons
                          </span>
                        )}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="max-w-3xl mx-auto" style={{ height: "500px" }}>
                        <Radar
                          data={radarData}
                          options={{
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                              r: {
                                beginAtZero: true,
                                max: 100,
                                ticks: {
                                  stepSize: 20,
                                  color: "#6B7280",
                                  font: {
                                    size: 11,
                                  },
                                },
                                grid: {
                                  color: "#E5E7EB",
                                },
                                pointLabels: {
                                  color: "#1F2937",
                                  font: {
                                    size: 13,
                                    weight: 600,
                                  },
                                },
                              },
                            },
                            plugins: {
                              legend: {
                                position: "top",
                                labels: {
                                  color: "#1F2937",
                                  font: {
                                    size: 14,
                                    weight: 600,
                                  },
                                  padding: 20,
                                },
                              },
                              tooltip: {
                                callbacks: {
                                  label: (context) => {
                                    return `${context.dataset.label}: ${context.parsed.r.toFixed(1)}%`;
                                  },
                                },
                              },
                            },
                          }}
                        />
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Key Players Section */}
                <div className="mt-8">
                  <h3 className="text-xl font-bold text-primary mb-2">🌟 Key Players</h3>
                  <p className="text-sm text-gray-600 mb-4">Top market value and elite performers from each team</p>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Team 1 Key Players */}
                    <Card className="shadow-lg border-2 border-blue-200">
                      <CardHeader className="bg-gradient-to-r from-blue-50 to-blue-100/50">
                        <CardTitle className="text-lg flex items-center gap-2">
                          <span className="text-2xl">🔵</span>
                          <span>{team1Name}</span>
                        </CardTitle>
                        <CardDescription className="text-xs">
                          {team1League} • {formatSeason(team1Season)}
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="pt-6">
                        {/* Top 3 by Market Value */}
                        <div className="mb-6">
                          <h4 className="text-sm font-semibold text-blue-700 mb-3 flex items-center gap-2">
                            <span>💰</span>
                            <span>Top 3 by Market Value</span>
                          </h4>
                          {comparison.top_value_team1 && comparison.top_value_team1.length > 0 ? (
                            comparison.top_value_team1.map((player, index) => (
                              <div
                                key={`mv-${player.player_id}`}
                                className="border-2 border-green-200 rounded-lg p-2.5 bg-gradient-to-r from-green-50/50 to-white mb-3"
                              >
                                <div className="flex items-center gap-2">
                                  {/* Rank Badge */}
                                  <div
                                    className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                                      index === 0
                                        ? "bg-gradient-to-br from-yellow-400 to-yellow-600 text-white"
                                        : index === 1
                                        ? "bg-gradient-to-br from-gray-300 to-gray-500 text-white"
                                        : "bg-gradient-to-br from-orange-400 to-orange-600 text-white"
                                    }`}
                                  >
                                    {index + 1}
                                  </div>

                                  {/* Player Image */}
                                  {player.image_url ? (
                                    <img
                                      src={player.image_url}
                                      alt={player.player_name}
                                      className="w-10 h-10 rounded-full object-cover border-2 border-green-400 flex-shrink-0"
                                    />
                                  ) : (
                                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-green-300 to-green-500 flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
                                      {player.player_name.charAt(0)}
                                    </div>
                                  )}

                                  {/* Player Info */}
                                  <div className="flex-1 min-w-0">
                                    <p className="font-bold text-sm text-gray-900 truncate leading-tight">{player.player_name}</p>
                                    <p className="text-xs text-gray-600 leading-tight">{getPositionDisplayName(player.position)}</p>
                                  </div>

                                  {/* Market Value */}
                                  <Badge className="bg-green text-navy font-bold px-2 py-1 text-xs flex-shrink-0 whitespace-nowrap">
                                    €{player.market_value_eur?.toFixed(1)}M
                                  </Badge>
                                </div>
                              </div>
                            ))
                          ) : (
                            <div className="text-center py-4 text-gray-500">
                              <p className="text-sm">No market value data available</p>
                            </div>
                          )}
                        </div>

                        {/* Elite Players (Top 10%) */}
                        <div>
                          <h4 className="text-sm font-semibold text-blue-700 mb-3 flex items-center gap-2">
                            <span>⭐</span>
                            <span>Elite Players (Top 10%)</span>
                          </h4>
                          {comparison.elite_players_team1 && comparison.elite_players_team1.length > 0 ? (
                          <div className="space-y-4">
                            {comparison.elite_players_team1.map((player) => (
                              <div
                                key={player.player_id}
                                className="border-2 border-blue-200 rounded-lg p-4 bg-gradient-to-r from-blue-50/50 to-white hover:from-blue-100/50 transition-colors"
                              >
                                <div className="flex items-start gap-3 mb-3">
                                  {player.image_url ? (
                                    <img
                                      src={player.image_url}
                                      alt={player.player_name}
                                      className="w-12 h-12 rounded-full object-cover border-2 border-blue-400"
                                    />
                                  ) : (
                                    <div className="w-12 h-12 rounded-full bg-blue-300 flex items-center justify-center text-blue-800 font-bold">
                                      {player.player_name.charAt(0)}
                                    </div>
                                  )}
                                  <div className="flex-1">
                                    <p className="font-bold text-gray-900">{player.player_name}</p>
                                    <p className="text-xs text-gray-600">{getPositionDisplayName(player.position)}</p>
                                  </div>
                                </div>
                                <div className="flex flex-wrap gap-1.5">
                                  {Object.entries(player.elite_categories)
                                    .sort(([, a], [, b]) => b - a) // Sort by quantile descending
                                    .map(([category, quantile]) => (
                                      <Badge
                                        key={category}
                                        variant="outline"
                                        className="text-xs border-blue-400 text-blue-700 bg-blue-50 font-medium"
                                      >
                                        {category}: {formatQuantile(quantile)}
                                      </Badge>
                                    ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-center py-8 text-gray-500">
                            <p className="text-sm">No players in top 10% compared to competition</p>
                          </div>
                        )}
                        </div>
                      </CardContent>
                    </Card>

                    {/* Team 2 Key Players */}
                    <Card className="shadow-lg border-2 border-red-200">
                      <CardHeader className="bg-gradient-to-r from-red-50 to-red-100/50">
                        <CardTitle className="text-lg flex items-center gap-2">
                          <span className="text-2xl">🔴</span>
                          <span>{team2Name}</span>
                        </CardTitle>
                        <CardDescription className="text-xs">
                          {team2League} • {formatSeason(team2Season)}
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="pt-6">
                        {/* Top 3 by Market Value */}
                        <div className="mb-6">
                          <h4 className="text-sm font-semibold text-red-700 mb-3 flex items-center gap-2">
                            <span>💰</span>
                            <span>Top 3 by Market Value</span>
                          </h4>
                          {comparison.top_value_team2 && comparison.top_value_team2.length > 0 ? (
                            comparison.top_value_team2.map((player, index) => (
                              <div
                                key={`mv-${player.player_id}`}
                                className="border-2 border-green-200 rounded-lg p-2.5 bg-gradient-to-r from-green-50/50 to-white mb-3"
                              >
                                <div className="flex items-center gap-2">
                                  {/* Rank Badge */}
                                  <div
                                    className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                                      index === 0
                                        ? "bg-gradient-to-br from-yellow-400 to-yellow-600 text-white"
                                        : index === 1
                                        ? "bg-gradient-to-br from-gray-300 to-gray-500 text-white"
                                        : "bg-gradient-to-br from-orange-400 to-orange-600 text-white"
                                    }`}
                                  >
                                    {index + 1}
                                  </div>

                                  {/* Player Image */}
                                  {player.image_url ? (
                                    <img
                                      src={player.image_url}
                                      alt={player.player_name}
                                      className="w-10 h-10 rounded-full object-cover border-2 border-green-400 flex-shrink-0"
                                    />
                                  ) : (
                                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-green-300 to-green-500 flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
                                      {player.player_name.charAt(0)}
                                    </div>
                                  )}

                                  {/* Player Info */}
                                  <div className="flex-1 min-w-0">
                                    <p className="font-bold text-sm text-gray-900 truncate leading-tight">{player.player_name}</p>
                                    <p className="text-xs text-gray-600 leading-tight">{getPositionDisplayName(player.position)}</p>
                                  </div>

                                  {/* Market Value */}
                                  <Badge className="bg-green text-navy font-bold px-2 py-1 text-xs flex-shrink-0 whitespace-nowrap">
                                    €{player.market_value_eur?.toFixed(1)}M
                                  </Badge>
                                </div>
                              </div>
                            ))
                          ) : (
                            <div className="text-center py-4 text-gray-500">
                              <p className="text-sm">No market value data available</p>
                            </div>
                          )}
                        </div>

                        {/* Elite Players (Top 10%) */}
                        <div>
                          <h4 className="text-sm font-semibold text-red-700 mb-3 flex items-center gap-2">
                            <span>⭐</span>
                            <span>Elite Players (Top 10%)</span>
                          </h4>
                          {comparison.elite_players_team2 && comparison.elite_players_team2.length > 0 ? (
                          <div className="space-y-4">
                            {comparison.elite_players_team2.map((player) => (
                              <div
                                key={player.player_id}
                                className="border-2 border-red-200 rounded-lg p-4 bg-gradient-to-r from-red-50/50 to-white hover:from-red-100/50 transition-colors"
                              >
                                <div className="flex items-start gap-3 mb-3">
                                  {player.image_url ? (
                                    <img
                                      src={player.image_url}
                                      alt={player.player_name}
                                      className="w-12 h-12 rounded-full object-cover border-2 border-red-400"
                                    />
                                  ) : (
                                    <div className="w-12 h-12 rounded-full bg-red-300 flex items-center justify-center text-red-800 font-bold">
                                      {player.player_name.charAt(0)}
                                    </div>
                                  )}
                                  <div className="flex-1">
                                    <p className="font-bold text-gray-900">{player.player_name}</p>
                                    <p className="text-xs text-gray-600">{getPositionDisplayName(player.position)}</p>
                                  </div>
                                </div>
                                <div className="flex flex-wrap gap-1.5">
                                  {Object.entries(player.elite_categories)
                                    .sort(([, a], [, b]) => b - a) // Sort by quantile descending
                                    .map(([category, quantile]) => (
                                      <Badge
                                        key={category}
                                        variant="outline"
                                        className="text-xs border-red-400 text-red-700 bg-red-50 font-medium"
                                      >
                                        {category}: {formatQuantile(quantile)}
                                      </Badge>
                                    ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-center py-8 text-gray-500">
                            <p className="text-sm">No players in top 10% compared to competition</p>
                          </div>
                        )}
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>
      ) : (
        /* Empty State */
        <section className="py-12 bg-gradient-to-br from-blue-50 via-slate-50 to-indigo-100/50">
          <div className="container mx-auto px-4 max-w-4xl">
            <Card className="shadow-lg border-2 border-dashed border-blue-300">
              <CardContent className="pt-12 pb-12">
                <div className="text-center">
                  <div className="text-6xl mb-6">🏆</div>
                  <h3 className="text-2xl font-bold text-navy mb-3">
                    Select Two Teams to Compare
                  </h3>
                  <p className="text-gray-600 mb-8 max-w-md mx-auto">
                    Choose league, season, and team for each side. You can compare teams from different leagues and seasons!
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </section>
      )}

      {/* Call to Action & Feedback Section - Side by Side */}
      <section className="py-10 bg-gradient-to-br from-slate-50 via-cyan-50 to-blue-50">
        <div className="container mx-auto px-4">
          <div className="max-w-6xl mx-auto">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Team Rankings CTA */}
              <Card className="border-2 border-slate-200 shadow-xl">
                <CardContent className="pt-6 pb-6 px-4 sm:pt-7 sm:pb-7 sm:px-6">
                  <div className="text-center">
                    <h2 className="text-xl sm:text-2xl font-bold text-navy mb-3 px-2">
                      Explore Team Rankings
                    </h2>
                    <p className="text-sm sm:text-base text-gray-600 mb-4 sm:mb-5 px-2">
                      Discover the best performing teams across different categories. From most complete teams to most entertaining,
                      see how teams rank in finishing, passing, defense, and more.
                    </p>

                    <Button
                      asChild
                      size="lg"
                      className="bg-gradient-to-r from-slate-600 to-cyan-600 text-white hover:from-slate-700 hover:to-cyan-700 font-bold px-4 sm:px-5 py-3 sm:py-4 text-sm sm:text-base shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 w-full sm:w-auto"
                    >
                      <Link href="/team-rankings">
                        View Team Rankings
                      </Link>
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Inline Feedback */}
              <InlineFeedback context="team-analysis" />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

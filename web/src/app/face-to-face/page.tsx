"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { InteractiveChart } from "@/components/InteractiveChart";
import { PlayerComparison } from "@/components/PlayerComparison";
import { InlineFeedback } from "@/components/InlineFeedback";
import { fetchLeagues, fetchSeasons, fetchPositions, fetchPlayers, fetchTeams, fetchNations } from "@/lib/api";
import { fetchMetricCategories, type MetricCategory } from "@/lib/api-client";
import { POSITION_MAPPING, getPositionEmoji, DEFAULT_FILTERS, getCountryName } from "@/lib/constants";
import { formatSeason } from "@/lib/utils";

export default function FaceToFace() {
  const router = useRouter();

  // Player Arena comparison anchor
  const comparisonRef = useRef<HTMLDivElement>(null);

  // Use position mapping from shared constants
  const positionMapping = POSITION_MAPPING;

  // Player Arena filters
  const [selectedXMetric, setSelectedXMetric] = useState<string>("finishing");
  const [selectedYMetric, setSelectedYMetric] = useState<string>("passing");

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

  const [arenaLeague, setArenaLeague] = useState<string>(DEFAULT_FILTERS.league);
  const [arenaSeason, setArenaSeason] = useState<string>(DEFAULT_FILTERS.season);
  const [arenaPosition, setArenaPosition] = useState<string>("all");
  const [arenaMinMinutes, setArenaMinMinutes] = useState<string>(DEFAULT_FILTERS.minMinutes);
  const [arenaTeam, setArenaTeam] = useState<string>(DEFAULT_FILTERS.team);
  const [arenaNation, setArenaNation] = useState<string>(DEFAULT_FILTERS.nation);
  const [arenaMinValue, setArenaMinValue] = useState<string>("");
  const [arenaMaxValue, setArenaMaxValue] = useState<string>("");
  const [arenaMinAge, setArenaMinAge] = useState<string>("");
  const [arenaMaxAge, setArenaMaxAge] = useState<string>("");

  // Set initial filter visibility based on screen size (only on mount, not on resize/scroll)
  const [showFilters, setShowFilters] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth >= 600;
    }
    return true;
  });

  // Search states for comparison block
  const [comparisonPlayer1Search, setComparisonPlayer1Search] = useState<string>("");
  const [comparisonPlayer1Results, setComparisonPlayer1Results] = useState<any[]>([]);
  const [isComparisonPlayer1Searching, setIsComparisonPlayer1Searching] = useState(false);

  const [comparisonPlayer2Search, setComparisonPlayer2Search] = useState<string>("");
  const [comparisonPlayer2Results, setComparisonPlayer2Results] = useState<any[]>([]);
  const [isComparisonPlayer2Searching, setIsComparisonPlayer2Searching] = useState(false);

  // Player comparison state
  const [firstPlayerForComparison, setFirstPlayerForComparison] = useState<{
    player_id: number;
    player_name: string;
    team_name: string | null;
    position: string | null;
    x: number;
    y: number;
    image_url?: string;
    value_m_eur?: number | null;
  } | null>(null);
  const [secondPlayerForComparison, setSecondPlayerForComparison] = useState<{
    player_id: number;
    player_name: string;
    team_name: string | null;
    position: string | null;
    x: number;
    y: number;
    image_url?: string;
    value_m_eur?: number | null;
  } | null>(null);

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


  // Search function for comparison player 1
  const searchComparisonPlayer1 = async (query: string) => {
    if (!query.trim() || query.length < 2) {
      setComparisonPlayer1Results([]);
      setIsComparisonPlayer1Searching(false);
      return;
    }

    setIsComparisonPlayer1Searching(true);
    try {
      const results = await fetchPlayers({
        q: query,
        season: arenaSeason,
        league: arenaLeague !== "Aggregated (All Leagues)" ? arenaLeague : undefined,
        limit: 50,
      });

      let filteredResults = results.items || [];

      // Filter duplicates based on league selection
      if (arenaLeague === "Aggregated (All Leagues)") {
        filteredResults = filteredResults.filter(player =>
          player.league_name === "Aggregated (All Leagues)"
        );
      } else {
        filteredResults = filteredResults.filter(player =>
          player.league_name === arenaLeague
        );
      }

      const uniqueResults = filteredResults.filter((player, index, self) =>
        index === self.findIndex(p => p.player_id === player.player_id)
      );

      setComparisonPlayer1Results(uniqueResults.slice(0, 10));
    } catch (error) {
      console.error('Comparison Player 1 search error:', error);
      setComparisonPlayer1Results([]);
    } finally {
      setIsComparisonPlayer1Searching(false);
    }
  };

  // Search function for comparison player 2
  const searchComparisonPlayer2 = async (query: string) => {
    if (!query.trim() || query.length < 2) {
      setComparisonPlayer2Results([]);
      setIsComparisonPlayer2Searching(false);
      return;
    }

    setIsComparisonPlayer2Searching(true);
    try {
      const results = await fetchPlayers({
        q: query,
        season: arenaSeason,
        league: arenaLeague !== "Aggregated (All Leagues)" ? arenaLeague : undefined,
        limit: 50,
      });

      let filteredResults = results.items || [];

      // Filter duplicates based on league selection
      if (arenaLeague === "Aggregated (All Leagues)") {
        filteredResults = filteredResults.filter(player =>
          player.league_name === "Aggregated (All Leagues)"
        );
      } else {
        filteredResults = filteredResults.filter(player =>
          player.league_name === arenaLeague
        );
      }

      const uniqueResults = filteredResults.filter((player, index, self) =>
        index === self.findIndex(p => p.player_id === player.player_id) &&
        player.player_id !== firstPlayerForComparison?.player_id
      );

      setComparisonPlayer2Results(uniqueResults.slice(0, 10));
    } catch (error) {
      console.error('Comparison Player 2 search error:', error);
      setComparisonPlayer2Results([]);
    } finally {
      setIsComparisonPlayer2Searching(false);
    }
  };

  // Debounced search effects - reduced latency from 300ms to 150ms for faster response
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      searchComparisonPlayer1(comparisonPlayer1Search);
    }, 150);
    return () => clearTimeout(timeoutId);
  }, [comparisonPlayer1Search, arenaSeason, arenaLeague]);

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      searchComparisonPlayer2(comparisonPlayer2Search);
    }, 150);
    return () => clearTimeout(timeoutId);
  }, [comparisonPlayer2Search, firstPlayerForComparison?.player_id, arenaSeason, arenaLeague]);


  // Handler for selecting player 1 from comparison search
  const selectComparisonPlayer1FromSearch = (player: any) => {
    handleReplacePlayer1({
      player_id: player.player_id,
      player_name: player.player_name,
      team_name: player.team_name,
      league_name: player.league_name || "Aggregated (All Leagues)",
      season_label: arenaSeason,
      position: player.position
    });
    setComparisonPlayer1Search("");
    setComparisonPlayer1Results([]);
  };

  // Handler for selecting player 2 from comparison search
  const selectComparisonPlayer2FromSearch = (player: any) => {
    handleReplacePlayer2({
      player_id: player.player_id,
      player_name: player.player_name,
      team_name: player.team_name,
      league_name: player.league_name || "Aggregated (All Leagues)",
      season_label: arenaSeason,
      position: player.position
    });
    setComparisonPlayer2Search("");
    setComparisonPlayer2Results([]);
  };

  const handlePointClick = (data: { player_id: number; player_name: string; team_name: string | null; position: string | null; image_url?: string; value_m_eur?: number | null; x: number; y: number }) => {
    console.log('Player Arena point clicked:', data);

    // If no player selected yet, set as first player
    if (!firstPlayerForComparison) {
      setFirstPlayerForComparison(data);
      console.log('First player selected from chart:', data.player_name);
    }
    // If first player exists but no second player, set as second player (unless same as first)
    else if (!secondPlayerForComparison) {
      if (data.player_id !== firstPlayerForComparison.player_id) {
        setSecondPlayerForComparison(data);
        console.log('Second player selected from chart:', data.player_name);
      } else {
        console.log('Cannot compare player with themselves');
      }
    }
    // If both players exist, replace second player with new selection
    else {
      if (data.player_id !== firstPlayerForComparison.player_id) {
        setSecondPlayerForComparison(data);
        console.log('Second player replaced from chart:', data.player_name);
      }
    }
  };

  const handleClearComparison = () => {
    setFirstPlayerForComparison(null);
    setSecondPlayerForComparison(null);
    console.log('Comparison cleared');
  };

  const handleReplacePlayer1 = (newPlayer: { player_id: number; player_name: string; team_name: string | null; league_name: string; season_label: string; position: string | null; image_url?: string }) => {
    setFirstPlayerForComparison({
      player_id: newPlayer.player_id,
      player_name: newPlayer.player_name,
      team_name: newPlayer.team_name,
      position: newPlayer.position,
      x: 0,
      y: 0,
      image_url: newPlayer.image_url
    });
    console.log('Player 1 replaced with:', newPlayer.player_name);

    // Keep comparison section in view
    setTimeout(() => {
      if (comparisonRef.current) {
        comparisonRef.current.scrollIntoView({
          behavior: 'smooth',
          block: 'center'
        });
      }
    }, 100);
  };

  const handleReplacePlayer2 = (newPlayer: { player_id: number; player_name: string; team_name: string | null; league_name: string; season_label: string; position: string | null; image_url?: string }) => {
    setSecondPlayerForComparison({
      player_id: newPlayer.player_id,
      player_name: newPlayer.player_name,
      team_name: newPlayer.team_name,
      position: newPlayer.position,
      x: 0,
      y: 0,
      image_url: newPlayer.image_url
    });
    console.log('Player 2 replaced with:', newPlayer.player_name);

    // Keep comparison section in view
    setTimeout(() => {
      if (comparisonRef.current) {
        comparisonRef.current.scrollIntoView({
          behavior: 'smooth',
          block: 'center'
        });
      }
    }, 100);
  };


  const arenaChartUrl = new URLSearchParams({
    x: categoryToMetricCode[selectedXMetric] || selectedXMetric,
    y: categoryToMetricCode[selectedYMetric] || selectedYMetric,
    league: arenaLeague,
    season: arenaSeason,
    min_minutes: arenaMinMinutes,
    limit: "20000", // Use maximum allowed limit
    ...(arenaPosition !== "all" && { pos: arenaPosition }),
    ...(arenaTeam !== "All Teams" && { team: arenaTeam }),
    ...(arenaNation !== "All Nations" && { nation: arenaNation }),
    ...(arenaMinValue && { min_value: arenaMinValue }),
    ...(arenaMaxValue && { max_value: arenaMaxValue }),
    ...(arenaMinAge && { min_age: arenaMinAge }),
    ...(arenaMaxAge && { max_age: arenaMaxAge }),
  }).toString();

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <section className="bg-navy text-white py-8 md:py-12 relative">
        <div className="container mx-auto px-2 sm:px-4 text-center">
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold mb-3 md:mb-4 text-white">
            Face-to-Face <span className="text-orange">Player Comparison</span>
          </h1>
          <p className="text-sm sm:text-base md:text-lg text-gray-200 max-w-2xl mx-auto mb-4 md:mb-6 px-2">
            Compare players head-to-head with interactive charts and radar analysis
          </p>
        </div>
      </section>

      {/* Filters Section - AT THE TOP */}
      <section className="py-4 md:py-6 bg-white border-b">
        <div className="container mx-auto px-2 sm:px-4 max-w-5xl">
          <Card className="shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <CardTitle className="text-sm">Chart filters</CardTitle>
                  {!showFilters && (arenaLeague !== "Aggregated (All Leagues)" || arenaSeason !== "2425" || arenaPosition !== "all" || arenaMinMinutes !== "0" || arenaTeam !== "All Teams" || arenaNation !== "All Nations" || arenaMinValue || arenaMaxValue || arenaMinAge || arenaMaxAge) && (
                    <Badge variant="secondary" className="text-xs px-2 py-0">
                      Active
                    </Badge>
                  )}
                </div>
                <CardDescription className="text-xs">
                  {showFilters ? "Customize your player analysis view" : "Click 'Show' to customize filters"}
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
                {(arenaLeague !== "Aggregated (All Leagues)" || arenaSeason !== "2425" || arenaPosition !== "all" || arenaMinMinutes !== "0" || arenaTeam !== "All Teams" || arenaNation !== "All Nations" || arenaMinValue || arenaMaxValue || arenaMinAge || arenaMaxAge) && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSelectedXMetric("finishing");
                      setSelectedYMetric("passing");
                      setArenaLeague("Aggregated (All Leagues)");
                      setArenaSeason("2425");
                      setArenaPosition("all");
                      setArenaMinMinutes("0");
                      setArenaTeam("All Teams");
                      setArenaNation("All Nations");
                      setArenaMinValue("");
                      setArenaMaxValue("");
                      setArenaMinAge("");
                      setArenaMaxAge("");
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
                    value={arenaLeague}
                    onValueChange={setArenaLeague}
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
                        variant={arenaSeason === season ? "default" : "outline"}
                        className={`cursor-pointer px-2 py-0.5 text-xs transition-all duration-200 ${
                          arenaSeason === season
                            ? "bg-navy text-white"
                            : "hover:bg-navy hover:text-white"
                        }`}
                        onClick={() => setArenaSeason(season)}
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
                      value={arenaTeam}
                      onValueChange={(value) => setArenaTeam(value)}
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
                      value={arenaNation}
                      onValueChange={setArenaNation}
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
                  <div className="space-y-1">
                    <Input
                      type="number"
                      value={arenaMinValue}
                      onChange={(e) => setArenaMinValue(e.target.value)}
                      placeholder="Min"
                      className="w-full h-8 text-xs"
                    />
                    <Input
                      type="number"
                      value={arenaMaxValue}
                      onChange={(e) => setArenaMaxValue(e.target.value)}
                      placeholder="Max"
                      className="w-full h-8 text-xs"
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
                      value={arenaMinAge}
                      onChange={(e) => setArenaMinAge(e.target.value)}
                      placeholder="Min"
                      min="15"
                      max="50"
                      className="w-full h-8 text-xs"
                    />
                    <Input
                      type="number"
                      value={arenaMaxAge}
                      onChange={(e) => setArenaMaxAge(e.target.value)}
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
                    variant={arenaPosition === "all" ? "default" : "outline"}
                    className={`cursor-pointer px-2 py-0.5 text-xs transition-all duration-200 ${
                      arenaPosition === "all"
                        ? "bg-navy text-white"
                        : "hover:bg-navy hover:text-white"
                    }`}
                    onClick={() => setArenaPosition("all")}
                  >
                    All
                  </Badge>
                  {positions.map((position) => (
                    <Badge
                      key={position}
                      variant={arenaPosition === position ? "default" : "outline"}
                      className={`cursor-pointer px-2 py-0.5 text-xs transition-all duration-200 ${
                        arenaPosition === position
                          ? "bg-navy text-white"
                          : "hover:bg-navy hover:text-white"
                      }`}
                      onClick={() => setArenaPosition(position)}
                    >
                      {getPositionEmoji(position)} {positionMapping[position] || position}
                    </Badge>
                  ))}
                </div>
              </div>
            </CardContent>
            )}
          </Card>
          </div>
      </section>

      {/* Player Comparison Section */}
      <section className="py-6 md:py-12 bg-gradient-to-br from-blue-50 via-slate-50 to-indigo-100/50">
        <div className="container mx-auto px-2 sm:px-4 max-w-5xl">
          {firstPlayerForComparison && secondPlayerForComparison ? (
            <div ref={comparisonRef}>
              <PlayerComparison
                player1={firstPlayerForComparison}
                player2={secondPlayerForComparison}
                season={arenaSeason}
                league={arenaLeague}
                onClear={handleClearComparison}
                onReplacePlayer1={handleReplacePlayer1}
                onReplacePlayer2={handleReplacePlayer2}
                onSearchPlayer1={setComparisonPlayer1Search}
                onSearchPlayer2={setComparisonPlayer2Search}
                player1SearchQuery={comparisonPlayer1Search}
                player2SearchQuery={comparisonPlayer2Search}
                player1SearchResults={comparisonPlayer1Results}
                player2SearchResults={comparisonPlayer2Results}
                onSelectPlayer1={selectComparisonPlayer1FromSearch}
                onSelectPlayer2={selectComparisonPlayer2FromSearch}
                isSearching1={isComparisonPlayer1Searching}
                isSearching2={isComparisonPlayer2Searching}
              />
            </div>
          ) : (
            <Card className="mb-6 shadow-lg border-2 border-dashed border-accent/30">
              <CardContent className="pt-8 pb-8">
                <div className="text-center mb-4 md:mb-6">
                  <div className="text-3xl md:text-4xl mb-3 md:mb-4">⚔️</div>
                  <h3 className="text-lg sm:text-xl font-bold text-navy mb-2 px-2">Select Two Players to Compare</h3>
                  <p className="text-sm sm:text-base text-gray-600 mb-4 md:mb-6 px-2">
                    Search for players below or click on the scatter plot to select players for comparison
                  </p>
                  {firstPlayerForComparison && !secondPlayerForComparison && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 inline-block mb-6">
                      <div className="text-sm text-blue-700 font-medium mb-2">
                        ✅ First player selected: <strong>{firstPlayerForComparison.player_name}</strong>
                      </div>
                      <div className="text-xs text-blue-600">
                        Now select a second player using the search or chart below
                      </div>
                    </div>
                  )}
                </div>

                {/* Search bars in empty state */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
                  {/* Player 1 Search - uses comparison search */}
                  <div className="p-4 bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg border-2 border-blue-200">
                    <div className="text-center mb-3">
                      <div className="text-3xl mb-2">👤</div>
                      <h4 className="text-sm font-bold text-blue-700">Player 1</h4>
                    </div>
                    <div className="relative">
                      <Input
                        type="text"
                        placeholder={`Search in ${formatSeason(arenaSeason)}${arenaLeague !== "Aggregated (All Leagues)" ? ` - ${arenaLeague}` : ""}...`}
                        value={comparisonPlayer1Search}
                        onChange={(e) => setComparisonPlayer1Search(e.target.value)}
                        className="w-full border-blue-300 focus:border-blue-500 focus:ring-blue-500"
                      />
                      {isComparisonPlayer1Searching && (
                        <div className="absolute right-3 top-3">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
                        </div>
                      )}

                      {/* Search Results Dropdown */}
                      {comparisonPlayer1Results.length > 0 && (
                        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-blue-200 rounded-lg shadow-lg z-50 max-h-60 overflow-y-auto">
                          {comparisonPlayer1Results.map((player) => (
                            <div
                              key={player.player_id}
                              onClick={() => selectComparisonPlayer1FromSearch(player)}
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
                  </div>

                  {/* Player 2 Search - uses comparison search */}
                  <div className="p-4 bg-gradient-to-br from-red-50 to-red-100 rounded-lg border-2 border-red-200">
                    <div className="text-center mb-3">
                      <div className="text-3xl mb-2">👤</div>
                      <h4 className="text-sm font-bold text-red-700">Player 2</h4>
                    </div>
                    <div className="relative">
                      <Input
                        type="text"
                        placeholder={`Search in ${formatSeason(arenaSeason)}${arenaLeague !== "Aggregated (All Leagues)" ? ` - ${arenaLeague}` : ""}...`}
                        value={comparisonPlayer2Search}
                        onChange={(e) => setComparisonPlayer2Search(e.target.value)}
                        className="w-full border-red-300 focus:border-red-500 focus:ring-red-500"
                        disabled={!firstPlayerForComparison}
                      />
                      {isComparisonPlayer2Searching && (
                        <div className="absolute right-3 top-3">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-red-500"></div>
                        </div>
                      )}

                      {/* Search Results Dropdown */}
                      {comparisonPlayer2Results.length > 0 && (
                        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-red-200 rounded-lg shadow-lg z-50 max-h-60 overflow-y-auto">
                          {comparisonPlayer2Results.map((player) => (
                            <div
                              key={player.player_id}
                              onClick={() => selectComparisonPlayer2FromSearch(player)}
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

                      {!firstPlayerForComparison && (
                        <div className="text-xs text-red-600 mt-2 text-center italic">
                          Select Player 1 first
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </section>

      {/* Player Search and Scatter Plot Section */}
      <section className="py-6 md:py-12 bg-white">
        <div className="container mx-auto px-2 sm:px-4 max-w-5xl">
          {/* Main Chart Area */}
          <div className="grid grid-cols-12 gap-4">
            {/* Chart Area - Full Width */}
            <div className="col-span-12">
              {/* Chart */}
              <Card>
                <CardHeader className="pb-2 md:pb-3">
                  <CardTitle className="text-center text-sm sm:text-base">
                    {availableMetricCategories.find(c => c.category.toLowerCase() === selectedXMetric)?.category || selectedXMetric} vs{" "}
                    {availableMetricCategories.find(c => c.category.toLowerCase() === selectedYMetric)?.category || selectedYMetric}
                  </CardTitle>
                  <CardDescription className="text-center">
                    <span className="text-blue-600 text-xs sm:text-sm">
                      {firstPlayerForComparison && secondPlayerForComparison ? (
                        <span className="block text-xs text-green-600 flex items-center justify-center gap-1">
                          ✅ Both players selected - scroll up to see comparison
                          <span className="animate-bounce">⬆️</span>
                        </span>
                      ) : firstPlayerForComparison ? (
                        <>
                          💡 Click another player to compare with <strong>{firstPlayerForComparison.player_name}</strong>
                        </>
                      ) : (
                        <>
                          💡 Click on any player to start comparison
                        </>
                      )}
                    </span>
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <InteractiveChart
                    src={`/api/scatter?${arenaChartUrl}`}
                    title={`${selectedXMetric} vs ${selectedYMetric}`}
                    xLabel={availableMetricCategories.find(c => c.category.toLowerCase() === selectedXMetric)?.category || selectedXMetric}
                    yLabel={availableMetricCategories.find(c => c.category.toLowerCase() === selectedYMetric)?.category || selectedYMetric}
                    selectedPlayer={null}
                    shouldZoomOnSelected={false}
                    comparisonPlayers={[firstPlayerForComparison, secondPlayerForComparison].filter(Boolean).map(p => ({ player_id: p!.player_id }))}
                    onPointClick={handlePointClick}
                  />
                </CardContent>
              </Card>

              {/* Metric Selectors - Compact Design */}
              <Card className="mt-3 md:mt-4 shadow-sm">
                <CardContent className="pt-3 md:pt-4 pb-2 md:pb-3">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
                    {/* X Axis Selector */}
                    <div className="space-y-1.5 md:space-y-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs sm:text-sm font-semibold text-blue-600">📊 X Axis</span>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {availableMetricCategories.filter(category => !category.isGoalkeeper && category.category !== "Discipline").map((category) => (
                          <button
                            key={category.category}
                            type="button"
                            onClick={() => setSelectedXMetric(category.category.toLowerCase())}
                            className={`
                              px-2 py-1 rounded text-xs font-medium transition-all duration-200
                              ${
                                selectedXMetric === category.category.toLowerCase()
                                  ? "bg-blue-500 text-white shadow-sm"
                                  : "bg-white text-primary border border-slate-200 hover:border-blue-400 hover:bg-blue-50"
                              }
                            `}
                          >
                            {category.category === "Finishing" && "⚽"}
                            {category.category === "Penalty" && "🎯"}
                            {category.category === "Passing" && "🎨"}
                            {category.category === "Defense" && "🛡️"}
                            {category.category === "Dribbling" && "⚡"}
                            {category.category === "Aerial" && "🦅"}
                            <span className="ml-1">{category.category}</span>
                          </button>
                        ))}
                        {availableMetricCategories.filter(category => category.isGoalkeeper).map((category) => (
                          <button
                            key={category.category}
                            type="button"
                            onClick={() => setSelectedXMetric(category.category.toLowerCase())}
                            className={`
                              px-2 py-1 rounded text-xs font-medium transition-all duration-200
                              ${
                                selectedXMetric === category.category.toLowerCase()
                                  ? "bg-blue-500 text-white shadow-sm"
                                  : "bg-white text-primary border border-slate-200 hover:border-blue-400 hover:bg-blue-50"
                              }
                            `}
                          >
                            {category.category.toLowerCase().includes("reflexes") && "🥅"}
                            {category.category.toLowerCase().includes("footwork") && "👟"}
                            {category.category.toLowerCase().includes("air") && "☁️"}
                            {category.category.toLowerCase().includes("sweeper") && "🧹"}
                            {category.category.toLowerCase().includes("penalty") && "🎯"}
                            <span className="ml-1">{category.category}</span>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Y Axis Selector */}
                    <div className="space-y-1.5 md:space-y-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs sm:text-sm font-semibold text-green-600">📈 Y Axis</span>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {availableMetricCategories.filter(category => !category.isGoalkeeper && category.category !== "Discipline").map((category) => (
                          <button
                            key={category.category}
                            type="button"
                            onClick={() => setSelectedYMetric(category.category.toLowerCase())}
                            className={`
                              px-2 py-1 rounded text-xs font-medium transition-all duration-200
                              ${
                                selectedYMetric === category.category.toLowerCase()
                                  ? "bg-green-500 text-white shadow-sm"
                                  : "bg-white text-primary border border-slate-200 hover:border-green-400 hover:bg-green-50"
                              }
                            `}
                          >
                            {category.category === "Finishing" && "⚽"}
                            {category.category === "Penalty" && "🎯"}
                            {category.category === "Passing" && "🎨"}
                            {category.category === "Defense" && "🛡️"}
                            {category.category === "Dribbling" && "⚡"}
                            {category.category === "Aerial" && "🦅"}
                            <span className="ml-1">{category.category}</span>
                          </button>
                        ))}
                        {availableMetricCategories.filter(category => category.isGoalkeeper).map((category) => (
                          <button
                            key={category.category}
                            type="button"
                            onClick={() => setSelectedYMetric(category.category.toLowerCase())}
                            className={`
                              px-2 py-1 rounded text-xs font-medium transition-all duration-200
                              ${
                                selectedYMetric === category.category.toLowerCase()
                                  ? "bg-green-500 text-white shadow-sm"
                                  : "bg-white text-primary border border-slate-200 hover:border-green-400 hover:bg-green-50"
                              }
                            `}
                          >
                            {category.category.toLowerCase().includes("reflexes") && "🥅"}
                            {category.category.toLowerCase().includes("footwork") && "👟"}
                            {category.category.toLowerCase().includes("air") && "☁️"}
                            {category.category.toLowerCase().includes("sweeper") && "🧹"}
                            {category.category.toLowerCase().includes("penalty") && "🎯"}
                            <span className="ml-1">{category.category}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* Call to Action & Feedback Section - Side by Side */}
      <section className="py-6 md:py-10 bg-gradient-to-br from-emerald-50 via-teal-50 to-green-50">
        <div className="container mx-auto px-2 sm:px-4 max-w-5xl">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Similarity Search CTA */}
            <Card className="border-2 border-emerald-200 shadow-xl">
                <CardContent className="pt-6 pb-6 px-4 sm:pt-7 sm:pb-7 sm:px-6">
                  <div className="text-center">
                    <h2 className="text-xl sm:text-2xl font-bold text-navy mb-3 px-2">
                      Discover Similar Players
                    </h2>
                    <p className="text-sm sm:text-base text-gray-600 mb-4 sm:mb-5 px-2">
                      Find players with similar playing styles and characteristics.
                      Search by name and get instant recommendations based on performance metrics and attributes.
                    </p>

                    <Button
                      asChild
                      size="lg"
                      className="bg-gradient-to-r from-emerald-600 to-teal-600 text-white hover:from-emerald-700 hover:to-teal-700 font-bold px-4 sm:px-5 py-3 sm:py-4 text-sm sm:text-base shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 w-full sm:w-auto"
                    >
                      <Link href="/similarity-search">
                        Try Similarity Search
                      </Link>
                    </Button>
                  </div>
                </CardContent>
              </Card>

            {/* Inline Feedback */}
            <InlineFeedback context="face-to-face" />
          </div>
        </div>
      </section>
    </div>
  );
}

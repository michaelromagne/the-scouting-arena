"use client";

import { useState, useMemo, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { fetchPlayers, fetchLeagues, fetchSeasons, fetchTeams, fetchNations, fetchPositions } from "@/lib/api";
import { POSITION_MAPPING, DEFAULT_FILTERS, getCountryName } from "@/lib/constants";
import { formatSeason } from "@/lib/utils";
import BookmarkButton from "@/components/BookmarkButton";
import { InlineFeedback } from "@/components/InlineFeedback";

// Enhanced spinner component with visible blue rotating animation
function LoadingSpinner() {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="spinner-loading rounded-full h-12 w-12 border-4 border-gray-200 border-t-blue-500"></div>
      <div className="mt-4 text-slate-600 font-medium animate-pulse">
        Loading players...
      </div>
      <div className="text-sm text-slate-400 mt-1">
        Searching through 5000+ player profiles
      </div>
    </div>
  );
}

export default function TalentPoolPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedLeague, setSelectedLeague] = useState<string>(DEFAULT_FILTERS.league);
  const [selectedSeason, setSelectedSeason] = useState<string>(DEFAULT_FILTERS.season);
  const [selectedTeam, setSelectedTeam] = useState<string>(DEFAULT_FILTERS.team);
  const [selectedNation, setSelectedNation] = useState<string>(DEFAULT_FILTERS.nation);
  const [selectedPosition, setSelectedPosition] = useState<string>(DEFAULT_FILTERS.position);
  const [currentPage, setCurrentPage] = useState(1);
  const [playersPerPage, setPlayersPerPage] = useState(25);
  const [pageInput, setPageInput] = useState("");
  // Set initial filter visibility based on screen size (only on mount, not on resize/scroll)
  const [showFilters, setShowFilters] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth >= 600;
    }
    return true;
  });

  // Fetch players with current filters
  const { data: playersData, isLoading: playersLoading, error: playersError } = useQuery({
    queryKey: ["players", {
      league: selectedLeague,
      season: selectedSeason,
      team: selectedTeam !== "All Teams" ? selectedTeam : undefined,
      position: selectedPosition !== "All Positions" ? selectedPosition : undefined,
      limit: 50000, // Fetch all players - 2268 total in DB
      q: searchQuery.length > 2 ? searchQuery : undefined
    }],
    queryFn: () => fetchPlayers({
      league: selectedLeague,
      season: selectedSeason,
      team: selectedTeam !== "All Teams" ? selectedTeam : undefined,
      position: selectedPosition !== "All Positions" ? selectedPosition : undefined,
      limit: 50000,
      q: searchQuery.length > 2 ? searchQuery : undefined
    }),
    staleTime: 1000 * 60 * 5,
  });

  // Players successfully loaded - fetching all players from database

  // Fetch leagues and seasons for filters
  const { data: leagues = [] } = useQuery({
    queryKey: ["leagues"],
    queryFn: fetchLeagues,
  });

  const { data: seasons = [] } = useQuery({
    queryKey: ["seasons"],
    queryFn: fetchSeasons,
  });

  // Fetch teams for filter
  const { data: teams = [] } = useQuery({
    queryKey: ["teams"],
    queryFn: fetchTeams,
    staleTime: 1000 * 60 * 10,
  });

  // Fetch nations and positions for filters
  const { data: nations = [] } = useQuery({
    queryKey: ["nations"],
    queryFn: fetchNations,
    staleTime: 1000 * 60 * 10,
  });

  const { data: positions = [] } = useQuery({
    queryKey: ["positions"],
    queryFn: fetchPositions,
    staleTime: 1000 * 60 * 10,
  });

  // Process teams for searchable filter (same logic as rankings/scatter)
  const uniqueTeams = useMemo(() => {
    const teamSet = new Set<string>();
    teams.forEach((team) => {
      if (team.includes(" & ")) {
        // Handle combined teams like "Aston Villa & Manchester United"
        team.split(" & ").forEach((t) => teamSet.add(t.trim()));
      } else {
        teamSet.add(team);
      }
    });
    return Array.from(teamSet).sort();
  }, [teams]);

  // Fetch hot players for different categories
  const { data: topScorers } = useQuery({
    queryKey: ["rankings", "shooting", selectedLeague, selectedSeason],
    queryFn: async () => {
      const response = await fetch(`/api/rankings?metric=finishing&league=${encodeURIComponent(selectedLeague)}&season=${selectedSeason}&limit=5&min_minutes=0`);
      return response.json();
    },
    staleTime: 1000 * 60 * 10,
  });

  const { data: topPassers } = useQuery({
    queryKey: ["rankings", "passing", selectedLeague, selectedSeason],
    queryFn: async () => {
      const response = await fetch(`/api/rankings?metric=passing&league=${encodeURIComponent(selectedLeague)}&season=${selectedSeason}&limit=5&min_minutes=0`);
      return response.json();
    },
    staleTime: 1000 * 60 * 10,
  });

  const { data: topDefenders } = useQuery({
    queryKey: ["rankings", "defense", selectedLeague, selectedSeason],
    queryFn: async () => {
      const response = await fetch(`/api/rankings?metric=defense&league=${encodeURIComponent(selectedLeague)}&season=${selectedSeason}&limit=5&min_minutes=0`);
      return response.json();
    },
    staleTime: 1000 * 60 * 10,
  });

  // Filter and sort players
  const filteredAndSortedPlayers = useMemo(() => {
    if (!playersData?.items) return [];

    let filtered = playersData.items;

    // Debug: Log first few players to check market value data
    console.log('🔍 Top 5 players with market values:',
      filtered.slice(0, 5).map(p => ({
        name: p.player_name,
        value: p.market_value_eur
      }))
    );

    // Client-side search if query is short (server doesn't handle it)
    if (searchQuery && searchQuery.length <= 2) {
      filtered = filtered.filter(player =>
        player.player_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (player.team_name && player.team_name.toLowerCase().includes(searchQuery.toLowerCase()))
      );
    }

    // Sort by market value descending, then by name for consistent display
    return filtered.sort((a, b) => {
      const valueA = a.market_value_eur;
      const valueB = b.market_value_eur;

      // Players with no market value go to the end
      if (valueA == null && valueB == null) {
        return a.player_name.localeCompare(b.player_name);
      }
      if (valueA == null) return 1; // a goes after b
      if (valueB == null) return -1; // b goes after a

      // Both have values, sort by value descending
      if (valueB !== valueA) {
        return valueB - valueA;
      }

      // If market values are equal, sort by name
      return a.player_name.localeCompare(b.player_name);
    });

    // Debug: Log first few sorted players
    console.log('✅ Top 5 sorted players:',
      filtered.slice(0, 5).map(p => ({
        name: p.player_name,
        value: p.market_value_eur
      }))
    );

    return filtered;
  }, [playersData, searchQuery]);

  // Pagination
  // Pagination handlers
  const handlePageSizeChange = (newSize: number) => {
    setPlayersPerPage(newSize);
    setCurrentPage(1); // Reset to first page when changing page size
  };

  const handlePageInputSubmit = () => {
    const pageNum = parseInt(pageInput);
    if (pageNum >= 1 && pageNum <= totalPages) {
      setCurrentPage(pageNum);
    }
    setPageInput("");
  };

  const handlePageInputKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handlePageInputSubmit();
    }
  };

  const totalPlayers = filteredAndSortedPlayers.length;
  const totalPages = Math.ceil(totalPlayers / playersPerPage);
  const startIndex = (currentPage - 1) * playersPerPage;
  const paginatedPlayers = filteredAndSortedPlayers.slice(startIndex, startIndex + playersPerPage);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header Section */}
      <section className="bg-navy text-white py-8">
        <div className="container mx-auto px-4">
          <div className="text-center">
            <h1 className="text-3xl md:text-4xl font-bold mb-2">
              Talent Pool
            </h1>
            <p className="text-base text-gray-200 mb-4">
              Discover {playersData?.total || "5000+"} professional footballers across top leagues
            </p>
          </div>
        </div>
      </section>

      {/* Filters */}
      <section className="bg-white border-b border-gray-200 py-6">
        <div className="container mx-auto px-4">
          <Card className="shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <CardTitle className="text-sm">Search & Filters</CardTitle>
                  {!showFilters && (selectedLeague !== DEFAULT_FILTERS.league || selectedSeason !== DEFAULT_FILTERS.season || selectedTeam !== DEFAULT_FILTERS.team || selectedNation !== DEFAULT_FILTERS.nation || selectedPosition !== DEFAULT_FILTERS.position || searchQuery) && (
                    <Badge variant="secondary" className="text-xs px-2 py-0">
                      Active
                    </Badge>
                  )}
                </div>
                <CardDescription className="text-xs">
                  {showFilters ? "Find players by name, team, league, and more" : "Click 'Show' to customize filters"}
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
                {(selectedLeague !== DEFAULT_FILTERS.league || selectedSeason !== DEFAULT_FILTERS.season || selectedTeam !== DEFAULT_FILTERS.team || selectedNation !== DEFAULT_FILTERS.nation || selectedPosition !== DEFAULT_FILTERS.position || searchQuery) && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSearchQuery("");
                      setSelectedLeague(DEFAULT_FILTERS.league);
                      setSelectedSeason(DEFAULT_FILTERS.season);
                      setSelectedTeam(DEFAULT_FILTERS.team);
                      setSelectedNation("All Nations");
                      setSelectedPosition("All Positions");
                      setCurrentPage(1);
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
              {/* Search Bar */}
              <div className="mb-4">
                <Input
                  placeholder="🔍 Search player name (e.g. Mbappe, Lewandowski, etc.)"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="h-9 text-sm"
                />
              </div>

              {/* Filter Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                {/* League Filter */}
                <div className="space-y-1.5">
                  <div className="flex items-center gap-1">
                    <span className="text-sm">🏆</span>
                    <label className="text-xs font-medium text-primary">League</label>
                  </div>
                  <Select
                    value={selectedLeague}
                    onValueChange={(value) => {
                      setSelectedLeague(value);
                      setCurrentPage(1);
                    }}
                  >
                    <SelectTrigger className="w-full h-8 text-xs bg-white text-gray-900 border-gray-300 hover:border-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                      <SelectValue placeholder="Select league" />
                    </SelectTrigger>
                    <SelectContent>
                      {leagues.map((league) => (
                        <SelectItem key={league} value={league} className="text-xs">
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
                          setSelectedSeason(season);
                          setCurrentPage(1);
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
                  <Select
                    value={selectedTeam}
                    onValueChange={(value) => {
                      setSelectedTeam(value);
                      setCurrentPage(1);
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

                {/* Nation Filter */}
                <div className="space-y-1.5">
                  <div className="flex items-center gap-1">
                    <span className="text-sm">🌍</span>
                    <label className="text-xs font-medium text-primary">Nation</label>
                  </div>
                  <Select
                    value={selectedNation}
                    onValueChange={(value) => {
                      setSelectedNation(value);
                      setCurrentPage(1);
                    }}
                  >
                    <SelectTrigger className="w-full h-8 text-xs bg-white text-gray-900 border-gray-300 hover:border-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                      <SelectValue placeholder="Select nation" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="All Nations" className="text-xs">All Nations</SelectItem>
                      {nations
                        .filter((nation) => nation !== "0")
                        .sort((a, b) => getCountryName(a).localeCompare(getCountryName(b)))
                        .map((nation) => (
                          <SelectItem key={nation} value={nation} className="text-xs">
                            {getCountryName(nation)}
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Position Filter */}
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
                        setSelectedPosition("All Positions");
                        setCurrentPage(1);
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
                          setSelectedPosition(position);
                          setCurrentPage(1);
                        }}
                      >
                        {POSITION_MAPPING[position] || position}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
            )}
          </Card>

          {/* Stats Summary */}
          <div className="flex flex-wrap justify-center gap-2 mt-4 text-xs">
            <Badge variant="secondary" className="px-3 py-1">
              {totalPlayers} players found
            </Badge>
            {selectedTeam !== "All Teams" && (
              <Badge variant="outline" className="bg-blue-50 text-blue-700 px-3 py-1">
                Team: {selectedTeam}
              </Badge>
            )}
            {selectedNation !== "All Nations" && (
              <Badge variant="outline" className="bg-green-50 text-green-700 px-3 py-1">
                Nation: {getCountryName(selectedNation)}
              </Badge>
            )}
            {selectedPosition !== "All Positions" && (
              <Badge variant="outline" className="bg-purple-50 text-purple-700 px-3 py-1">
                {POSITION_MAPPING[selectedPosition] || selectedPosition}
              </Badge>
            )}
            {playersError && (
              <Badge variant="destructive" className="px-3 py-1">
                API Error
              </Badge>
            )}
          </div>
        </div>
      </section>

      {/* Top Players Cards */}
      <section className="py-4 bg-gray-50">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-3 gap-4">
            {/* Top Scorers */}
            <Card>
              <CardHeader className="pb-0">
                <div className="flex items-center gap-1.5">
                  <div className="w-6 h-6 rounded-full bg-red-100 flex items-center justify-center">
                    <span className="text-xs">⚽</span>
                  </div>
                  <div>
                    <CardTitle className="text-xs text-red-600">Top Scorers</CardTitle>
                    <CardDescription className="text-xs">Best finishing metrics</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-0.5 pt-0 -mt-2">
                {topScorers?.items?.slice(0, 5).map((player: any, index: number) => (
                  <Link key={player.player_id} href={`/talent-pool/${player.player_id}`}>
                    <div className="flex items-center gap-1.5 p-1 rounded hover:bg-red-50 transition-colors cursor-pointer">
                      <span className="text-xs font-bold text-red-600 w-4">#{index + 1}</span>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-xs text-navy truncate">{player.player_name}</p>
                        <p className="text-xs text-gray-500 truncate">{player.team_name}</p>
                      </div>
                      <Badge variant="secondary" className="text-xs px-1 py-0">{player.quantile_value?.toFixed(1)}</Badge>
                    </div>
                  </Link>
                ))}
                <Link href="/#rankings-section" className="block">
                  <Button variant="outline" size="sm" className="w-full text-red-600 border-red-200 hover:bg-red-50 text-xs">
                    View All →
                  </Button>
                </Link>
              </CardContent>
            </Card>

            {/* Top Passers */}
            <Card>
              <CardHeader className="pb-0">
                <div className="flex items-center gap-1.5">
                  <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center">
                    <span className="text-xs">🎯</span>
                  </div>
                  <div>
                    <CardTitle className="text-xs text-blue-600">Top Passers</CardTitle>
                    <CardDescription className="text-xs">Best passing metrics</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-0.5 pt-0 -mt-2">
                {topPassers?.items?.slice(0, 5).map((player: any, index: number) => (
                  <Link key={player.player_id} href={`/talent-pool/${player.player_id}`}>
                    <div className="flex items-center gap-1.5 p-1 rounded hover:bg-blue-50 transition-colors cursor-pointer">
                      <span className="text-xs font-bold text-blue-600 w-4">#{index + 1}</span>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-xs text-navy truncate">{player.player_name}</p>
                        <p className="text-xs text-gray-500 truncate">{player.team_name}</p>
                      </div>
                      <Badge variant="secondary" className="text-xs px-1 py-0">{player.quantile_value?.toFixed(1)}</Badge>
                    </div>
                  </Link>
                ))}
                <Link href="/#rankings-section" className="block">
                  <Button variant="outline" size="sm" className="w-full text-blue-600 border-blue-200 hover:bg-blue-50 text-xs">
                    View All →
                  </Button>
                </Link>
              </CardContent>
            </Card>

            {/* Top Defenders */}
            <Card>
              <CardHeader className="pb-0">
                <div className="flex items-center gap-1.5">
                  <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center">
                    <span className="text-xs">🛡️</span>
                  </div>
                  <div>
                    <CardTitle className="text-xs text-green-600">Top Defenders</CardTitle>
                    <CardDescription className="text-xs">Best defensive metrics</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-0.5 pt-0 -mt-2">
                {topDefenders?.items?.slice(0, 5).map((player: any, index: number) => (
                  <Link key={player.player_id} href={`/talent-pool/${player.player_id}`}>
                    <div className="flex items-center gap-1.5 p-1 rounded hover:bg-green-50 transition-colors cursor-pointer">
                      <span className="text-xs font-bold text-green-600 w-4">#{index + 1}</span>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-xs text-navy truncate">{player.player_name}</p>
                        <p className="text-xs text-gray-500 truncate">{player.team_name}</p>
                      </div>
                      <Badge variant="secondary" className="text-xs px-1 py-0">{player.quantile_value?.toFixed(1)}</Badge>
                    </div>
                  </Link>
                ))}
                <Link href="/#rankings-section" className="block">
                  <Button variant="outline" size="sm" className="w-full text-green-600 border-green-200 hover:bg-green-50 text-xs">
                    View All →
                  </Button>
                </Link>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Main Content: Player Database */}
      <section className="py-8 bg-white">
        <div className="container mx-auto px-4">
          <div className="mb-6">
            <p className="text-gray-600 text-center">Dive into our comprehensive talent pool</p>
          </div>

          {playersLoading ? (
            <LoadingSpinner />
          ) : playersError ? (
            <div className="text-center py-16">
              <div className="mb-6">
                <div className="w-16 h-16 bg-red-200 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-gray-700 mb-2">Error loading players</h3>
                <p className="text-gray-500 mb-4">
                  {(playersError as Error)?.message || "Failed to load players from the database"}
                </p>
                <p className="text-xs text-gray-400">
                  Check the console for more details
                </p>
              </div>
            </div>
          ) : paginatedPlayers.length > 0 ? (
            <>
              <div className="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 mb-8">
                {paginatedPlayers.map((player, index) => {
                  const age = player.birth_date
                    ? new Date().getFullYear() - new Date(player.birth_date).getFullYear()
                    : null;

                  return (
                    <div key={`${player.player_id}-${player.season_label}-${player.league_name}-${index}`}>
                      <Card className="h-full hover:shadow-lg transition-all duration-200 hover:-translate-y-0.5">
                        <CardContent className="p-2">
                          <div className="text-center">
                            {/* Player Photo */}
                            <Link href={`/talent-pool/${player.player_id}`} className="group block">
                              <div className="w-12 h-12 rounded-full overflow-hidden mx-auto mb-2 group-hover:scale-105 transition-transform">
                                <img
                                  src={player.image_url || "https://via.placeholder.com/48x48/0B1B3F/ffffff?text=👤"}
                                  alt={player.player_name}
                                  className="w-full h-full object-cover"
                                  style={{ objectPosition: 'center 20%' }}
                                  onError={(e) => {
                                    // Fallback to letter avatar if image fails to load
                                    const target = e.target as HTMLImageElement;
                                    target.style.display = 'none';
                                    const fallback = target.nextElementSibling as HTMLElement;
                                    if (fallback) fallback.style.display = 'flex';
                                  }}
                                />
                                {/* Fallback letter avatar */}
                                <div className="w-12 h-12 bg-gradient-to-br from-navy to-blue-600 rounded-full flex items-center justify-center text-white text-lg font-bold" style={{ display: 'none' }}>
                                  {player.player_name.charAt(0).toUpperCase()}
                                </div>
                              </div>

                              <h3 className="font-semibold text-navy text-xs mb-1 group-hover:text-green transition-colors">
                                {player.player_name}
                              </h3>
                            </Link>

                            <div className="space-y-0.5 mb-2">
                              {player.team_name && (
                                <p className="text-xs text-gray-600 truncate">{player.team_name}</p>
                              )}
                              <div className="flex flex-wrap justify-center gap-0.5">
                                {player.position && (
                                  <Badge variant="outline" className="text-xs px-1 py-0">
                                    {POSITION_MAPPING[player.position] || player.position}
                                  </Badge>
                                )}
                                <Badge variant="outline" className="text-xs px-1 py-0">
                                  {player.season_label ? formatSeason(player.season_label) : 'N/A'}
                                </Badge>
                              </div>

                              {/* Additional Info Badges */}
                              <div className="flex flex-wrap justify-center gap-0.5 mt-1">
                                {age && age > 0 && (
                                  <Badge variant="outline" className="text-xs px-1 py-0 bg-blue-50 text-blue-700 border-blue-500">
                                    {age} yo
                                  </Badge>
                                )}
                                {player.nationality && (
                                  <Badge variant="outline" className="text-xs px-1 py-0 bg-purple-50 text-purple-700 border-purple-500">
                                    {getCountryName(player.nationality)}
                                  </Badge>
                                )}
                                {player.market_value_eur !== null && player.market_value_eur !== undefined && player.market_value_eur > 0 && (
                                  <Badge variant="outline" className="text-xs px-1 py-0 bg-emerald-50 text-emerald-700 border-emerald-600 font-semibold">
                                    €{player.market_value_eur.toFixed(1)}M
                                  </Badge>
                                )}
                              </div>
                            </div>

                            {/* Bookmark Button */}
                            <div className="mt-2">
                              <BookmarkButton
                                // Backend returns one row per player-season; `player_id` is actually the player_season_id.
                                playerSeasonId={player.player_id}
                                variant="outline"
                                size="sm"
                                className="w-full text-xs h-7"
                              />
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  );
                })}
              </div>

              {/* Enhanced Pagination */}
              {totalPages > 1 && (
                <div className="space-y-4">
                  {/* Pagination Info and Controls */}
                  <div className="flex flex-col sm:flex-row justify-between items-center gap-4 p-4 bg-gray-50 rounded-lg">
                    {/* Left: Page Info */}
                    <div className="flex items-center gap-4 text-sm text-gray-600">
                      <span>
                        Showing <span className="font-semibold text-navy">{startIndex + 1}</span> to{' '}
                        <span className="font-semibold text-navy">{Math.min(startIndex + playersPerPage, totalPlayers)}</span> of{' '}
                        <span className="font-semibold text-navy">{totalPlayers}</span> players
                      </span>
                    </div>

                    {/* Right: Page Size Selector */}
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-gray-600">Show:</span>
                      <Select value={playersPerPage.toString()} onValueChange={(value) => handlePageSizeChange(parseInt(value))}>
                        <SelectTrigger className="w-20 h-8">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="25">25</SelectItem>
                          <SelectItem value="50">50</SelectItem>
                          <SelectItem value="100">100</SelectItem>
                          <SelectItem value="200">200</SelectItem>
                        </SelectContent>
                      </Select>
                      <span className="text-gray-600">per page</span>
                    </div>
                  </div>

                  {/* Main Pagination Controls */}
                  <div className="flex flex-col sm:flex-row justify-center items-center gap-4">
                    {/* Left: Navigation Buttons */}
                    <div className="flex items-center gap-1">
                      {/* First Page */}
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPage(1)}
                        disabled={currentPage === 1}
                        className="px-3"
                      >
                        ⏮️ First
                      </Button>

                      {/* Previous Page */}
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                        disabled={currentPage === 1}
                      >
                        ← Prev
                      </Button>
                    </div>

                    {/* Center: Page Numbers with Ellipses */}
                    <div className="flex items-center gap-1">
                      {(() => {
                        const pages = [];
                        const maxVisible = 5;

                        if (totalPages <= maxVisible + 2) {
                          // Show all pages if total is small
                          for (let i = 1; i <= totalPages; i++) {
                            pages.push(
                              <Button
                                key={i}
                                variant={i === currentPage ? "default" : "outline"}
                                size="sm"
                                onClick={() => setCurrentPage(i)}
                                className={`min-w-[40px] ${i === currentPage ? "bg-navy" : ""}`}
                              >
                                {i}
                              </Button>
                            );
                          }
                        } else {
                          // Complex logic with ellipses
                          if (currentPage <= 3) {
                            // Near start
                            for (let i = 1; i <= 4; i++) {
                              pages.push(
                                <Button
                                  key={i}
                                  variant={i === currentPage ? "default" : "outline"}
                                  size="sm"
                                  onClick={() => setCurrentPage(i)}
                                  className={`min-w-[40px] ${i === currentPage ? "bg-navy" : ""}`}
                                >
                                  {i}
                                </Button>
                              );
                            }
                            pages.push(<span key="ellipsis1" className="px-2 text-gray-400">...</span>);
                            pages.push(
                              <Button
                                key={totalPages}
                                variant="outline"
                                size="sm"
                                onClick={() => setCurrentPage(totalPages)}
                                className="min-w-[40px]"
                              >
                                {totalPages}
                              </Button>
                            );
                          } else if (currentPage >= totalPages - 2) {
                            // Near end
                            pages.push(
                              <Button
                                key={1}
                                variant="outline"
                                size="sm"
                                onClick={() => setCurrentPage(1)}
                                className="min-w-[40px]"
                              >
                                1
                              </Button>
                            );
                            pages.push(<span key="ellipsis2" className="px-2 text-gray-400">...</span>);
                            for (let i = totalPages - 3; i <= totalPages; i++) {
                              pages.push(
                                <Button
                                  key={i}
                                  variant={i === currentPage ? "default" : "outline"}
                                  size="sm"
                                  onClick={() => setCurrentPage(i)}
                                  className={`min-w-[40px] ${i === currentPage ? "bg-navy" : ""}`}
                                >
                                  {i}
                                </Button>
                              );
                            }
                          } else {
                            // In middle
                            pages.push(
                              <Button
                                key={1}
                                variant="outline"
                                size="sm"
                                onClick={() => setCurrentPage(1)}
                                className="min-w-[40px]"
                              >
                                1
                              </Button>
                            );
                            pages.push(<span key="ellipsis3" className="px-2 text-gray-400">...</span>);
                            for (let i = currentPage - 1; i <= currentPage + 1; i++) {
                              pages.push(
                                <Button
                                  key={i}
                                  variant={i === currentPage ? "default" : "outline"}
                                  size="sm"
                                  onClick={() => setCurrentPage(i)}
                                  className={`min-w-[40px] ${i === currentPage ? "bg-navy" : ""}`}
                                >
                                  {i}
                                </Button>
                              );
                            }
                            pages.push(<span key="ellipsis4" className="px-2 text-gray-400">...</span>);
                            pages.push(
                              <Button
                                key={totalPages}
                                variant="outline"
                                size="sm"
                                onClick={() => setCurrentPage(totalPages)}
                                className="min-w-[40px]"
                              >
                                {totalPages}
                              </Button>
                            );
                          }
                        }
                        return pages;
                      })()}
                    </div>

                    {/* Right: Navigation Buttons */}
                    <div className="flex items-center gap-1">
                      {/* Next Page */}
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                        disabled={currentPage === totalPages}
                      >
                        Next →
                      </Button>

                      {/* Last Page */}
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPage(totalPages)}
                        disabled={currentPage === totalPages}
                        className="px-3"
                      >
                        Last ⏭️
                      </Button>
                    </div>
                  </div>

                  {/* Jump to Page Input */}
                  <div className="flex justify-center items-center gap-2 text-sm">
                    <span className="text-gray-600">Go to page:</span>
                    <Input
                      type="number"
                      value={pageInput}
                      onChange={(e) => setPageInput(e.target.value)}
                      onKeyPress={handlePageInputKeyPress}
                      placeholder="1"
                      min="1"
                      max={totalPages.toString()}
                      className="w-20 h-8 text-center"
                    />
                    <span className="text-gray-400">of {totalPages}</span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handlePageInputSubmit}
                      disabled={!pageInput || parseInt(pageInput) < 1 || parseInt(pageInput) > totalPages}
                      className="h-8 px-3"
                    >
                      Go
                    </Button>
                  </div>
                </div>
              )}
                </>
              ) : (
                <div className="text-center py-16">
                  <div className="mb-6">
                    <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4">
                      <svg className="w-8 h-8 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                    </div>
                    <h3 className="text-xl font-semibold text-gray-700 mb-3">No players found</h3>
                    <div className="max-w-md mx-auto space-y-2">
                      <p className="text-gray-600 text-sm">
                        {searchQuery ? (
                          <>
                            <span className="font-medium">Searching for "{searchQuery}"</span> returned no results.
                          </>
                        ) : (
                          "No players match your current filters."
                        )}
                      </p>
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-4">
                        <p className="text-sm text-blue-900 font-medium mb-2">💡 Suggestions:</p>
                        <ul className="text-sm text-blue-800 text-left space-y-1.5">
                          <li className="flex items-start gap-2">
                            <span className="text-blue-600 mt-0.5">•</span>
                            <span>Players with fewer than <strong>90 minutes</strong> played are filtered out</span>
                          </li>
                          {searchQuery && (
                            <li className="flex items-start gap-2">
                              <span className="text-blue-600 mt-0.5">•</span>
                              <span>Check the player name spelling</span>
                            </li>
                          )}
                          <li className="flex items-start gap-2">
                            <span className="text-blue-600 mt-0.5">•</span>
                            <span>Try selecting "All Leagues" or a different season</span>
                          </li>
                          {(selectedTeam !== "All Teams" || selectedPosition !== "All Positions" || selectedNation !== "All Nations") && (
                            <li className="flex items-start gap-2">
                              <span className="text-blue-600 mt-0.5">•</span>
                              <span>Remove team, position, or nationality filters</span>
                            </li>
                          )}
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              )}
        </div>
      </section>

      {/* Feedback Section */}
      <section className="py-10 bg-gray-50">
        <div className="container mx-auto px-4">
          <div className="max-w-2xl mx-auto">
            <InlineFeedback context="talent-pool" />
          </div>
        </div>
      </section>
    </div>
  );
}

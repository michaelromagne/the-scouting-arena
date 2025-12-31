"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { fetchPlayers, fetchSimilarPlayers, fetchSeasons, fetchLeagues, fetchPositions, fetchNations, type SimilarPlayer } from "@/lib/api";
import { DEFAULT_FILTERS, POSITION_MAPPING } from "@/lib/constants";
import { formatSeason } from "@/lib/utils";
import { Search, TrendingUp, Users } from "lucide-react";
import Link from "next/link";
import { InlineFeedback } from "@/components/InlineFeedback";

export default function SimilaritySearchPage() {
  const router = useRouter();
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedPlayerId, setSelectedPlayerId] = useState<number | null>(null);
  const [selectedPlayerName, setSelectedPlayerName] = useState("");
  const [selectedSeason, setSelectedSeason] = useState(DEFAULT_FILTERS.season);
  const [selectedLeague, setSelectedLeague] = useState(DEFAULT_FILTERS.league);

  // Filter states
  const [selectedPosition, setSelectedPosition] = useState<string>("All");
  const [selectedNation, setSelectedNation] = useState<string>("All");
  const [minValue, setMinValue] = useState<string>("");
  const [maxValue, setMaxValue] = useState<string>("");
  const [minMinutes, setMinMinutes] = useState<string>("0");

  // Fetch seasons and leagues
  const { data: seasons = [] } = useQuery({
    queryKey: ["seasons"],
    queryFn: fetchSeasons,
  });

  const { data: leagues = [] } = useQuery({
    queryKey: ["leagues"],
    queryFn: fetchLeagues,
  });

  const { data: positions = [] } = useQuery({
    queryKey: ["positions"],
    queryFn: fetchPositions,
  });

  const { data: nations = [] } = useQuery({
    queryKey: ["nations"],
    queryFn: fetchNations,
  });

  // Search for players - filter by league to get unique results
  const { data: searchResults, isLoading: isSearching } = useQuery({
    queryKey: ["player-search", searchTerm, selectedSeason, selectedLeague],
    queryFn: () => fetchPlayers({
      q: searchTerm,
      season: selectedSeason,
      league: selectedLeague === "Aggregated (All Leagues)" ? "Aggregated (All Leagues)" : selectedLeague,
      limit: 10
    }),
    enabled: searchTerm.length >= 2,
  });

  // Fetch similar players (always returns top 20 from database)
  const { data: similarPlayersData, isLoading: isLoadingSimilar } = useQuery({
    queryKey: [
      "similar-players",
      selectedPlayerId,
      selectedSeason,
      selectedLeague,
      selectedPosition,
      selectedNation,
      minValue,
      maxValue,
      minMinutes,
    ],
    queryFn: () =>
      fetchSimilarPlayers({
        playerId: selectedPlayerId!,
        season: selectedSeason,
        league: selectedLeague,
        k: 20, // Database only has 20 precomputed similar players
        min_minutes: minMinutes ? parseInt(minMinutes) : 0,
        pos: selectedPosition !== "All" ? selectedPosition : undefined,
        nation: selectedNation !== "All" ? selectedNation : undefined,
        min_value: minValue ? parseFloat(minValue) : undefined,
        max_value: maxValue ? parseFloat(maxValue) : undefined,
      }),
    enabled: selectedPlayerId !== null,
  });

  const handlePlayerSelect = (playerId: number, playerName: string) => {
    setSelectedPlayerId(playerId);
    setSelectedPlayerName(playerName);
    setSearchTerm("");
  };

  // Calculate age from birth date
  const calculateAge = (birthDate: string | null | undefined): number | null => {
    if (!birthDate) return null;
    const birth = new Date(birthDate);
    const today = new Date();
    let age = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
      age--;
    }
    return age;
  };

  const handleSimilarPlayerClick = (playerId: number) => {
    router.push(`/talent-pool/${playerId}`);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <section className="bg-navy text-white py-12">
        <div className="container mx-auto px-4">
          <div className="text-center">
            <h1 className="text-3xl md:text-4xl font-bold mb-4 text-white">
              <span className="text-emerald-400">Similarity Search</span>
            </h1>
            <p className="text-lg text-gray-200 max-w-2xl mx-auto">
              Find players with similar playing styles and characteristics
            </p>
          </div>
        </div>
      </section>

      {/* Main Content */}
      <section className="py-12">
        <div className="container mx-auto px-4 max-w-6xl">
          {/* Search Card */}
          <Card className="mb-8">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Search className="w-5 h-5" />
                Search for a Player
              </CardTitle>
              <CardDescription>
                Type a player's name to find their most similar players
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Search Input, League and Season Filters */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="md:col-span-2">
                    <label className="text-sm font-medium mb-2 block">🔎 Player Name</label>
                    <Input
                      type="text"
                      placeholder="Search for a player..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium mb-2 block">🏆 League</label>
                    <Select value={selectedLeague} onValueChange={setSelectedLeague}>
                      <SelectTrigger>
                        <SelectValue />
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
                  <div>
                    <label className="text-sm font-medium mb-2 block">📅 Season</label>
                    <Select value={selectedSeason} onValueChange={setSelectedSeason}>
                      <SelectTrigger>
                        <SelectValue />
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
                </div>

                {/* Search Results Dropdown */}
                {searchTerm.length >= 2 && (
                  <Card className="border-2">
                    <CardContent className="pt-4">
                      {isSearching ? (
                        <p className="text-sm text-muted-foreground">Searching...</p>
                      ) : searchResults?.items.length === 0 ? (
                        <p className="text-sm text-muted-foreground">No players found</p>
                      ) : (
                        <div className="space-y-1.5">
                          {searchResults?.items.map((player) => (
                            <button
                              key={player.player_id}
                              onClick={() => handlePlayerSelect(player.player_id, player.player_name)}
                              className="w-full text-left p-2 rounded-lg hover:bg-emerald-50 transition-colors border border-transparent hover:border-emerald-600"
                            >
                              <div className="flex items-center gap-2">
                                {/* Player Image */}
                                <div className="flex-shrink-0">
                                  {player.image_url ? (
                                    <img
                                      src={player.image_url}
                                      alt={player.player_name}
                                      className="w-10 h-10 rounded-full object-cover border-2 border-emerald-200"
                                      onError={(e) => {
                                        e.currentTarget.src = "https://via.placeholder.com/40x40/10b981/ffffff?text=" + player.player_name.charAt(0);
                                      }}
                                    />
                                  ) : (
                                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center text-white font-bold text-sm border-2 border-emerald-200">
                                      {player.player_name.charAt(0)}
                                    </div>
                                  )}
                                </div>

                                <div className="flex-1 min-w-0">
                                  <p className="font-medium text-sm truncate leading-tight">{player.player_name}</p>
                                  <div className="flex items-center gap-1 text-xs text-muted-foreground leading-tight mt-0.5">
                                    <span className="truncate">{player.team_name}</span>
                                    {player.position && (
                                      <>
                                        <span className="hidden sm:inline">•</span>
                                        <span className="hidden sm:inline flex-shrink-0">{POSITION_MAPPING[player.position] || player.position}</span>
                                      </>
                                    )}
                                  </div>
                                  <div className="flex flex-wrap items-center gap-1 mt-0.5">
                                    {player.market_value_eur !== null && player.market_value_eur !== undefined && player.market_value_eur > 0 && (
                                      <Badge variant="outline" className="text-xs px-1.5 py-0 bg-emerald-50 text-emerald-700 border-emerald-600 font-semibold">
                                        €{player.market_value_eur.toFixed(1)}M
                                      </Badge>
                                    )}
                                    <Badge variant="outline" className="text-xs px-1.5 py-0 flex-shrink-0">
                                      {player.season_label ? formatSeason(player.season_label) : 'N/A'}
                                    </Badge>
                                  </div>
                                </div>
                              </div>
                            </button>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* Selected Player Display */}
                {selectedPlayerId && (
                  <div className="flex items-center justify-between p-4 bg-emerald-50 rounded-lg border-2 border-emerald-600">
                    <div className="flex items-center gap-3">
                      <Users className="w-5 h-5 text-emerald-700" />
                      <div>
                        <p className="font-semibold text-lg text-emerald-900">{selectedPlayerName}</p>
                        <p className="text-sm text-emerald-700">
                          Finding top 20 most similar players...
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setSelectedPlayerId(null);
                        setSelectedPlayerName("");
                      }}
                      className="border-emerald-600 text-emerald-700 hover:bg-emerald-100"
                    >
                      Clear
                    </Button>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Similar Players Results */}
          {selectedPlayerId && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-emerald-600" />
                  Top 20 Most Similar Players to {selectedPlayerName}
                </CardTitle>
                <CardDescription>
                  Based on playing style and performance metrics • {formatSeason(selectedSeason)}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {isLoadingSimilar ? (
                  <div className="text-center py-12">
                    <p className="text-muted-foreground">Loading similar players...</p>
                  </div>
                ) : similarPlayersData?.similar_players.length === 0 ? (
                  <div className="text-center py-12">
                    <p className="text-muted-foreground">No similar players found</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {similarPlayersData?.similar_players.map((player: SimilarPlayer, index: number) => {
                      const age = calculateAge(player.birth_date);
                      return (
                        <button
                          key={player.player_id}
                          onClick={() => handleSimilarPlayerClick(player.player_id)}
                          className="w-full text-left p-2.5 rounded-lg border border-gray-200 hover:border-emerald-600 hover:bg-emerald-50 transition-all duration-200 group"
                        >
                          <div className="flex items-center gap-2">
                            {/* Rank Badge */}
                            <div className="flex items-center justify-center w-7 h-7 rounded-full bg-navy text-white font-bold text-xs flex-shrink-0">
                              {index + 1}
                            </div>

                            {/* Player Photo */}
                            <div className="w-10 h-10 rounded-full overflow-hidden border-2 border-gray-200 flex-shrink-0">
                              <img
                                src={player.image_url || "https://via.placeholder.com/40x40/f1f5f9/64748b?text=👤"}
                                alt={player.player_name}
                                className="w-full h-full object-cover"
                                onError={(e) => {
                                  e.currentTarget.src = "https://via.placeholder.com/40x40/f1f5f9/64748b?text=👤";
                                }}
                              />
                            </div>

                            {/* Player Info */}
                            <div className="flex-1 min-w-0">
                              <p className="font-semibold text-sm group-hover:text-emerald-700 transition-colors truncate leading-tight">
                                {player.player_name}
                              </p>
                              {/* First line: Team and Position */}
                              <div className="flex items-center gap-1 text-xs text-muted-foreground leading-tight mt-0.5">
                                <span className="truncate">{player.team_name}</span>
                                {player.position && (
                                  <>
                                    <span>•</span>
                                    <span className="flex-shrink-0">{POSITION_MAPPING[player.position] || player.position}</span>
                                  </>
                                )}
                              </div>
                              {/* Second line: Age, Nationality, Value */}
                              <div className="flex flex-wrap items-center gap-1 text-xs mt-0.5">
                                {age && age > 0 && (
                                  <Badge variant="outline" className="text-xs px-1.5 py-0 bg-blue-50 text-blue-700 border-blue-500">
                                    {age}yo
                                  </Badge>
                                )}
                                {player.nationality && (
                                  <Badge variant="outline" className="text-xs px-1.5 py-0 bg-purple-50 text-purple-700 border-purple-500">
                                    {player.nationality}
                                  </Badge>
                                )}
                                {player.value_m_eur !== null && player.value_m_eur !== undefined && player.value_m_eur > 0 && (
                                  <Badge variant="outline" className="text-xs px-1.5 py-0 bg-emerald-50 text-emerald-700 border-emerald-600 font-semibold">
                                    €{player.value_m_eur.toFixed(1)}M
                                  </Badge>
                                )}
                              </div>
                            </div>

                            {/* Similarity Score - Compact */}
                            <div className="flex items-center gap-1.5 flex-shrink-0">
                              <div className="hidden sm:block w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-gradient-to-r from-emerald-600 to-emerald-500"
                                  style={{ width: `${player.similarity_score * 100}%` }}
                                />
                              </div>
                              <Badge
                                variant="outline"
                                className={`font-bold text-xs px-1.5 py-0.5 whitespace-nowrap ${
                                  player.similarity_score >= 0.9
                                    ? "bg-emerald-50 text-emerald-700 border-emerald-600"
                                    : player.similarity_score >= 0.8
                                    ? "bg-blue-500/10 text-blue-600 border-blue-500"
                                    : "bg-orange/10 text-orange border-orange"
                                }`}
                              >
                                {(player.similarity_score * 100).toFixed(0)}%
                              </Badge>
                            </div>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Empty State */}
          {!selectedPlayerId && searchTerm.length < 2 && (
            <Card className="border-dashed">
              <CardContent className="pt-12 pb-12">
                <div className="text-center">
                  <Search className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
                  <h3 className="text-xl font-semibold mb-2">Start Your Search</h3>
                  <p className="text-muted-foreground max-w-md mx-auto">
                    Enter a player's name above to discover similar players based on their
                    playing style, performance metrics, and characteristics.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </section>

      {/* Call to Action & Feedback Section - Side by Side */}
      <section className="py-10 bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
        <div className="container mx-auto px-4">
          <div className="max-w-6xl mx-auto">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Team Analysis CTA */}
              <Card className="border-2 border-blue-200 shadow-xl">
                <CardContent className="pt-6 pb-6 px-4 sm:pt-7 sm:pb-7 sm:px-6">
                  <div className="text-center">
                    <h2 className="text-xl sm:text-2xl font-bold text-navy mb-3 px-2">
                      Ready for Team Analysis?
                    </h2>
                    <p className="text-sm sm:text-base text-gray-600 mb-4 sm:mb-5 px-2">
                      Compare two teams head-to-head with radar charts across all performance categories.
                      Discover key players and elite performers in each team.
                    </p>

                    <Button
                      asChild
                      size="lg"
                      className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-700 hover:to-indigo-700 font-bold px-4 sm:px-5 py-3 sm:py-4 text-sm sm:text-base shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 w-full sm:w-auto"
                    >
                      <Link href="/team-analysis">
                        Explore Team Analysis
                      </Link>
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Inline Feedback */}
              <InlineFeedback context="similarity-search" />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

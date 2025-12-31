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
  fetchNationalTeam,
  fetchNations,
  fetchSeasons,
  type NationalTeam,
} from "@/lib/api";
import { getPositionDisplayName, getCountryName } from "@/lib/constants";
import { formatSeason } from "@/lib/utils";

export default function NationalTeamsPage() {
  const [selectedNationality, setSelectedNationality] = useState<string>("");
  const [selectedSeason, setSelectedSeason] = useState<string>("2526");
  const [showLimit, setShowLimit] = useState(10);
  const [hasSearched, setHasSearched] = useState(false);

  // Helper function to format quantile as "Top X%"
  const formatQuantile = (quantile: number): string => {
    const topPercent = 100 - quantile;
    if (topPercent < 1) {
      return "Top 1%";
    }
    return `Top ${Math.round(topPercent)}%`;
  };

  // Fetch nations
  const { data: nations = [] } = useQuery<string[]>({
    queryKey: ["nations"],
    queryFn: fetchNations,
  });

  // Fetch seasons
  const { data: seasons = [] } = useQuery<string[]>({
    queryKey: ["seasons"],
    queryFn: fetchSeasons,
  });

  // Fetch national team data (always fetch 20, display based on showLimit)
  const {
    data: nationalTeam,
    isLoading,
    error,
  } = useQuery<NationalTeam>({
    queryKey: ["national-team", selectedNationality, selectedSeason],
    queryFn: () => fetchNationalTeam(selectedNationality, selectedSeason, 20),
    enabled: hasSearched && !!selectedNationality,
  });

  const handleSearch = () => {
    if (selectedNationality) {
      setHasSearched(true);
      setShowLimit(10); // Reset to 10 when searching
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-purple-50 to-pink-50">
      {/* Hero Section */}
      <section className="bg-navy text-white py-16">
        <div className="container mx-auto px-4">
          <div className="max-w-3xl mx-auto text-center">
            <h1 className="text-4xl md:text-5xl font-bold mb-4">
              National Teams Showcase
            </h1>
            <p className="text-lg md:text-xl text-gray-200">
              Discover the elite players representing their nations
            </p>
            <p className="text-sm md:text-base text-gray-300 mt-2">
              Players to watch out for — showcasing top performers in each category
            </p>
          </div>
        </div>
      </section>

      {/* Filters Section */}
      <section className="py-8 bg-white border-b">
        <div className="container mx-auto px-4">
          <Card className="max-w-2xl mx-auto shadow-lg">
            <CardHeader>
              <CardTitle className="text-xl">Select National Team</CardTitle>
              <CardDescription>
                Choose a nationality and season to view their elite players
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                {/* Nationality Selector */}
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2 block">
                    Nationality
                  </label>
                  <Select value={selectedNationality} onValueChange={setSelectedNationality}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select nationality..." />
                    </SelectTrigger>
                    <SelectContent onPointerDown={(e) => e.stopPropagation()} onTouchStart={(e) => e.stopPropagation()}>
                      {nations
                        .filter((nation) => nation !== "0")
                        .sort((a, b) => getCountryName(a).localeCompare(getCountryName(b)))
                        .map((nation) => (
                          <SelectItem key={nation} value={nation}>
                            {getCountryName(nation)}
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Season Selector */}
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2 block">
                    Season
                  </label>
                  <Select value={selectedSeason} onValueChange={setSelectedSeason}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent onPointerDown={(e) => e.stopPropagation()} onTouchStart={(e) => e.stopPropagation()}>
                      {seasons.map((season) => (
                        <SelectItem key={season} value={season}>
                          {formatSeason(season)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <Button
                onClick={handleSearch}
                disabled={!selectedNationality}
                className="w-full bg-green text-navy hover:bg-green/90"
              >
                View Elite Players
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Results Section */}
      {hasSearched && (
        <section className="py-12">
          <div className="container mx-auto px-4">
            <div className="max-w-4xl mx-auto">
              {isLoading && (
                <div className="text-center py-12">
                  <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
                  <p className="mt-4 text-gray-600">Loading elite players...</p>
                </div>
              )}

              {error && (
                <Card className="border-red-200 bg-red-50">
                  <CardContent className="pt-6">
                    <p className="text-red-600 text-center">
                      Error loading data: {(error as Error).message}
                    </p>
                  </CardContent>
                </Card>
              )}

              {nationalTeam && !isLoading && (
                <>
                  {/* Header */}
                  <div className="text-center mb-8">
                    <h2 className="text-3xl font-bold text-gray-900 mb-2">
                      {getCountryName(nationalTeam.nationality)}
                    </h2>
                    <p className="text-lg text-gray-600">
                      Season {formatSeason(nationalTeam.season_label)} • Top {showLimit} Players to Watch Out For
                    </p>
                    <p className="text-sm text-gray-500 mt-2">
                      Elite players with at least one category above 90th percentile
                    </p>
                  </div>

                  {/* Top 3 by Market Value */}
                  {nationalTeam.top_value_players && nationalTeam.top_value_players.length > 0 && (
                    <div className="mb-8">
                      <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <span>💰</span>
                        <span>Top 3 by Market Value</span>
                      </h3>

                      {/* Desktop: Grid layout */}
                      <div className="hidden md:grid md:grid-cols-3 gap-3">
                        {nationalTeam.top_value_players.map((player, index) => (
                            <Card
                              key={player.player_id}
                              className={`shadow-md border-2 ${
                                index === 0
                                  ? "border-yellow-400 bg-gradient-to-br from-yellow-50 to-white"
                                  : index === 1
                                  ? "border-gray-400 bg-gradient-to-br from-gray-50 to-white"
                                  : "border-orange-400 bg-gradient-to-br from-orange-50 to-white"
                              }`}
                            >
                              <CardContent className="pt-3 pb-3">
                                <div className="text-center">
                                  {/* Rank Badge */}
                                  <div className="flex justify-center mb-2">
                                    <div
                                      className={`w-8 h-8 rounded-full flex items-center justify-center text-base font-bold ${
                                        index === 0
                                          ? "bg-gradient-to-br from-yellow-400 to-yellow-600 text-white"
                                          : index === 1
                                          ? "bg-gradient-to-br from-gray-300 to-gray-500 text-white"
                                          : "bg-gradient-to-br from-orange-400 to-orange-600 text-white"
                                      }`}
                                    >
                                      {index + 1}
                                    </div>
                                  </div>

                                  {/* Player Image */}
                                  {player.image_url ? (
                                    <img
                                      src={player.image_url}
                                      alt={player.player_name}
                                      className="w-16 h-16 rounded-full object-cover border-3 border-green-400 mx-auto mb-2"
                                    />
                                  ) : (
                                    <div className="w-16 h-16 rounded-full bg-gradient-to-br from-green-300 to-green-500 flex items-center justify-center text-white font-bold text-xl border-3 border-green-400 mx-auto mb-2">
                                      {player.player_name.charAt(0)}
                                    </div>
                                  )}

                                  {/* Player Name */}
                                  <h4 className="font-bold text-sm text-gray-900 mb-0.5 leading-tight">{player.player_name}</h4>
                                  <p className="text-xs text-gray-600 mb-2 leading-tight">{getPositionDisplayName(player.position)}</p>

                                  {/* Market Value */}
                                  <div className="mb-2">
                                    <Badge className="bg-green text-navy font-bold px-2.5 py-1 text-sm">
                                      €{player.market_value_eur?.toFixed(1)}M
                                    </Badge>
                                  </div>

                                  {/* Team */}
                                  {player.team_name && (
                                    <p className="text-xs text-gray-600 truncate px-2">{player.team_name}</p>
                                  )}
                                </div>
                              </CardContent>
                            </Card>
                          ))}
                      </div>

                      {/* Mobile: Horizontal layout */}
                      <div className="md:hidden space-y-2">
                        {nationalTeam.top_value_players.map((player, index) => (
                          <Card
                            key={player.player_id}
                            className={`shadow-sm border-2 ${
                              index === 0
                                ? "border-yellow-400 bg-gradient-to-r from-yellow-50 to-white"
                                : index === 1
                                ? "border-gray-400 bg-gradient-to-r from-gray-50 to-white"
                                : "border-orange-400 bg-gradient-to-r from-orange-50 to-white"
                            }`}
                          >
                            <CardContent className="py-2 px-3">
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
                                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-green-300 to-green-500 flex items-center justify-center text-white font-bold text-sm border-2 border-green-400 flex-shrink-0">
                                    {player.player_name.charAt(0)}
                                  </div>
                                )}

                                {/* Player Info */}
                                <div className="flex-1 min-w-0">
                                  <h4 className="font-bold text-sm text-gray-900 truncate leading-tight">{player.player_name}</h4>
                                  <div className="flex items-center gap-1.5 text-xs text-gray-600 leading-tight">
                                    <span>{getPositionDisplayName(player.position)}</span>
                                    {player.team_name && (
                                      <>
                                        <span>•</span>
                                        <span className="truncate">{player.team_name}</span>
                                      </>
                                    )}
                                  </div>
                                </div>

                                {/* Market Value */}
                                <Badge className="bg-green text-navy font-bold px-2 py-1 text-xs flex-shrink-0 whitespace-nowrap">
                                  €{player.market_value_eur?.toFixed(1)}M
                                </Badge>
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Elite Players */}
                  {nationalTeam.elite_players && nationalTeam.elite_players.length > 0 ? (
                    <div className="space-y-3">
                      <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <span>🏆</span>
                        <span>Top {showLimit} Players for season {formatSeason(nationalTeam.season_label)}</span>
                      </h3>
                      {[...nationalTeam.elite_players]
                        .slice(0, showLimit)
                        .sort((a, b) => {
                          // Get sorted quantile values (highest to lowest) for each player
                          const quantilesA = Object.values(a.elite_categories).sort((x, y) => y - x);
                          const quantilesB = Object.values(b.elite_categories).sort((x, y) => y - x);

                          // Compare quantiles one by one (highest first, then 2nd highest, etc.)
                          const maxLength = Math.max(quantilesA.length, quantilesB.length);
                          for (let i = 0; i < maxLength; i++) {
                            const qA = quantilesA[i] || 0;
                            const qB = quantilesB[i] || 0;
                            if (qB !== qA) {
                              return qB - qA;
                            }
                          }

                          // If all quantiles are equal, prioritize field players over goalkeepers
                          const isGkA = a.position?.toUpperCase() === "GK" || a.position?.toUpperCase() === "GOALKEEPER";
                          const isGkB = b.position?.toUpperCase() === "GK" || b.position?.toUpperCase() === "GOALKEEPER";
                          if (isGkA !== isGkB) {
                            return isGkA ? 1 : -1; // Field player (false) comes before GK (true)
                          }

                          return 0;
                        })
                        .map((player, index) => (
                          <Card
                            key={player.player_id}
                            className="shadow-sm border border-blue-200 hover:shadow-md transition-shadow"
                          >
                            <CardContent className="py-2 px-3">
                              <div className="flex items-center gap-2">
                                {/* Rank Badge */}
                                <div className="flex-shrink-0">
                                  <div
                                    className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
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
                                      className="w-10 h-10 rounded-full object-cover border-2 border-purple-300"
                                    />
                                  ) : (
                                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-300 to-pink-400 flex items-center justify-center text-white font-bold text-sm border-2 border-purple-300">
                                      {player.player_name.charAt(0)}
                                    </div>
                                  )}
                                </div>

                                {/* Player Info */}
                                <div className="flex-1 min-w-0">
                                  <h3 className="text-sm font-bold text-gray-900 mb-0 leading-tight truncate">
                                    {player.player_name}
                                  </h3>

                                  {/* Player Details */}
                                  <div className="flex flex-wrap gap-1 mb-1 text-xs text-gray-600 leading-tight">
                                    <span className="font-medium">{getPositionDisplayName(player.position)}</span>
                                    {player.team_name && (
                                      <>
                                        <span>•</span>
                                        <span className="truncate">{player.team_name}</span>
                                      </>
                                    )}
                                    {player.market_value_eur !== null && player.market_value_eur !== undefined && player.market_value_eur > 0 && (
                                      <>
                                        <span>•</span>
                                        <span className="font-semibold text-green-600">
                                          €{player.market_value_eur.toFixed(1)}M
                                        </span>
                                      </>
                                    )}
                                    {player.birth_date && (
                                      <>
                                        <span>•</span>
                                        <span>
                                          {(() => {
                                            const birthDate = new Date(player.birth_date);
                                            const age = new Date().getFullYear() - birthDate.getFullYear();
                                            return `${age} years`;
                                          })()}
                                        </span>
                                      </>
                                    )}
                                    {player.minutes !== null && player.minutes !== undefined && (
                                      <>
                                        <span>•</span>
                                        <span>{player.minutes} min</span>
                                      </>
                                    )}
                                  </div>

                                  {/* Elite Categories */}
                                  <div className="flex flex-wrap gap-1">
                                    {Object.entries(player.elite_categories)
                                      .sort(([, a], [, b]) => b - a) // Sort by quantile descending
                                      .map(([category, quantile]) => (
                                        <Badge
                                          key={category}
                                          className="bg-green text-navy font-medium px-2 py-0.5 text-xs"
                                        >
                                          {category}: {formatQuantile(quantile)}
                                        </Badge>
                                      ))}
                                  </div>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        ))}

                      {/* Show More / Show Less Button */}
                      {nationalTeam.elite_players.length > 10 && (
                        <div className="mt-6 text-center">
                          {showLimit === 10 ? (
                            <Button
                              onClick={() => setShowLimit(20)}
                              variant="outline"
                              size="lg"
                              className="bg-white hover:bg-purple-600 hover:text-white border-2 border-purple-600 text-purple-600 font-semibold px-8 py-3 transition-all duration-200"
                            >
                              Show More ({Math.min(nationalTeam.elite_players.length - 10, 10)} more players)
                            </Button>
                          ) : (
                            <Button
                              onClick={() => setShowLimit(10)}
                              variant="outline"
                              size="lg"
                              className="bg-white hover:bg-purple-600 hover:text-white border-2 border-purple-600 text-purple-600 font-semibold px-8 py-3 transition-all duration-200"
                            >
                              Show Less (10 players)
                            </Button>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <Card className="border-gray-200 bg-gray-50">
                      <CardContent className="pt-6">
                        <div className="text-center py-8">
                          <p className="text-gray-600 text-lg mb-2">
                            No elite players found for {getCountryName(nationalTeam.nationality)}
                          </p>
                          <p className="text-sm text-gray-500">
                            No players from this nationality are in the top 10% compared to the competition
                            in the selected season.
                          </p>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </>
              )}
            </div>
          </div>
        </section>
      )}

      {/* Info Section */}
      {!hasSearched && (
        <section className="py-16">
          <div className="container mx-auto px-4">
            <div className="max-w-2xl mx-auto text-center">
              <div className="text-6xl mb-4">🌟</div>
              <h3 className="text-2xl font-bold text-gray-900 mb-4">
                Discover National Team Stars
              </h3>
              <p className="text-gray-600 mb-6">
                Select a nationality above to view the top 10 elite players representing that nation.
                See which categories they excel in, their club, market value, and what makes them stand out on the international stage.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-500">
                <div>
                  <div className="text-2xl mb-2">⚽</div>
                  <p className="font-semibold">Field Players</p>
                  <p>Top 10% threshold</p>
                </div>
                <div>
                  <div className="text-2xl mb-2">🧤</div>
                  <p className="font-semibold">Goalkeepers</p>
                  <p>Top 10% threshold</p>
                </div>
                <div>
                  <div className="text-2xl mb-2">🏆</div>
                  <p className="font-semibold">Top 10 Players</p>
                  <p>Best performers shown</p>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Call to Action & Feedback Section - Side by Side */}
      <section className="py-10 bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
        <div className="container mx-auto px-4">
          <div className="max-w-6xl mx-auto">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Talent Pool CTA */}
              <Card className="border-2 border-slate-200 shadow-xl">
                <CardContent className="pt-6 pb-6 px-4 sm:pt-7 sm:pb-7 sm:px-6">
                  <div className="text-center">
                    <h2 className="text-xl sm:text-2xl font-bold text-navy mb-3 px-2">
                      Explore the Full Talent Pool
                    </h2>
                    <p className="text-sm sm:text-base text-gray-600 mb-4 sm:mb-5 px-2">
                      Browse through thousands of players with advanced filters and detailed profiles.
                      View comprehensive statistics, performance metrics, and find your next scouting target.
                    </p>

                    <Button
                      asChild
                      size="lg"
                      className="bg-gradient-to-r from-slate-600 to-blue-600 text-white hover:from-slate-700 hover:to-blue-700 font-bold px-4 sm:px-5 py-3 sm:py-4 text-sm sm:text-base shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 w-full sm:w-auto"
                    >
                      <Link href="/talent-pool">
                        Browse Talent Pool
                      </Link>
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Inline Feedback */}
              <InlineFeedback context="national-teams" />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

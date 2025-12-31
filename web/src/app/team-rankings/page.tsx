"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { InlineFeedback } from "@/components/InlineFeedback";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { fetchLeagues, fetchSeasons } from "@/lib/api";
import { formatSeason } from "@/lib/utils";

interface TeamRankingItem {
  team_id: number;
  team_name: string;
  league_name: string | null;
  season_label: string | null;
  quantile_value: number;
  games_played: number | null;
}

const CATEGORIES = [
  { value: "complete", label: "Most Complete", description: "Best overall team performance" },
  { value: "entertaining", label: "Most Entertaining", description: "Finishing + Passing + Dribbling" },
  { value: "finishing", label: "Finishing", description: "Goal scoring ability" },
  { value: "passing", label: "Passing", description: "Passing quality and creativity" },
  { value: "dribbling", label: "Dribbling", description: "Ball progression and dribbling" },
  { value: "defense", label: "Defense", description: "Defensive solidity" },
  { value: "aerial", label: "Aerial", description: "Aerial duels and set pieces" },
  { value: "gk", label: "Goalkeeper", description: "Goalkeeper performance" },
];

export default function TeamRankingsPage() {
  const [selectedCategory, setSelectedCategory] = useState<string>("complete");
  const [selectedLeague, setSelectedLeague] = useState<string>("Aggregated (All Leagues)");
  const [selectedSeason, setSelectedSeason] = useState<string>("2526");

  // Fetch leagues
  const { data: allLeagues = [] } = useQuery({
    queryKey: ["leagues"],
    queryFn: fetchLeagues,
  });

  // Include all leagues (domestic + European competitions + aggregated)
  const leagues = allLeagues;

  // Fetch seasons
  const { data: seasons = [] } = useQuery({
    queryKey: ["seasons"],
    queryFn: fetchSeasons,
  });

  // Fetch team rankings
  const {
    data: rankings = [],
    isLoading,
    error,
  } = useQuery<TeamRankingItem[]>({
    queryKey: ["team-rankings", selectedCategory, selectedLeague, selectedSeason],
    queryFn: async () => {
      const params = new URLSearchParams({
        category: selectedCategory,
        league: selectedLeague,
        season: selectedSeason,
        limit: "20",
      });
      const response = await fetch(`/api/teams/rankings?${params}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch team rankings: ${response.statusText}`);
      }
      return response.json();
    },
  });

  const selectedCategoryInfo = CATEGORIES.find((c) => c.value === selectedCategory);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* Hero Section */}
      <section className="bg-navy text-white py-16">
        <div className="container mx-auto px-4">
          <div className="max-w-3xl mx-auto text-center">
            <h1 className="text-4xl md:text-5xl font-bold mb-4">
              Team Rankings
            </h1>
            <p className="text-lg md:text-xl text-gray-200">
              Discover the best performing teams across different categories
            </p>
            <p className="text-sm md:text-base text-gray-300 mt-2">
              Compare teams by overall performance, entertainment value, or specific skills
            </p>
          </div>
        </div>
      </section>

      {/* Filters Section */}
      <section className="py-8 bg-white border-b">
        <div className="container mx-auto px-4">
          <Card className="max-w-4xl mx-auto shadow-lg">
            <CardHeader>
              <CardTitle className="text-xl">Select Ranking Category</CardTitle>
              <CardDescription>
                Choose a category, league, and season to view top 20 teams
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Category Selector */}
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2 block">
                    Category
                  </label>
                  <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CATEGORIES.map((cat) => (
                        <SelectItem key={cat.value} value={cat.value}>
                          {cat.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {selectedCategoryInfo && (
                    <p className="text-xs text-gray-500 mt-1">
                      {selectedCategoryInfo.description}
                    </p>
                  )}
                </div>

                {/* League Selector */}
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2 block">
                    League
                  </label>
                  <Select value={selectedLeague} onValueChange={setSelectedLeague}>
                    <SelectTrigger>
                      <SelectValue />
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

                {/* Season Selector */}
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2 block">
                    Season
                  </label>
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
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Results Section */}
      <section className="py-12">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            {isLoading && (
              <div className="text-center py-12">
                <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                <p className="mt-4 text-gray-600">Loading rankings...</p>
              </div>
            )}

            {error && (
              <Card className="border-red-200 bg-red-50">
                <CardContent className="pt-6">
                  <p className="text-red-600 text-center">
                    Error loading rankings: {(error as Error).message}
                  </p>
                </CardContent>
              </Card>
            )}

            {rankings && rankings.length > 0 && !isLoading && (
              <>
                {/* Header */}
                <div className="text-center mb-8">
                  <h2 className="text-3xl font-bold text-gray-900 mb-2">
                    {selectedCategoryInfo?.label}
                  </h2>
                  <p className="text-lg text-gray-600">
                    {selectedLeague} • Season {formatSeason(selectedSeason)} • Top {rankings.length} Teams
                  </p>
                  <p className="text-sm text-gray-500 mt-2">
                    Scores are based on aggregated statistics from all team players, normalized by league and season.
                    Higher scores indicate better performance.
                  </p>
                </div>

                {/* Rankings List */}
                <div className="space-y-3">
                  {rankings.map((team, index) => (
                    <Card
                      key={team.team_id}
                      className={`shadow-md border-2 hover:shadow-lg transition-shadow ${
                        index === 0
                          ? "border-yellow-400 bg-gradient-to-r from-yellow-50 to-white"
                          : index === 1
                          ? "border-gray-400 bg-gradient-to-r from-gray-50 to-white"
                          : index === 2
                          ? "border-orange-400 bg-gradient-to-r from-orange-50 to-white"
                          : "border-blue-200"
                      }`}
                    >
                      <CardContent className="py-4 px-6">
                        <div className="flex items-center gap-4">
                          {/* Rank Badge */}
                          <div className="flex-shrink-0">
                            <div
                              className={`w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold ${
                                index === 0
                                  ? "bg-gradient-to-br from-yellow-400 to-yellow-600 text-white"
                                  : index === 1
                                  ? "bg-gradient-to-br from-gray-300 to-gray-500 text-white"
                                  : index === 2
                                  ? "bg-gradient-to-br from-orange-400 to-orange-600 text-white"
                                  : "bg-gradient-to-br from-blue-600 to-blue-800 text-white"
                              }`}
                            >
                              {index + 1}
                            </div>
                          </div>

                          {/* Team Info */}
                          <div className="flex-1 min-w-0">
                            <h3 className="text-xl font-bold text-gray-900 mb-1">
                              {team.team_name}
                            </h3>
                            <div className="flex flex-wrap gap-2 items-center text-sm text-gray-600">
                              {team.league_name && (
                                <span className="font-medium">{team.league_name}</span>
                              )}
                              {team.games_played !== null && team.games_played !== undefined && (
                                <>
                                  <span>•</span>
                                  <span>{team.games_played} games</span>
                                </>
                              )}
                            </div>
                          </div>

                          {/* Score Badge */}
                          <div className="flex-shrink-0">
                            <Badge className="bg-green text-navy font-bold px-4 py-2 text-lg">
                              {team.quantile_value.toFixed(1)}
                            </Badge>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </>
            )}

            {rankings && rankings.length === 0 && !isLoading && (
              <Card className="border-gray-200 bg-gray-50">
                <CardContent className="pt-6">
                  <div className="text-center py-8">
                    <p className="text-gray-600 text-lg mb-2">
                      No teams found for this selection
                    </p>
                    <p className="text-sm text-gray-500">
                      Try selecting a different league or season
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </section>

      {/* Info Section */}
      <section className="py-16 bg-white">
        <div className="container mx-auto px-4">
          <div className="max-w-3xl mx-auto">
            <h3 className="text-2xl font-bold text-gray-900 mb-6 text-center">
              Understanding Team Rankings
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Most Complete</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-600">
                    Overall team performance combining all field player categories (Finishing, Passing, Dribbling, Defense, Aerial)
                    plus goalkeeper performance (weighted by 1/5 since it's a single player). The score is the average
                    of normalized statistics across all these dimensions.
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Most Entertaining</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-600">
                    Attacking prowess measured by summing the Finishing, Passing, and Dribbling category scores.
                    These are the teams that create chances, score goals, and play attractive football!
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* Call to Action & Feedback Section - Side by Side */}
      <section className="py-10 bg-gradient-to-br from-purple-50 via-pink-50 to-rose-50">
        <div className="container mx-auto px-4">
          <div className="max-w-6xl mx-auto">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* National Teams CTA */}
              <Card className="border-2 border-purple-200 shadow-xl">
                <CardContent className="pt-6 pb-6 px-4 sm:pt-7 sm:pb-7 sm:px-6">
                  <div className="text-center">
                    <h2 className="text-xl sm:text-2xl font-bold text-navy mb-3 px-2">
                      Discover National Teams Elite Players
                    </h2>
                    <p className="text-sm sm:text-base text-gray-600 mb-4 sm:mb-5 px-2">
                      Explore the best players representing their nations. See who excels in each performance category
                      and discover the stars to watch out for in international competitions.
                    </p>

                    <Button
                      asChild
                      size="lg"
                      className="bg-gradient-to-r from-purple-600 to-pink-600 text-white hover:from-purple-700 hover:to-pink-700 font-bold px-4 sm:px-5 py-3 sm:py-4 text-sm sm:text-base shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 w-full sm:w-auto"
                    >
                      <Link href="/national-teams">
                        Explore National Teams
                      </Link>
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Inline Feedback */}
              <InlineFeedback context="team-rankings" />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

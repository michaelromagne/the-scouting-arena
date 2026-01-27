"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatusBadge } from "@/components/demands/StatusBadge";
import { MatchPlayerCard } from "@/components/demands/MatchPlayerCard";
import {
  getDemand,
  getDemandMatches,
  runMatching,
  updateMatch,
  updateDemand,
  deleteMatch,
  type DemandDetail,
  type DemandMatch,
} from "@/lib/api/demands";

export default function DemandDetailPage() {
  const params = useParams();
  const router = useRouter();
  const demandId = parseInt(params.id as string);

  const [demand, setDemand] = useState<DemandDetail | null>(null);
  const [matches, setMatches] = useState<DemandMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [matchingLoading, setMatchingLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("all");

  useEffect(() => {
    loadDemand();
    loadMatches();
  }, [demandId]);

  const loadDemand = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getDemand(demandId);
      setDemand(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load demand");
    } finally {
      setLoading(false);
    }
  };

  const loadMatches = async () => {
    try {
      const data = await getDemandMatches(demandId);
      setMatches(data);
    } catch (err) {
      console.error("Failed to load matches:", err);
    }
  };

  const handleRunMatching = async () => {
    try {
      setMatchingLoading(true);
      const newMatches = await runMatching(demandId, { limit: 50 });
      setMatches(newMatches);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run matching");
    } finally {
      setMatchingLoading(false);
    }
  };

  const handleStatusChange = async (playerId: number, status: DemandMatch["status"]) => {
    try {
      await updateMatch(demandId, playerId, { status });
      await loadMatches();
      await loadDemand(); // Refresh counts
    } catch (err) {
      console.error("Failed to update status:", err);
    }
  };

  const handleNotesChange = async (playerId: number, notes: string) => {
    try {
      await updateMatch(demandId, playerId, { notes });
      await loadMatches();
    } catch (err) {
      console.error("Failed to update notes:", err);
    }
  };

  const handleRemove = async (playerId: number) => {
    if (!confirm("Are you sure you want to remove this player from the demand?")) {
      return;
    }
    try {
      await deleteMatch(demandId, playerId);
      await loadMatches();
      await loadDemand(); // Refresh counts
    } catch (err) {
      console.error("Failed to remove match:", err);
    }
  };

  const handleStatusToggle = async () => {
    if (!demand) return;
    try {
      const newStatus = demand.status === "open" ? "closed" : "open";
      await updateDemand(demandId, { status: newStatus });
      await loadDemand();
    } catch (err) {
      console.error("Failed to update status:", err);
    }
  };

  const filterMatchesByStatus = (status?: string) => {
    if (!status || status === "all") return matches;
    return matches.filter((m) => m.status === status);
  };

  const filteredMatches = filterMatchesByStatus(activeTab);

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center py-12">Loading...</div>
      </div>
    );
  }

  if (error || !demand) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-800 dark:text-red-200">{error || "Demand not found"}</p>
          <Button onClick={() => router.back()} variant="outline" size="sm" className="mt-2">
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold mb-2">{demand.club_name}</h1>
          <div className="flex gap-2 items-center">
            {demand.position.map((pos) => (
              <Badge key={pos} variant="outline">
                {pos}
              </Badge>
            ))}
            <StatusBadge status={demand.status} />
            <Badge
              variant={
                demand.priority === "high"
                  ? "destructive"
                  : demand.priority === "medium"
                    ? "default"
                    : "secondary"
              }
            >
              {demand.priority}
            </Badge>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleStatusToggle} variant="outline">
            {demand.status === "open" ? "Close Demand" : "Reopen Demand"}
          </Button>
          <Button onClick={() => router.back()} variant="outline">
            Back
          </Button>
        </div>
      </div>

      {/* Demand Info Card */}
      <Card className="p-6 mb-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Age Range</div>
            <div className="font-semibold">
              {demand.age_min && demand.age_max
                ? `${demand.age_min}-${demand.age_max}`
                : demand.age_min
                  ? `${demand.age_min}+`
                  : demand.age_max
                    ? `<${demand.age_max}`
                    : "Any"}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Season</div>
            <div className="font-semibold">{demand.default_season}</div>
          </div>
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Deadline</div>
            <div className="font-semibold">
              {demand.deadline
                ? new Date(demand.deadline).toLocaleDateString()
                : "No deadline"}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Contact</div>
            <div className="font-semibold">
              {demand.club_contact_name || "No contact"}
            </div>
          </div>
        </div>

        {demand.playing_style_notes && (
          <div className="mb-4">
            <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
              Playing Style
            </div>
            <div className="text-sm">{demand.playing_style_notes}</div>
          </div>
        )}

        {demand.internal_notes && (
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
              Internal Notes
            </div>
            <div className="text-sm bg-yellow-50 dark:bg-yellow-900/20 p-2 rounded">
              {demand.internal_notes}
            </div>
          </div>
        )}
      </Card>

      {/* Run Matching Button */}
      <div className="mb-6">
        <Button onClick={handleRunMatching} disabled={matchingLoading} size="lg">
          {matchingLoading ? "Running Matching..." : "Run Matching Algorithm"}
        </Button>
        {matches.length > 0 && (
          <span className="ml-4 text-sm text-gray-600 dark:text-gray-400">
            {matches.length} players matched
          </span>
        )}
      </div>

      {/* Matches Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="all">
            All ({matches.length})
          </TabsTrigger>
          <TabsTrigger value="suggested">
            Suggested ({demand.match_counts.suggested})
          </TabsTrigger>
          <TabsTrigger value="proposed">
            Proposed ({demand.match_counts.proposed})
          </TabsTrigger>
          <TabsTrigger value="interested">
            Interested ({demand.match_counts.interested})
          </TabsTrigger>
          <TabsTrigger value="rejected">
            Rejected ({demand.match_counts.rejected})
          </TabsTrigger>
          <TabsTrigger value="signed">
            Signed ({demand.match_counts.signed})
          </TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="mt-6">
          {filteredMatches.length === 0 ? (
            <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <p className="text-gray-600 dark:text-gray-400">
                No players in this category
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredMatches.map((match) => (
                <MatchPlayerCard
                  key={match.id}
                  match={match}
                  onStatusChange={handleStatusChange}
                  onNotesChange={handleNotesChange}
                  onRemove={handleRemove}
                />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

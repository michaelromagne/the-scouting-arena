"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DemandCard } from "@/components/demands/DemandCard";
import { listDemands, type DemandSummary } from "@/lib/api/demands";

export default function DemandsPage() {
  const [demands, setDemands] = useState<DemandSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<"all" | "open" | "closed">("all");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    loadDemands();
  }, [statusFilter]);

  const loadDemands = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = statusFilter !== "all" ? { status: statusFilter } : {};
      const data = await listDemands(params);
      setDemands(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load demands");
    } finally {
      setLoading(false);
    }
  };

  const filteredDemands = demands.filter((demand) =>
    demand.club_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">Club Demands</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Track and manage club recruitment requests
          </p>
        </div>
        <Link href="/demands/new">
          <Button size="lg">Create Demand</Button>
        </Link>
      </div>

      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <Input
          type="text"
          placeholder="Search by club name..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="max-w-sm"
        />
        <Select value={statusFilter} onValueChange={setStatusFilter as any}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="open">Open</SelectItem>
            <SelectItem value="closed">Closed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="text-center py-12">
          <div className="text-gray-600">Loading demands...</div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
          <p className="text-red-800 dark:text-red-200">{error}</p>
          <Button onClick={loadDemands} variant="outline" size="sm" className="mt-2">
            Retry
          </Button>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && filteredDemands.length === 0 && (
        <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <h3 className="text-xl font-semibold mb-2">No demands found</h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            {searchQuery
              ? "Try adjusting your search"
              : "Create your first demand to get started"}
          </p>
          {!searchQuery && (
            <Link href="/demands/new">
              <Button>Create Demand</Button>
            </Link>
          )}
        </div>
      )}

      {/* Demands Grid */}
      {!loading && !error && filteredDemands.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredDemands.map((demand) => (
            <DemandCard key={demand.id} demand={demand} />
          ))}
        </div>
      )}
    </div>
  );
}

"use client";

import Link from "next/link";
import { useSession, signIn } from "next-auth/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import { fetchBookmarks, type Bookmark } from "@/lib/api";

async function removeBookmark(playerSeasonId: number): Promise<void> {
  const response = await fetch(`/api/bookmarks?player_season_id=${playerSeasonId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Failed to remove bookmark");
  }
}

function BookmarkCard({
  item,
  onRemove,
  isRemoving,
}: {
  item: Bookmark;
  onRemove: () => void;
  isRemoving: boolean;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base text-navy">
          <Link className="hover:underline" href={`/talent-pool/${item.player_id}`}>
            {item.player_name}
          </Link>
        </CardTitle>
        <CardDescription>
          {item.team_name || "Unknown team"} • {item.league_name || "Unknown league"} •{" "}
          {item.season_label || "Unknown season"}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          {(item.position || item.position_primary || "—")}{item.minutes ? ` • ${item.minutes} min` : ""}
        </div>
        <Button variant="outline" size="sm" onClick={onRemove} disabled={isRemoving}>
          {isRemoving ? "Removing..." : "Remove"}
        </Button>
      </CardContent>
    </Card>
  );
}

export default function BookmarksPage() {
  const { data: session, status } = useSession();
  const { toast } = useToast();
  const qc = useQueryClient();

  const bookmarksQuery = useQuery({
    queryKey: ["bookmarks"],
    queryFn: fetchBookmarks,
    enabled: !!session?.user?.id,
  });

  const removeMutation = useMutation({
    mutationFn: removeBookmark,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["bookmarks"] });
      toast({ title: "Removed", description: "Player removed from bookmarks" });
    },
    onError: (err) => {
      toast({
        title: "Error",
        description: err instanceof Error ? err.message : "Failed to remove bookmark",
        variant: "destructive",
      });
    },
  });

  if (status === "loading") {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="h-32 rounded-xl bg-gray-100 animate-pulse" />
      </div>
    );
  }

  if (!session) {
    return (
      <div className="container mx-auto px-4 py-10">
        <Card className="max-w-xl mx-auto">
          <CardHeader>
            <CardTitle className="text-navy">Sign in required</CardTitle>
            <CardDescription>Sign in to access your bookmarked players.</CardDescription>
          </CardHeader>
          <CardContent className="flex gap-3">
            <Button onClick={() => signIn("google")}>Continue with Google</Button>
            <Button asChild variant="outline">
              <Link href="/talent-pool">Browse players</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const items = bookmarksQuery.data ?? [];

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-navy">Bookmarked Players</h1>
          <p className="text-sm text-muted-foreground">
            Your saved players across leagues and seasons.
          </p>
        </div>
        <Button asChild variant="outline">
          <Link href="/talent-pool">Add more</Link>
        </Button>
      </div>

      {bookmarksQuery.isLoading ? (
        <div className="h-40 rounded-xl bg-gray-100 animate-pulse" />
      ) : bookmarksQuery.isError ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-navy">Couldn&apos;t load bookmarks</CardTitle>
            <CardDescription>
              {bookmarksQuery.error instanceof Error ? bookmarksQuery.error.message : "Unknown error"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" onClick={() => bookmarksQuery.refetch()}>
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : items.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-navy">No bookmarks yet</CardTitle>
            <CardDescription>
              Go to the Talent Pool and bookmark players you want to track.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link href="/talent-pool">Open Talent Pool</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Mobile: cards */}
          <div className="grid gap-3 md:hidden">
            {items.map((item) => (
              <BookmarkCard
                key={item.bookmark_id}
                item={item}
                isRemoving={removeMutation.isPending && removeMutation.variables === item.player_season_id}
                onRemove={() => removeMutation.mutate(item.player_season_id)}
              />
            ))}
          </div>

          {/* Desktop: table */}
          <div className="hidden md:block rounded-lg border bg-white overflow-hidden">
            <Table>
              <TableHeader className="sticky top-0 bg-white">
                <TableRow>
                  <TableHead>Player</TableHead>
                  <TableHead>Team</TableHead>
                  <TableHead>League</TableHead>
                  <TableHead>Season</TableHead>
                  <TableHead className="text-right">Minutes</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.bookmark_id} className="odd:bg-gray-50">
                    <TableCell className="font-medium text-navy">
                      <Link className="hover:underline" href={`/talent-pool/${item.player_id}`}>
                        {item.player_name}
                      </Link>
                      <div className="text-xs text-muted-foreground">
                        {item.position || item.position_primary || "—"}
                      </div>
                    </TableCell>
                    <TableCell>{item.team_name || "—"}</TableCell>
                    <TableCell>{item.league_name || "—"}</TableCell>
                    <TableCell>{item.season_label || "—"}</TableCell>
                    <TableCell className="text-right">
                      {item.minutes ?? "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={removeMutation.isPending && removeMutation.variables === item.player_season_id}
                        onClick={() => removeMutation.mutate(item.player_season_id)}
                      >
                        {removeMutation.isPending && removeMutation.variables === item.player_season_id
                          ? "Removing..."
                          : "Remove"}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </>
      )}
    </div>
  );
}

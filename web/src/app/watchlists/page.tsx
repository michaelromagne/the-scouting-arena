"use client";

import Link from "next/link";
import { useState } from "react";
import { useSession, signIn } from "next-auth/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { createWatchlist, deleteWatchlist, fetchWatchlists, type Watchlist } from "@/lib/api";

function WatchlistCard({
  item,
  onDelete,
  isDeleting,
}: {
  item: Watchlist;
  onDelete: () => void;
  isDeleting: boolean;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base text-navy">{item.name}</CardTitle>
        <CardDescription>{item.description || "No description"}</CardDescription>
      </CardHeader>
      <CardContent className="flex items-center justify-between">
        <div className="text-xs text-muted-foreground">
          {item.is_public ? "Public" : "Private"}
        </div>
        <Button variant="outline" size="sm" onClick={onDelete} disabled={isDeleting}>
          {isDeleting ? "Deleting..." : "Delete"}
        </Button>
      </CardContent>
    </Card>
  );
}

export default function WatchlistsPage() {
  const { data: session, status } = useSession();
  const { toast } = useToast();
  const qc = useQueryClient();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [open, setOpen] = useState(false);

  const watchlistsQuery = useQuery({
    queryKey: ["watchlists"],
    queryFn: fetchWatchlists,
    enabled: !!session?.user?.id,
  });

  const createMutation = useMutation({
    mutationFn: createWatchlist,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["watchlists"] });
      toast({ title: "Watchlist created" });
      setName("");
      setDescription("");
      setOpen(false);
    },
    onError: (err) => {
      toast({
        title: "Error",
        description: err instanceof Error ? err.message : "Failed to create watchlist",
        variant: "destructive",
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteWatchlist,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["watchlists"] });
      toast({ title: "Watchlist deleted" });
    },
    onError: (err) => {
      toast({
        title: "Error",
        description: err instanceof Error ? err.message : "Failed to delete watchlist",
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
            <CardDescription>Sign in to manage your watchlists.</CardDescription>
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

  const items = watchlistsQuery.data ?? [];

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-navy">My Watchlists</h1>
          <p className="text-sm text-muted-foreground">
            Create collections of players you want to monitor.
          </p>
        </div>

        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button className="bg-navy text-white hover:bg-navy/90">New watchlist</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create watchlist</DialogTitle>
              <DialogDescription>
                Give your watchlist a name (and optionally a description).
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-3">
              <div className="grid gap-2">
                <label className="text-sm font-medium" htmlFor="watchlist-name">
                  Name
                </label>
                <Input
                  id="watchlist-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. January targets"
                />
              </div>
              <div className="grid gap-2">
                <label className="text-sm font-medium" htmlFor="watchlist-description">
                  Description (optional)
                </label>
                <Input
                  id="watchlist-description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Notes about this list"
                />
              </div>
            </div>
            <DialogFooter className="gap-2">
              <Button variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={() => createMutation.mutate({ name, description })}
                disabled={createMutation.isPending || !name.trim()}
              >
                {createMutation.isPending ? "Creating..." : "Create"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {watchlistsQuery.isLoading ? (
        <div className="h-40 rounded-xl bg-gray-100 animate-pulse" />
      ) : watchlistsQuery.isError ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-navy">Couldn&apos;t load watchlists</CardTitle>
            <CardDescription>
              {watchlistsQuery.error instanceof Error ? watchlistsQuery.error.message : "Unknown error"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" onClick={() => watchlistsQuery.refetch()}>
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : items.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-navy">No watchlists yet</CardTitle>
            <CardDescription>
              Create a watchlist to organize players. Adding players to lists is the next step.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex gap-3">
            <Button onClick={() => setOpen(true)}>Create first watchlist</Button>
            <Button asChild variant="outline">
              <Link href="/bookmarks">View bookmarks</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {items.map((item) => (
            <WatchlistCard
              key={item.id}
              item={item}
              isDeleting={deleteMutation.isPending && deleteMutation.variables === item.id}
              onDelete={() => deleteMutation.mutate(item.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

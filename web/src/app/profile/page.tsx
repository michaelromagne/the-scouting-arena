"use client";

import Link from "next/link";
import { useSession, signIn, signOut } from "next-auth/react";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchBookmarks, fetchWatchlists } from "@/lib/api";

export default function ProfilePage() {
  const { data: session, status } = useSession();

  const bookmarksQuery = useQuery({
    queryKey: ["bookmarks"],
    queryFn: fetchBookmarks,
    enabled: !!session?.user?.id,
  });

  const watchlistsQuery = useQuery({
    queryKey: ["watchlists"],
    queryFn: fetchWatchlists,
    enabled: !!session?.user?.id,
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
            <CardDescription>
              Sign in to view your profile, bookmarks, and watchlists.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex gap-3">
            <Button onClick={() => signIn("google")}>Continue with Google</Button>
            <Button asChild variant="outline">
              <Link href="/">Back to app</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const tier = session.user?.subscriptionTier || "free";
  const isPremium = tier !== "free";

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div className="flex items-center gap-4">
            {session.user?.image ? (
              <img
                src={session.user.image}
                alt={session.user.name || "User"}
                className="w-14 h-14 rounded-full border border-gray-200"
              />
            ) : (
              <div className="w-14 h-14 rounded-full bg-gradient-to-br from-green to-blue-500 flex items-center justify-center text-white font-semibold text-lg">
                {session.user?.name?.charAt(0).toUpperCase() || "U"}
              </div>
            )}
            <div>
              <div className="text-xl font-semibold text-navy">
                {session.user?.name || "My Profile"}
              </div>
              <div className="text-sm text-muted-foreground">
                {session.user?.email}
              </div>
              {isPremium ? (
                <Badge className="mt-2 bg-gradient-to-r from-orange to-yellow-500 text-white">
                  ⭐ {tier.toUpperCase()}
                </Badge>
              ) : (
                <Badge variant="outline" className="mt-2">
                  Free
                </Badge>
              )}
            </div>
          </div>
          <Button
            variant="outline"
            onClick={() => signOut({ callbackUrl: "/" })}
          >
            Sign out
          </Button>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <Card className="border-dashed">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Bookmarks</CardTitle>
              <CardDescription>Saved players</CardDescription>
            </CardHeader>
            <CardContent className="flex items-center justify-between">
              <div className="text-2xl font-semibold text-navy">
                {bookmarksQuery.data?.length ?? 0}
              </div>
              <Button asChild variant="outline" size="sm">
                <Link href="/bookmarks">View</Link>
              </Button>
            </CardContent>
          </Card>

          <Card className="border-dashed">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Watchlists</CardTitle>
              <CardDescription>Collections</CardDescription>
            </CardHeader>
            <CardContent className="flex items-center justify-between">
              <div className="text-2xl font-semibold text-navy">
                {watchlistsQuery.data?.length ?? 0}
              </div>
              <Button asChild variant="outline" size="sm">
                <Link href="/watchlists">View</Link>
              </Button>
            </CardContent>
          </Card>

          <Card className="border-dashed">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Plan</CardTitle>
              <CardDescription>Upgrade anytime</CardDescription>
            </CardHeader>
            <CardContent className="flex items-center justify-between">
              <div className="text-sm text-muted-foreground">
                {isPremium ? "Premium active" : "Free tier"}
              </div>
              <Button asChild size="sm" className="bg-navy text-white hover:bg-navy/90">
                <Link href="/pricing">Upgrade</Link>
              </Button>
            </CardContent>
          </Card>
        </CardContent>
      </Card>
    </div>
  );
}

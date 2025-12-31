"use client";

import Link from "next/link";
import { useSession } from "next-auth/react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function PricingPage() {
  const { data: session } = useSession();
  const tier = session?.user?.subscriptionTier || "free";

  return (
    <div className="container mx-auto px-4 py-10">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-navy">Pricing</h1>
            <p className="text-sm text-muted-foreground">
              Premium plans are coming soon. Your current plan is{" "}
              <Badge variant="outline">{tier}</Badge>.
            </p>
          </div>
          <Button asChild variant="outline">
            <Link href="/profile">Back to profile</Link>
          </Button>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <Card className="border-dashed">
            <CardHeader>
              <CardTitle className="text-navy">Free</CardTitle>
              <CardDescription>Core scouting features</CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Rankings, similarity, and basic bookmarking.
            </CardContent>
          </Card>

          <Card className="border-orange/30">
            <CardHeader>
              <CardTitle className="text-navy">Pro</CardTitle>
              <CardDescription>Advanced workflows</CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Saved comparisons, exports, and richer watchlists.
            </CardContent>
          </Card>

          <Card className="border-orange/30">
            <CardHeader>
              <CardTitle className="text-navy">Club</CardTitle>
              <CardDescription>Team features</CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Shared watchlists, collaboration, and admin controls.
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

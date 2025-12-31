"use client";

import Link from "next/link";
import { useSession, signIn } from "next-auth/react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function SettingsPage() {
  const { data: session, status } = useSession();

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
            <CardDescription>Sign in to access settings.</CardDescription>
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

  return (
    <div className="container mx-auto px-4 py-10">
      <Card className="max-w-2xl mx-auto">
        <CardHeader>
          <CardTitle className="text-navy">Settings</CardTitle>
          <CardDescription>
            Coming soon: email preferences, notifications, and privacy options.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex gap-3">
          <Button asChild variant="outline">
            <Link href="/profile">Back to profile</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

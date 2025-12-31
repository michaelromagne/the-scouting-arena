"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

function AuthErrorContent() {
  const searchParams = useSearchParams();
  const error = searchParams.get("error") || "Unknown";

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-navy via-blue-900 to-navy p-4">
      <Card className="w-full max-w-md shadow-2xl">
        <CardHeader className="text-center space-y-2">
          <CardTitle className="text-2xl font-bold text-navy">Sign-in error</CardTitle>
          <CardDescription className="text-base">
            Something went wrong while trying to authenticate.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            <div className="font-semibold">Error</div>
            <div className="break-words">{error}</div>
          </div>

          <Button asChild className="w-full">
            <Link href="/auth/signin">Back to sign in</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

export default function AuthErrorPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-navy via-blue-900 to-navy">
        <div className="text-white">Loading...</div>
      </div>
    }>
      <AuthErrorContent />
    </Suspense>
  );
}

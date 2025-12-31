"use client";

import { Suspense } from "react";
import { signIn } from "next-auth/react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useSearchParams } from "next/navigation";

function SignInForm() {
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") || "/";
  const error = searchParams.get("error");

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-navy via-blue-900 to-navy p-4">
      <Card className="w-full max-w-md shadow-2xl">
        <CardHeader className="text-center space-y-2">
          <div className="mx-auto w-16 h-16 bg-gradient-to-br from-green to-blue-500 rounded-full flex items-center justify-center text-3xl mb-4">
            ⚽
          </div>
          <CardTitle className="text-2xl font-bold text-navy">Welcome to Scouting</CardTitle>
          <CardDescription className="text-base">
            Sign in to bookmark players, track your searches, and unlock premium features
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error === "OAuthSignin" && "Error connecting to Google. Please try again."}
              {error === "OAuthCallback" && "Error during sign in. Please try again."}
              {error === "OAuthCreateAccount" && "Could not create account. Please try again."}
              {error === "EmailCreateAccount" && "Could not create account. Please try again."}
              {error === "Callback" && "Error during sign in. Please try again."}
              {error === "OAuthAccountNotLinked" && "This email is already associated with another account."}
              {error === "EmailSignin" && "Check your email for a sign in link."}
              {error === "CredentialsSignin" && "Sign in failed. Check your credentials."}
              {!["OAuthSignin", "OAuthCallback", "OAuthCreateAccount", "EmailCreateAccount", "Callback", "OAuthAccountNotLinked", "EmailSignin", "CredentialsSignin"].includes(error) && "An error occurred. Please try again."}
            </div>
          )}

          <Button
            onClick={() => signIn("google", { callbackUrl })}
            className="w-full bg-white hover:bg-gray-50 text-gray-900 border border-gray-300 shadow-sm h-12 text-base font-medium"
            variant="outline"
          >
            <svg className="w-5 h-5 mr-3" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            Continue with Google
          </Button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500">Why sign in?</span>
            </div>
          </div>

          <div className="space-y-3 text-sm text-gray-600">
            <div className="flex items-start gap-3">
              <div className="text-green text-xl">📌</div>
              <div>
                <div className="font-semibold text-navy">Bookmark Players</div>
                <div className="text-xs">Save your favorite players and build custom watchlists</div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="text-green text-xl">📊</div>
              <div>
                <div className="font-semibold text-navy">Track Your Activity</div>
                <div className="text-xs">Get personalized recommendations based on your searches</div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="text-green text-xl">⭐</div>
              <div>
                <div className="font-semibold text-navy">Premium Features</div>
                <div className="text-xs">Unlock advanced analytics and export capabilities</div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="text-green text-xl">📧</div>
              <div>
                <div className="font-semibold text-navy">Weekly Insights</div>
                <div className="text-xs">Receive personalized player updates and market trends</div>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-gray-200 text-center text-xs text-gray-500">
            By signing in, you agree to our Terms of Service and Privacy Policy
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function SignInPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-navy via-blue-900 to-navy">
        <div className="text-white">Loading...</div>
      </div>
    }>
      <SignInForm />
    </Suspense>
  );
}

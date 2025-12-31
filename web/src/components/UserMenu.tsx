"use client";

import { useSession, signIn, signOut } from "next-auth/react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import Link from "next/link";

export default function UserMenu() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return (
      <div className="w-8 h-8 rounded-full bg-gray-200 animate-pulse"></div>
    );
  }

  if (!session) {
    return (
      <Button
        onClick={() => signIn("google")}
        variant="outline"
        size="sm"
        className="bg-white hover:bg-gray-50 text-navy border-navy/20"
      >
        Sign In
      </Button>
    );
  }

  const isPremium = session.user?.subscriptionTier !== "free";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="flex items-center gap-2 focus:outline-none focus:ring-2 focus:ring-green rounded-full">
          {session.user?.image ? (
            <img
              src={session.user.image}
              alt={session.user.name || "User"}
              className="w-8 h-8 rounded-full border-2 border-white shadow-sm"
            />
          ) : (
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-green to-blue-500 flex items-center justify-center text-white font-semibold text-sm">
              {session.user?.name?.charAt(0).toUpperCase() || "U"}
            </div>
          )}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <div className="flex flex-col gap-1">
            <div className="font-semibold text-navy">{session.user?.name}</div>
            <div className="text-xs text-gray-500 font-normal">{session.user?.email}</div>
            {isPremium && (
              <Badge className="bg-gradient-to-r from-orange to-yellow-500 text-white text-xs w-fit mt-1">
                ⭐ {session.user?.subscriptionTier?.toUpperCase()}
              </Badge>
            )}
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/profile" className="cursor-pointer">
            <span className="mr-2">👤</span> My Profile
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href="/bookmarks" className="cursor-pointer">
            <span className="mr-2">📌</span> Bookmarked Players
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href="/watchlists" className="cursor-pointer">
            <span className="mr-2">📋</span> My Watchlists
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href="/comparisons" className="cursor-pointer">
            <span className="mr-2">⚖️</span> Saved Comparisons
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        {!isPremium && (
          <>
            <DropdownMenuItem asChild>
              <Link href="/pricing" className="cursor-pointer text-orange font-semibold">
                <span className="mr-2">⭐</span> Upgrade to Premium
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
          </>
        )}
        <DropdownMenuItem asChild>
          <Link href="/settings" className="cursor-pointer">
            <span className="mr-2">⚙️</span> Settings
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={() => signOut({ callbackUrl: "/" })}
          className="cursor-pointer text-red-600 focus:text-red-600"
        >
          <span className="mr-2">🚪</span> Sign Out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

"use client";

import { useState } from "react";
import { useSession, signIn } from "next-auth/react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";

interface BookmarkButtonProps {
  playerSeasonId: number;
  initialBookmarked?: boolean;
  variant?: "default" | "outline" | "secondary" | "ghost" | "link" | "destructive";
  size?: "default" | "sm" | "lg" | "icon";
  className?: string;
}

export default function BookmarkButton({
  playerSeasonId,
  initialBookmarked = false,
  variant = "outline",
  size = "sm",
  className = "",
}: BookmarkButtonProps) {
  const { data: session } = useSession();
  const { toast } = useToast();
  const [isBookmarked, setIsBookmarked] = useState(initialBookmarked);
  const [isLoading, setIsLoading] = useState(false);

  const handleBookmark = async () => {
    if (!Number.isFinite(playerSeasonId) || playerSeasonId <= 0) {
      toast({
        title: "Bookmark unavailable",
        description: "Missing player season id for this row.",
        variant: "destructive",
      });
      return;
    }

    if (!session) {
      toast({
        title: "Sign in required",
        description: "Please sign in to bookmark players",
        variant: "destructive",
      });
      signIn("google");
      return;
    }

    setIsLoading(true);

    try {
      if (isBookmarked) {
        // Remove bookmark
        const response = await fetch(
          `/api/bookmarks?player_season_id=${playerSeasonId}`,
          { method: "DELETE" }
        );

        if (!response.ok) throw new Error("Failed to remove bookmark");

        setIsBookmarked(false);
        toast({
          title: "Removed from bookmarks",
          description: "Player removed from your bookmarks",
        });
      } else {
        // Add bookmark
        const response = await fetch("/api/bookmarks", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ player_season_id: playerSeasonId }),
        });

        if (!response.ok) {
          const error = await response.json();
          if (response.status === 409) {
            setIsBookmarked(true);
            return;
          }
          throw new Error(error.error || "Failed to add bookmark");
        }

        setIsBookmarked(true);
        toast({
          title: "Added to bookmarks",
          description: "Player added to your bookmarks",
        });
      }
    } catch (error) {
      console.error("Bookmark error:", error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Something went wrong",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Button
      onClick={handleBookmark}
      disabled={isLoading}
      variant={variant}
      size={size}
      className={`${className} ${isBookmarked ? "text-orange" : ""}`}
    >
      {isLoading ? (
        <span className="animate-spin">⏳</span>
      ) : isBookmarked ? (
        <>
          <span className="mr-1">📌</span> Bookmarked
        </>
      ) : (
        <>
          <span className="mr-1">📍</span> Bookmark
        </>
      )}
    </Button>
  );
}

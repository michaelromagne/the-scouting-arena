"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ThumbsUp, ThumbsDown, Send } from "lucide-react";

interface InlineFeedbackProps {
  context?: string; // e.g., "rankings", "comparison"
}

export function InlineFeedback({ context = "page" }: InlineFeedbackProps) {
  const [sentiment, setSentiment] = useState<"positive" | "negative" | null>(null);
  const [comment, setComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async () => {
    if (!sentiment) return;

    setIsSubmitting(true);
    try {
      const payload = {
        sentiment: sentiment === "positive" ? 4 : 2,
        comment: comment || null,
        page: `${window.location.pathname} (${context})`,
        timestamp: new Date().toISOString(),
      };

      console.log("📤 Submitting feedback:", payload);

      const response = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      console.log("📥 Feedback response:", response.status, response.statusText);

      if (!response.ok) {
        const errorText = await response.text();
        console.error("❌ Feedback submission failed:", response.status, errorText);
        throw new Error(`Failed to submit feedback: ${response.status}`);
      }

      setSubmitted(true);
    } catch (error) {
      console.error("❌ Failed to submit feedback:", error);
      alert("Failed to submit feedback. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <Card className="bg-gradient-to-r from-green-50 to-green-100 border-green-200 h-full">
        <CardContent className="pt-6 pb-6 px-4 sm:pt-7 sm:pb-7 sm:px-6 h-full flex flex-col justify-center">
          <div className="text-center">
            <div className="text-4xl mb-2">✅</div>
            <p className="text-lg font-semibold text-green-800">Thank you for your feedback!</p>
            <p className="text-sm text-green-600 mt-1">Your input helps us improve.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-gradient-to-r from-[#0B1B3F] to-[#1A2C5B] border-[#0B1B3F] h-full">
      <CardContent className="pt-6 pb-6 px-4 sm:pt-7 sm:pb-7 sm:px-6 h-full flex flex-col">
        <div className="text-center mb-4 sm:mb-5 flex-grow">
          <h3 className="text-xl sm:text-2xl font-bold text-white mb-3 px-2">How are we doing?</h3>
          <p className="text-sm sm:text-base text-gray-300 mb-4 sm:mb-5 px-2">Your feedback helps us improve the platform</p>

          {/* Sentiment Buttons */}
          <div className="flex justify-center gap-4">
            <button
              onClick={() => setSentiment("positive")}
              className={`flex items-center gap-2 px-4 sm:px-6 py-3 rounded-lg transition-all ${
                sentiment === "positive"
                  ? "bg-[#00FF88] text-[#0B1B3F] scale-110"
                  : "bg-white/10 text-white hover:bg-white/20"
              }`}
              aria-label="Positive feedback"
            >
              <ThumbsUp className="w-5 h-5" />
              <span className="font-medium">Good</span>
            </button>
            <button
              onClick={() => setSentiment("negative")}
              className={`flex items-center gap-2 px-4 sm:px-6 py-3 rounded-lg transition-all ${
                sentiment === "negative"
                  ? "bg-[#FF6B35] text-white scale-110"
                  : "bg-white/10 text-white hover:bg-white/20"
              }`}
              aria-label="Negative feedback"
            >
              <ThumbsDown className="w-5 h-5" />
              <span className="font-medium">Needs work</span>
            </button>
          </div>
        </div>

        {/* Comment Box and Submit Button - Only show if sentiment selected */}
        {sentiment && (
          <div className="space-y-3 mt-auto">
            <Textarea
              placeholder="Tell us more (optional)..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={2}
              className="resize-none bg-white/10 border-white/20 text-white placeholder:text-gray-400"
            />
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting}
              size="lg"
              className="w-full sm:w-auto bg-[#00FF88] hover:bg-[#00DD77] text-[#0B1B3F] font-bold px-4 sm:px-5 py-3 sm:py-4 text-sm sm:text-base shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105"
            >
              {isSubmitting ? (
                "Sending..."
              ) : (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  Send Feedback
                </>
              )}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

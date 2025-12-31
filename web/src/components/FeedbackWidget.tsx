"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { MessageSquare, Send } from "lucide-react";

const sentiments = [
  { emoji: "😞", label: "Poor", value: 1 },
  { emoji: "😐", label: "Okay", value: 2 },
  { emoji: "🙂", label: "Good", value: 3 },
  { emoji: "😀", label: "Great", value: 4 },
];

export function FeedbackWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [sentiment, setSentiment] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async () => {
    if (!sentiment) return;

    setIsSubmitting(true);
    try {
      const payload = {
        sentiment,
        comment: comment || null,
        page: window.location.pathname,
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
      setTimeout(() => {
        setIsOpen(false);
        setSubmitted(false);
        setSentiment(null);
        setComment("");
      }, 2000);
    } catch (error) {
      console.error("❌ Failed to submit feedback:", error);
      alert("Failed to submit feedback. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      {/* Floating Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-50 bg-[#0B1B3F] hover:bg-[#1A2C5B] text-white rounded-full p-4 shadow-lg transition-all hover:scale-110 focus:outline-none focus:ring-2 focus:ring-[#00FF88] focus:ring-offset-2"
        aria-label="Give feedback"
      >
        <MessageSquare className="w-6 h-6" />
      </button>

      {/* Feedback Dialog */}
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Share Your Feedback</DialogTitle>
            <DialogDescription>
              Help us improve your experience. How are you finding the platform?
            </DialogDescription>
          </DialogHeader>

          {submitted ? (
            <div className="py-8 text-center">
              <div className="text-5xl mb-4">✅</div>
              <p className="text-lg font-semibold">Thank you!</p>
              <p className="text-sm text-gray-600">Your feedback helps us improve.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Sentiment Selection */}
              <div className="flex justify-center gap-4">
                {sentiments.map((s) => (
                  <button
                    key={s.value}
                    onClick={() => setSentiment(s.value)}
                    className={`flex flex-col items-center p-3 rounded-lg transition-all ${
                      sentiment === s.value
                        ? "bg-[#00FF88] scale-110"
                        : "bg-gray-100 hover:bg-gray-200"
                    }`}
                    aria-label={`Rate as ${s.label}`}
                  >
                    <span className="text-3xl">{s.emoji}</span>
                    <span className="text-xs mt-1">{s.label}</span>
                  </button>
                ))}
              </div>

              {/* Comment Box */}
              <Textarea
                placeholder="Tell us more (optional)..."
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                rows={4}
                className="resize-none"
              />

              {/* Submit Button */}
              <Button
                onClick={handleSubmit}
                disabled={!sentiment || isSubmitting}
                className="w-full bg-[#0B1B3F] hover:bg-[#1A2C5B]"
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
        </DialogContent>
      </Dialog>
    </>
  );
}

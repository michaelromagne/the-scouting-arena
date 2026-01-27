"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { createDemand } from "@/lib/api/demands";

const POSITIONS = ["GK", "DF", "MF", "FW", "DF,MF", "MF,FW"];
const PRIORITIES = ["low", "medium", "high"] as const;

export default function NewDemandPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    club_name: "",
    club_contact_name: "",
    club_contact_email: "",
    deadline: "",
    priority: "medium" as (typeof PRIORITIES)[number],
    position: [] as string[],
    age_min: "",
    age_max: "",
    default_season: "2526",
    playing_style_notes: "",
    internal_notes: "",
  });

  const handlePositionToggle = (pos: string) => {
    setFormData((prev) => ({
      ...prev,
      position: prev.position.includes(pos)
        ? prev.position.filter((p) => p !== pos)
        : [...prev.position, pos],
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!formData.club_name.trim()) {
      setError("Club name is required");
      return;
    }

    if (formData.position.length === 0) {
      setError("At least one position is required");
      return;
    }

    try {
      setLoading(true);
      const demand = await createDemand({
        club_name: formData.club_name,
        club_contact_name: formData.club_contact_name || undefined,
        club_contact_email: formData.club_contact_email || undefined,
        deadline: formData.deadline || undefined,
        priority: formData.priority,
        position: formData.position,
        age_min: formData.age_min ? parseInt(formData.age_min) : undefined,
        age_max: formData.age_max ? parseInt(formData.age_max) : undefined,
        default_season: formData.default_season,
        playing_style_notes: formData.playing_style_notes || undefined,
        internal_notes: formData.internal_notes || undefined,
      });
      router.push(`/demands/${demand.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create demand");
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-3xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Create New Demand</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-2">
          Define the player profile requirements for this club
        </p>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
          <p className="text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {/* Basic Information */}
        <Card className="p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Basic Information</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                Club Name <span className="text-red-500">*</span>
              </label>
              <Input
                value={formData.club_name}
                onChange={(e) =>
                  setFormData({ ...formData, club_name: e.target.value })
                }
                placeholder="e.g., FC Barcelona"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Contact Name</label>
                <Input
                  value={formData.club_contact_name}
                  onChange={(e) =>
                    setFormData({ ...formData, club_contact_name: e.target.value })
                  }
                  placeholder="e.g., John Doe"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Contact Email</label>
                <Input
                  type="email"
                  value={formData.club_contact_email}
                  onChange={(e) =>
                    setFormData({ ...formData, club_contact_email: e.target.value })
                  }
                  placeholder="e.g., john@club.com"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Deadline</label>
                <Input
                  type="date"
                  value={formData.deadline}
                  onChange={(e) =>
                    setFormData({ ...formData, deadline: e.target.value })
                  }
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Priority</label>
                <Select
                  value={formData.priority}
                  onValueChange={(value: any) =>
                    setFormData({ ...formData, priority: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Low</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        </Card>

        {/* Position & Demographics */}
        <Card className="p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Position & Demographics</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                Position(s) <span className="text-red-500">*</span>
              </label>
              <div className="flex flex-wrap gap-2">
                {POSITIONS.map((pos) => (
                  <Button
                    key={pos}
                    type="button"
                    variant={formData.position.includes(pos) ? "default" : "outline"}
                    onClick={() => handlePositionToggle(pos)}
                  >
                    {pos}
                  </Button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Minimum Age</label>
                <Input
                  type="number"
                  min="16"
                  max="45"
                  value={formData.age_min}
                  onChange={(e) =>
                    setFormData({ ...formData, age_min: e.target.value })
                  }
                  placeholder="e.g., 20"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Maximum Age</label>
                <Input
                  type="number"
                  min="16"
                  max="45"
                  value={formData.age_max}
                  onChange={(e) =>
                    setFormData({ ...formData, age_max: e.target.value })
                  }
                  placeholder="e.g., 28"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Default Season</label>
              <Select
                value={formData.default_season}
                onValueChange={(value) =>
                  setFormData({ ...formData, default_season: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="2526">2025/26</SelectItem>
                  <SelectItem value="2425">2024/25</SelectItem>
                  <SelectItem value="2324">2023/24</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </Card>

        {/* Notes */}
        <Card className="p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Additional Information</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                Playing Style Notes
              </label>
              <Textarea
                value={formData.playing_style_notes}
                onChange={(e) =>
                  setFormData({ ...formData, playing_style_notes: e.target.value })
                }
                placeholder="Describe the desired playing style, characteristics, etc."
                rows={4}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Internal Notes</label>
              <Textarea
                value={formData.internal_notes}
                onChange={(e) =>
                  setFormData({ ...formData, internal_notes: e.target.value })
                }
                placeholder="Private notes for your team"
                rows={3}
              />
            </div>
          </div>
        </Card>

        {/* Actions */}
        <div className="flex gap-4">
          <Button type="submit" disabled={loading} size="lg">
            {loading ? "Creating..." : "Create Demand"}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => router.back()}
            size="lg"
          >
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}

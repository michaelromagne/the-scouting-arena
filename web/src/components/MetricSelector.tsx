import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchMetricsByCategory, type Metric } from "@/lib/api-client";

interface MetricSelectorProps {
  selectedMetric?: string;
  onMetricChange: (metric: string) => void;
  placeholder?: string;
  showDetails?: boolean;
  filterCategory?: string;
}

export function MetricSelector({
  selectedMetric,
  onMetricChange,
  placeholder = "Select metric",
  showDetails = false,
  filterCategory
}: MetricSelectorProps) {
  const [selectedMetricDetails, setSelectedMetricDetails] = useState<Metric | null>(null);

  // Fetch metrics grouped by category
  const { data: metricsByCategory = {}, isLoading } = useQuery({
    queryKey: ["metrics-by-category"],
    queryFn: fetchMetricsByCategory,
    staleTime: 1000 * 60 * 10, // 10 minutes - metrics don't change often
  });

  const handleMetricChange = (metricCode: string) => {
    onMetricChange(metricCode);

    if (showDetails) {
      // Find the metric details across all categories
      for (const categoryMetrics of Object.values(metricsByCategory)) {
        const metric = categoryMetrics.find(m => m.code === metricCode);
        if (metric) {
          setSelectedMetricDetails(metric);
          break;
        }
      }
    }
  };

  const filteredCategories = filterCategory
    ? { [filterCategory]: metricsByCategory[filterCategory] || [] }
    : metricsByCategory;

  if (isLoading) {
    return (
      <Select disabled>
        <SelectTrigger>
          <SelectValue placeholder="Loading metrics..." />
        </SelectTrigger>
      </Select>
    );
  }

  return (
    <div className="space-y-4">
      <Select value={selectedMetric} onValueChange={handleMetricChange}>
        <SelectTrigger>
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {Object.entries(filteredCategories).map(([category, metrics]) => (
            <div key={category}>
              {/* Category header */}
              <div className="px-2 py-1.5 text-sm font-semibold text-muted-foreground">
                {category}
              </div>
              {/* Metrics in this category */}
              {metrics.map((metric) => (
                <SelectItem key={metric.code} value={metric.code}>
                  <div className="flex items-center justify-between w-full">
                    <span>{metric.name}</span>
                    {metric.direction === "lower_is_better" && (
                      <Badge variant="secondary" className="ml-2 text-xs">↓</Badge>
                    )}
                  </div>
                </SelectItem>
              ))}
              {/* Separator between categories */}
              {Object.keys(filteredCategories).indexOf(category) < Object.keys(filteredCategories).length - 1 && (
                <div className="border-t my-1" />
              )}
            </div>
          ))}
        </SelectContent>
      </Select>

      {/* Show detailed information about the selected metric */}
      {showDetails && selectedMetricDetails && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              {selectedMetricDetails.name}
              <Badge variant={selectedMetricDetails.direction === "lower_is_better" ? "destructive" : "default"}>
                {selectedMetricDetails.direction === "lower_is_better" ? "Lower is Better" : "Higher is Better"}
              </Badge>
            </CardTitle>
            {selectedMetricDetails.category && (
              <CardDescription>
                Category: {selectedMetricDetails.category}
              </CardDescription>
            )}
          </CardHeader>
          {(selectedMetricDetails.description || selectedMetricDetails.scale) && (
            <CardContent>
              {selectedMetricDetails.description && (
                <p className="text-sm text-muted-foreground mb-2">
                  {selectedMetricDetails.description}
                </p>
              )}
              {selectedMetricDetails.scale && (
                <p className="text-xs text-muted-foreground">
                  <strong>Scale:</strong> {selectedMetricDetails.scale}
                </p>
              )}
            </CardContent>
          )}
        </Card>
      )}
    </div>
  );
}

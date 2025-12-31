"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

export interface RankingPlayer {
  player_id: number;
  player_name: string;
  team_name: string;
  league_name: string;
  value: number;
  image_url?: string | null;
}

// Keep internal alias for backward compatibility
type Player = RankingPlayer;

interface HorizontalBarChartProps {
  src: string;
  title: string;
  onBarClick?: (data: { player_id: number; player_name: string }) => void;
  onLoadingChange?: (loading: boolean) => void;
  onDataLoaded?: (players: RankingPlayer[]) => void;
  height?: number; // px, default 700
  topN?: number; // default 20
}

export function HorizontalBarChart({
  src,
  title,
  onBarClick,
  onLoadingChange,
  onDataLoaded,
  height = 700,
  topN = 20,
}: HorizontalBarChartProps) {
  const [players, setPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Notify parent about loading state (for page-level overlays if needed)
  useEffect(() => {
    onLoadingChange?.(loading);
  }, [loading, onLoadingChange]);

  useEffect(() => {
    const controller = new AbortController();
    const loadData = async () => {
      try {
        setError(null);
        setLoading(true);
        const response = await fetch(src, { signal: controller.signal });
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
        const data = await response.json();
        const rawItems = Array.isArray(data?.items) ? data.items : [];
        // Transform API response: map quantile_value to value for compatibility
        const items: Player[] = rawItems.map((item: any) => ({
          ...item,
          value: item.quantile_value ?? item.value ?? 0,
        }));
        const slicedItems = items.slice(0, topN);
        setPlayers(slicedItems);
        onDataLoaded?.(slicedItems);
      } catch (err: any) {
        if (err?.name !== "AbortError") {
          setError(err?.message || "Failed to load data");
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    };
    loadData();
    return () => controller.abort();
  }, [src, topN]);

  // Safe min/max (avoid divide-by-zero if range is flat)
  const [minScore, maxScore] = useMemo(() => {
    if (!players.length) return [0, 1];
    const vals = players.map(p => p.value);
    const max = Math.max(...vals);
    const min = Math.min(...vals);
    return max === min ? [min - 1, max + 1] : [min, max];
  }, [players]);

  const getColor = (value: number, alpha = 1) => {
    const normalized = (value - minScore) / (maxScore - minScore); // 0..1
    // RdYlGn
    let r, g, b;
    if (normalized > 0.5) {
      const t = (normalized - 0.5) * 2;
      r = Math.round(254 - (254 - 26) * t);
      g = Math.round(224 - (224 - 152) * t);
      b = Math.round(139 - (139 - 80) * t);
    } else {
      const t = normalized * 2;
      r = Math.round(215 + (254 - 215) * t);
      g = Math.round(48 + (224 - 48) * t);
      b = Math.round(39 + (139 - 39) * t);
    }
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };

  const chartData = useMemo(() => {
    const getPlayerLabel = (player: Player, index: number) => {
      const rank = index + 1;
      const medal = rank === 1 ? "🥇 " : rank === 2 ? "🥈 " : rank === 3 ? "🥉 " : "";
      return `${medal}${rank}. ${player.player_name}`;
    };
    return {
      labels: players.map((p, i) => getPlayerLabel(p, i)),
      datasets: [
        {
          label: "Score",
          data: players.map(p => p.value),
          backgroundColor: players.map(p => getColor(p.value, 1)),
          borderColor: players.map(p => getColor(p.value, 1)),
          borderWidth: 1,
          barThickness: 28,
          categoryPercentage: 0.85,
        },
      ],
    };
  }, [players, getColor]);

  const options = useMemo(
    () => ({
      indexAxis: "y" as const,
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: { left: 20, right: 20, top: 10, bottom: 10 } },
      plugins: {
        legend: { display: false },
        title: {
          display: true,
          text: title,
          color: "#0B1B3F",
          font: { size: 18, weight: "bold" as const },
          padding: 20,
        },
        tooltip: {
          callbacks: {
            title: (ctx: any) => {
              const player = players[ctx[0].dataIndex];
              const rank = ctx[0].dataIndex + 1;
              return `#${rank} ${player.player_name}`;
            },
            label: (ctx: any) => {
              const player = players[ctx.dataIndex];
              const rank = ctx.dataIndex + 1;
              return [
                `Rank: #${rank} of ${topN}`,
                `Team: ${player.team_name}`,
                `League: ${player.league_name}`,
                `Score: ${ctx.parsed.x?.toFixed?.(3) ?? ctx.parsed.x}`,
              ];
            },
          },
        },
      },
      scales: {
        x: {
          beginAtZero: true,
          grid: { color: "rgba(0, 0, 0, 0.1)" },
          ticks: { color: "#4B5563" },
        },
        y: {
          grid: { display: false },
          ticks: {
            color: "#0B1B3F",
            font: (ctx: any) => ({
              size: 16,
              weight: (ctx.index < 3 ? "bold" : "normal") as "bold" | "normal",
              family: "Inter, sans-serif",
            }),
            padding: 12,
            maxTicksLimit: topN,
          },
        },
      },
      onClick: (event: any, elements: any[]) => {
        if (elements.length && onBarClick) {
          const index = elements[0].index;
          const player = players[index];
          onBarClick({ player_id: player.player_id, player_name: player.player_name });
        }
      },
      animation: { duration: 0 }, // optional: further reduce any perceived jump
    }),
    [players, title, onBarClick, topN]
  );

  return (
    <div className="w-full bg-white rounded-lg p-4 relative">
      {/* Fixed-size chart area — stays mounted, no layout shift */}
      <div style={{ height, position: "relative" }}>
        <Bar data={chartData} options={options} />

        {/* Overlay: Loading / Error / Empty — absolute so it doesn't affect layout */}
        {(loading || error || players.length === 0) && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/70 backdrop-blur-[1px]">
            {loading && (
              <div className="w-11/12 max-w-3xl">
                {/* simple skeletons to avoid extra deps */}
                <div className="h-6 w-1/3 mb-4 rounded animate-pulse bg-gray-200" />
                <div className="space-y-2">
                  {Array.from({ length: Math.min(topN, 8) }).map((_, i) => (
                    <div key={i} className="h-8 rounded animate-pulse bg-gray-200" />
                  ))}
                </div>
              </div>
            )}
            {!loading && error && (
              <div className="text-red-600 text-sm">Error: {error}</div>
            )}
            {!loading && !error && players.length === 0 && (
              <div className="text-gray-600 text-sm">No data available</div>
            )}
          </div>
        )}
      </div>

      <div className="mt-3 text-center text-sm text-gray-600">
        💡 Click on any bar to view that player's profile
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { Chart as ChartJS, RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend } from 'chart.js';
import { Radar } from 'react-chartjs-2';

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

interface PlayerMetric {
  code: string;
  name: string;
  category?: string;
  value?: number;
  percentile?: number;
}

interface PlayerStats {
  player_id: number;
  player_name: string;
  team_name: string;
  position: string;
  season_label: string;
  minutes: number;
  metrics: PlayerMetric[];
  // Parsed metric categories - updated to match new categories
  aerial?: number;
  defense?: number;
  discipline?: number;
  passing?: number;
  finishing?: number;
  penalty?: number;
  dribbling?: number;
  // Goalkeeper categories
  penalty_specialist?: number;
  reflexes_saves?: number;
  sweeper_play?: number;
  footwork_distribution?: number;
  air_dominance?: number;
}

interface PlayerRadarChartProps {
  playerId: number;
  season?: string;
  league?: string;
}

// Metric categories for radar chart - updated to match new categories (filtered out penalty and discipline)
const FIELD_PLAYER_CATEGORIES = [
  { key: 'aerial', label: 'Aerial' },
  { key: 'passing', label: 'Passing' },
  { key: 'defense', label: 'Defense' },
  { key: 'finishing', label: 'Finishing' },
  { key: 'dribbling', label: 'Dribbling' },
];

const GOALKEEPER_CATEGORIES = [
  { key: 'penalty_specialist', label: 'Penalty Specialist' },
  { key: 'reflexes_saves', label: 'Reflexes & Saves' },
  { key: 'sweeper_play', label: 'Sweeper Play' },
  { key: 'footwork_distribution', label: 'Footwork & Distribution' },
  { key: 'air_dominance', label: 'Air Dominance' },
];

// Parse API response metrics into component format
const parsePlayerStats = (apiResponse: any): PlayerStats => {
  const parsedStats: PlayerStats = {
    player_id: apiResponse.player_id,
    player_name: apiResponse.player_name,
    team_name: apiResponse.team_name || '',
    position: apiResponse.position || '',
    season_label: apiResponse.season_label || '',
    minutes: apiResponse.minutes || 0,
    metrics: apiResponse.metrics || [],
  };

  // Convert metrics array to direct properties
  if (apiResponse.metrics) {
    for (const metric of apiResponse.metrics) {
      // Use quantile_value if available, fallback to value for backward compatibility
      const metricValue = metric.quantile_value ?? metric.value;
      if (metric.code && metricValue !== null && metricValue !== undefined) {
        // Map metric codes to component properties - updated for new categories
        switch (metric.code) {
          // Field player categories
          case 'aerial':
            parsedStats.aerial = metricValue;
            break;
          case 'defense':
            parsedStats.defense = metricValue;
            break;
          case 'discipline':
            parsedStats.discipline = metricValue;
            break;
          case 'passing':
            parsedStats.passing = metricValue;
            break;
          case 'finishing':
            parsedStats.finishing = metricValue;
            break;
          case 'penalty':
            parsedStats.penalty = metricValue;
            break;
          case 'dribbling':
            parsedStats.dribbling = metricValue;
            break;
          // Goalkeeper categories
          case 'penalty_specialist':
            parsedStats.penalty_specialist = metricValue;
            break;
          case 'reflexes_&_saves':
            parsedStats.reflexes_saves = metricValue;
            break;
          case 'sweeper_play':
            parsedStats.sweeper_play = metricValue;
            break;
          case 'footwork_&_distribution':
            parsedStats.footwork_distribution = metricValue;
            break;
          case 'air_dominance':
            parsedStats.air_dominance = metricValue;
            break;
        }
      }
    }
  }

  return parsedStats;
};

export function PlayerRadarChart({ playerId, season = "2425", league = "Aggregated (All Leagues)" }: PlayerRadarChartProps) {
  const [playerStats, setPlayerStats] = useState<PlayerStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch player statistics
  useEffect(() => {
    const fetchPlayerStats = async () => {
      setLoading(true);
      setError(null);

      try {
        console.log('🔄 Fetching radar data for player:', playerId);

        const response = await fetch(`/api/players/${playerId}?season=${season}&league=${encodeURIComponent(league)}`);

        if (!response.ok) {
          throw new Error('Failed to fetch player statistics');
        }

        const rawStats = await response.json();
        console.log('📊 Raw player stats for radar:', rawStats);

        // Parse the API response into the format expected by the component
        const parsedStats = parsePlayerStats(rawStats);
        console.log('✅ Parsed stats for radar:', parsedStats);

        setPlayerStats(parsedStats);
      } catch (err) {
        console.error('❌ Error fetching player stats for radar:', err);
        setError(err instanceof Error ? err.message : 'Failed to load player statistics');
      } finally {
        setLoading(false);
      }
    };

    fetchPlayerStats();
  }, [playerId, season, league]);

  // Prepare radar chart data
  const getRadarData = () => {
    if (!playerStats) return null;

    // Determine if player is a goalkeeper
    const isKeeper = playerStats.position?.includes('GK');
    const categories = isKeeper ? GOALKEEPER_CATEGORIES : FIELD_PLAYER_CATEGORIES;

    const labels = categories.map(cat => cat.label);
    const playerData = categories.map(cat => {
      const value = playerStats[cat.key as keyof PlayerStats];
      // Convert negative values to 0 for radar display
      return typeof value === 'number' ? Math.max(0, value) : 0;
    });

    // Calculate dynamic max scale based on actual data range (like Python implementation)
    const validData = playerData.filter(val => val > 0); // Only consider non-zero values
    const maxValue = Math.max(...validData);
    const minValue = Math.min(...validData);

    console.log('🔍 Raw player data values:', playerData);
    console.log('🔍 Valid data range:', { minValue, maxValue });

    // Dynamic scaling similar to Python radar charts
    let dynamicMax: number;
    let dynamicMin: number;

    if (validData.length === 0) {
      // Fallback if no valid data
      dynamicMax = 100;
      dynamicMin = 0;
    } else {
      // Always start from 0 but scale the max to show variation
      dynamicMin = 0;

      // Scale max based on data distribution
      if (maxValue <= 1) {
        // Very small values (0-1 range)
        dynamicMax = Math.ceil(maxValue * 1.2);
      } else if (maxValue <= 10) {
        // Small values (1-10 range)
        dynamicMax = Math.ceil(maxValue * 1.15);
      } else if (maxValue <= 100) {
        // Medium values (10-100 range) - likely percentile data
        dynamicMax = Math.min(100, Math.ceil(maxValue * 1.1));
      } else {
        // Large values (>100) - absolute values
        dynamicMax = Math.ceil(maxValue * 1.1);
      }

      // Ensure minimum meaningful range (allow very small ranges for precise scaling)
      if (dynamicMax - dynamicMin < 0.5) {
        dynamicMax = Math.max(0.5, maxValue + 0.1);
      }
    }

    console.log('📈 Radar scaling:', {
      playerData,
      minValue,
      maxValue,
      dynamicMax,
      scalingRange: `0 to ${dynamicMax}`,
      note: 'Negative values displayed as 0'
    });

    return {
      labels,
      datasets: [
        {
          label: playerStats.player_name,
          data: playerData,
          borderColor: '#00FF88', // Bright electric green
          backgroundColor: 'rgba(0, 255, 136, 0.25)', // Subtle fill for modern look
          borderWidth: 2.5, // Modern line thickness
          pointRadius: 3, // Smaller, more modern points
          pointBackgroundColor: '#00FF88',
          pointBorderColor: '#ffffff',
          pointBorderWidth: 1.5, // Thinner point border for modern look
          pointHoverRadius: 6, // Smaller hover radius
          pointHoverBackgroundColor: '#FF6B35', // Orange highlight on hover
          pointHoverBorderColor: '#ffffff',
          pointHoverBorderWidth: 4,
        },
      ],
      dynamicMax,
      dynamicMin: 0, // Always 0
    };
  };

  const radarData = getRadarData();

  const radarOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: {
        beginAtZero: true, // Always start from 0 for consistency
        min: 0, // Always start from 0
        max: radarData?.dynamicMax || 100,
        ticks: {
          stepSize: Math.max(0.1, Math.ceil((radarData?.dynamicMax || 100) / 4 * 10) / 10),
          font: {
            size: 12,
            family: 'Inter, sans-serif',
            weight: 'normal' as const,
          },
          color: 'rgba(255, 255, 255, 0.9)', // Much brighter text
          backdropColor: 'rgba(11, 27, 63, 0.8)', // Semi-transparent navy background for numbers
          backdropPadding: 4,
        },
        grid: {
          color: 'rgba(255, 255, 255, 0.25)', // Much more visible grid lines
          lineWidth: 1.5, // Thicker grid lines
        },
        angleLines: {
          color: 'rgba(255, 255, 255, 0.25)', // Much more visible angle lines
          lineWidth: 1.5, // Thicker angle lines
        },
        pointLabels: {
          font: {
            size: 14, // Bigger text
            weight: 'bold' as const, // Bold text
            family: 'Inter, sans-serif',
          },
          color: '#ffffff', // Pure white text
          padding: 25, // More padding for better spacing
        },
      },
    },
    plugins: {
      legend: {
        display: false, // Hide legend for single player
      },
      tooltip: {
        enabled: true,
        backgroundColor: 'rgba(11, 27, 63, 0.95)', // Navy background
        titleColor: '#00FF88', // Green for consistency
        bodyColor: '#ffffff',
        borderColor: '#00FF88',
        borderWidth: 2,
        cornerRadius: 8,
        padding: 12,
        titleFont: {
          size: 13,
          weight: 'bold' as const,
          family: 'Inter, sans-serif',
        },
        bodyFont: {
          size: 12,
          family: 'Inter, sans-serif',
        },
        callbacks: {
          title: function(context: any) {
            return `${context[0].label}`;
          },
          label: function(context: any) {
            return `Score: ${context.parsed.r.toFixed(1)}`;
          },
          afterLabel: function(context: any) {
            // Add percentile rank if available
            return `Player: ${context.dataset.label}`;
          },
        },
        displayColors: false, // Clean tooltip without color squares
      },
    },
    elements: {
      line: {
        tension: 0.1,
      },
      point: {
        hoverRadius: 8,
      },
    },
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green mx-auto mb-2"></div>
          <div className="text-white/70 text-sm">Loading radar...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center text-red-400">
          <div className="mb-2">⚠️</div>
          <div className="text-sm">Failed to load radar data</div>
        </div>
      </div>
    );
  }

  if (!playerStats || !radarData) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center text-white/70">
          <div className="mb-2">📊</div>
          <div className="text-sm">No radar data available</div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full relative">
      {/* Add subtle glow effect behind the radar */}
      <div className="absolute inset-0 rounded-lg" style={{
        background: 'radial-gradient(circle at center, rgba(0, 255, 136, 0.05) 0%, transparent 70%)',
        filter: 'blur(20px)',
        zIndex: 0
      }}></div>
      <div className="relative z-10 w-full h-full">
        <Radar data={radarData} options={radarOptions} />
      </div>
    </div>
  );
}

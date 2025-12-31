"use client";

import React, { useEffect, useState } from "react";
import { POSITION_MAPPING, getPositionColor, getPlayerPosition } from "@/lib/constants";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Plugin,
} from "chart.js";
import { Scatter } from "react-chartjs-2";

// Custom plugin to draw player names above dots
const playerNamesPlugin: Plugin = {
  id: 'playerNames',
  afterDatasetsDraw(chart: any) {
    const ctx = chart.ctx;
    const meta = chart.getDatasetMeta(0); // Get first dataset meta for scale info

    chart.data.datasets.forEach((dataset: any, datasetIndex: number) => {
      const meta = chart.getDatasetMeta(datasetIndex);

      meta.data.forEach((element: any, index: number) => {
        const dataPoint = dataset.data[index];
        if (!dataPoint || !dataPoint.player_name) return;

        // Only display name if x OR y is greater than 3
        if (dataPoint.x <= 3 && dataPoint.y <= 3) return;

        const x = element.x;
        const y = element.y;

        // Draw player name above the dot
        ctx.save();
        ctx.font = '10px Inter, sans-serif';
        ctx.fillStyle = '#00B366'; // Slightly darker accent green
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';

        // Position text above the dot (subtract radius + 4px)
        const radius = dataPoint.pointRadius || 5.5;
        ctx.fillText(dataPoint.player_name, x, y - radius - 4);

        ctx.restore();
      });
    });
  },
};

ChartJS.register(CategoryScale, LinearScale, PointElement, Title, Tooltip, Legend, playerNamesPlugin);

interface ChartPoint {
  player_id: number;
  player_name: string;
  team_name: string | null;
  league_name: string | null;
  season_label: string | null;
  position: string | null;
  image_url?: string;
  value_m_eur?: number | null;
  x: number;
  y: number;
}

interface ChartResponse {
  x_metric: string;
  y_metric: string;
  total: number;
  items: ChartPoint[];
}

interface InteractiveChartProps {
  src: string;
  title: string;
  xLabel: string;
  yLabel: string;
  selectedPlayer?: { player_id: number } | null;
  shouldZoomOnSelected?: boolean;
  comparisonPlayers?: Array<{ player_id: number }> | null;
  onPointClick?: (data: { player_id: number; player_name: string; team_name: string | null; position: string | null; image_url?: string; value_m_eur?: number | null; x: number; y: number }) => void;
}

export function InteractiveChart({ src, title, xLabel, yLabel, selectedPlayer, shouldZoomOnSelected = false, comparisonPlayers, onPointClick }: InteractiveChartProps) {
  const [chartData, setChartData] = useState<ChartResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [windowWidth, setWindowWidth] = useState(typeof window !== 'undefined' ? window.innerWidth : 1024);

  // Position mapping (from constants)
  const positionMapping = {
    ...POSITION_MAPPING,
    "Unknown": "Unknown",
  };

  // Window resize listener for responsive point sizes and height
  useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth);

    if (typeof window !== 'undefined') {
      window.addEventListener('resize', handleResize);
      return () => window.removeEventListener('resize', handleResize);
    }
  }, []);

  // Calculate responsive chart height based on screen width
  const getResponsiveHeight = () => {
    if (windowWidth < 640) return '500px'; // Mobile
    if (windowWidth < 768) return '550px'; // Small tablet
    if (windowWidth < 1024) return '600px'; // Tablet
    if (windowWidth < 1280) return '650px'; // Small desktop
    return '700px'; // Large desktop
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        setError(null);
        console.log('🔄 Fetching chart data from:', src);
        const response = await fetch(src);
        if (!response.ok) throw new Error('Failed to fetch chart data');
        const data: ChartResponse = await response.json();
        console.log('📊 Chart data received:', data);
        console.log('📊 Items count:', data.items?.length || 0);
        setChartData(data);
      } catch (err) {
        console.error('❌ Error fetching chart data:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setIsLoading(false);
        console.log('✅ Chart data loading finished');
      }
    };

    fetchData();
  }, [src]);

  // Empty data for loading/error states
  const emptyData = { datasets: [] };

  // Get position or default to 'Unknown'
  const getPlayerPositionFromItem = (item: ChartPoint): string => {
    return getPlayerPosition(item.position);
  };

  // Get color for position
  const getPositionColorFromItem = (position: string): string => {
    return getPositionColor(position);
  };

  // Build datasets - always create them, even if empty
  let datasets: any[] = [];
  let positionsInData: string[] = [];

  // Calculate responsive point size based on screen width
  const getResponsivePointSize = () => {
    if (windowWidth < 640) return { base: 4, hover: 6 }; // Mobile
    if (windowWidth < 1024) return { base: 5, hover: 7 }; // Tablet
    return { base: 5.5, hover: 7.5 }; // Desktop - slightly smaller than original
  };

  const pointSizes = getResponsivePointSize();

  // Auto-zoom calculation for selected player (only when requested)
  const getZoomRanges = () => {
    if (!chartData?.items || !selectedPlayer || !shouldZoomOnSelected) {
      return null; // Default zoom - show all data
    }

    const selectedPlayerData = chartData.items.find(item => item.player_id === selectedPlayer.player_id);
    if (!selectedPlayerData) {
      return null;
    }

    // Calculate zoom range around selected player
    const zoomPadding = {
      x: 0.5, // Adjust based on your data range
      y: 0.5,
    };

    return {
      x: {
        min: selectedPlayerData.x - zoomPadding.x,
        max: selectedPlayerData.x + zoomPadding.x,
      },
      y: {
        min: selectedPlayerData.y - zoomPadding.y,
        max: selectedPlayerData.y + zoomPadding.y,
      },
    };
  };

  const zoomRanges = getZoomRanges();
  console.log('🎯 Auto-zoom ranges:', zoomRanges);

  if (chartData && chartData.items && chartData.items.length > 0) {
    // Group players by position and create datasets
    const rawPositionsInData = [...new Set(chartData.items.map(item => getPlayerPositionFromItem(item)))];
    positionsInData = rawPositionsInData.map(pos => POSITION_MAPPING[pos] || pos);
    console.log('🎨 Raw positions in data:', rawPositionsInData);
    console.log('🎨 Formatted positions for legend:', positionsInData);
    console.log('⭐ Selected player ID:', selectedPlayer?.player_id);

    datasets = rawPositionsInData.map(rawPosition => {
      const positionPlayers = chartData.items.filter(item => getPlayerPositionFromItem(item) === rawPosition);

      const positionData = positionPlayers.map(item => {
        const isSelected = selectedPlayer && item.player_id === selectedPlayer.player_id;
        const isComparisonPlayer = comparisonPlayers?.some(cp => cp.player_id === item.player_id) || false;
        const isFirstComparison = comparisonPlayers && comparisonPlayers.length > 0 && comparisonPlayers[0].player_id === item.player_id;
        const isSecondComparison = comparisonPlayers && comparisonPlayers.length > 1 && comparisonPlayers[1].player_id === item.player_id;

        // Determine styling based on selection type
        let borderColor = '#0B1B3F';
        let borderWidth = 1;
        let radius = pointSizes.base;
        let backgroundColor = getPositionColorFromItem(getPlayerPositionFromItem(item));

        if (isSelected) {
          // Single player selection (normal mode)
          borderColor = '#FFD700';
          borderWidth = 4;
          radius = pointSizes.base + 4;
          backgroundColor = '#FFD700';
        } else if (isFirstComparison) {
          // First player in comparison mode
          borderColor = '#4d8ef7';
          borderWidth = 4;
          radius = pointSizes.base + 3;
          backgroundColor = '#4d8ef7';
        } else if (isSecondComparison) {
          // Second player in comparison mode
          borderColor = '#ed5a5d';
          borderWidth = 4;
          radius = pointSizes.base + 3;
          backgroundColor = '#ed5a5d';
        }

        return {
          x: item.x,
          y: item.y,
          player_id: item.player_id,
          player_name: item.player_name,
          team_name: item.team_name,
          league_name: item.league_name,
          position: item.position,
          image_url: item.image_url,
          value_m_eur: item.value_m_eur,
          // Individual point styling based on selection
          pointBorderColor: borderColor,
          pointBorderWidth: borderWidth,
          pointRadius: radius,
          pointHoverRadius: isSelected || isComparisonPlayer ? pointSizes.hover + 5 : pointSizes.hover,
          pointHoverBorderWidth: isSelected || isComparisonPlayer ? 5 : 2,
          pointBackgroundColor: backgroundColor,
        };
      });

      console.log(`📍 ${rawPosition} dataset:`, positionData.length, 'players');

      return {
        label: POSITION_MAPPING[rawPosition] || rawPosition,
        data: positionData,
        backgroundColor: positionData.map(point => point.pointBackgroundColor),
        borderColor: positionData.map(point => point.pointBorderColor),
        borderWidth: positionData.map(point => point.pointBorderWidth),
        pointRadius: positionData.map(point => point.pointRadius),
        pointHoverRadius: positionData.map(point => point.pointHoverRadius),
        pointHoverBorderWidth: positionData.map(point => point.pointHoverBorderWidth),
        pointHoverBackgroundColor: positionData.map(point => point.pointBackgroundColor),
        pointHitRadius: 6, // Larger hit area for selected players
      };
    });
  } else {
    console.log('📉 No data available, using empty datasets');
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      intersect: false,
      mode: 'nearest' as const, // Only show tooltip for nearest point
      axis: 'xy' as const, // Consider both x and y distance
    },
    hover: {
      mode: 'nearest' as const,
      intersect: false,
      axis: 'xy' as const,
    },
    elements: {
      point: {
        hoverRadius: pointSizes.hover + 1,
        hitRadius: 4, // Smaller hit radius to reduce overlapping detection
      },
    },
    plugins: {
      legend: {
        display: true, // Show legend to explain position colors
        position: 'top' as const,
        align: 'end' as const,
        labels: {
          usePointStyle: true,
          pointStyle: 'circle',
          padding: 15,
          font: {
            size: 12,
            family: 'Inter, sans-serif',
          },
          color: '#4B5563',
          filter: function(legendItem: any) {
            // Only show positions that actually have data
            return positionsInData.includes(legendItem.text);
          },
        },
      },
      title: {
        display: false, // We'll handle title externally
      },
      tooltip: {
        enabled: true,
        backgroundColor: '#0B1B3F',
        titleColor: '#FFFFFF',
        bodyColor: '#FFFFFF',
        borderColor: '#00E673',
        borderWidth: 1,
        displayColors: false, // No color indicators for cleaner look
        cornerRadius: 6,
        padding: 8, // Smaller padding for compact tooltip
        caretSize: 4,
        caretPadding: 8,
        position: 'nearest' as const,
        xAlign: 'center' as const,
        yAlign: 'top' as const,
        callbacks: {
          title: function(context: any) {
            if (context && context.length > 0) {
              const point = context[0];
              return point.raw.player_name || 'Unknown Player';
            }
            return 'Unknown Player';
          },
          label: function(context: any) {
            const point = context.raw;
            const labels = [];

            // Team name
            if (point.team_name) {
              labels.push(`🏟️ ${point.team_name}`);
            }

            // Position
            if (point.position) {
              const positionDisplay = POSITION_MAPPING[point.position] || point.position;
              labels.push(`⚽ ${positionDisplay}`);
            }

            // Market value
            if (point.value_m_eur !== null && point.value_m_eur !== undefined && point.value_m_eur > 0) {
              labels.push(`💰 €${point.value_m_eur.toFixed(1)}M`);
            }

            labels.push('');
            labels.push('🖱️ Click to know more');

            return labels;
          },
        },
      },
    },
    layout: {
      padding: {
        top: 30,    // Space for compact tooltips
        right: 15,  // Small right padding
        bottom: 10, // Minimal bottom padding
        left: 10,   // Minimal left padding
      },
    },
    scales: {
      x: {
        type: 'linear' as const,
        position: 'bottom' as const,
        ...(zoomRanges && {
          min: zoomRanges.x.min,
          max: zoomRanges.x.max,
        }),
        title: {
          display: true,
          text: xLabel,
          font: {
            size: 14,
            weight: 'bold' as const,
            family: 'Inter, sans-serif',
          },
          color: '#0B1B3F',
        },
        grid: {
          color: 'rgba(0,0,0,0.1)',
        },
        ticks: {
          color: '#4B5563',
          font: {
            size: 12,
            family: 'Inter, sans-serif',
          },
        },
      },
      y: {
        type: 'linear' as const,
        ...(zoomRanges && {
          min: zoomRanges.y.min,
          max: zoomRanges.y.max,
        }),
        title: {
          display: true,
          text: yLabel,
          font: {
            size: 14,
            weight: 'bold' as const,
            family: 'Inter, sans-serif',
          },
          color: '#0B1B3F',
        },
        grid: {
          color: 'rgba(0,0,0,0.1)',
        },
        ticks: {
          color: '#4B5563',
          font: {
            size: 12,
            family: 'Inter, sans-serif',
          },
        },
      },
    },
    onClick: (event: any, elements: any[]) => {
      if (elements.length > 0 && onPointClick) {
        const element = elements[0];
        const datasetIndex = element.datasetIndex;
        const dataIndex = element.index;

        // Get the clicked point from the correct dataset
        const dataset = datasets[datasetIndex];
        const point = dataset.data[dataIndex];

        console.log('🎯 Scatter point clicked:', point);
        onPointClick({
          player_id: point.player_id,
          player_name: point.player_name,
          team_name: point.team_name,
          position: point.position,
          image_url: point.image_url,
          value_m_eur: point.value_m_eur,
          x: point.x,
          y: point.y,
        });
      }
    },
  };

  const chartConfig = {
    datasets,
  };

  console.log('📈 Final chart config:', chartConfig);

  return (
    <div className="w-full bg-white rounded-lg relative">
      {/* Responsive chart area — adapts to screen size */}
      <div style={{ height: getResponsiveHeight(), maxWidth: '900px', margin: '0 auto' }} className="p-2 relative">
                  <Scatter data={chartConfig} options={options} />

        {/* Overlay: Loading / Error / Empty — absolute so it doesn't affect layout */}
        {(isLoading || error || !chartData || !chartData.items || chartData.items.length === 0) && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/90 backdrop-blur-[1px] rounded-lg">
            {isLoading && (
              <div className="text-center">
                <div className="w-8 h-8 border-4 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                <p className="text-muted-foreground">Loading scatter plot...</p>
              </div>
            )}
            {!isLoading && error && (
              <div className="text-center text-red-500">
                <p>Error loading scatter plot</p>
                <p className="text-sm text-muted-foreground mt-1">{error}</p>
              </div>
            )}
            {!isLoading && !error && chartData && (!chartData.items || chartData.items.length === 0) && (
              <div className="text-center text-muted-foreground">
                <p>No data available for the selected filters</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

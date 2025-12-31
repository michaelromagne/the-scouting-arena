"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false }) as any;

interface PlotlyFigureProps {
  src: string;
  height?: number;
  maxWidth?: number;
}

export function PlotlyFigure({ src, height = 500, maxWidth }: PlotlyFigureProps) {
  const [plotData, setPlotData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const response = await fetch(src);
        const data = await response.json();
        setPlotData(data);
        setIsLoading(false);
      } catch (error) {
        console.error('Chart load error:', error);
        setIsLoading(false);
      }
    };

    loadData();
  }, [src]);

  if (isLoading) {
    return <div className="h-64 flex items-center justify-center">Loading...</div>;
  }

  if (!plotData) {
    return <div className="h-64 flex items-center justify-center">No data</div>;
  }

  const containerStyle = {
    height,
    width: "100%",
    maxWidth: maxWidth ? `${maxWidth}px` : undefined,
    margin: maxWidth ? "0 auto" : undefined,
  };

  return (
    <div style={containerStyle}>
      <Plot
        data={plotData.data}
        layout={{
          ...plotData.layout,
          autosize: true,
          // Ensure the chart respects container bounds
          margin: {
            l: 50,
            r: 50,
            t: 60,
            b: 50,
            ...(plotData.layout?.margin || {})
          }
        }}
        config={{
          responsive: true,
          displayModeBar: false, // Hide toolbar for cleaner look
        }}
        style={{ width: "100%", height: "100%" }}
        useResizeHandler={true}
      />
    </div>
  );
}

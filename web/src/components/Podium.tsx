"use client";

import { useRouter } from "next/navigation";

interface PodiumPlayer {
  player_id: number;
  player_name: string;
  team_name: string;
  value: number;
  image_url?: string | null;
}

interface PodiumProps {
  players: PodiumPlayer[];
  metricName: string;
}

// Metric descriptions based on scouting categories
// Using lowercase keys for case-insensitive matching
const METRIC_DESCRIPTIONS: Record<string, string> = {
  // Outfield categories
  "finishing": "Goal threat and shot efficiency — e.g., goals, shots, shots on target, shot quality",
  "passing": "Creating chances for teammates through passing — e.g., assists, key passes, dangerous final balls, with a variety and execution of passes",
  "dribbling": "Dribbling and carrying that advances play — e.g., take-ons, carries, progressive moves, receiving between lines",
  "defense": "Ball winning and preventing danger — e.g., tackles, interceptions, blocks, clearances, duel success",
  "aerial": "Effectiveness in the air — e.g., aerial duel volume and win rate",
  "discipline": "Game management and mistakes — e.g., cards, fouls committed, offsides, penalties conceded",
  "penalty": "Penalty taking and conversion — e.g., penalties scored, conversion rate",

  // Goalkeeper categories
  "reflexes & saves": "Shot-stopping quality and handling — e.g., saves, save rate, goals prevented",
  "air dominance": "Command of high balls and the box — e.g., crosses faced, claims, claim success",
  "sweeper play": "Proactive interventions off the line — e.g., rushes, interceptions of through balls, average sweep distance",
  "footwork & distribution": "Quality of build-up play — e.g., short build-up and throws, long kicks/launches, goal-kick profile",
  "penalty specialist": "Reading and stopping penalties — e.g., penalties faced and saved",
};

export function Podium({ players, metricName }: PodiumProps) {
  const router = useRouter();

  if (players.length < 3) {
    return null;
  }

  const [first, second, third] = players.slice(0, 3);

  const handlePlayerClick = (playerId: number) => {
    router.push(`/talent-pool/${playerId}`);
  };

  const podiumConfig = [
    {
      player: second,
      rank: 2,
      medal: "🥈",
      height: "h-20",
      containerHeight: "mt-8",
      bgGradient: "from-slate-300 to-slate-400",
      borderColor: "border-slate-400",
      ringColor: "ring-slate-300",
    },
    {
      player: first,
      rank: 1,
      medal: "🥇",
      height: "h-28",
      containerHeight: "mt-0",
      bgGradient: "from-amber-300 to-yellow-500",
      borderColor: "border-yellow-500",
      ringColor: "ring-amber-300",
    },
    {
      player: third,
      rank: 3,
      medal: "🥉",
      height: "h-16",
      containerHeight: "mt-12",
      bgGradient: "from-orange-300 to-orange-500",
      borderColor: "border-orange-400",
      ringColor: "ring-orange-300",
    },
  ];

  // Look up description using lowercase for case-insensitive matching
  const description = METRIC_DESCRIPTIONS[metricName.toLowerCase()];

  return (
    <div className="w-full max-w-2xl mx-auto mb-8">
      <div className="text-center mb-4">
        <h3 className="text-lg font-semibold text-navy mb-1">
          🏆 Top 3 in {metricName}
        </h3>
        {description && (
          <p className="text-sm text-gray-600 italic max-w-xl mx-auto">
            {description}
          </p>
        )}
      </div>

      <div className="flex items-end justify-center gap-3 px-4">
        {podiumConfig.map(({ player, rank, medal, height, containerHeight, bgGradient, borderColor, ringColor }) => (
          <div
            key={player.player_id}
            className={`flex flex-col items-center ${containerHeight} cursor-pointer group`}
            onClick={() => handlePlayerClick(player.player_id)}
          >
            {/* Player Info */}
            <div className="flex flex-col items-center mb-2">
              {/* Player Image */}
              <div
                className={`relative w-16 h-16 md:w-20 md:h-20 rounded-full overflow-hidden border-3 ${borderColor} shadow-lg
                  group-hover:scale-110 transition-transform duration-200 ring-2 ${ringColor} ring-offset-2`}
              >
                {player.image_url ? (
                  <img
                    src={player.image_url}
                    alt={player.player_name}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      e.currentTarget.src = `https://via.placeholder.com/80x80/f1f5f9/64748b?text=${encodeURIComponent(player.player_name.charAt(0))}`;
                    }}
                  />
                ) : (
                  <div className="w-full h-full bg-gradient-to-br from-slate-100 to-slate-200 flex items-center justify-center">
                    <span className="text-2xl font-bold text-slate-400">
                      {player.player_name.charAt(0)}
                    </span>
                  </div>
                )}
              </div>

              {/* Player Name & Team */}
              <div className="mt-2 text-center max-w-[100px] md:max-w-[120px]">
                <div className="text-xs md:text-sm font-bold text-navy truncate group-hover:text-accent transition-colors">
                  {player.player_name}
                </div>
                <div className="text-xs text-gray-500 truncate">
                  {player.team_name}
                </div>
                <div className="text-xs font-bold mt-0.5" style={{ color: "rgb(26, 152, 80)" }}>
                  {player.value !== undefined && player.value !== null ? player.value.toFixed(2) : "N/A"}
                </div>
              </div>
            </div>

            {/* Podium Block */}
            <div
              className={`w-20 md:w-24 ${height} rounded-t-lg bg-gradient-to-t ${bgGradient}
                flex items-center justify-center shadow-md group-hover:shadow-lg transition-shadow`}
            >
              <span className="text-2xl md:text-3xl">{medal}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

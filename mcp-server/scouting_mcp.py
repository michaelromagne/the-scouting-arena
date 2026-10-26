"""MCP Server for The Scouting Arena API to be used with Claude Desktop."""

import asyncio
import logging
import os
import sys
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Set up logging to stderr (Claude Desktop captures this)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("scouting-arena-mcp")

# API Configuration
API_BASE_URL = os.getenv("SCOUTING_API_URL")

if not API_BASE_URL:
    logger.error("SCOUTING_API_URL environment variable is not set")
    raise ValueError("SCOUTING_API_URL environment variable is not set")

logger.info(f"MCP Server starting with API URL: {API_BASE_URL}")

app = Server("the-scouting-arena")


async def make_api_request(endpoint: str, params: dict[str, Any] | None = None) -> dict:
    """Make HTTP request to Scouting Arena API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{API_BASE_URL}{endpoint}"
        logger.info(f"Making API request to: {url} with params: {params}")
        try:
            response = await client.get(url, params=params or {})
            response.raise_for_status()
            logger.info(f"API request successful: {response.status_code}")
            return response.json()
        except Exception as e:
            logger.error(f"API request failed: {e}")
            raise


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools for querying football statistics."""
    return [
        Tool(
            name="search_players",
            description="Search for players by name, league, season, team, or nationality. Returns player details including position, team, and market value.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Player name to search (e.g., 'Mbappé', 'Haaland')",
                    },
                    "league": {
                        "type": "string",
                        "description": "Filter by league (e.g., 'FRA-Ligue 1', 'ENG-Premier League', 'Big 5 European Leagues')",
                    },
                    "season": {
                        "type": "string",
                        "description": "Season label (e.g., '2526' for 2025-26, '2425' for 2024-25)",
                    },
                    "team": {
                        "type": "string",
                        "description": "Filter by team name (e.g., 'Paris Saint-Germain')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 50)",
                        "default": 50,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_player_details",
            description="Get detailed statistics and metrics for a specific player by ID. Returns all performance metrics across categories. Use 'search_players' first to get the player_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "player_id": {
                        "type": "integer",
                        "description": "Player ID (obtained from search_players tool)",
                    },
                    "season": {
                        "type": "string",
                        "description": "Season label (optional, defaults to latest)",
                    },
                },
                "required": ["player_id"],
            },
        ),
        Tool(
            name="get_rankings",
            description="Get top players ranked by a specific metric (e.g., finishing, passing, dribbling). Supports filtering by league, position, age, and market value.",
            inputSchema={
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "description": "Metric code (e.g., 'finishing', 'passing', 'dribbling', 'defense', 'aerial')",
                    },
                    "league": {
                        "type": "string",
                        "description": "Filter by league (optional)",
                    },
                    "season": {
                        "type": "string",
                        "description": "Season label (optional)",
                    },
                    "position": {
                        "type": "string",
                        "description": "Filter by position: FW, MF, DF, GK (optional)",
                    },
                    "min_minutes": {
                        "type": "integer",
                        "description": "Minimum minutes played (default: 0)",
                        "default": 0,
                    },
                    "min_value": {
                        "type": "number",
                        "description": "Minimum market value in millions EUR (optional)",
                    },
                    "max_value": {
                        "type": "number",
                        "description": "Maximum market value in millions EUR (optional)",
                    },
                    "min_age": {
                        "type": "integer",
                        "description": "Minimum player age (optional, 1-99)",
                    },
                    "max_age": {
                        "type": "integer",
                        "description": "Maximum player age (optional, 1-99)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of players to return (default: 25)",
                        "default": 25,
                    },
                },
                "required": ["metric"],
            },
        ),
        Tool(
            name="find_similar_players",
            description="Find players with similar playing styles and statistics to a target player. Uses pre-computed similarity scores. IMPORTANT: You must first use 'search_players' to get the player_id before calling this tool.",
            inputSchema={
                "type": "object",
                "properties": {
                    "player_id": {
                        "type": "integer",
                        "description": "Target player ID (obtained from search_players tool)",
                    },
                    "season": {
                        "type": "string",
                        "description": "Season label (default: '2526')",
                        "default": "2526",
                    },
                    "k": {
                        "type": "integer",
                        "description": "Number of similar players to return (default: 10)",
                        "default": 10,
                    },
                    "position": {
                        "type": "string",
                        "description": "Filter by position (optional)",
                    },
                    "min_value": {
                        "type": "number",
                        "description": "Minimum market value in millions EUR (optional)",
                    },
                    "max_value": {
                        "type": "number",
                        "description": "Maximum market value in millions EUR (optional)",
                    },
                    "min_minutes": {
                        "type": "integer",
                        "description": "Minimum minutes played (optional)",
                    },
                    "min_age": {
                        "type": "integer",
                        "description": "Minimum player age (optional, 1-99)",
                    },
                    "max_age": {
                        "type": "integer",
                        "description": "Maximum player age (optional, 1-99)",
                    },
                },
                "required": ["player_id"],
            },
        ),
        Tool(
            name="compare_metrics",
            description="Compare two metrics across players in a scatter plot format. Returns data points for visualization.",
            inputSchema={
                "type": "object",
                "properties": {
                    "x_metric": {
                        "type": "string",
                        "description": "X-axis metric code",
                    },
                    "y_metric": {
                        "type": "string",
                        "description": "Y-axis metric code",
                    },
                    "league": {
                        "type": "string",
                        "description": "Filter by league (optional)",
                    },
                    "season": {
                        "type": "string",
                        "description": "Season label (optional)",
                    },
                    "position": {
                        "type": "string",
                        "description": "Filter by position (optional)",
                    },
                    "min_minutes": {
                        "type": "integer",
                        "description": "Minimum minutes played (optional)",
                    },
                    "min_value": {
                        "type": "number",
                        "description": "Minimum market value in millions EUR (optional)",
                    },
                    "max_value": {
                        "type": "number",
                        "description": "Maximum market value in millions EUR (optional)",
                    },
                    "min_age": {
                        "type": "integer",
                        "description": "Minimum player age (optional, 1-99)",
                    },
                    "max_age": {
                        "type": "integer",
                        "description": "Maximum player age (optional, 1-99)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum data points (default: 100)",
                        "default": 100,
                    },
                },
                "required": ["x_metric", "y_metric"],
            },
        ),
        Tool(
            name="list_available_metrics",
            description="List all available performance metrics with descriptions. Useful for discovering what statistics can be queried.",
            inputSchema={
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": "Search term to filter metrics (optional)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results (default: 50)",
                        "default": 50,
                    },
                },
            },
        ),
        Tool(
            name="get_team_stats",
            description="Get comprehensive statistics for a specific team in a season.",
            inputSchema={
                "type": "object",
                "properties": {
                    "team_id": {
                        "type": "integer",
                        "description": "Team ID",
                    },
                    "season": {
                        "type": "string",
                        "description": "Season label (default: '2526')",
                        "default": "2526",
                    },
                },
                "required": ["team_id"],
            },
        ),
        Tool(
            name="compare_teams",
            description="Compare two teams side-by-side, including elite players and top performers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "team1_id": {
                        "type": "integer",
                        "description": "First team ID",
                    },
                    "team2_id": {
                        "type": "integer",
                        "description": "Second team ID",
                    },
                    "season": {
                        "type": "string",
                        "description": "Season label (default: '2526')",
                        "default": "2526",
                    },
                },
                "required": ["team1_id", "team2_id"],
            },
        ),
        Tool(
            name="list_teams",
            description="List all teams, optionally filtered by league and season.",
            inputSchema={
                "type": "object",
                "properties": {
                    "league": {
                        "type": "string",
                        "description": "Filter by league (optional)",
                    },
                    "season": {
                        "type": "string",
                        "description": "Filter by season (optional)",
                    },
                },
            },
        ),
        Tool(
            name="get_national_team_players",
            description="Get elite players from a specific nationality/national team.",
            inputSchema={
                "type": "object",
                "properties": {
                    "nationality": {
                        "type": "string",
                        "description": "Nationality (e.g., 'France', 'Brazil', 'England')",
                    },
                    "season": {
                        "type": "string",
                        "description": "Season label (default: '2526')",
                        "default": "2526",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of elite players (default: 10)",
                        "default": 10,
                    },
                },
                "required": ["nationality"],
            },
        ),
        Tool(
            name="list_leagues",
            description="List all available leagues in the database.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="list_seasons",
            description="List all available seasons in the database.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Execute tool calls to query the Scouting Arena API."""
    logger.info(f"Tool called: {name} with arguments: {arguments}")
    try:
        if name == "search_players":
            data = await make_api_request(
                "/players",
                {
                    "q": arguments.get("query"),
                    "league": arguments.get("league"),
                    "season": arguments.get("season"),
                    "team": arguments.get("team"),
                    "limit": arguments.get("limit", 50),
                },
            )
            return [
                TextContent(
                    type="text",
                    text=f"Found {data['total']} players:\n\n"
                    + "\n".join(
                        f"• {p['player_name']} (ID: {p['player_id']}) - {p['position'] or 'N/A'} - "
                        f"{p['team_name'] or 'N/A'} ({p['league_name'] or 'N/A'}) - "
                        f"Season: {p['season_label'] or 'N/A'} - "
                        f"Market Value: €{p['market_value_eur']:.1f}M"
                        if p.get("market_value_eur")
                        else f"• {p['player_name']} (ID: {p['player_id']}) - {p['position'] or 'N/A'} - "
                        f"{p['team_name'] or 'N/A'} ({p['league_name'] or 'N/A'}) - "
                        f"Season: {p['season_label'] or 'N/A'}"
                        for p in data["items"][:20]
                    ),
                )
            ]

        elif name == "get_player_details":
            data = await make_api_request(
                f"/players/{arguments['player_id']}",
                {"season": arguments.get("season")} if arguments.get("season") else {},
            )
            metrics_by_category = {}
            for m in data["metrics"]:
                cat = m.get("category") or "Other"
                if cat not in metrics_by_category:
                    metrics_by_category[cat] = []
                metrics_by_category[cat].append(
                    f"  - {m['name']}: {m['quantile_value']:.1f}%"
                    if m.get("quantile_value") is not None
                    else f"  - {m['name']}: N/A"
                )

            metrics_text = "\n".join(
                f"\n{cat}:\n" + "\n".join(metrics)
                for cat, metrics in sorted(metrics_by_category.items())
            )

            return [
                TextContent(
                    type="text",
                    text=f"Player: {data['player_name']}\n"
                    f"Team: {data['team_name'] or 'N/A'}\n"
                    f"League: {data['league_name'] or 'N/A'}\n"
                    f"Season: {data['season_label'] or 'N/A'}\n"
                    f"Position: {data['position'] or 'N/A'}\n"
                    f"Minutes: {data['minutes'] or 'N/A'}\n"
                    f"Market Value: €{data['value_m_eur']:.1f}M\n"
                    f"\nPerformance Metrics (Percentile Rankings):\n{metrics_text}"
                    if data.get("value_m_eur")
                    else f"Player: {data['player_name']}\n"
                    f"Team: {data['team_name'] or 'N/A'}\n"
                    f"League: {data['league_name'] or 'N/A'}\n"
                    f"Season: {data['season_label'] or 'N/A'}\n"
                    f"Position: {data['position'] or 'N/A'}\n"
                    f"Minutes: {data['minutes'] or 'N/A'}\n"
                    f"\nPerformance Metrics (Percentile Rankings):\n{metrics_text}",
                )
            ]

        elif name == "get_rankings":
            params = {
                "metric": arguments["metric"],
                "min_minutes": arguments.get("min_minutes", 0),
                "limit": arguments.get("limit", 25),
            }
            # Add optional filters
            if arguments.get("league"):
                params["league"] = arguments["league"]
            if arguments.get("season"):
                params["season"] = arguments["season"]
            if arguments.get("position"):
                params["pos"] = arguments["position"]
            if arguments.get("min_value") is not None:
                params["min_value"] = arguments["min_value"]
            if arguments.get("max_value") is not None:
                params["max_value"] = arguments["max_value"]
            if arguments.get("min_age") is not None:
                params["min_age"] = arguments["min_age"]
            if arguments.get("max_age") is not None:
                params["max_age"] = arguments["max_age"]

            data = await make_api_request("/rankings", params)
            return [
                TextContent(
                    type="text",
                    text=f"Top {len(data['items'])} players by {data['metric']} "
                    f"({data['direction']}):\n\n"
                    + "\n".join(
                        f"{i + 1}. {p['player_name']} ({p['team_name'] or 'N/A'}) - "
                        f"{p['quantile_value']:.1f}% - {p['league_name'] or 'N/A'}"
                        for i, p in enumerate(data["items"])
                    ),
                )
            ]

        elif name == "find_similar_players":
            # Build params, excluding None values to use API defaults
            params = {
                "season": arguments.get("season", "2526"),
                "k": arguments.get("k", 10),
                "league": "Aggregated (All Leagues)",  # Always use Aggregated league
            }
            # Add optional filters
            if arguments.get("position"):
                params["pos"] = arguments["position"]
            if arguments.get("min_minutes") is not None:
                params["min_minutes"] = arguments["min_minutes"]
            if arguments.get("min_value") is not None:
                params["min_value"] = arguments["min_value"]
            if arguments.get("max_value") is not None:
                params["max_value"] = arguments["max_value"]
            if arguments.get("min_age") is not None:
                params["min_age"] = arguments["min_age"]
            if arguments.get("max_age") is not None:
                params["max_age"] = arguments["max_age"]

            data = await make_api_request(
                f"/players/{arguments['player_id']}/similar",
                params,
            )

            # Log the response for debugging
            logger.info(
                f"Similar players response: found {len(data.get('similar_players', []))} similar players"
            )

            if not data.get("similar_players"):
                return [
                    TextContent(
                        type="text",
                        text=f"No similar players found for {data.get('target_player_name', 'this player')}. "
                        f"This may mean similarity data hasn't been computed for this player/season combination yet.",
                    )
                ]

            return [
                TextContent(
                    type="text",
                    text=f"Players similar to {data['target_player_name']}:\n\n"
                    + "\n".join(
                        f"{i + 1}. {p['player_name']} ({p['age']} years old) - "
                        f"{p['team_name'] or 'N/A'} ({p['league_name'] or 'N/A'}) - "
                        f"Similarity: {p['similarity_score']:.1%}"
                        if p.get("age")
                        else f"{i + 1}. {p['player_name']} (ID: {p['player_id']}) - "
                        f"{p['team_name'] or 'N/A'} ({p['league_name'] or 'N/A'}) - "
                        f"Similarity: {p['similarity_score']:.1%}"
                        for i, p in enumerate(data["similar_players"])
                    ),
                )
            ]

        elif name == "compare_metrics":
            params = {
                "x": arguments["x_metric"],
                "y": arguments["y_metric"],
                "limit": arguments.get("limit", 100),
            }
            # Add optional filters
            if arguments.get("league"):
                params["league"] = arguments["league"]
            if arguments.get("season"):
                params["season"] = arguments["season"]
            if arguments.get("position"):
                params["pos"] = arguments["position"]
            if arguments.get("min_minutes") is not None:
                params["min_minutes"] = arguments["min_minutes"]
            if arguments.get("min_value") is not None:
                params["min_value"] = arguments["min_value"]
            if arguments.get("max_value") is not None:
                params["max_value"] = arguments["max_value"]
            if arguments.get("min_age") is not None:
                params["min_age"] = arguments["min_age"]
            if arguments.get("max_age") is not None:
                params["max_age"] = arguments["max_age"]

            data = await make_api_request("/scatter", params)
            return [
                TextContent(
                    type="text",
                    text=f"Scatter plot data: {data['x']} vs {data['y']}\n"
                    f"Total points: {data['total']}\n\n"
                    f"Sample players:\n"
                    + "\n".join(
                        f"• {p['player_name']} ({p['position']}) - "
                        f"{data['x']}: {p['x']:.2f}, {data['y']}: {p['y']:.2f}"
                        for p in data["items"][:10]
                    ),
                )
            ]

        elif name == "list_available_metrics":
            data = await make_api_request(
                "/metrics",
                {
                    "q": arguments.get("search"),
                    "limit": arguments.get("limit", 50),
                },
            )
            return [
                TextContent(
                    type="text",
                    text=f"Available metrics ({data['total']} total):\n\n"
                    + "\n".join(
                        f"• {m['code']} - {m['name']}\n"
                        f"  Category: {m.get('category') or 'N/A'}\n"
                        f"  Direction: {m['direction']}\n"
                        f"  Description: {m.get('description') or 'N/A'}"
                        for m in data["items"]
                    ),
                )
            ]

        elif name == "get_team_stats":
            data = await make_api_request(
                f"/teams/{arguments['team_id']}/stats",
                {"season": arguments.get("season", "2526")},
            )
            return [
                TextContent(
                    type="text",
                    text=f"Team: {data['team_name']}\n"
                    f"League: {data['league_name'] or 'N/A'}\n"
                    f"Season: {data['season_label'] or 'N/A'}\n"
                    f"Games Played: {data['games_played'] or 'N/A'}\n\n"
                    f"Top Metrics:\n"
                    + "\n".join(
                        f"• {code}: {metric['quantile_value']:.1f}%"
                        for code, metric in sorted(
                            data["metrics"].items(),
                            key=lambda x: x[1]["quantile_value"],
                            reverse=True,
                        )[:10]
                    ),
                )
            ]

        elif name == "compare_teams":
            data = await make_api_request(
                "/teams/compare",
                {
                    "team1_id": arguments["team1_id"],
                    "team2_id": arguments["team2_id"],
                    "season": arguments.get("season", "2526"),
                },
            )
            return [
                TextContent(
                    type="text",
                    text=f"Team Comparison:\n\n"
                    f"Team 1: {data['team1']['team_name']}\n"
                    f"Elite Players: {', '.join(p['player_name'] for p in data['elite_players_team1'][:5])}\n\n"
                    f"Team 2: {data['team2']['team_name']}\n"
                    f"Elite Players: {', '.join(p['player_name'] for p in data['elite_players_team2'][:5])}",
                )
            ]

        elif name == "list_teams":
            data = await make_api_request(
                "/teams/list",
                {
                    "league": arguments.get("league"),
                    "season": arguments.get("season"),
                },
            )
            return [
                TextContent(
                    type="text",
                    text=f"Found {len(data)} teams:\n\n"
                    + "\n".join(
                        f"• {t['name']} (ID: {t['id']}) - {t['league_name'] or 'N/A'}"
                        for t in data[:50]
                    ),
                )
            ]

        elif name == "get_national_team_players":
            data = await make_api_request(
                f"/national-teams/{arguments['nationality']}",
                {
                    "season": arguments.get("season", "2526"),
                    "limit": arguments.get("limit", 10),
                },
            )
            return [
                TextContent(
                    type="text",
                    text=f"Elite players from {data['nationality']}:\n\n"
                    + "\n".join(
                        f"{i + 1}. {p['player_name']} ({p['position']}) - {p['team_name']}\n"
                        f"   Elite categories: {', '.join(p['elite_categories'].keys())}"
                        for i, p in enumerate(data["elite_players"])
                    ),
                )
            ]

        elif name == "list_leagues":
            data = await make_api_request("/leagues")
            return [
                TextContent(
                    type="text",
                    text="Available leagues:\n\n"
                    + "\n".join(f"• {league}" for league in data),
                )
            ]

        elif name == "list_seasons":
            data = await make_api_request("/seasons")
            return [
                TextContent(
                    type="text",
                    text="Available seasons:\n\n"
                    + "\n".join(f"• {season}" for season in data),
                )
            ]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except httpx.HTTPStatusError as e:
        return [
            TextContent(
                type="text",
                text=f"API Error: {e.response.status_code} - {e.response.text}",
            )
        ]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())

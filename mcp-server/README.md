# The Scouting Arena MCP Server

MCP (Model Context Protocol) server for querying The Scouting Arena football statistics API through Claude Desktop.

## Features

Query football statistics using natural language:
- **Player Search**: Find players by name, league, team, nationality
- **Player Details**: Get comprehensive statistics and performance metrics
- **Rankings**: Top players by any metric with filters (age, value, position, minutes)
- **Similar Players**: Find players with similar playing styles (with value/age filters)
- **Metric Comparison**: Compare two metrics across players (with comprehensive filters)
- **Team Analysis**: Team statistics and comparisons
- **National Teams**: Elite players by nationality

### Advanced Filtering

All ranking and comparison tools support:
- **Age filters**: `min_age` and `max_age` (e.g., find players under 23)
- **Market value filters**: `min_value` and `max_value` in millions EUR (e.g., €50M-€100M)
- **Minutes played**: `min_minutes` (e.g., only players with 500+ minutes)
- **Position**: FW, MF, DF, GK
- **League**: Any league or "Big 5 European Leagues"

## Installation

### 1. Set up the MCP server

At the root of the repo, run:

```bash
poetry install
```

or

```bash
poetry install --only mcp
```

### 2. Configure Claude Desktop

Add to your Claude Desktop config file (do not forget to replace SCOUTING_API_URL placeholder value):

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "scouting-arena": {
      "command": "/Users/michaelromagne/perso/the-scouting-arena/mcp-server/.venv/bin/python",
      "args": [
        "/Users/michaelromagne/perso/the-scouting-arena/mcp-server/scouting_mcp.py"
      ],
      "env": {
        "SCOUTING_API_URL": "https://your-railway-app.railway.app"
      }
    }
  }
}
```


### 3. Restart Claude Desktop

Completely quit and restart Claude Desktop for the changes to take effect.

## Usage Examples

Once configured, you can ask Claude questions like:

### Player Queries
- "Find information about Kylian Mbappé in the 2025-26 season"
- "Who are the top 10 finishers in the Premier League?"
- "Show me players similar to Erling Haaland"
- "Compare passing vs dribbling for midfielders in Ligue 1"
- "Find top forwards under 23 years old with market value over €50M"
- "Show me similar players to Mbappé worth between €30M and €100M"
- "Find similar players to Haaland who are under 25 years old"
- "Compare finishing vs dribbling for young players (under 25) in La Liga"

**Note:** When asking for similar players or detailed stats, Claude will automatically:
1. First search for the player by name to get their ID
2. Then use that ID to fetch similar players or detailed statistics

Example conversation:
- **You:** "Find players similar to Kylian Mbappé"
- **Claude:** *Searches for "Mbappé" → Gets player_id → Finds similar players*

### Team Queries
- "Compare Paris Saint-Germain and Manchester City"
- "What are the stats for Real Madrid this season?"
- "List all teams in the Premier League"

### National Team Queries
- "Show me the best French players"
- "Who are the elite Brazilian forwards?"

### Metrics & Rankings
- "What metrics are available for defenders?"
- "Rank goalkeepers by reflexes and saves"
- "Show me the best young players under 23"

## API Endpoints Used

The MCP server connects to these API endpoints:

- `GET /players` - Search players
- `GET /players/{id}` - Player details
- `GET /rankings` - Top players by metric
- `GET /players/{id}/similar` - Similar players
- `GET /scatter` - Metric comparison data
- `GET /metrics` - Available metrics
- `GET /teams/list` - List teams
- `GET /teams/{id}/stats` - Team statistics
- `GET /teams/compare` - Compare teams
- `GET /national-teams/{nationality}` - National team players
- `GET /leagues` - Available leagues
- `GET /seasons` - Available seasons

## Configuration

### Environment Variables

- `SCOUTING_API_URL`: Base URL of your Scouting Arena API (required)

### Railway Deployment

When your API is deployed on Railway:

1. Get your Railway app URL (e.g., `https://scouting-api-production.up.railway.app`)
2. Update the `SCOUTING_API_URL` in your Claude Desktop config
3. Ensure your Railway app has CORS configured to allow requests

### Making API Public Temporarily

If you need to make your Railway API public for testing:

1. Go to your Railway project dashboard
2. Navigate to Settings → Networking
3. Enable "Public Networking"
4. Copy the public URL
5. Update your MCP config with this URL
6. **Remember to disable public access** when done testing

## Security Notes

- The API URL is stored in Claude Desktop config (local to your machine)
- No authentication is currently implemented in the MCP server
- If your API requires authentication, add headers in `make_api_request()`
- Consider using Railway's private networking for production

## Debugging

### View Claude Desktop Logs

**macOS:**
```bash
# Real-time logs
tail -f ~/Library/Logs/Claude/mcp*.log

# Or view specific log
tail -f ~/Library/Logs/Claude/mcp-server-scouting-arena.log

# List all logs
ls -la ~/Library/Logs/Claude/
```

**Windows:**
```powershell
# Logs location
%APPDATA%\Claude\logs\
```

### Test MCP Server Manually

Test if the server starts correctly:

```bash
cd /Users/michaelromagne/perso/the-scouting-arena/mcp-server
source .venv/bin/activate
export SCOUTING_API_URL="https://your-railway-app.railway.app"
python scouting_mcp.py
```

If it hangs (waiting for input), that's good - it means the server is running. Press Ctrl+C to exit.

### Common Issues

**"SCOUTING_API_URL environment variable is not set"**
- Check your Claude Desktop config has the `env` section
- Verify the URL is correct (no trailing slash)
- Restart Claude Desktop after config changes

**"Module not found" errors**
- Install dependencies: `uv pip install mcp httpx`
- Or use system Python: `pip install mcp httpx`
- Check the Python path in config matches your installation

**"Connection refused" errors**
- Verify your Railway app is running
- Check the API URL is correct in config
- Test the URL in your browser first
- Ensure CORS is configured properly

**"Tool not found" errors**
- Restart Claude Desktop completely (Cmd+Q on Mac)
- Verify the config file path is correct
- Check the Python path in the config matches your venv

**API timeout errors**
- The default timeout is 30 seconds
- For large queries, you may need to increase this in `make_api_request()`

### Enable Debug Logging

The MCP server now logs to stderr, which Claude Desktop captures. Check the logs at:
- macOS: `~/Library/Logs/Claude/mcp-server-scouting-arena.log`
- Windows: `%APPDATA%\Claude\logs\`

Logs include:
- Server startup messages
- API requests and responses
- Tool invocations
- Error details

## Development

To modify the MCP server:

1. Edit `scouting_mcp.py`
2. Restart Claude Desktop to reload changes
3. Test with Claude by asking relevant questions

### Adding New Tools

To add a new tool:

1. Add tool definition in `list_tools()`
2. Add handler in `call_tool()`
3. Test the API endpoint manually first
4. Restart Claude Desktop

## License

Same as The Scouting Arena project.

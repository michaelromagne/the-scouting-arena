# Club Demand Tracking Feature Design

**Date**: 2026-01-27
**Status**: Draft
**Author**: Design session with prospect input

## Overview

Add demand tracking capabilities to The Scouting Arena to enable scouting agencies to manage club requests for players. The system will track demands from clubs looking for specific player profiles, automatically suggest matching players using existing platform statistics, and manage the full proposal lifecycle from suggestion through deal closure.

## Goals

1. Enable scouts to log and track club demands with detailed scouting criteria
2. Leverage existing player statistics and similarity systems to automatically suggest matching candidates
3. Track the full lifecycle: demand → matched players → proposals → status updates → closure
4. Keep existing platform features unchanged, integrating demand tracking as a new top-level section
5. Design the system to support player demands in the future (players looking for clubs)

## Non-Goals (v1)

- Player demand tracking (future enhancement)
- Automated notifications/reminders
- Email integration for club communications
- Multi-user/team collaboration features
- Advanced analytics/reporting dashboards

## Architecture

### Data Model

#### ClubDemand Table

| Field | Type | Description |
|-------|------|-------------|
| id | Integer (PK) | Unique identifier |
| club_name | String | Name of the requesting club |
| club_contact_name | String (nullable) | Contact person at club |
| club_contact_email | String (nullable) | Contact email |
| created_date | DateTime | When demand was created |
| deadline | Date (nullable) | Club's decision timeline |
| status | Enum | open, closed |
| priority | Enum | low, medium, high |
| position | String[] | Required positions (e.g., ["ST", "RW"]) |
| age_min | Integer (nullable) | Minimum age |
| age_max | Integer (nullable) | Maximum age |
| nationality_preferences | String[] (nullable) | Preferred nationalities |
| budget_min | Integer (nullable) | Budget range (EUR) |
| budget_max | Integer (nullable) | Budget range (EUR) |
| metrics_requirements | JSONB | Metric thresholds (e.g., `{"assists_per90": {"min": 5}}`) |
| playing_style_notes | Text (nullable) | Free-form description of playing style |
| default_season | String | Default season for matching (e.g., "2526") |
| internal_notes | Text (nullable) | Scout's private notes |

#### DemandMatch Table

| Field | Type | Description |
|-------|------|-------------|
| id | Integer (PK) | Unique identifier |
| demand_id | Integer (FK) | References ClubDemand |
| player_id | Integer (FK) | References Player |
| match_score | Float | 0-1 score indicating fit quality |
| status | Enum | suggested, proposed, interested, rejected, signed |
| added_date | DateTime | When player was matched |
| status_updated_date | DateTime | Last status change |
| notes | Text (nullable) | Scout notes about this match |

#### Status Enum Values

- **suggested**: System-generated match, not yet reviewed
- **proposed**: Scout has pitched player to club
- **interested**: Club has expressed interest
- **rejected**: Club has passed or deal fell through
- **signed**: Deal completed successfully

#### Future: PlayerDemand Table

Similar structure to ClubDemand but inverted (player looking for club). To be designed when needed. Will add `demand_type` enum to differentiate.

### Database Schema Changes

- Add two new tables via Alembic migration
- No changes to existing Player, Team, Metric, or Similarity tables
- Foreign keys: DemandMatch.demand_id → ClubDemand.id, DemandMatch.player_id → Player.id

## Matching Algorithm

### Hybrid Filter + Rank Approach

**Step 1: Hard Filters**
- Filter players based on non-negotiable criteria:
  - Position matches one of demand's required positions
  - Age within [age_min, age_max] range
  - Nationality in nationality_preferences (if specified)
  - Minutes played >= 270 (existing platform threshold)
  - Season = demand.default_season (or season specified by scout)

**Step 2: Metrics Threshold Filtering**
- Parse metrics_requirements JSON
- For each metric with a threshold, filter players:
  - Example: `{"assists_per90": {"min": 5}}` → player.assists_per90 >= 5
- Query against existing tall metrics schema (PlayerMetric table)

**Step 3: Ranking & Scoring**
- Calculate match_score for remaining players:
  - Count how many optional criteria they satisfy
  - Weight by category scores (shooting, passing, defending, etc.)
  - Optionally: Use existing similarity system to find players similar to top performers in that position
- Sort by match_score descending
- Return top N players (configurable, default 50)

### Implementation Details

- Reuse existing database query patterns from `/rankings` and `/players/{id}/similar` endpoints
- Match_score calculation in Python (FastAPI service layer)
- Cache results in Redis with key: `demand:{demand_id}:matches:{criteria_hash}`
- Cache TTL: 10 minutes, invalidate when demand criteria change

### User Flow

1. Scout creates demand with detailed criteria
2. Scout clicks "Run Matching" → system executes algorithm
3. System populates DemandMatch table with status="suggested"
4. Scout reviews suggestions, curates list
5. Scout moves selected players to status="proposed"
6. Scout updates status as club provides feedback

## API Design

### New Router: `/demands`

#### Core CRUD

**POST /demands**
- Create new club demand
- Request body: ClubDemand fields
- Response: Created demand object with id
- Status: 201 Created

**GET /demands**
- List all demands with optional filters
- Query params: `status`, `club_name`, `position`, `date_from`, `date_to`
- Response: Array of demand summaries with match counts
- Status: 200 OK

**GET /demands/{id}**
- Get demand detail
- Response: Full demand object + match statistics (counts by status)
- Status: 200 OK

**PATCH /demands/{id}**
- Update demand (criteria, status, notes)
- Request body: Partial ClubDemand fields
- Response: Updated demand object
- Status: 200 OK

**DELETE /demands/{id}**
- Delete demand and associated matches
- Status: 204 No Content

#### Matching & Suggestions

**POST /demands/{id}/match**
- Run matching algorithm
- Query params: `season` (optional, overrides default_season), `limit` (default 50)
- Response: Array of matched players with match_score
- Side effect: Populates DemandMatch table with status="suggested"
- Status: 200 OK

**GET /demands/{id}/matches**
- Get all matched players for a demand
- Query params: `status` (filter by status), `sort_by` (match_score, added_date)
- Response: Array of DemandMatch objects with enriched player data
- Status: 200 OK

#### Proposal Management

**PATCH /demands/{id}/matches/{player_id}**
- Update match status and/or notes
- Request body: `{"status": "proposed", "notes": "Great fit for their system"}`
- Response: Updated DemandMatch object
- Status: 200 OK

**POST /demands/{id}/matches/{player_id}/propose**
- Shortcut to set status="proposed"
- Status: 200 OK

**DELETE /demands/{id}/matches/{player_id}**
- Remove player from demand matches
- Status: 204 No Content

### Response Formats

**Demand Summary (List)**
```json
{
  "id": 1,
  "club_name": "FC Example",
  "position": ["ST"],
  "status": "open",
  "deadline": "2026-03-15",
  "created_date": "2026-01-27T10:00:00Z",
  "match_counts": {
    "suggested": 20,
    "proposed": 5,
    "interested": 2,
    "rejected": 1,
    "signed": 0
  }
}
```

**Demand Detail**
```json
{
  "id": 1,
  "club_name": "FC Example",
  "club_contact_name": "John Doe",
  "club_contact_email": "john@fcexample.com",
  "created_date": "2026-01-27T10:00:00Z",
  "deadline": "2026-03-15",
  "status": "open",
  "priority": "high",
  "position": ["ST"],
  "age_min": 23,
  "age_max": 28,
  "nationality_preferences": ["FRA", "ESP"],
  "budget_min": 5000000,
  "budget_max": 15000000,
  "metrics_requirements": {
    "assists_per90": {"min": 5},
    "progressive_passes": {"min": 3.5}
  },
  "playing_style_notes": "Looking for a creative forward who can link play",
  "default_season": "2526",
  "internal_notes": "Spoke with sporting director on Jan 25",
  "match_counts": {
    "suggested": 20,
    "proposed": 5,
    "interested": 2,
    "rejected": 1,
    "signed": 0
  }
}
```

**DemandMatch (with enriched player data)**
```json
{
  "id": 1,
  "demand_id": 1,
  "player_id": 123,
  "match_score": 0.87,
  "status": "proposed",
  "added_date": "2026-01-27T11:00:00Z",
  "status_updated_date": "2026-01-27T14:30:00Z",
  "notes": "Presented to club on Jan 27",
  "player": {
    "id": 123,
    "name": "Example Player",
    "team": "Example Team",
    "position": "ST",
    "age": 25,
    "nationality": "FRA",
    "image_url": "https://...",
    "market_value": 10000000,
    "key_metrics": {
      "assists_per90": 6.2,
      "progressive_passes": 4.1
    }
  }
}
```

### Caching Strategy

- **Demand list**: 5min cache, key: `demands:list:{filters_hash}`
- **Demand detail**: 2min cache, key: `demand:{id}`, invalidate on PATCH/DELETE
- **Match suggestions**: 10min cache, key: `demand:{id}:matches:{criteria_hash}`, invalidate when criteria change
- Reuse existing Redis configuration and cache decorators

## Frontend Design

### New Route Group: `/web/app/demands/`

#### Pages

**`/demands`** - Demands Dashboard
- Layout: Table or card grid view (toggle)
- Columns: Club Name, Position, Status Badge, Deadline, Match Counts, Created Date, Actions
- Filters:
  - Status dropdown (All, Open, Closed)
  - Position multi-select
  - Date range picker
  - Search by club name
- Actions: "Create Demand" button (top-right), row actions (view, edit, delete)
- Sort: by deadline, created_date, club_name

**`/demands/new`** - Create Demand Form
- Multi-section form:
  - **Basic Information**: Club name, contact name, contact email, deadline, priority
  - **Position & Demographics**: Position checkboxes (ST, RW, CM, etc.), age range slider, nationality multi-select
  - **Metrics Requirements**: Dynamic form
    - Select metric from dropdown (all available metrics)
    - Set min/max threshold
    - Add multiple metric requirements
  - **Playing Style**: Rich text editor for free-form description
  - **Season**: Dropdown to select default season, checkbox for "use latest season"
- Validation: Required fields (club_name, position, default_season)
- Submit → POST /demands → redirect to /demands/{id}

**`/demands/[id]`** - Demand Detail & Management
- Top section: Demand info card (editable inline or via edit button)
  - Club name, contact, deadline, priority
  - Criteria summary: positions, age range, budget, key metrics
  - Status toggle (open/closed)
- "Run Matching" button → calls POST /demands/{id}/match
- Tabs:
  - **All Matches**: All matched players, sortable by match_score/status/date
  - **Suggested**: Filtered to status=suggested (system suggestions awaiting review)
  - **Proposed**: Filtered to status=proposed (actively pitching to club)
  - **Pipeline**: Filtered to status=interested or signed (active opportunities)
  - **Rejected**: Archived rejections
- Player cards in each tab:
  - Player photo, name, team, position, age, nationality
  - Match score (visual indicator: progress bar or percentage)
  - Key metrics (those specified in demand criteria)
  - Status dropdown (change status inline)
  - Notes text field (editable)
  - Actions: View player profile (link to /players/{id}), Remove from demand

**`/demands/[id]/edit`** - Edit Demand (optional separate page)
- Same form as `/demands/new` but pre-populated
- Submit → PATCH /demands/{id}

### Components (New)

**DemandCard**
- Reusable card for dashboard view
- Shows: club name, position badges, status badge, deadline countdown, match count summary
- Click → navigate to /demands/{id}

**DemandForm**
- Reusable form for create/edit
- Handles validation, submission, error states

**MatchPlayerCard**
- Player card showing: photo, name, stats, match_score, status, notes
- Extends existing PlayerCard component
- Actions: status dropdown, notes editor, remove button

**StatusBadge**
- Color-coded badges for demand status and match status
- suggested: gray, proposed: blue, interested: green, rejected: red, signed: purple

**MetricsRequirementBuilder**
- Dynamic form component for adding/removing metric thresholds
- Dropdown of available metrics + min/max inputs

### Navigation

- Add "Demands" to main navigation (same level as Home, Rankings, Players, etc.)
- Badge showing count of open demands (optional)

### Component Reuse

- **PlayerCard**: Extend for MatchPlayerCard
- **Metric selectors**: Reuse from existing rankings/filter components
- **Plotly charts**: Add visualizations for match score distribution, demand pipeline funnel
- **Form inputs**: Reuse from existing forms (shadcn/ui components)

### State Management

- React Query for API calls, caching, optimistic updates
- Cache invalidation: invalidate demand list when creating/updating/deleting demands
- Optimistic status updates: update UI immediately, rollback on error

## Implementation Plan

### Phase 1: Backend

1. **Database Migration**
   - Create Alembic migration for ClubDemand and DemandMatch tables
   - Run migration in dev environment

2. **API Router & Services**
   - Create `scouting/api/routers/demands.py`
   - Implement CRUD endpoints
   - Create `scouting/api/services/demand_matching.py` for matching algorithm
   - Reuse existing player query utilities from rankings/similarity modules

3. **Testing**
   - Unit tests for matching algorithm with known player dataset
   - Integration tests for API endpoints
   - Test various filter combinations and edge cases

### Phase 2: Frontend

1. **API Client**
   - Create `web/lib/api/demands.ts` with typed API client functions
   - Define TypeScript interfaces for Demand and DemandMatch

2. **Components**
   - Build DemandCard, DemandForm, MatchPlayerCard, StatusBadge, MetricsRequirementBuilder
   - Reuse existing shadcn/ui components and patterns

3. **Pages**
   - `/demands` - Dashboard with table/card view, filters, search
   - `/demands/new` - Create demand form
   - `/demands/[id]` - Demand detail with tabs and match management
   - `/demands/[id]/edit` - Edit form (or inline editing on detail page)

4. **Integration**
   - Add "Demands" to main navigation
   - Test full flow: create → match → propose → status updates

### Phase 3: Polish & Launch

1. **UI/UX Refinement**
   - Loading states, error handling, empty states
   - Responsive design for mobile/tablet
   - Accessibility (keyboard navigation, ARIA labels)

2. **Performance**
   - Optimize match algorithm queries
   - Add pagination for large result sets
   - Monitor Redis cache hit rates

3. **Documentation**
   - Update README with demand tracking feature
   - API documentation in /docs endpoint
   - User guide for scouts (if needed)

## Testing Strategy

### Backend Tests

- **Unit**: Matching algorithm with various criteria combinations
- **Integration**: API endpoints with mock database
- **E2E**: Full flow from create demand through match to closure

### Frontend Tests

- **Component**: DemandForm validation, StatusBadge rendering, MatchPlayerCard actions
- **Integration**: Page interactions (filter, sort, status updates)
- **E2E**: Playwright tests for critical paths (create demand, run matching, propose player)

## Future Enhancements

### Player Demands
- Add PlayerDemand table with inverted structure
- Add demand_type enum (club/player)
- Invert matching algorithm (find clubs for player)
- Reuse 80% of UI components with conditional rendering

### Advanced Features
- Email integration for sending proposals
- Automated deadline reminders
- Multi-user collaboration (assign demands to scouts)
- Advanced analytics dashboard (conversion rates, time-to-close metrics)
- Demand templates for common profiles
- Bulk actions (propose multiple players at once)

## Success Metrics

- Number of demands created per month
- Average number of matches per demand
- Conversion rates: suggested → proposed → interested → signed
- Time from demand creation to first proposal
- User feedback from prospect and their team

## Open Questions

- Should budget_min/budget_max be displayed in frontend or kept internal?
- Do we need role-based access (admin vs scout) or is single-user sufficient for v1?
- Should match_score be visible to users or kept as internal ranking mechanism?

## Conclusion

This design leverages The Scouting Arena's existing player statistics, similarity engine, and frontend components to add comprehensive demand tracking capabilities. By starting with club demands and designing for future player demands, the system provides immediate value to scouting agencies while maintaining flexibility for growth.

The hybrid filter+rank matching algorithm reuses proven infrastructure, and the dedicated "Demands" section keeps the feature isolated from existing workflows. The full lifecycle tracking (suggested → proposed → interested → rejected → signed) provides visibility into the sales funnel while remaining simple to use.

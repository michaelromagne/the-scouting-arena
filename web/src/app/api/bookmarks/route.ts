import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "../auth/[...nextauth]/route";
import { Pool } from "pg";

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

function asIntUserId(value: unknown): number | null {
  if (typeof value !== "string" && typeof value !== "number") return null;
  const s = String(value).trim();
  if (!/^\d+$/.test(s)) return null;
  if (s.length > 10) return null;
  const n = Number(s);
  if (!Number.isSafeInteger(n)) return null;
  if (n < 1 || n > 2147483647) return null;
  return n;
}

// GET /api/bookmarks - Get user's bookmarked players
export async function GET(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const userId = asIntUserId(session.user.id);
    if (userId === null) {
      return NextResponse.json({ error: "Invalid user id" }, { status: 400 });
    }

    const result = await pool.query(
      `SELECT
        ub.id as bookmark_id,
        ub.notes,
        ub.tags,
        ub.created_at,
        ps.id as player_season_id,
        p.id as player_id,
        p.name as player_name,
        p.position_primary,
        ps.position,
        ps.minutes,
        ps.market_value_eur,
        ps.birth_date,
        ps.nationality,
        ps.image_url,
        t.name as team_name,
        l.name as league_name,
        s.label as season_label
      FROM user_bookmarks ub
      JOIN player_seasons ps ON ub.player_season_id = ps.id
      JOIN players p ON ps.player_id = p.id
      LEFT JOIN teams t ON ps.team_id = t.id
      LEFT JOIN leagues l ON t.league_id = l.id
      LEFT JOIN seasons s ON ps.season_id = s.id
      WHERE ub.user_id = $1
      ORDER BY ub.created_at DESC`,
      [userId]
    );

    return NextResponse.json({ bookmarks: result.rows });
  } catch (error) {
    console.error("Error fetching bookmarks:", error);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}

// POST /api/bookmarks - Add a bookmark
export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const userId = asIntUserId(session.user.id);
    if (userId === null) {
      return NextResponse.json({ error: "Invalid user id" }, { status: 400 });
    }

    const body = await request.json();
    const { player_season_id, notes, tags } = body;

    if (!player_season_id) {
      return NextResponse.json({ error: "player_season_id is required" }, { status: 400 });
    }

    // Check if already bookmarked
    const existing = await pool.query(
      `SELECT id FROM user_bookmarks WHERE user_id = $1 AND player_season_id = $2`,
      [userId, player_season_id]
    );

    if (existing.rows.length > 0) {
      return NextResponse.json({ error: "Already bookmarked" }, { status: 409 });
    }

    // Add bookmark
    const result = await pool.query(
      `INSERT INTO user_bookmarks (user_id, player_season_id, notes, tags)
       VALUES ($1, $2, $3, $4)
       RETURNING id, created_at`,
      [userId, player_season_id, notes || null, tags || null]
    );

    // Track activity
    try {
      await pool.query(
        `INSERT INTO user_activity (user_id, activity_type, player_id, metadata)
         VALUES ($1, 'bookmark', $2, $3)`,
        [userId, player_season_id, JSON.stringify({ notes, tags })]
      );
    } catch (err) {
      console.warn("Non-fatal: failed to track bookmark activity:", err);
    }

    return NextResponse.json({
      success: true,
      bookmark: result.rows[0]
    }, { status: 201 });
  } catch (error) {
    console.error("Error creating bookmark:", error);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}

// DELETE /api/bookmarks - Remove a bookmark
export async function DELETE(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const userId = asIntUserId(session.user.id);
    if (userId === null) {
      return NextResponse.json({ error: "Invalid user id" }, { status: 400 });
    }

    const { searchParams } = new URL(request.url);
    const player_season_id = searchParams.get("player_season_id");

    if (!player_season_id) {
      return NextResponse.json({ error: "player_season_id is required" }, { status: 400 });
    }

    const result = await pool.query(
      `DELETE FROM user_bookmarks
       WHERE user_id = $1 AND player_season_id = $2
       RETURNING id`,
      [userId, player_season_id]
    );

    if (result.rows.length === 0) {
      return NextResponse.json({ error: "Bookmark not found" }, { status: 404 });
    }

    // Track activity
    try {
      await pool.query(
        `INSERT INTO user_activity (user_id, activity_type, player_id)
         VALUES ($1, 'unbookmark', $2)`,
        [userId, player_season_id]
      );
    } catch (err) {
      console.warn("Non-fatal: failed to track unbookmark activity:", err);
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error deleting bookmark:", error);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}

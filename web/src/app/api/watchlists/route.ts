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

// GET /api/watchlists - List user's watchlists
export async function GET(_request: NextRequest) {
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
      `SELECT id, name, description, is_public, created_at, updated_at
       FROM user_watchlists
       WHERE user_id = $1
       ORDER BY updated_at DESC NULLS LAST, created_at DESC`,
      [userId]
    );

    return NextResponse.json({ watchlists: result.rows });
  } catch (error) {
    console.error("Error fetching watchlists:", error);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}

// POST /api/watchlists - Create watchlist
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
    const name = typeof body?.name === "string" ? body.name.trim() : "";
    const description =
      typeof body?.description === "string" ? body.description.trim() : null;

    if (!name) {
      return NextResponse.json({ error: "name is required" }, { status: 400 });
    }

    const result = await pool.query(
      `INSERT INTO user_watchlists (user_id, name, description)
       VALUES ($1, $2, $3)
       RETURNING id, name, description, is_public, created_at, updated_at`,
      [userId, name, description || null]
    );

    // Best-effort activity tracking
    try {
      await pool.query(
        `INSERT INTO user_activity (user_id, activity_type, metadata)
         VALUES ($1, 'create_watchlist', $2)`,
        [userId, JSON.stringify({ name })]
      );
    } catch (err) {
      console.warn("Non-fatal: failed to track watchlist creation:", err);
    }

    return NextResponse.json({ watchlist: result.rows[0] }, { status: 201 });
  } catch (error) {
    console.error("Error creating watchlist:", error);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}

// DELETE /api/watchlists?watchlist_id=123 - Delete watchlist
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
    const watchlistIdRaw = searchParams.get("watchlist_id");
    const watchlistId = watchlistIdRaw ? Number(watchlistIdRaw) : NaN;
    if (!Number.isInteger(watchlistId) || watchlistId < 1) {
      return NextResponse.json(
        { error: "watchlist_id is required" },
        { status: 400 }
      );
    }

    const result = await pool.query(
      `DELETE FROM user_watchlists
       WHERE id = $1 AND user_id = $2
       RETURNING id`,
      [watchlistId, userId]
    );

    if (result.rows.length === 0) {
      return NextResponse.json({ error: "Watchlist not found" }, { status: 404 });
    }

    try {
      await pool.query(
        `INSERT INTO user_activity (user_id, activity_type, metadata)
         VALUES ($1, 'delete_watchlist', $2)`,
        [userId, JSON.stringify({ watchlist_id: watchlistId })]
      );
    } catch (err) {
      console.warn("Non-fatal: failed to track watchlist deletion:", err);
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error deleting watchlist:", error);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}

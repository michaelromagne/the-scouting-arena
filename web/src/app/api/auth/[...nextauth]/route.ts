import NextAuth, { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import { Pool } from "pg";
import type { Adapter } from "next-auth/adapters";
import type {
  AdapterAccount,
  AdapterSession,
  AdapterUser,
  VerificationToken,
} from "next-auth/adapters";

// PostgreSQL connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

function asIntUserId(value: unknown): number | null {
  if (typeof value !== "string" && typeof value !== "number") return null;
  const s = String(value).trim();
  if (!/^\d+$/.test(s)) return null;
  // Avoid BigInt literals since TS target is ES2017. Keep it simple:
  // internal DB user IDs are small (SERIAL int), so reject long numeric strings.
  if (s.length > 10) return null;
  const n = Number(s);
  if (!Number.isSafeInteger(n)) return null;
  if (n < 1 || n > 2147483647) return null; // INT4 range
  return n;
}

function CustomPostgresAdapter(): Adapter {
  return {
  async createUser(user: Omit<AdapterUser, "id">) {
    const result = await pool.query(
      `INSERT INTO users (name, email, "emailVerified", image)
       VALUES ($1, $2, $3, $4)
       RETURNING id, name, email, "emailVerified", image`,
      [user.name, user.email, user.emailVerified, user.image]
    );
    const row = result.rows[0];
    return {
      id: row.id.toString(),
      name: row.name,
      email: row.email,
      emailVerified: row.emailVerified,
      image: row.image,
    };
  },

  async getUser(id: string) {
    const result = await pool.query(
      `SELECT id, name, email, "emailVerified", image, subscription_tier as "subscriptionTier"
       FROM users WHERE id = $1`,
      [id]
    );
    if (!result.rows[0]) return null;
    const row = result.rows[0];
    return {
      id: row.id.toString(),
      name: row.name,
      email: row.email,
      emailVerified: row.emailVerified,
      image: row.image,
      subscriptionTier: row.subscriptionTier,
    };
  },

  async getUserByEmail(email: string) {
    const result = await pool.query(
      `SELECT id, name, email, "emailVerified", image, subscription_tier as "subscriptionTier"
       FROM users WHERE email = $1`,
      [email]
    );
    if (!result.rows[0]) return null;
    const row = result.rows[0];
    return {
      id: row.id.toString(),
      name: row.name,
      email: row.email,
      emailVerified: row.emailVerified,
      image: row.image,
      subscriptionTier: row.subscriptionTier,
    };
  },

  async getUserByAccount({
    providerAccountId,
    provider,
  }: Pick<AdapterAccount, "provider" | "providerAccountId">) {
    const result = await pool.query(
      `SELECT u.id, u.name, u.email, u."emailVerified" as "emailVerified", u.image, u.subscription_tier as "subscriptionTier"
       FROM users u
       JOIN accounts a ON u.id = a."userId"
       WHERE a.provider = $1 AND a."providerAccountId" = $2`,
      [provider, providerAccountId]
    );
    if (!result.rows[0]) return null;
    const row = result.rows[0];
    return {
      id: row.id.toString(),
      name: row.name,
      email: row.email,
      emailVerified: row.emailVerified,
      image: row.image,
      subscriptionTier: row.subscriptionTier,
    };
  },

  async updateUser(user: Partial<AdapterUser> & Pick<AdapterUser, "id">) {
    const result = await pool.query(
      `UPDATE users
       SET name = $1, email = $2, "emailVerified" = $3, image = $4, updated_at = CURRENT_TIMESTAMP
       WHERE id = $5
       RETURNING id, name, email, "emailVerified", image`,
      [user.name, user.email, user.emailVerified, user.image, user.id]
    );
    const row = result.rows[0];
    return {
      id: row.id.toString(),
      name: row.name,
      email: row.email,
      emailVerified: row.emailVerified,
      image: row.image,
    };
  },

  async deleteUser(userId: string) {
    await pool.query(`DELETE FROM users WHERE id = $1`, [userId]);
  },

  async linkAccount(account: AdapterAccount) {
    await pool.query(
      `INSERT INTO accounts (
        "userId", type, provider, "providerAccountId",
        refresh_token, access_token, expires_at, token_type, scope, id_token
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)`,
      [
        account.userId,
        account.type,
        account.provider,
        account.providerAccountId,
        account.refresh_token,
        account.access_token,
        account.expires_at,
        account.token_type,
        account.scope,
        account.id_token,
      ]
    );
  },

  async unlinkAccount({
    provider,
    providerAccountId,
  }: Pick<AdapterAccount, "provider" | "providerAccountId">) {
    await pool.query(
      `DELETE FROM accounts WHERE provider = $1 AND "providerAccountId" = $2`,
      [provider, providerAccountId]
    );
  },

  async createSession({
    sessionToken,
    userId,
    expires,
  }: AdapterSession) {
    await pool.query(
      `INSERT INTO sessions ("sessionToken", "userId", expires) VALUES ($1, $2, $3)`,
      [sessionToken, userId, expires]
    );
    return { sessionToken, userId, expires };
  },

  async getSessionAndUser(sessionToken: string) {
    const result = await pool.query(
      `SELECT
        s."sessionToken" as "sessionToken", s."userId" as "userId", s.expires,
        u.id, u.name, u.email, u."emailVerified" as "emailVerified", u.image, u.subscription_tier as "subscriptionTier"
       FROM sessions s
       JOIN users u ON s."userId" = u.id
       WHERE s."sessionToken" = $1 AND s.expires > NOW()`,
      [sessionToken]
    );

    if (!result.rows[0]) return null;

    const row = result.rows[0];
    return {
      session: {
        sessionToken: row.sessionToken,
        userId: row.userId.toString(),
        expires: row.expires
      },
      user: {
        id: row.id.toString(),
        name: row.name,
        email: row.email,
        emailVerified: row.emailVerified,
        image: row.image,
        subscriptionTier: row.subscriptionTier,
      },
    };
  },

  async updateSession({
    sessionToken,
    expires,
    userId,
  }: Partial<AdapterSession> & Pick<AdapterSession, "sessionToken">) {
    const result = await pool.query(
      `UPDATE sessions
       SET
         expires = COALESCE($1, expires),
         "userId" = COALESCE($2, "userId")
       WHERE "sessionToken" = $3
       RETURNING "sessionToken" as "sessionToken", "userId" as "userId", expires`,
      [expires ?? null, userId ?? null, sessionToken]
    );
    if (!result.rows[0]) return null;
    return {
      sessionToken: result.rows[0].sessionToken,
      userId: result.rows[0].userId.toString(),
      expires: result.rows[0].expires,
    };
  },

  async deleteSession(sessionToken: string) {
    await pool.query(`DELETE FROM sessions WHERE "sessionToken" = $1`, [sessionToken]);
  },

  async createVerificationToken({
    identifier,
    token,
    expires,
  }: VerificationToken) {
    const result = await pool.query(
      `INSERT INTO verification_token (identifier, token, expires)
       VALUES ($1, $2, $3)
       RETURNING identifier, token, expires`,
      [identifier, token, expires]
    );
    return result.rows[0];
  },

  async useVerificationToken({
    identifier,
    token,
  }: Pick<VerificationToken, "identifier" | "token">) {
    const result = await pool.query(
      `DELETE FROM verification_token
       WHERE identifier = $1 AND token = $2
       RETURNING identifier, token, expires`,
      [identifier, token]
    );
    return result.rows[0] ?? null;
  },
  };
}

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  adapter: CustomPostgresAdapter(),
  session: {
    strategy: "database",
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  pages: {
    signIn: "/auth/signin",
    error: "/auth/error",
  },
  callbacks: {
    async session({ session, user }) {
      // Add custom user data to session
      if (session.user) {
        session.user.id = user.id;
        session.user.subscriptionTier = (user as any).subscriptionTier || "free";
      }

      // Track login
      const userId = asIntUserId(user.id);
      if (userId !== null) {
        try {
          await pool.query(
            `UPDATE users
             SET last_login_at = CURRENT_TIMESTAMP, total_logins = total_logins + 1
             WHERE id = $1`,
            [userId]
          );
        } catch (err) {
          console.warn("Non-fatal: failed to track login:", err);
        }
      }

      return session;
    },
  },
  events: {
    async createUser({ user }) {
      // Send welcome email
      console.log(`New user created: ${user.email}`);

      // Initialize email preferences
      const userId = asIntUserId(user.id);
      if (userId !== null) {
        await pool.query(
          `INSERT INTO user_email_preferences (user_id) VALUES ($1)`,
          [userId]
        );
      }
    },
    async signIn({ user, account }) {
      // Log user activity (best-effort; should never block auth)
      const userId = asIntUserId(user.id);
      if (userId === null) return;
      try {
        await pool.query(
          `INSERT INTO user_activity (user_id, activity_type, metadata)
           VALUES ($1, 'sign_in', $2)`,
          [userId, JSON.stringify({ provider: account?.provider })]
        );
      } catch (err) {
        console.warn("Non-fatal: failed to track sign-in:", err);
      }
    },
  },
};

const handler = NextAuth(authOptions);
export { handler as GET, handler as POST };

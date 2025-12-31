-- Fix Google OAuth provider IDs being stored in an INTEGER column.
--
-- Symptom:
--   value "1059..." is out of range for type integer
--
-- Root cause:
--   Google "sub" / providerAccountId values can exceed BIGINT and must be stored as TEXT.
--
-- This migration is safe to run multiple times. It targets both naming conventions:
-- - snake_case: accounts.provider_account_id
-- - camelCase (Auth.js schema): accounts."providerAccountId"

DO $$
DECLARE
  col_type TEXT;
BEGIN
  -- snake_case schema (our NextAuth v4 custom adapter)
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'accounts'
      AND column_name = 'provider_account_id'
  ) THEN
    SELECT data_type
    INTO col_type
    FROM information_schema.columns
    WHERE table_name = 'accounts'
      AND column_name = 'provider_account_id';

    IF col_type <> 'text' THEN
      EXECUTE 'ALTER TABLE accounts ALTER COLUMN provider_account_id TYPE TEXT USING provider_account_id::text';
    END IF;
  END IF;

  -- camelCase schema (Auth.js / quoted identifiers)
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'accounts'
      AND column_name = 'providerAccountId'
  ) THEN
    SELECT data_type
    INTO col_type
    FROM information_schema.columns
    WHERE table_name = 'accounts'
      AND column_name = 'providerAccountId';

    IF col_type <> 'text' THEN
      EXECUTE 'ALTER TABLE accounts ALTER COLUMN "providerAccountId" TYPE TEXT USING "providerAccountId"::text';
    END IF;
  END IF;
END $$;

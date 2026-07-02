-- ══════════════════════════════════════════════════════════════
--   Reward Ads — Full Schema
--   شغّل هذا في Supabase SQL Editor
-- ══════════════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── users ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id                 BIGSERIAL PRIMARY KEY,
    user_id            VARCHAR(50)     UNIQUE NOT NULL,
    username           VARCHAR(100)    UNIQUE NOT NULL,
    first_name         VARCHAR(100)    DEFAULT '',
    email              VARCHAR(200)    DEFAULT '',
    password_hash      VARCHAR(200)    NOT NULL,
    balance            NUMERIC(20,10)  DEFAULT 0,
    total_earned       NUMERIC(20,10)  DEFAULT 0,
    referrer_id        VARCHAR(50)     DEFAULT NULL,
    referral_count     INTEGER         DEFAULT 0,
    ads_today          INTEGER         DEFAULT 0,
    ads_since_captcha  INTEGER         DEFAULT 0,
    last_ad_time       TIMESTAMPTZ     DEFAULT NULL,
    last_ad_date       VARCHAR(10)     DEFAULT '',
    join_date          TIMESTAMPTZ     DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_user_id  ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- ── withdrawals ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS withdrawals (
    id             BIGSERIAL PRIMARY KEY,
    user_id        VARCHAR(50)     NOT NULL,
    amount         NUMERIC(20,10)  NOT NULL,
    commission     NUMERIC(20,10)  DEFAULT 1,
    wallet_type    VARCHAR(50)     NOT NULL,
    wallet_number  VARCHAR(200)    NOT NULL,
    status         VARCHAR(20)     DEFAULT 'pending',
    created_at     TIMESTAMPTZ     DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_w_user_id ON withdrawals(user_id);
CREATE INDEX IF NOT EXISTS idx_w_status  ON withdrawals(status);

-- ── transactions ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS transactions (
    id          BIGSERIAL PRIMARY KEY,
    user_id     VARCHAR(50)     NOT NULL,
    type        VARCHAR(50)     NOT NULL,
    amount      NUMERIC(20,10)  NOT NULL,
    description VARCHAR(255)    DEFAULT '',
    created_at  TIMESTAMPTZ     DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tx_user_id ON transactions(user_id);

-- ── settings ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS settings (
    id                    BIGSERIAL PRIMARY KEY,
    reward_per_ad         NUMERIC(20,10)  DEFAULT 0.5,
    minimum_withdraw      NUMERIC(20,10)  DEFAULT 5.0,
    cooldown_seconds      INTEGER         DEFAULT 20,
    max_ads_per_day       INTEGER         DEFAULT 100,
    withdrawal_commission NUMERIC(20,10)  DEFAULT 1.0,
    captcha_every         INTEGER         DEFAULT 10,
    welcome_message       TEXT            DEFAULT '',
    welcome_active        BOOLEAN         DEFAULT FALSE,
    active_theme          VARCHAR(20)     DEFAULT 'dark_gold',
    min_vodafone          NUMERIC(20,10)  DEFAULT 5,
    fee_vodafone          NUMERIC(20,10)  DEFAULT 1,
    min_etisalat          NUMERIC(20,10)  DEFAULT 5,
    fee_etisalat          NUMERIC(20,10)  DEFAULT 1,
    min_orange            NUMERIC(20,10)  DEFAULT 5,
    fee_orange            NUMERIC(20,10)  DEFAULT 1,
    min_we                NUMERIC(20,10)  DEFAULT 5,
    fee_we                NUMERIC(20,10)  DEFAULT 1,
    min_binance           NUMERIC(20,10)  DEFAULT 10,
    fee_binance           NUMERIC(20,10)  DEFAULT 0.5,
    min_ethereum          NUMERIC(20,10)  DEFAULT 20,
    fee_ethereum          NUMERIC(20,10)  DEFAULT 2,
    min_usdt              NUMERIC(20,10)  DEFAULT 10,
    fee_usdt              NUMERIC(20,10)  DEFAULT 1,
    usdt_networks         TEXT            DEFAULT 'TRC20,ERC20,BEP20',
    active_usdt_nets      TEXT            DEFAULT 'TRC20,ERC20,BEP20'
);

INSERT INTO settings DEFAULT VALUES ON CONFLICT DO NOTHING;

-- ── featured_bots ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS featured_bots (
    id         BIGSERIAL PRIMARY KEY,
    title      VARCHAR(200) NOT NULL,
    message    TEXT         NOT NULL,
    bot_link   VARCHAR(300) NOT NULL,
    is_active  BOOLEAN      DEFAULT TRUE,
    created_at TIMESTAMPTZ  DEFAULT NOW()
);

-- ── tasks (مهام الربح) ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
    id          BIGSERIAL PRIMARY KEY,
    title       VARCHAR(200)    NOT NULL,
    description TEXT            DEFAULT '',
    link        VARCHAR(500)    NOT NULL,
    reward      NUMERIC(20,10)  NOT NULL,
    task_type   VARCHAR(20)     DEFAULT 'visit',
    is_active   BOOLEAN         DEFAULT TRUE,
    created_at  TIMESTAMPTZ     DEFAULT NOW()
);

-- ── user_tasks (سجل إتمام كل مستخدم) ────────────────────────
CREATE TABLE IF NOT EXISTS user_tasks (
    id           BIGSERIAL PRIMARY KEY,
    user_id      VARCHAR(50)     NOT NULL,
    task_id      BIGINT          NOT NULL,
    reward       NUMERIC(20,10)  DEFAULT 0,
    completed_at TIMESTAMPTZ     DEFAULT NOW(),
    UNIQUE(user_id, task_id)
);
CREATE INDEX IF NOT EXISTS idx_ut_user_id ON user_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_ut_task_id ON user_tasks(task_id);

-- ── RLS ───────────────────────────────────────────────────────
ALTER TABLE users         ENABLE ROW LEVEL SECURITY;
ALTER TABLE withdrawals   ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions  ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings      ENABLE ROW LEVEL SECURITY;
ALTER TABLE featured_bots ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks         ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_tasks    ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  CREATE POLICY "svc_all" ON users         FOR ALL TO service_role USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
  CREATE POLICY "svc_all" ON withdrawals   FOR ALL TO service_role USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
  CREATE POLICY "svc_all" ON transactions  FOR ALL TO service_role USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
  CREATE POLICY "svc_all" ON settings      FOR ALL TO service_role USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
  CREATE POLICY "svc_all" ON featured_bots FOR ALL TO service_role USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
  CREATE POLICY "svc_all" ON tasks         FOR ALL TO service_role USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
  CREATE POLICY "svc_all" ON user_tasks    FOR ALL TO service_role USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ── admin_auth (بيانات دخول الأدمن) ────────────────────────
CREATE TABLE IF NOT EXISTS admin_auth (
    id            BIGSERIAL PRIMARY KEY,
    admin_id      VARCHAR(50)  UNIQUE NOT NULL,
    password_hash VARCHAR(200) DEFAULT '',
    updated_at    TIMESTAMPTZ  DEFAULT NOW()
);

ALTER TABLE admin_auth ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
  CREATE POLICY "svc_all" ON admin_auth FOR ALL TO service_role USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

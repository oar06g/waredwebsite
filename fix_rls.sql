-- ══════════════════════════════════════════════════════
--   شغّل هذا في Supabase SQL Editor
--   يحل مشكلة RLS ويضيف صف settings افتراضي
-- ══════════════════════════════════════════════════════

-- 1. إدراج الإعدادات الافتراضية (لو مش موجودة)
INSERT INTO settings (
    reward_per_ad, minimum_withdraw, cooldown_seconds,
    max_ads_per_day, withdrawal_commission, captcha_every,
    welcome_message, welcome_active, active_theme,
    min_vodafone, fee_vodafone, min_etisalat, fee_etisalat,
    min_orange, fee_orange, min_we, fee_we,
    min_binance, fee_binance, min_ethereum, fee_ethereum,
    min_usdt, fee_usdt, usdt_networks, active_usdt_nets
) VALUES (
    0.5, 5.0, 20, 100, 1.0, 10,
    '', false, 'dark_gold',
    5, 1, 5, 1, 5, 1, 5, 1,
    10, 0.5, 20, 2,
    10, 1, 'TRC20,ERC20,BEP20', 'TRC20,ERC20,BEP20'
) ON CONFLICT DO NOTHING;

-- 2. إصلاح RLS policies
-- حذف القديمة لو موجودة
DROP POLICY IF EXISTS "svc_all" ON users;
DROP POLICY IF EXISTS "svc_all" ON withdrawals;
DROP POLICY IF EXISTS "svc_all" ON transactions;
DROP POLICY IF EXISTS "svc_all" ON settings;
DROP POLICY IF EXISTS "svc_all" ON featured_bots;
DROP POLICY IF EXISTS "svc_all" ON tasks;
DROP POLICY IF EXISTS "svc_all" ON user_tasks;
DROP POLICY IF EXISTS "svc_all" ON admin_auth;

-- إعادة إنشاء policies صح
CREATE POLICY "allow_all_service" ON users         FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow_all_service" ON withdrawals   FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow_all_service" ON transactions  FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow_all_service" ON settings      FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow_all_service" ON featured_bots FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow_all_service" ON tasks         FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow_all_service" ON user_tasks    FOR ALL USING (true) WITH CHECK (true);

-- admin_auth لو الجدول موجود
DO $$ BEGIN
    CREATE POLICY "allow_all_service" ON admin_auth FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN undefined_table THEN NULL;
         WHEN duplicate_object THEN NULL;
END $$;

-- 3. تأكيد إن الإعدادات موجودة
SELECT * FROM settings LIMIT 1;

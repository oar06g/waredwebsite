"""
website/app.py — موقع المستخدم
Flask + Supabase (بدون SQLAlchemy)
PORT: 5000
"""
import sys, os, uuid, secrets, time, json, hmac, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from datetime import datetime
from db import (
    supabase,
    get_user, get_user_by_username, create_user, update_user,
    add_balance, user_to_dict, inc_referral_count,
    create_withdrawal, get_user_withdrawals, withdrawal_to_dict,
    create_transaction, get_user_transactions, transaction_to_dict,
    get_settings, get_active_bots, bot_to_dict,
    hash_password, check_password,
)

load_dotenv()

# ── تسجيل البوت (Webhook) ─────────────────────────────────────────────────────
from bot_simple import register_bot

# ── إعداد التطبيق ─────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('WEBSITE_SECRET_KEY', 'change_me')
BOT_TOKEN   = os.environ.get('BOT_TOKEN',   '')
BOT_USERNAME = os.environ.get('BOT_USERNAME', 'medo_add_bot')

# ── تفعيل الـ Webhook ────────────────────────────────────────────────────────────
register_bot(app)

# ── توكنز الجلسات (RAM) ───────────────────────────────────────────────────────
# ملاحظة للمبرمج: في الإنتاج استبدلها بـ Redis
user_tokens: dict = {}   # token  → user_id
ad_tokens:   dict = {}   # token  → { user_id, time }

# ── Headers ──────────────────────────────────────────────────────────────────
@app.after_request
def set_headers(r):
    r.headers['Access-Control-Allow-Origin']  = '*'
    r.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Auth-Token, ngrok-skip-browser-warning'
    r.headers['ngrok-skip-browser-warning']   = 'true'
    return r

# ── مساعد: جلب المستخدم الحالي ───────────────────────────────────────────────
def current_user() -> dict | None:
    token  = request.headers.get('X-Auth-Token', '')
    uid    = user_tokens.get(token)
    if not uid:
        return None
    return get_user(uid)

def make_token(user_id: str) -> str:
    token = secrets.token_hex(32)
    user_tokens[token] = user_id
    return token

# ── التحقق من initData تيليجرام ───────────────────────────────────────────────
def verify_tg_data(init_data: str) -> dict:
    try:
        from urllib.parse import unquote
        params    = dict(p.split('=', 1) for p in init_data.split('&') if '=' in p)
        check     = params.pop('hash', '')
        data_str  = '\n'.join(f"{k}={v}" for k, v in sorted(params.items()))
        secret    = hmac.new(b'WebAppData', BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed  = hmac.new(secret, data_str.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(computed, check):
            return json.loads(unquote(params.get('user', '{}')))
    except Exception:
        pass
    return {}

# ══════════════════════════════════════════════════════════════════════════════
# صفحات HTML
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def page_home():
    return render_template('index.html')

@app.route('/dashboard')
def page_dashboard():
    return render_template('dashboard.html')

# ══════════════════════════════════════════════════════════════════════════════
# API — المصادقة
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/register', methods=['POST'])
def register():
    d        = request.json or {}
    username = d.get('username', '').strip()
    password = d.get('password', '')
    email    = d.get('email',    '').strip()
    ref      = d.get('ref',      '').strip()

    if not username or not password:
        return jsonify({'error': 'أدخل اسم المستخدم وكلمة المرور'}), 400
    if len(password) < 6:
        return jsonify({'error': 'كلمة المرور 6 أحرف على الأقل'}), 400
    if get_user_by_username(username):
        return jsonify({'error': 'اسم المستخدم موجود بالفعل'}), 400

    uid  = str(uuid.uuid4())[:8]
    user = create_user(
        user_id    = uid,
        username   = username,
        email      = email,
        password   = password,
        referrer_id= ref or None
    )
    token    = make_token(uid)
    settings = get_settings()
    return jsonify({'success': True, 'token': token,
                    'user': user_to_dict(user), 'settings': settings})


@app.route('/api/login', methods=['POST'])
def login():
    d        = request.json or {}
    username = d.get('username', '').strip()
    password = d.get('password', '')

    user = get_user_by_username(username)
    if not user or not check_password(password, user.get('password_hash', '')):
        return jsonify({'error': 'اسم المستخدم أو كلمة المرور غلط'}), 401

    token    = make_token(user['user_id'])
    settings = get_settings()
    return jsonify({'success': True, 'token': token,
                    'user': user_to_dict(user), 'settings': settings})


@app.route('/api/tg_auth', methods=['POST'])
def tg_auth():
    """دخول تلقائي من تيليجرام — بدون كلمة مرور"""
    d           = request.json or {}
    telegram_id = str(d.get('telegram_id', ''))
    first_name  = d.get('first_name', '')
    username    = d.get('username',   '')
    ref         = d.get('ref',        '').strip()
    init_data   = d.get('init_data',  '')

    # التحقق من initData لو موجود
    if init_data and BOT_TOKEN:
        tg_user = verify_tg_data(init_data)
        if tg_user:
            telegram_id = str(tg_user.get('id', telegram_id))
            first_name  = tg_user.get('first_name', first_name)
            username    = tg_user.get('username',   username)

    if not telegram_id:
        return jsonify({'error': 'بيانات تيليجرام غير صحيحة'}), 400

    uid  = 'tg_' + telegram_id
    user = get_user(uid)

    if not user:
        # مستخدم جديد
        user = create_user(
            user_id    = uid,
            username   = username or ('user_' + telegram_id),
            first_name = first_name,
            referrer_id= ref or None
        )
    else:
        # تحديث الاسم لو اتغيّر
        updates = {}
        if first_name and user.get('first_name') != first_name:
            updates['first_name'] = first_name
        if username and user.get('username') != username:
            updates['username'] = username
        if updates:
            update_user(uid, **updates)
            user = get_user(uid)

    token    = make_token(uid)
    settings = get_settings()
    return jsonify({'success': True, 'token': token,
                    'user': user_to_dict(user), 'settings': settings})


@app.route('/api/me')
def me():
    user = current_user()
    if not user:
        return jsonify({'success': False}), 401

    uid      = user['user_id']
    settings = get_settings()
    now      = datetime.utcnow()
    today    = now.strftime('%Y-%m-%d')

    # reset عداد اليوم لو تغيّر اليوم
    if user.get('last_ad_date', '') != today:
        update_user(uid, ads_today=0, last_ad_date=today)
        user = get_user(uid)

    # حساب الكولداون المتبقي
    cooldown  = settings['cooldown_seconds']
    remaining = 0
    last_ad   = user.get('last_ad_time')
    if last_ad:
        try:
            last_dt   = datetime.fromisoformat(last_ad.replace('Z', '+00:00')).replace(tzinfo=None)
            elapsed   = (now - last_dt).total_seconds()
            remaining = max(0, cooldown - elapsed)
        except Exception:
            remaining = 0

    return jsonify({
        'success':   True,
        'user':      user_to_dict(user),
        'settings':  settings,
        'ad_status': {
            'remaining_cooldown': int(remaining),
            'ads_today':          int(user.get('ads_today') or 0),
            'max_ads_per_day':    settings['max_ads_per_day'],
            'can_watch':          remaining <= 0 and int(user.get('ads_today') or 0) < settings['max_ads_per_day']
        }
    })

# ══════════════════════════════════════════════════════════════════════════════
# API — الإعلانات
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/ad_token', methods=['POST'])
def ad_token():
    user = current_user()
    if not user:
        return jsonify({'error': 'غير مسجل'}), 401

    uid      = user['user_id']
    settings = get_settings()
    cooldown = settings['cooldown_seconds']
    max_ads  = settings['max_ads_per_day']
    now      = datetime.utcnow()
    today    = now.strftime('%Y-%m-%d')

    # reset اليوم
    if user.get('last_ad_date', '') != today:
        update_user(uid, ads_today=0, last_ad_date=today)
        user = get_user(uid)

    # تحقق من الحد اليومي
    ads_today = int(user.get('ads_today') or 0)
    if ads_today >= max_ads:
        return jsonify({'error': f'وصلت للحد اليومي ({max_ads} إعلان)، تعال غداً!'}), 429

    # تحقق من الكولداون
    last_ad = user.get('last_ad_time')
    if last_ad:
        try:
            last_dt   = datetime.fromisoformat(last_ad.replace('Z', '+00:00')).replace(tzinfo=None)
            elapsed   = (now - last_dt).total_seconds()
            remaining = cooldown - elapsed
            if remaining > 0:
                return jsonify({'error': f'انتظر {int(remaining)} ثانية', 'wait': int(remaining)}), 429
        except Exception:
            pass

    # إنشاء توكن
    token = secrets.token_hex(16)
    ad_tokens[token] = {'user_id': uid, 'time': time.time()}

    # تنظيف القديم
    expired = [k for k, v in list(ad_tokens.items()) if time.time() - v['time'] > 600]
    for k in expired:
        del ad_tokens[k]

    return jsonify({'token': token, 'duration': cooldown})


@app.route('/api/watch_ad', methods=['POST'])
def watch_ad():
    user = current_user()
    if not user:
        return jsonify({'error': 'غير مسجل'}), 401

    uid   = user['user_id']
    token = (request.json or {}).get('token', '')

    if not token or token not in ad_tokens:
        return jsonify({'error': 'انتهت صلاحية الجلسة، اضغط مشاهدة مرة أخرى'}), 400

    tdata = ad_tokens.pop(token)
    if tdata['user_id'] != uid:
        return jsonify({'error': 'خطأ في التحقق'}), 400

    settings = get_settings()
    required = settings['cooldown_seconds']
    elapsed  = time.time() - tdata['time']

    if elapsed < required - 2:
        return jsonify({'error': f'مضى {int(elapsed)} ثانية فقط، المطلوب {required} ثانية'}), 400

    # تحقق الحد اليومي
    max_ads   = settings['max_ads_per_day']
    today     = datetime.utcnow().strftime('%Y-%m-%d')
    ads_today = int(user.get('ads_today') or 0)
    if user.get('last_ad_date', '') != today:
        ads_today = 0
    if ads_today >= max_ads:
        return jsonify({'error': 'وصلت للحد اليومي!'}), 429

    # تحقق من captcha
    captcha_every = settings.get('captcha_every', 10)
    ads_since_cap = int(user.get('ads_since_captcha') or 0)
    need_captcha  = (ads_since_cap > 0 and ads_since_cap % captcha_every == 0)

    # إضافة المكافأة
    reward    = float(settings['reward_per_ad'])
    new_bal   = float(user.get('balance') or 0) + reward
    new_earn  = float(user.get('total_earned') or 0) + reward
    new_today = ads_today + 1

    update_user(uid,
        balance      = new_bal,
        total_earned = new_earn,
        ads_today    = new_today,
        last_ad_time = datetime.utcnow().isoformat(),
        last_ad_date = today
    )

    create_transaction(uid, 'ad_reward', reward, 'مكافأة مشاهدة إعلان')

    # عمولة الإحالة 5%
    referrer_id = user.get('referrer_id')
    if referrer_id:
        referrer = get_user(referrer_id)
        if referrer:
            commission = round(reward * 0.05, 10)
            update_user(referrer_id,
                balance      = float(referrer.get('balance') or 0) + commission,
                total_earned = float(referrer.get('total_earned') or 0) + commission
            )
            create_transaction(referrer_id, 'referral_commission', commission,
                               f'عمولة 5% من {user.get("username", uid)}')

    # زيادة عداد الـ captcha
    from db import increment_ads_since_captcha, reset_captcha_count
    new_cap = increment_ads_since_captcha(uid)
    next_captcha = captcha_every - (new_cap % captcha_every)

    return jsonify({
        'success':       True,
        'reward':        reward,
        'new_balance':   new_bal,
        'ads_today':     new_today,
        'need_captcha':  need_captcha,
        'next_captcha':  next_captcha
    })

# ══════════════════════════════════════════════════════════════════════════════
# API — التحقق البشري (Captcha)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/verify_captcha', methods=['POST'])
def verify_captcha():
    user = current_user()
    if not user:
        return jsonify({'error': 'غير مسجل'}), 401
    answer   = str((request.json or {}).get('answer', '')).strip()
    expected = str((request.json or {}).get('expected', '')).strip()
    if answer != expected:
        return jsonify({'success': False, 'error': 'إجابة خاطئة، حاول مرة أخرى'})
    from db import reset_captcha_count
    reset_captcha_count(user['user_id'])
    return jsonify({'success': True})

# ══════════════════════════════════════════════════════════════════════════════
# API — السحب
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/withdraw', methods=['POST'])
def withdraw():
    user = current_user()
    if not user:
        return jsonify({'error': 'غير مسجل'}), 401

    uid           = user['user_id']
    d             = request.json or {}
    amount        = float(d.get('amount', 0))
    wallet_type   = d.get('wallet_type',   '')
    wallet_number = d.get('wallet_number', '')

    settings = get_settings()
    balance  = float(user.get('balance') or 0)

    # خريطة طرق السحب → مفاتيح الإعدادات
    wallet_keys = {
        'Vodafone Cash':  ('min_vodafone',  'fee_vodafone'),
        'Etisalat Cash':  ('min_etisalat',  'fee_etisalat'),
        'Orange Cash':    ('min_orange',    'fee_orange'),
        'WE Pay':         ('min_we',        'fee_we'),
        'Binance':        ('min_binance',   'fee_binance'),
        'Ethereum ERC20': ('min_ethereum',  'fee_ethereum'),
    }
    # USDT — كل شبكاته بنفس الحدود والرسوم
    if wallet_type.startswith('USDT'):
        wallet_keys[wallet_type] = ('min_usdt', 'fee_usdt')
    min_key, fee_key = wallet_keys.get(wallet_type, ('min_withdraw', 'withdrawal_commission'))
    min_w      = float(settings.get(min_key, settings.get('min_withdraw', 5)))
    commission = float(settings.get(fee_key, settings.get('withdrawal_commission', 1)))
    total      = amount + commission

    if amount < min_w:
        return jsonify({'error': f'الحد الأدنى لـ {wallet_type} هو {min_w} ج.م'}), 400
    if balance < total:
        return jsonify({'error': f'رصيد غير كافٍ (المبلغ + رسوم {commission} ج.م)'}), 400

    # خصم من الرصيد
    update_user(uid, balance=round(balance - total, 10))

    # إنشاء طلب السحب
    create_withdrawal(uid, amount, commission, wallet_type, wallet_number)

    # تسجيل العملية
    create_transaction(uid, 'withdrawal_request', -total,
                       f'طلب سحب {amount} ج.م + عمولة {commission} ج.م عبر {wallet_type}')

    return jsonify({'success': True, 'total_deducted': total})


@app.route('/api/my_withdrawals', methods=['POST'])
def my_withdrawals():
    user = current_user()
    if not user:
        return jsonify({'error': 'غير مسجل'}), 401
    rows = get_user_withdrawals(user['user_id'])
    return jsonify({'withdrawals': [withdrawal_to_dict(w) for w in rows]})


@app.route('/api/transactions', methods=['POST'])
def transactions():
    user = current_user()
    if not user:
        return jsonify({'error': 'غير مسجل'}), 401
    rows = get_user_transactions(user['user_id'])
    return jsonify({'transactions': [transaction_to_dict(t) for t in rows]})

# ══════════════════════════════════════════════════════════════════════════════
# API — البوتات المميزة
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/usdt_networks')
def usdt_networks():
    """إرجاع شبكات USDT المفعّلة"""
    s = get_settings()
    nets = [n.strip() for n in s.get('active_usdt_nets','TRC20').split(',') if n.strip()]
    return jsonify({
        'networks': nets,
        'default':  nets[0] if nets else 'TRC20'
    })

@app.route('/api/site_config')
def site_config():
    """إعدادات الموقع العامة — ثيم + رسالة ترحيب"""
    s = get_settings()
    return jsonify({
        'active_theme':   s.get('active_theme',   'dark_gold'),
        'welcome_active': s.get('welcome_active', False),
        'welcome_message':s.get('welcome_message',''),
    })

@app.route('/api/featured_bots')
def featured_bots():
    bots = get_active_bots()
    return jsonify({'bots': [bot_to_dict(b) for b in bots]})

# ══════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print("🌐 Website → http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)

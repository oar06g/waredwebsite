"""
bot_simple.py — بوت تيليجرام بسيط
المكتبات: requests فقط (موجودة في Python أصلاً تقريباً)
يشتغل كـ Webhook جوه Flask

طريقة التشغيل:
  1. أضف هذا الملف لمجلد website/
  2. في website/app.py أضف: from bot_simple import register_bot
  3. بعد تعريف app: register_bot(app)
  4. بعد رفع الموقع شغّل set_webhook() مرة واحدة
"""

import os, requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN    = os.environ.get('BOT_TOKEN',    'YOUR_BOT_TOKEN_HERE')
WEBAPP_URL   = os.environ.get('WEBAPP_URL',   'https://waredwebsite2.vercel.app/')
ADMIN_ID    = int(os.environ.get('ADMIN_ID', '8988236075'))
CHANNEL_URL = os.environ.get('CHANNEL_URL', 'https://t.me/medo_channel')
SUPPORT_URL = os.environ.get('SUPPORT_URL', 'https://t.me/medo_add')
TG_API      = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ── إرسال رسالة ───────────────────────────────────────────────────────────────
def send_message(chat_id: int, text: str, reply_markup: dict = None):
    payload = {
        'chat_id':    chat_id,
        'text':       text,
        'parse_mode': 'Markdown'
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        requests.post(f"{TG_API}/sendMessage", json=payload, timeout=10)
    except Exception:
        pass

# ── بناء الـ keyboard ─────────────────────────────────────────────────────────
def main_keyboard(url: str) -> dict:
    return {
        'inline_keyboard': [
            [{'text': '🚀 افتح التطبيق', 'web_app': {'url': url}}],
            [
                {'text': '📢 قناتنا', 'url': CHANNEL_URL},
                {'text': '🆘 الدعم',  'url': SUPPORT_URL}
            ]
        ]
    }

# ── معالجة أوامر البوت ────────────────────────────────────────────────────────
def handle_update(update: dict):
    message = update.get('message', {})
    if not message:
        return

    chat_id   = message.get('chat', {}).get('id')
    text      = message.get('text', '')
    user      = message.get('from', {})
    from_id   = user.get('id')
    first_name = user.get('first_name', 'مستخدم')

    if not chat_id or not text:
        return

    # ── /start ──────────────────────────────────────────────────────────────
    if text.startswith('/start'):
        parts = text.split()
        ref   = parts[1].replace('ref_', '') if len(parts) > 1 and parts[1].startswith('ref_') else ''
        url   = f"{WEBAPP_URL}?tg=1&ref={ref}" if ref else f"{WEBAPP_URL}?tg=1"

        send_message(chat_id,
            f"👋 أهلاً *{first_name}*!\n\n"
            "⚡ *Reward Ads* — اكسب من مشاهدة الإعلانات\n\n"
            "📺 شاهد إعلانات واكسب مكافآت فورية\n"
            "👥 ادعُ أصدقاءك واحصل على عمولة *5%*\n"
            "💳 اسحب أرباحك عبر محافظ الدفع الإلكتروني\n\n"
            "👇 اضغط لفتح التطبيق الآن!",
            reply_markup=main_keyboard(url)
        )

    # ── /help ───────────────────────────────────────────────────────────────
    elif text == '/help':
        url = f"{WEBAPP_URL}?tg=1"
        send_message(chat_id,
            "📋 *كيفية الاستخدام:*\n\n"
            "1️⃣ افتح التطبيق\n"
            "2️⃣ اضغط 'شاهد إعلان' وانتظر العداد\n"
            "3️⃣ تُضاف المكافأة لرصيدك تلقائياً\n"
            "4️⃣ شارك رابط الإحالة واكسب 5%\n"
            "5️⃣ اسحب عند وصول رصيدك للحد الأدنى",
            reply_markup=main_keyboard(url)
        )

    # ── /admin ──────────────────────────────────────────────────────────────
    elif text == '/admin':
        if from_id != ADMIN_ID:
            send_message(chat_id, "⛔ غير مصرح لك")
            return
        admin_url = WEBAPP_URL.replace(':5000', ':5001').rstrip('/') + '/'
        send_message(chat_id, "🛡️ *لوحة الأدمن*",
            reply_markup={'inline_keyboard': [[
                {'text': '⚙️ لوحة التحكم', 'url': admin_url}
            ]]}
        )

# ── تسجيل الـ Webhook في Flask ────────────────────────────────────────────────
def register_bot(flask_app):
    """
    استدعِ هذه الدالة بعد إنشاء Flask app:
        from bot_simple import register_bot
        register_bot(app)
    """
    from flask import request as flask_request, jsonify

    @flask_app.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
    def webhook():
        update = flask_request.get_json(silent=True) or {}
        handle_update(update)
        return jsonify({'ok': True})

# ── تسجيل الـ Webhook مع تيليجرام (شغّله مرة واحدة فقط) ─────────────────────
def set_webhook(site_url: str = None):
    """
    شغّل هذه الدالة مرة واحدة بعد رفع الموقع:
        python -c "from bot_simple import set_webhook; set_webhook('https://your-site.com')"
    """
    url = site_url or WEBAPP_URL
    webhook_url = f"{url}/webhook/{BOT_TOKEN}"
    r = requests.post(f"{TG_API}/setWebhook", json={'url': webhook_url}, timeout=10)
    result = r.json()
    if result.get('ok'):
        print(f"✅ Webhook set: {webhook_url}")
    else:
        print(f"❌ Error: {result}")
    return result

def delete_webhook():
    """لحذف الـ Webhook"""
    r = requests.post(f"{TG_API}/deleteWebhook", timeout=10)
    print(r.json())

def get_webhook_info():
    """للتحقق من حالة الـ Webhook"""
    r = requests.get(f"{TG_API}/getWebhookInfo", timeout=10)
    print(r.json())

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'set':
            url = sys.argv[2] if len(sys.argv) > 2 else WEBAPP_URL
            set_webhook(url)
        elif cmd == 'delete':
            delete_webhook()
        elif cmd == 'info':
            get_webhook_info()
    else:
        print("الاستخدام:")
        print("  python bot_simple.py set https://your-site.com")
        print("  python bot_simple.py delete")
        print("  python bot_simple.py info")

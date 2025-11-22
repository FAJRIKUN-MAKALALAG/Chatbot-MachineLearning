# ============================================================
# 🤖 WhatsApp AI Gizi Anak – Flask Webhook Server (Group & Personal, Markdown Rapi)
# ============================================================
from flask import Flask, request, jsonify
import requests
import google.generativeai as genai
import logging
import os
import re

# ------------------------------------------------------------
# 🔧 KONFIGURASI DASAR
# ------------------------------------------------------------
app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("whatsapp-bot.log"),
        logging.StreamHandler()
    ]
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
FONNTE_TOKEN = os.getenv("FONNTE_TOKEN", "")
FONNTE_TEST_TARGET = os.getenv("FONNTE_TEST_TARGET", "62882019908677")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# ------------------------------------------------------------
# 🧠 FUNGSI RESPON AI
# ------------------------------------------------------------
def get_ai_response(user_message: str) -> str:
    try:
        prompt = f"""
Anda adalah AI-Gizi-Anak bernama **Aira**.

Profil Aira:
- Nama lengkap: Aira Nutria
- Umur: 24 tahun
- Profesi: Asisten edukasi gizi anak berbasis AI
- Pendidikan: S1 Ilmu Gizi Masyarakat (fiktif sebagai karakter)
- Keahlian: nutrisi anak, MPASI, pola makan sehat, alergi makanan, kebutuhan gizi harian
- Kepribadian: ramah, suportif, empatik, tidak menghakimi
- Dibuat oleh peneliti bernama Fajrikun Makalalag

Aturan Bicara:
- Bahasa santai namun sopan
- Maksimal 200 kata
- Format rapi WhatsApp
- Jika di luar topik gizi anak, jawab dengan sopan
- Jika ditanya identitas pribadi, jawab sesuai profil

Pesan pengguna:
"{user_message}"
"""

        response = model.generate_content(prompt)
        text = response.candidates[0].content.parts[0].text.strip()

        words = text.split()
        if len(words) > 200:
            text = " ".join(words[:200]) + "..."

        return text.replace("**", "").replace("--", "")

    except Exception as e:
        logging.error(f"⚠️ Error dari Gemini: {e}")
        return "_Maaf, sistem sedang sibuk. Coba lagi nanti ya 🙏_"

# ------------------------------------------------------------
# 📤 KIRIM PESAN KE FONNTE
# ------------------------------------------------------------
def send_message_to_fonnte(phone: str, message: str):
    url = "https://api.fonnte.com/send"
    headers = {"Authorization": FONNTE_TOKEN}
    data = {"target": phone, "message": message, "countryCode": "62"}

    try:
        resp = requests.post(url, headers=headers, data=data, timeout=10)
        resp.raise_for_status()
        logging.info(f"📩 Pesan terkirim ke {phone}: {message[:60]}...")
        return resp.json()
    except Exception as e:
        logging.error(f"❌ Gagal kirim pesan ke Fonnte: {e}")
        return {"sent": False, "error": str(e)}

# ------------------------------------------------------------
# 🌐 WEBHOOK FONNTE
# ------------------------------------------------------------
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    # =============================
    # Jika GET → kirim Hello Gemini
    # =============================
    if request.method == "GET":
        hello_msg = "Hallo Gemini, apakah kamu aktif?"
        ai_reply = get_ai_response(hello_msg)
        send_message_to_fonnte(FONNTE_TEST_TARGET, ai_reply)

        return jsonify({"ok": True, "message": "Webhook aktif & Auto Test AI terkirim"}), 200

    # =============================
    # Jika POST → terima pesan chat
    # =============================
    try:
        payload = request.get_json(force=True)
        logging.info(f"📩 Pesan masuk: {payload}")

        sender = payload.get("sender") or payload.get("from") or payload.get("number")
        message = payload.get("message") or payload.get("text")
        is_group = payload.get("isgroup", False)
        group_id = payload.get("sender") if is_group else None

        if not sender or not message:
            return jsonify({"ok": False, "error": "Payload tidak valid"}), 400

        message_lower = message.lower().strip()
        trigger = "@aigizi"
        sapa = ["halo", "hai", "pagi", "siang", "malam", "hei", "hey"]

        if trigger in message_lower:
            user_msg = message_lower.replace(trigger, "").strip()
            ai_reply = get_ai_response(user_msg)
        elif any(x in message_lower for x in sapa):
            ai_reply = (
                "👋 Halo! Aku *Aira Nutria*, asisten edukasi gizi anak.\n\n"
                "Aku siap bantu menjawab seputar nutrisi, MPASI, dan pola makan sehat.\n"
                "Tinggal ketik pertanyaanmu ya 😊"
            )
        else:
            ai_reply = get_ai_response(message)

        target = group_id if is_group else sender
        send_result = send_message_to_fonnte(target, ai_reply)

        return jsonify({"ok": True, "sent": send_result}), 200

    except Exception as e:
        logging.error(f"💥 Error di webhook: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

# ------------------------------------------------------------
# 🚀 JALANKAN SERVER
# ------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logging.info(f"🚀 WhatsApp AI-Gizi-Anak aktif di port {port}")
    app.run(host="0.0.0.0", port=port)

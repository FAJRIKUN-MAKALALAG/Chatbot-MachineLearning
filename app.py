# ============================================================
# 🤖 WhatsApp AI Gizi Anak – Flask Webhook Server (FULL UPDATE)
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

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# ------------------------------------------------------------
# 🧠 FUNGSI RESPON AI (Markdown + max 500 kata)
# ------------------------------------------------------------
def get_ai_response(user_message: str) -> str:
    try:
        prompt = f"""
Anda adalah *AI-Gizi-Anak*, asisten edukasi kesehatan anak.
🎯 Fokus: gizi anak, stunting, nutrisi balita, pola makan sehat, tumbuh kembang, tips parenting.
🧩 Aturan:
- Jawaban maksimal 500 kata
- Gunakan Markdown agar tampil rapi di WhatsApp
- Ramah, sopan, edukatif
- Jika di luar topik gizi anak/stunting, jawab: "Maaf, saya hanya bisa membantu seputar gizi anak dan stunting."

Pesan pengguna:
\"\"\"{user_message}\"\"\"
"""
        response = model.generate_content(prompt, request_options={"timeout": 15})
        # Truncate jika lebih dari 200 kata
        words = response.text.strip().split()
        return " ".join(words[:200])
    except Exception as e:
        logging.error(f"⚠️ Error dari Gemini: {e}")
        return "_Maaf, sistem sedang sibuk. Coba lagi nanti ya._"

# ------------------------------------------------------------
# 📤 KIRIM PESAN KE FONNTE
# ------------------------------------------------------------
def send_message_to_fonnte(target: str, message: str):
    url = "https://api.fonnte.com/send"
    headers = {"Authorization": FONNTE_TOKEN}
    data = {"target": target, "message": message, "countryCode": "62"}

    try:
        resp = requests.post(url, headers=headers, data=data, timeout=10)
        resp.raise_for_status()
        logging.info(f"✅ Balasan terkirim ke {target}: {message[:60]}...")
        return resp.json()
    except Exception as e:
        logging.error(f"❌ Gagal kirim pesan ke Fonnte: {e}")
        return {"sent": False, "error": str(e)}

# ------------------------------------------------------------
# 🌐 WEBHOOK FONNTE
# ------------------------------------------------------------
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return jsonify({"ok": True, "message": "Webhook aktif."})

    try:
        payload = request.get_json(force=True)
        logging.info(f"📩 Pesan masuk: {payload}")

        sender = payload.get("sender")
        group_id = payload.get("group_id")
        message = payload.get("message") or payload.get("text")
        is_group = payload.get("isgroup", False)

        if not sender or not message:
            return jsonify({"ok": False, "error": "Payload tidak valid"}), 400

        message_lower = message.lower().strip()
        sapaan = ["halo", "hai", "hallo", "pagi", "siang", "malam", "hey", "hei"]

        # 🔹 1. Cek perintah kirim ke nomor lain
        pattern_send_number = r"kirim pesan ke nomor (\d+) tentang (.+)"
        match_number = re.search(pattern_send_number, message_lower)

        if match_number:
            target_number = match_number.group(1)
            message_to_send = match_number.group(2)
            send_result = send_message_to_fonnte(target_number, message_to_send)
            ai_reply = f"✅ Pesan berhasil dikirim ke {target_number}"

        # 🔹 2. Chat di group dengan mention @aigizi
        elif is_group and "@aigizi" in message_lower:
            # Hapus mention sebelum dikirim ke AI
            user_message = message.replace("@aigizi", "").strip()
            ai_reply = get_ai_response(user_message)
            send_result = send_message_to_fonnte(group_id, ai_reply)
            return jsonify({"ok": True, "sent": send_result}), 200

        # 🔹 3. Chat pribadi dengan sapaan
        elif any(word in message_lower for word in sapaan):
            ai_reply = (
                "👋 Hai! Saya *AI-Gizi-Anak*, asisten edukasi kesehatan.\n\n"
                "Silakan tanya apa yang ingin kamu ketahui 😊"
            )

        # 🔹 4. Chat pribadi lain
        else:
            ai_reply = get_ai_response(message)

        # Kirim balasan ke pengirim di chat pribadi
        result = send_message_to_fonnte(sender, ai_reply)
        return jsonify({"ok": True, "sent": result}), 200

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

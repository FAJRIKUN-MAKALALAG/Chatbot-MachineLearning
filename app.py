# ============================================================
# 🤖 WhatsApp AI Gizi Anak – Flask Webhook Server
# ============================================================
from flask import Flask, request, jsonify
import requests
import google.generativeai as genai
import logging
import os

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

# Gunakan API Key dari environment (diset di Jenkins)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
FONNTE_TOKEN = os.getenv("FONNTE_TOKEN", "")

# Inisialisasi Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# ------------------------------------------------------------
# 🧠 FUNGSI RESPON AI (khusus topik gizi anak)
# ------------------------------------------------------------
def get_ai_response(user_message: str) -> str:
    """
    Menghasilkan jawaban AI seputar gizi anak & stunting
    menggunakan format markdown agar tampil rapi di WhatsApp.
    """
    try:
        prompt = f"""
Anda adalah *AI-Gizi-Anak*, asisten edukasi kesehatan anak.

🎯 **Fokus Utama:** gizi anak, stunting, nutrisi balita, pola makan sehat, tumbuh kembang, dan tips parenting sehat.

🧩 **Aturan:**
- Jika pertanyaan di luar topik gizi anak atau stunting, jawab:
  "Maaf, saya hanya bisa membantu seputar gizi anak dan stunting."
- Gunakan *markdown* agar tampilan pesan rapi di WhatsApp.
- Gaya bahasa: ramah, sopan, dan edukatif.
- Jika user menyapa (halo, hai, pagi, dsb), sambut hangat dan arahkan ke topik gizi anak.

Pesan pengguna:
\"\"\"{user_message}\"\"\"
"""
        response = model.generate_content(prompt, request_options={"timeout": 15})
        return response.text.strip()
    except Exception as e:
        logging.error(f"⚠️ Error dari Gemini: {e}")
        return "_Maaf, sistem sedang sibuk. Coba lagi nanti ya._"

# ------------------------------------------------------------
# 📤 KIRIM PESAN BALASAN KE FONNTE
# ------------------------------------------------------------
def send_message_to_fonnte(phone: str, message: str):
    url = "https://api.fonnte.com/send"
    headers = {"Authorization": FONNTE_TOKEN}
    data = {"target": phone, "message": message, "countryCode": "62"}

    try:
        resp = requests.post(url, headers=headers, data=data, timeout=10)
        resp.raise_for_status()
        logging.info(f"✅ Balasan terkirim ke {phone}: {message[:60]}...")
        return resp.json()
    except Exception as e:
        logging.error(f"❌ Gagal kirim pesan ke Fonnte: {e}")
        return {"sent": False, "error": str(e)}

# ------------------------------------------------------------
# 🌐 WEBHOOK FONNTE UNTUK TERIMA PESAN
# ------------------------------------------------------------
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return jsonify({"ok": True, "message": "Webhook aktif."})

    try:
        payload = request.get_json(force=True)
        logging.info(f"📩 Pesan masuk: {payload}")

        sender = payload.get("sender") or payload.get("from") or payload.get("number")
        message = payload.get("message") or payload.get("text")

        if not sender or not message:
            return jsonify({"ok": False, "error": "Payload tidak valid"}), 400

        message_lower = message.lower().strip()
        sapaan = ["halo", "hai", "hallo", "pagi", "siang", "malam", "hey", "hei"]

        if any(word in message_lower for word in sapaan):
            ai_reply = (
                "👋 Hai! Saya *AI-Gizi-Anak*, asisten edukasi kesehatan.\n\n"
                "Saya siap bantu kamu memahami seputar *gizi anak, stunting, dan nutrisi seimbang.* "
                "Silakan tanya apa yang ingin kamu ketahui 😊"
            )
        else:
            ai_reply = get_ai_response(message)

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

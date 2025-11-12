from flask import Flask, request, jsonify
import requests
import google.generativeai as genai
import logging
import os

# =======================================
# 🔧 KONFIGURASI DASAR
# =======================================
app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("whatsapp-bot.log"),
        logging.StreamHandler()
    ]
)

# Gunakan environment variable (Jenkins / manual)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "ISI_API_KEY_GEMINI")
FONNTE_TOKEN = os.getenv("FONNTE_TOKEN", "ISI_FONNTE_TOKEN")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# =======================================
# 🧠 FUNGSI GENERATOR RESPON AI
# =======================================
def get_ai_response(user_message: str) -> str:
    """
    Dapatkan respon dari Gemini dengan konteks spesifik gizi anak & stunting.
    Hasil diformat ke markdown agar rapi di WhatsApp.
    """
    try:
        prompt = f"""
Anda adalah *AI-Gizi-Anak*, asisten edukasi kesehatan yang sopan dan informatif.

🎯 **Fokus Utama:** Gizi anak, stunting, nutrisi balita, pola makan sehat, tumbuh kembang, dan tips parenting sehat.

🧩 **Peraturan:**
- Jika pertanyaan di luar topik gizi anak atau stunting, jawab dengan sopan: 
  "Maaf, saya hanya bisa membantu seputar gizi anak dan stunting."
- Format jawaban menggunakan *markdown* agar mudah dibaca di WhatsApp.
- Gunakan gaya bahasa sederhana, ramah, dan tetap profesional.
- Jika user menyapa (seperti 'halo', 'hai', 'pagi', dsb), sambut dengan hangat dan arahkan topik ke gizi anak.

Pesan dari pengguna:
\"\"\"{user_message}\"\"\"
"""

        response = model.generate_content(
            prompt,
            request_options={"timeout": 15}
        )
        return response.text.strip()

    except Exception as e:
        logging.error(f"⚠️ Error dari Gemini: {e}")
        return "_Maaf, sistem sedang sibuk. Coba lagi nanti ya._"


# =======================================
# 📤 KIRIM BALASAN KE FONNTE
# =======================================
def send_message_to_fonnte(phone: str, message: str):
    url = "https://api.fonnte.com/send"
    headers = {"Authorization": FONNTE_TOKEN}
    data = {
        "target": phone,
        "message": message,
        "countryCode": "62"
    }

    try:
        resp = requests.post(url, headers=headers, data=data, timeout=10)
        resp.raise_for_status()
        logging.info(f"✅ Pesan terkirim ke {phone}: {message[:60]}...")
        return resp.json()
    except Exception as e:
        logging.error(f"❌ Gagal kirim pesan ke Fonnte: {e}")
        return {"sent": False, "error": str(e)}


# =======================================
# 🌐 ENDPOINT WEBHOOK FONNTE
# =======================================
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        logging.info("Fonnte melakukan GET test ke webhook.")
        return jsonify({"ok": True, "message": "Webhook aktif dan siap menerima data."})

    try:
        payload = request.get_json(force=True)
        logging.info(f"📩 Payload masuk: {payload}")

        sender = (
            payload.get("sender")
            or payload.get("from")
            or payload.get("number")
        )
        message = (
            payload.get("message")
            or payload.get("text")
        )

        if not sender or not message:
            logging.warning("⚠️ Payload tidak lengkap.")
            return jsonify({"ok": False, "error": "Payload tidak valid"}), 400

        message_lower = message.lower().strip()

        # === Respons sapaan langsung ===
        sapaan = ["halo", "hai", "hallo", "pagi", "siang", "malam", "hey", "hei"]
        if any(word in message_lower for word in sapaan):
            ai_reply = (
                "👋 Hai! Saya *AI-Gizi-Anak*, asisten edukasi kesehatan.\n\n"
                "Saya bisa bantu kamu memahami seputar *gizi anak, stunting, dan nutrisi seimbang.* "
                "Silakan tanya apa yang ingin kamu ketahui 😊"
            )
        else:
            ai_reply = get_ai_response(message)

        # Kirim ke user
        result = send_message_to_fonnte(sender, ai_reply)

        return jsonify({"ok": True, "sent": result}), 200

    except Exception as e:
        logging.error(f"💥 Error di webhook: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# =======================================
# 🚀 JALANKAN SERVER
# =======================================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logging.info(f"🚀 WhatsApp AI-Gizi-Anak aktif di port {port}")
    app.run(host="0.0.0.0", port=port)

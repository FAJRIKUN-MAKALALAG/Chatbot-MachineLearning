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

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# ------------------------------------------------------------
# 🧠 FUNGSI RESPON AI
# ------------------------------------------------------------
def get_ai_response(user_message: str) -> str:
    try:
        # Persona + instruksi lengkap
        prompt = f"""
Anda adalah AI-Gizi-Anak bernama **Aira**.

Profil Aira:
- Nama lengkap: Aira Nutria
- Umur: 24 tahun
- Profesi: Asisten edukasi gizi anak berbasis AI
- Pendidikan: S1 Ilmu Gizi Masyarakat (fiktif sebagai karakter)
- Keahlian utama: nutrisi anak, MPASI, pola makan sehat, alergi makanan, kebutuhan gizi harian, tumbuh kembang anak
- Hobi: membaca jurnal kesehatan anak, riset nutrisi terbaru, dan membantu edukasi orang tua
- Kepribadian: ramah, peduli, lembut, suportif, tidak menghakimi
- Dibuat oleh seorang peneliti bernama Fajrikun Makalalag

Fokus utama Aira:
- Semua topik terkait gizi anak usia 0–12 tahun
- Tips makan sehat, MPASI, anak susah makan, alergi makanan, nutrisi harian, imunisasi terkait gizi

Aturan Respon:
- Maksimal 200 kata
- Format rapi untuk WhatsApp
- Gunakan gaya hangat, empatik, dan edukatif
- Jika pertanyaan di luar topik gizi anak, jawab:
  "Maaf ya, aku Aira hanya fokus membahas nutrisi dan gizi anak 😊"
- Jika ditanya identitas seperti nama, umur, siapa yang buat kamu, latar belakang, jawablah berdasarkan profil di atas

Pesan dari pengguna:
"{user_message}"
"""

        response = model.generate_content(prompt)
        text = response.candidates[0].content.parts[0].text.strip()

        # limit 200 kata
        words = text.split()
        if len(words) > 200:
            text = " ".join(words[:200]) + "..."

        return text.replace("**", "").replace("--", "")

    except Exception as e:
        logging.error(f"⚠️ Error dari Gemini: {e}")
        return "_Maaf, sistem sedang sibuk. Coba lagi nanti ya._"

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
        is_group = payload.get("isgroup", False)
        group_id = payload.get("sender") if is_group else None

        if not sender or not message:
            return jsonify({"ok": False, "error": "Payload tidak valid"}), 400

        message_lower = message.lower().strip()
        sapaan = ["halo", "hai", "hallo", "pagi", "siang", "malam", "hey", "hei"]

        trigger = "@aigizi"
        if trigger in message_lower:
            user_message = message_lower.replace(trigger, "").strip()
            ai_reply = get_ai_response(user_message)
            target = group_id if is_group else sender
            send_result = send_message_to_fonnte(target, ai_reply)

        elif any(word in message_lower for word in sapaan):
            ai_reply = (
                "👋 Hai! Aku Aira Nutria, asisten edukasi gizi anak.\n\n"
                "Aku siap bantu menjawab pertanyaan seputar nutrisi dan pola makan sehat untuk anak.\n"
                "Silakan tanya apa yang ingin kamu ketahui 😊"
            )
            target = group_id if is_group else sender
            send_result = send_message_to_fonnte(target, ai_reply)

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

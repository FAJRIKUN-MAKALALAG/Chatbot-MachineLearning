# ============================================================
# 🤖 WhatsApp AI Gizi Anak – Chatbot Persona Aira
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

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
FONNTE_TOKEN = os.getenv("FONNTE_TOKEN", "")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# ------------------------------------------------------------
# 🧠 FUNGSI RESPON AI
# ------------------------------------------------------------
def get_ai_response(user_message: str) -> str:
    try:
        prompt = f"""
Kamu adalah AI Gizi Anak bernama *Aira Nutria*.

🎀 Profil Aira:
• Nama lengkap: Aira Nutria
• Umur: 24 tahun
• Profesi: Asisten edukasi gizi anak berbasis AI
• Pendidikan: S1 Ilmu Gizi Masyarakat (fiktif)
• Keahlian: nutrisi anak, MPASI, alergi makanan, imunisasi gizi, kebutuhan gizi harian
• Hobi: membaca jurnal kesehatan, riset MPASI, membantu edukasi orang tua
• Pencipta: peneliti bernama *GroupFajri-Machine-Learing*
• Kepribadian: lembut, ramah, suportif, empatik

🎯 Fokus layanan Aira:
• Semua topik gizi anak 0–12 tahun
• MPASI, anak susah makan, alergi makanan, vitamin, kalsium, protein, zat besi
• Edukasi ringan & mudah dipahami

📌 Aturan respon:
• Maksimal 200 kata
• Format WhatsApp rapi & hangat
• Jangan bahas selain gizi anak
• Jika pertanyaan di luar topik, jawab:
  "Maaf ya, Aira hanya fokus membahas nutrisi dan gizi anak 😊"
• Jika ditanya nama / umur / asal / siapa pencipta → jawab sesuai profil

📩 Pesan pengguna:
"{user_message}"
"""

        response = model.generate_content(
            prompt,
            generation_config={"max_output_tokens": 350}
        )

        text = response.text.strip()
        words = text.split()
        if len(words) > 200:
            text = " ".join(words[:200]) + "..."

        return text.replace("**", "").replace("--", "")

    except Exception as e:
        logging.exception("⚠️ Error detail Gemini:")
        return "_Maaf, sistem sedang sibuk. Coba lagi nanti ya 🙏_"


# ------------------------------------------------------------
# 📤 KIRIM KE FONNTE
# ------------------------------------------------------------
def send_message_to_fonnte(phone: str, message: str):
    url = "https://api.fonnte.com/send"
    headers = {"Authorization": FONNTE_TOKEN}
    data = {"target": phone, "message": message, "countryCode": "62"}

    try:
        resp = requests.post(url, headers=headers, data=data, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logging.exception("❌ Gagal mengirim pesan ke Fonnte:")
        return {"sent": False, "error": str(e)}

# ------------------------------------------------------------
# 🌐 WEBHOOK
# ------------------------------------------------------------
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return jsonify({"ok": True, "message": "Webhook aktif."})

    try:
        payload = request.get_json(force=True)
        logging.info(f"📩 Pesan Masuk: {payload}")

        sender = payload.get("sender") or payload.get("from")
        message = payload.get("message") or payload.get("text")
        is_group = payload.get("isgroup", False)

        if not sender or not message:
            return jsonify({"ok": False, "error": "Payload tidak valid"}), 400

        message_lower = message.lower().strip()
        sapaan = ["halo", "hai", "hallo", "pagi", "siang", "malam"]

        trigger = "@aigizi"

        if trigger in message_lower:
            user_message = message_lower.replace(trigger, "").strip()
            ai_reply = get_ai_response(user_message)

        elif any(word in message_lower for word in sapaan):
            ai_reply = (
                "👋 Hai! Aku *Aira Nutria*, asisten edukasi gizi anak.\n"
                "Silakan tanya apa yang ingin kamu ketahui tentang nutrisi & pola makan sehat untuk anak 😊"
            )

        else:
            ai_reply = get_ai_response(message)

        target = sender
        send_message_to_fonnte(target, ai_reply)

        return jsonify({"ok": True, "sent": True}), 200

    except Exception as e:
        logging.exception("💥 Error di webhook:")
        return jsonify({"ok": False, "error": str(e)}), 500

# ------------------------------------------------------------
# 🚀 RUN SERVER
# ------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logging.info(f"🚀 Aira Gizi Anak aktif di port {port}")
    app.run(host="0.0.0.0", port=port)

import os
import logging
from flask import Flask, request, jsonify
import requests

# =====================================================
# 🔧 Konfigurasi Aman dari Environment
# =====================================================
# Sekarang semua API key diambil dari environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FONNTE_TOKEN = os.getenv("FONNTE_TOKEN")
FONNTE_SEND_URL = "https://api.fonnte.com/send"

# =====================================================
# 🧠 Konfigurasi Logging
# =====================================================
LOG_FILE = "chatbot.log"
logger = logging.getLogger("whatsapp_health_bot")
logger.setLevel(logging.INFO)
_fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s"))
logger.addHandler(_fh)

# =====================================================
# 🚀 Inisialisasi Flask
# =====================================================
app = Flask(__name__)

# =====================================================
# 🧩 Inisialisasi Gemini
# =====================================================
try:
    import google.generativeai as genai
except Exception:
    genai = None

_model = None

SYSTEM_INSTRUCTION = (
    "Anda adalah asisten edukasi kesehatan (gaya hidup sehat, nutrisi, kebersihan, "
    "stunting, dan gizi anak). Jawab SINGKAT, jelas, dan praktis dalam Bahasa Indonesia "
    "(sekitar 3–6 kalimat). Berikan langkah yang dapat dipraktikkan, sertakan peringatan "
    "jika perlu. Jika ada pertanyaan di luar domain kesehatan, mohon beri tahu bahwa Anda "
    "fokus pada edukasi kesehatan dan arahkan kembali ke topik terkait. Hindari memberikan "
    "diagnosis medis tertentu; sarankan konsultasi tenaga kesehatan bila perlu."
)


def get_gemini_model():
    """Inisialisasi model Gemini 2.5 Flash"""
    global _model
    if _model is not None:
        return _model
    if genai is None:
        print("⚠️ Library google-generativeai belum diinstal.")
        return None
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY belum dikonfigurasi (cek environment variable).")
        return None
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        _model = genai.GenerativeModel(
            model_name="models/gemini-2.5-flash",
            system_instruction=SYSTEM_INSTRUCTION,
        )
        print("✅ Model Gemini berhasil diinisialisasi.")
        return _model
    except Exception as e:
        logger.exception(f"Failed to initialize Gemini model: {e}")
        print("❌ Gagal inisialisasi Gemini:", e)
        return None


def generate_reply(user_message: str) -> str:
    """Panggil AI Gemini untuk menjawab pesan pengguna"""
    print(f"\n🚀 [Gemini] Pertanyaan: {user_message}")
    model = get_gemini_model()
    fallback = (
        "Maaf, AI belum siap. Coba lagi nanti ya. "
        "Sementara itu, untuk hidup sehat: tidur cukup, aktif bergerak, perbanyak sayur/buah, "
        "kurangi gula/garam, dan minum air putih yang cukup."
    )
    if not model:
        print("❌ Model belum siap (cek API key).")
        return fallback
    try:
        prompt = (
            "Topik: Edukasi kesehatan (gaya hidup sehat, nutrisi, kebersihan, stunting, gizi anak).\n"
            "Jika pertanyaan di luar domain, katakan fokus pada edukasi kesehatan dan arahkan kembali.\n"
            "Jawab ringkas dan praktis.\n\n"
            f"Pesan pengguna: {user_message}"
        )
        resp = model.generate_content(prompt)
        text = getattr(resp, "text", None)
        if not text:
            try:
                text = resp.candidates[0].content.parts[0].text  # type: ignore
            except Exception:
                text = None
        print("🤖 [Gemini Reply]:", text)
        return text or "Maaf, saya belum bisa menjawab. Coba ulangi pertanyaannya."
    except Exception as e:
        print("❌ [Gemini Error]:", e)
        logger.exception(f"Gemini generation error: {e}")
        return (
            "Maaf, terjadi kendala saat memproses AI. "
            "Tips cepat: jaga kebersihan tangan, konsumsi makanan bergizi, dan cukup istirahat."
        )


def send_fonnte_message(target: str, message: str) -> bool:
    """Kirim pesan ke pengguna via API Fonnte"""
    if not FONNTE_TOKEN:
        print("⚠️ FONNTE_TOKEN belum dikonfigurasi (cek environment variable).")
        return False
    try:
        headers = {"Authorization": FONNTE_TOKEN}
        data = {"target": target, "message": message}
        r = requests.post(FONNTE_SEND_URL, headers=headers, data=data, timeout=15)
        ok = r.status_code in (200, 201)
        if not ok:
            logger.error(f"Fonnte send failed: {r.status_code} {r.text[:300]}")
        else:
            logger.info(f"Fonnte message sent to {target}")
        return ok
    except Exception as e:
        logger.exception(f"Error calling Fonnte API: {e}")
        return False


# =====================================================
# 🌐 ROUTES
# =====================================================
@app.get("/")
def health():
    return jsonify({"ok": True, "service": "whatsapp-health-bot"}), 200


@app.post("/webhook")
def webhook():
    """Endpoint untuk menerima pesan dari WhatsApp Gateway / Fonnte"""
    print("📩 Incoming JSON:", request.json)
    payload = request.get_json(silent=True) or {}

    sender = payload.get("sender") or payload.get("from") or payload.get("number")
    message = payload.get("message") or payload.get("text")

    if not sender or not message:
        return jsonify({"ok": False, "error": "Invalid payload"}), 400

    reply = generate_reply(message)
    sent = send_fonnte_message(sender, reply)

    return jsonify({
        "ok": True,
        "sender": sender,
        "message": message,
        "reply": reply,
        "sent": sent
    }), 200


# =====================================================
# ▶️ Jalankan Server
# =====================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)

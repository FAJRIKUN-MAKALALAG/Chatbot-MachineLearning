import os
import logging
from datetime import datetime
from typing import Optional

import requests
from flask import Flask, request, jsonify

try:
    import google.generativeai as genai
except Exception:  # Library not yet installed during initial view
    genai = None  # type: ignore


# -----------------------------------------------------
# Logging configuration
# -----------------------------------------------------
LOG_FILE = "chatbot.log"
logger = logging.getLogger("whatsapp_health_bot")
logger.setLevel(logging.INFO)

_fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
_fh.setLevel(logging.INFO)
_fmt = logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s")
_fh.setFormatter(_fmt)
logger.addHandler(_fh)


# -----------------------------------------------------
# Flask app
# -----------------------------------------------------
app = Flask(__name__)


# -----------------------------------------------------
# Configuration (via environment variables, injected by Jenkins)
# -----------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
FONNTE_TOKEN = os.environ.get("FONNTE_TOKEN")
FONNTE_SEND_URL = os.environ.get("FONNTE_SEND_URL", "https://api.fonnte.com/send")


# -----------------------------------------------------
# Gemini model init
# -----------------------------------------------------
_model = None  # type: ignore

SYSTEM_INSTRUCTION = (
    "Anda adalah asisten edukasi kesehatan (gaya hidup sehat, nutrisi, kebersihan, "
    "stunting, dan gizi anak). Jawab SINGKAT, jelas, dan praktis dalam Bahasa Indonesia "
    "(sekitar 3–6 kalimat). Berikan langkah yang dapat dipraktikkan, sertakan peringatan "
    "jika perlu. Jika ada pertanyaan di luar domain kesehatan, mohon beri tahu bahwa Anda "
    "fokus pada edukasi kesehatan dan arahkan kembali ke topik terkait. Hindari memberikan "
    "diagnosis medis tertentu; sarankan konsultasi tenaga kesehatan bila perlu."
)


def get_gemini_model():
    global _model
    if _model is not None:
        return _model
    if genai is None:
        logger.warning("google-generativeai library not available yet.")
        return None
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not configured.")
        return None
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        _model = genai.GenerativeModel(
            model_name="models/gemini-2.5-flash",
            system_instruction=SYSTEM_INSTRUCTION,
        )
        return _model
    except Exception as e:
        logger.exception(f"Failed to initialize Gemini model: {e}")
        return None


def generate_reply(user_message: str) -> str:
    model = get_gemini_model()
    fallback = (
        "Maaf, konfigurasi AI belum siap. Coba lagi nanti ya. "
        "Sementara itu, untuk hidup sehat: tidur cukup, aktif bergerak, perbanyak sayur/buah, "
        "kurangi gula/garam, dan minum air yang cukup."
    )
    if not model:
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
            # Some SDK versions return candidates
            try:
                text = resp.candidates[0].content.parts[0].text  # type: ignore
            except Exception:
                text = None
        return text or "Maaf, saya belum bisa menjawab. Coba ulangi pertanyaannya."
    except Exception as e:
        logger.exception(f"Gemini generation error: {e}")
        return (
            "Maaf, terjadi kendala saat memproses AI. Coba lagi ya. "
            "Tips cepat: jaga kebersihan tangan, konsumsi makanan bergizi, dan cukup istirahat."
        )


def send_fonnte_message(target: str, message: str) -> bool:
    if not FONNTE_TOKEN:
        logger.error("FONNTE_TOKEN is not configured.")
        return False
    try:
        headers = {
            "Authorization": FONNTE_TOKEN,
        }
        # Fonnte commonly accepts form fields: target, message
        data = {
            "target": target,
            "message": message,
        }
        r = requests.post(FONNTE_SEND_URL, headers=headers, data=data, timeout=15)
        ok = r.status_code in (200, 201)
        if not ok:
            logger.error(
                f"Fonnte send failed status={r.status_code} body={r.text[:400]}"
            )
            return False
        # try to parse JSON for additional visibility
        try:
            j = r.json()
            logger.info(f"Fonnte response: {j}")
        except Exception:
            pass
        return True
    except Exception as e:
        logger.exception(f"Error calling Fonnte API: {e}")
        return False


@app.get("/")
def health():
    return jsonify({"ok": True, "service": "whatsapp-health-bot"}), 200


@app.post("/webhook")
def webhook():
    payload = request.get_json(silent=True) or {}
    sender = payload.get("sender")
    incoming_message = payload.get("message")

    if not sender or not incoming_message:
        logger.warning(f"Invalid payload: {payload}")
        return jsonify({"ok": False, "error": "Invalid payload"}), 400

    logger.info(f"INCOMING\tsender={sender}\tmsg={incoming_message}")

    reply = generate_reply(str(incoming_message))
    sent = send_fonnte_message(str(sender), reply)

    # conversation log line (tab-separated)
    log_line = f"CONV\t{sender}\t{incoming_message}\t{reply}\t{'SENT' if sent else 'FAILED'}"
    logger.info(log_line)

    return jsonify({"ok": True, "sent": bool(sent)}), 200


if __name__ == "__main__":
    # Local debug server (for development only)
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)


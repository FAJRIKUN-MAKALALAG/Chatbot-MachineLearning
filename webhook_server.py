from flask import Flask, request, jsonify
import google.generativeai as genai
import requests

app = Flask(__name__)

# 🔑 Ganti dengan API key kamu
GEMINI_API_KEY = "API_KEY_GEMINI_KAMU"
FONNTE_TOKEN = "API_KEY_FONNTE_KAMU"

genai.configure(api_key=GEMINI_API_KEY)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    sender = data.get("sender")
    message = data.get("message")

    print(f"📩 Pesan masuk dari {sender}: {message}")

    # 🔹 Panggil model Gemini untuk menjawab
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(f"Pertanyaan kesehatan: {message}")
    reply = response.text

    print(f"🤖 Balasan AI: {reply}")

    # 🔹 Kirim balasan ke Fonnte (WhatsApp)
    res = requests.post(
        "https://api.fonnte.com/send",
        headers={"Authorization": FONNTE_TOKEN},
        data={"target": sender, "message": reply}
    )

    sent_ok = res.status_code == 200
    print(f"📤 Status kirim WA: {sent_ok}")

    return jsonify({"ok": True, "sent": sent_ok, "reply": reply})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

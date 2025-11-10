// WhatsApp Health Education Chatbot (Flask + Gemini + Fonnte)

Chatbot WhatsApp dua arah untuk edukasi kesehatan (gaya hidup sehat, nutrisi, kebersihan, stunting, dan gizi anak). Alur: pengguna mengirim pesan → Fonnte API meneruskan via webhook → Flask memproses pesan menggunakan Google Gemini 2.5 Flash → balasan dikirim kembali ke pengguna lewat Fonnte.

## Arsitektur Singkat
- Webhook Flask: endpoint `POST /webhook` menerima JSON `{ "sender": "628xxxx", "message": "..." }` dari Fonnte.
- AI: Google Gemini 2.5 Flash via library `google-generativeai`.
- Kirim balasan: Fonnte API endpoint `https://api.fonnte.com/send`.
- Logging: semua percakapan dicatat ke file `chatbot.log`.
- Runtime: Gunicorn dikelola PM2 (di VPS) + Jenkins untuk CI/CD.

## File Struktur
- `app.py` — Webhook Flask utama + integrasi Gemini & Fonnte.
- `requirements.txt` — Dependency Python.
- `Jenkinsfile` — Pipeline Jenkins untuk deploy via PM2.
- `chatbot.log` — File log percakapan (akan di-append saat runtime).
- `README.md` — Dokumentasi ini.

## Prasyarat
- Python 3.10+ terpasang di server/agent Jenkins.
- Node.js + PM2 terpasang (global): `npm i -g pm2`.
- Akun Fonnte aktif (token API tersedia).
- Project Google AI Studio (API key Gemini 2.5 Flash).
- Jenkins terhubung ke repo ini (agent Linux direkomendasikan).

## Konfigurasi Kredensial (Jenkins Credentials Store)
Buat 2 credentials bertipe “Secret text”:
- ID: `GEMINI_API_KEY` — value: kunci API Gemini.
- ID: `FONNTE_TOKEN` — value: token Fonnte.

Pipeline `Jenkinsfile` akan memuat kedua credentials sebagai environment variables dan meng-inject ke proses PM2/Gunicorn.

## Deploy via Jenkins (CI/CD)
1. Pastikan agent memiliki `python3`, `node`, `pm2`.
2. Konfigurasi job multibranch/pipeline mengarah ke repo ini.
3. Jalankan pipeline:
   - Checkout source
   - Setup venv + install dependency
   - Start/reload PM2 dengan perintah: `gunicorn -w 2 -b 0.0.0.0:8000 app:app`
4. Verifikasi status: `pm2 status` dan `pm2 logs whatsapp-bot`.

Catatan: Jika perlu menyesuaikan port, ubah argumen `-b 0.0.0.0:8000` pada `Jenkinsfile`.

## Konfigurasi Fonnte Webhook
- Set URL webhook di dashboard Fonnte ke: `https://<domain-anda>/webhook`
- Body yang dikirim (contoh):
  ```json
  { "sender": "6281234567890", "message": "Halo bot!" }
  ```

## Uji Lokal (opsional)
1. Siapkan environment variable secara manual:
   ```bash
   export GEMINI_API_KEY="<api_key_gemini>"
   export FONNTE_TOKEN="<token_fonnte>"
   ```
2. Install deps & jalankan:
   ```bash
   python3 -m venv venv
   . venv/bin/activate
   pip install -r requirements.txt
   python app.py  # dev server di port 8000
   ```
3. Kirim request uji ke webhook:
   ```bash
   curl -X POST http://localhost:8000/webhook \
     -H 'Content-Type: application/json' \
     -d '{"sender":"6281234567890","message":"Tips hidup sehat dong"}'
   ```

> Catatan: untuk uji lokal, pengiriman ke Fonnte akan tetap dipanggil. Anda bisa sementara men-disable panggilan Fonnte atau gunakan nomor dummy untuk menghindari pengiriman nyata.

## Logging
- Semua interaksi dicatat di `chatbot.log` (format tab-separated). Contoh entri:
  - `INCOMING\tsender=628xxxx\tmsg=...`
  - `CONV\t<sender>\t<user_message>\t<reply>\tSENT|FAILED`

## Keamanan & Observabilitas
- Simpan kredensial hanya di Jenkins Credentials Store (bukan `.env`).
- Gunakan reverse proxy (Nginx/Caddy) dan HTTPS di depan Gunicorn.
- Pertimbangkan IP allowlist untuk sumber webhook Fonnte.
- Gunakan `pm2 logs whatsapp-bot` untuk memantau runtime, dan periksa `chatbot.log` untuk riwayat percakapan.

## Penyesuaian
- Ubah instruksi sistem AI di `app.py` (variabel `SYSTEM_INSTRUCTION`) untuk menyesuaikan gaya atau cakupan konten.
- Endpoint Fonnte dapat diatur lewat `FONNTE_SEND_URL` bila diperlukan.

---
Lisensi: internal project (sesuaikan kebutuhan Anda).

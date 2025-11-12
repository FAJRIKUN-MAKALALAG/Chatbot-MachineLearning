pipeline {
  agent any
  options { timestamps() }

  triggers {
    // Jalankan otomatis saat push dan polling tiap 2 menit
    pollSCM('H/2 * * * *')
    githubPush()
  }

  environment {
    APP_NAME = 'whatsapp-health-bot'
    APP_PORT = '8000'
    FONNTE_SEND_URL = 'https://api.fonnte.com/send'
    FONNTE_TEST_TARGET = '62882019908677' // Nomor WA kamu untuk notifikasi build
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Setup Python Environment') {
      steps {
        sh '''
          set -eu
          if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi
          $PY -m venv venv
          . venv/bin/activate
          pip install --upgrade pip
          pip install flask requests google-generativeai gunicorn
        '''
      }
    }

    stage('Install Node.js & PM2') {
      steps {
        sh '''
          set -eu
          if ! command -v pm2 >/dev/null 2>&1; then
            echo "🔧 Menginstal PM2..."
            if command -v npm >/dev/null 2>&1; then
              npm install -g pm2
            elif command -v apt-get >/dev/null 2>&1; then
              apt-get update -y
              apt-get install -y nodejs npm
              npm install -g pm2
            fi
          fi
          echo "✅ PM2 versi: $(pm2 -v)"
        '''
      }
    }

    stage('Deploy App (PM2 + Gunicorn)') {
      steps {
        withCredentials([
          string(credentialsId: 'GEMINI_API_KEY', variable: 'GEMINI_API_KEY'),
          string(credentialsId: 'FONNTE_TOKEN', variable: 'FONNTE_TOKEN')
        ]) {
          sh '''
            set -eu
            . venv/bin/activate
            export GEMINI_API_KEY="${GEMINI_API_KEY}"
            export FONNTE_TOKEN="${FONNTE_TOKEN}"

            echo "🚀 Menjalankan ${APP_NAME}..."
            if pm2 describe "${APP_NAME}" >/dev/null 2>&1; then
              pm2 reload "${APP_NAME}" --update-env
            else
              pm2 start "venv/bin/gunicorn -w 2 -b 0.0.0.0:${APP_PORT} app:app" \
                --name "${APP_NAME}" --update-env
            fi

            pm2 save
            pm2 status
          '''
        }
      }
    }

    stage('Expose Port & Show Public IP') {
      steps {
        sh '''
          echo "🔓 Membuka port ${APP_PORT}..."
          if command -v ufw >/dev/null 2>&1; then
            sudo ufw allow ${APP_PORT} || true
          elif command -v firewall-cmd >/dev/null 2>&1; then
            sudo firewall-cmd --add-port=${APP_PORT}/tcp --permanent || true
            sudo firewall-cmd --reload || true
          fi

          PUBLIC_IP=$(curl -s ifconfig.me || echo "Tidak bisa ambil IP publik")
          echo "🌍 Aplikasi aktif di: http://${PUBLIC_IP}:${APP_PORT}/webhook"
        '''
      }
    }
  }

  post {
    success {
      echo '✅ Build berhasil!'
      withCredentials([string(credentialsId: 'FONNTE_TOKEN', variable: 'FONNTE_TOKEN')]) {
        sh '''
          MSG="✅ *Build Sukses* untuk ${APP_NAME} pada $(date +'%F %T')"
          MSG="$MSG%0AStatus: SUCCESS"
          MSG="$MSG%0AHost: $(hostname)"
          MSG="$MSG%0AURL: http://$(curl -s ifconfig.me):${APP_PORT}/webhook"
          curl -sS -X POST "$FONNTE_SEND_URL" \
            -H "Authorization: ${FONNTE_TOKEN}" \
            --data-urlencode "target=${FONNTE_TEST_TARGET}" \
            --data-urlencode "message=${MSG}"
        '''
      }
    }

    failure {
      echo '❌ Build gagal!'
      withCredentials([string(credentialsId: 'FONNTE_TOKEN', variable: 'FONNTE_TOKEN')]) {
        sh '''
          MSG="❌ *Build Gagal* untuk ${APP_NAME} pada $(date +'%F %T')"
          MSG="$MSG%0AStatus: FAILED"
          MSG="$MSG%0AHost: $(hostname)"
          MSG="$MSG%0APeriksa log Jenkins untuk detail error."
          curl -sS -X POST "$FONNTE_SEND_URL" \
            -H "Authorization: ${FONNTE_TOKEN}" \
            --data-urlencode "target=${FONNTE_TEST_TARGET}" \
            --data-urlencode "message=${MSG}"
        '''
      }
    }
  }
}

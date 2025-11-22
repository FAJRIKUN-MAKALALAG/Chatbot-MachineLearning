pipeline {
  agent any
  options { timestamps() }

  triggers {
    pollSCM('H/1 * * * *')
    githubPush()
  }

  environment {
    APP_NAME = 'whatsapp-health-bot'
    APP_PORT = '8000'
    FONNTE_SEND_URL = 'https://api.fonnte.com/send'
    FONNTE_TEST_TARGET = '62882019908677'
  }

  stages {
    stage('Checkout Code') {
      steps { checkout scm }
    }

    stage('Setup Python Environment') {
      steps {
        sh '''
          set -eu
          echo "🐍 Mengecek Python..."
          if command -v python3 >/dev/null 2>&1; then PY=python3;
          elif command -v python >/dev/null 2>&1; then PY=python;
          else echo "❌ Python tidak ditemukan"; exit 1; fi

          echo "📦 Membuat Virtual Environment..."
          $PY -m venv venv
          . venv/bin/activate

          pip install --upgrade pip
          pip install flask requests google-generativeai gunicorn
        '''
      }
    }

    stage('Install PM2 (Node.js)') {
      steps {
        sh '''
          set -eu
          if ! command -v pm2 >/dev/null 2>&1; then
            echo "🔧 Instal PM2 dan Node.js..."
            if command -v npm >/dev/null 2>&1; then
              npm install -g pm2
            elif command -v apt-get >/dev/null 2>&1; then
              apt-get update -y
              apt-get install -y nodejs npm
              npm install -g pm2
            fi
          fi
          echo "🚀 PM2 version: $(pm2 -v)"
        '''
      }
    }

    stage('Deploy App (Gunicorn + PM2)') {
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

            echo "📦 Membersihkan PM2 crash logs..."
            pm2 delete "${APP_NAME}" || true

            echo "🚀 Menjalankan aplikasi..."
            pm2 start "venv/bin/gunicorn -w 2 -b 0.0.0.0:${APP_PORT} app:app" \
              --name "${APP_NAME}" --update-env

            pm2 save
            pm2 status
          '''
        }
      }
    }

    stage('Expose Firewall & Show Public URL') {
      steps {
        sh '''
          echo "🔓 Membuka port ${APP_PORT}..."
          if command -v ufw >/dev/null 2>&1; then ufw allow ${APP_PORT} || true; fi
          PUBLIC_IP=$(curl -s ifconfig.me || echo "Tidak dapet IP Publik")
          echo "🌍 URL: http://${PUBLIC_IP}:${APP_PORT}/webhook"
          echo "$PUBLIC_IP" > public_ip.txt
        '''
      }
    }

    stage('Test Webhook & Send Notification') {
      steps {
        withCredentials([string(credentialsId: 'FONNTE_TOKEN', variable: 'FONNTE_TOKEN')]) {
          sh '''
            PUBLIC_IP=$(cat public_ip.txt)
            URL="http://${PUBLIC_IP}:${APP_PORT}/webhook"

            echo "🔍 Testing: $URL"
            STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL")
            if [ "$STATUS" = "200" ]; then
              RESULT="Webhook aktif ✓"
            else
              RESULT="Webhook gagal (HTTP $STATUS) ✗"
            fi

            MSG="🤖 *Aira (AI Gizi Anak) Aktif!*%0AStatus: ${RESULT}%0AURL: ${URL}%0AHost: $(hostname)"
            curl -sS -X POST "$FONNTE_SEND_URL" \
              -H "Authorization: ${FONNTE_TOKEN}" \
              --data-urlencode "target=${FONNTE_TEST_TARGET}" \
              --data-urlencode "message=${MSG}"
          '''
        }
      }
    }
  }

  post {
    success {
      echo '✅ Build berhasil!'
    }

    failure {
      echo '❌ Build gagal!'
      withCredentials([string(credentialsId: 'FONNTE_TOKEN', variable: 'FONNTE_TOKEN')]) {
        sh '''
          MSG="❌ *Build Gagal* untuk ${APP_NAME}%0AHost: $(hostname)%0APeriksa log Jenkins segera."
          curl -sS -X POST "$FONNTE_SEND_URL" \
            -H "Authorization: ${FONNTE_TOKEN}" \
            --data-urlencode "target=${FONNTE_TEST_TARGET}" \
            --data-urlencode "message=${MSG}"
        '''
      }
    }
  }
}

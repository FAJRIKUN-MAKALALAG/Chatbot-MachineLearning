pipeline {
  agent any

  options {
    timestamps()
  }

  triggers {
    // Auto build tiap push ke GitHub
    githubPush()
    // Fallback polling tiap 2 menit
    pollSCM('H/2 * * * *')
  }

  environment {
    FONNTE_TEST_TARGET = '62882019908677'
    FONNTE_SEND_URL = 'https://api.fonnte.com/send'
    APP_NAME = 'whatsapp-health-bot'
    APP_PORT = '8000'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Setup Python Env') {
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
          if command -v pm2 >/dev/null 2>&1; then
            echo "pm2 already installed: $(pm2 -v)"
          else
            if command -v npm >/dev/null 2>&1; then
              npm install -g pm2
            elif command -v apt-get >/dev/null 2>&1; then
              apt-get update -y
              apt-get install -y nodejs npm
              npm install -g pm2
            elif command -v yum >/dev/null 2>&1; then
              yum install -y nodejs npm || true
              npm install -g pm2
            else
              echo "Node.js/npm tidak ditemukan dan package manager tidak dikenali."
              exit 1
            fi
          fi
          pm2 -v
        '''
      }
    }

    stage('Deploy App with PM2') {
      steps {
        withCredentials([
          string(credentialsId: 'GEMINI_API_KEY', variable: 'GEMINI_API_KEY'),
          string(credentialsId: 'FONNTE_TOKEN', variable: 'FONNTE_TOKEN')
        ]) {
          sh '''
            set -eu
            . venv/bin/activate

            # Simpan environment ke file agar PM2 baca
            cat > .env <<EOF
GEMINI_API_KEY=${GEMINI_API_KEY}
FONNTE_TOKEN=${FONNTE_TOKEN}
EOF

            echo "🚀 Jalankan atau reload ${APP_NAME}..."

            # Jalankan PM2 via konfigurasi
            pm2 startOrReload ecosystem.config.js --update-env

            # Simpan state PM2 agar otomatis start setelah reboot
            pm2 save

            # Tampilkan status
            pm2 status
          '''
        }
      }
    }

    stage('Expose Port & Show IP') {
      steps {
        sh '''
          echo "Membuka port ${APP_PORT}..."
          if command -v ufw >/dev/null 2>&1; then
            sudo ufw allow ${APP_PORT} || true
          elif command -v firewall-cmd >/dev/null 2>&1; then
            sudo firewall-cmd --add-port=${APP_PORT}/tcp --permanent || true
            sudo firewall-cmd --reload || true
          fi

          echo "Cek IP publik..."
          PUBLIC_IP=$(curl -s ifconfig.me || echo "Tidak bisa ambil IP publik")
          echo "✅ Webhook aktif di: http://${PUBLIC_IP}:${APP_PORT}/webhook"
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
          MSG="$MSG%0AService: http://$(curl -s ifconfig.me):${APP_PORT}/webhook"
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
          MSG="$MSG%0APeriksa log di Jenkins untuk detail error."
          curl -sS -X POST "$FONNTE_SEND_URL" \
            -H "Authorization: ${FONNTE_TOKEN}" \
            --data-urlencode "target=${FONNTE_TEST_TARGET}" \
            --data-urlencode "message=${MSG}"
        '''
      }
    }
  }
}

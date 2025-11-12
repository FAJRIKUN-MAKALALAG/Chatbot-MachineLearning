pipeline {
  agent any

  options {
    timestamps()
  }

  triggers {
    pollSCM('H/2 * * * *')   // Fallback polling tiap 2 menit
    githubPush()              // Trigger build saat push ke repo
  }

  environment {
    APP_NAME = 'whatsapp-health-bot'
    APP_PORT = '8000'
    FONNTE_SEND_URL = 'https://api.fonnte.com/send'
    FONNTE_TEST_TARGET = '62882019908677'
  }

  stages {
    stage('Checkout Source') {
      steps {
        checkout scm
      }
    }

    stage('Setup Python Environment') {
      steps {
        sh '''
          set -eu
          if ! command -v python3 >/dev/null 2>&1; then
            echo "❌ Python3 belum terinstal! Jalankan: sudo apt install python3 python3-venv -y"
            exit 1
          fi
          python3 -m venv venv
          . venv/bin/activate
          pip install --upgrade pip
        '''
      }
    }

    stage('Install Dependencies') {
      steps {
        sh '''
          set -eu
          . venv/bin/activate
          pip install -r requirements.txt || pip install flask requests google-generativeai gunicorn
        '''
      }
    }

    stage('Install Node.js & PM2') {
      steps {
        sh '''
          set -eu
          if ! command -v pm2 >/dev/null 2>&1; then
            echo "🔧 Menginstal Node.js dan PM2..."
            curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
            sudo apt-get install -y nodejs
            sudo npm install -g pm2
          fi
          pm2 -v
        '''
      }
    }

    stage('Test Fonnte Connectivity') {
      steps {
        withCredentials([string(credentialsId: 'FONNTE_TOKEN', variable: 'FONNTE_TOKEN')]) {
          sh '''
            set -eu
            MSG="[Jenkins] Tes konektivitas Fonnte berhasil dijalankan pada $(date +'%F %T')."
            echo "Mengirim pesan uji ke ${FONNTE_TEST_TARGET} ..."
            RESP=$(curl -sS -X POST "${FONNTE_SEND_URL}" \
              -H "Authorization: ${FONNTE_TOKEN}" \
              --data-urlencode "target=${FONNTE_TEST_TARGET}" \
              --data-urlencode "message=${MSG}" || true)
            echo "Fonnte response: $RESP"
          '''
        }
      }
    }

    stage('Deploy / Reload Webhook') {
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

            CMD="venv/bin/gunicorn -w 2 -b 0.0.0.0:${APP_PORT} app:app"

            echo "🚀 Menjalankan ${APP_NAME} di port ${APP_PORT} ..."
            if pm2 describe ${APP_NAME} >/dev/null 2>&1; then
              pm2 reload ${APP_NAME} --update-env
            else
              pm2 start "$CMD" --name ${APP_NAME} --update-env
            fi

            pm2 save
            pm2 status
          '''
        }
      }
    }

    stage('Show Webhook URL') {
      steps {
        script {
          def ip = sh(script: "hostname -I | awk '{print $1}'", returnStdout: true).trim()
          echo "🌐 Webhook aktif di: http://${ip}:${APP_PORT}/webhook"
          echo "Pastikan port ${APP_PORT} dibuka melalui UFW atau firewall VPS."
        }
      }
    }
  }

  post {
    success {
      echo "✅ Build sukses! Webhook siap diakses dari Fonnte atau WhatsApp Gateway."
    }
    failure {
      echo "❌ Build gagal. Cek log Jenkins dan environment variable."
    }
  }
}

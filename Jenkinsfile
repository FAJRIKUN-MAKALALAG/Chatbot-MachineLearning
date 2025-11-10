pipeline {
  agent any

  options {
    timestamps()
  }

  triggers {
    // Poll SCM setiap ~2 menit untuk fallback bila webhook tidak aktif
    pollSCM('H/2 * * * *')
    // Trigger build saat ada push GitHub (butuh GitHub plugin di Jenkins)
    githubPush()
  }

  environment {
    FONNTE_TEST_TARGET = '62882019908677'
    FONNTE_SEND_URL = 'https://api.fonnte.com/send'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Setup Python venv') {
      steps {
        sh '''
          set -euxo pipefail
          if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi
          $PY -m venv venv
          . venv/bin/activate
          pip install --upgrade pip
        '''
      }
    }

    stage('Install dependencies') {
      steps {
        sh '''
          set -euxo pipefail
          . venv/bin/activate
          pip install -r requirements.txt
        '''
      }
    }

    stage('Fonnte Connectivity Test') {
      steps {
        withCredentials([
          string(credentialsId: 'FONNTE_TOKEN', variable: 'FONNTE_TOKEN')
        ]) {
          sh '''
            set -euxo pipefail
            if [ -n "${FONNTE_TEST_TARGET}" ]; then
              FONNTE_SEND_URL="${FONNTE_SEND_URL:-https://api.fonnte.com/send}"
              MSG="[Jenkins] Tes konektivitas Fonnte OK pada $(date +'%F %T'). Jika Anda menerima pesan ini, token & koneksi Fonnte berfungsi."
              echo "Mengirim pesan uji ke ${FONNTE_TEST_TARGET} ..."
              RESP=$(curl -sS -X POST "$FONNTE_SEND_URL" \
                -H "Authorization: ${FONNTE_TOKEN}" \
                --data-urlencode "target=${FONNTE_TEST_TARGET}" \
                --data-urlencode "message=${MSG}" || true)
              echo "Fonnte response: $RESP"
            else
              echo "Lewati tes Fonnte: FONNTE_TEST_TARGET kosong."
            fi
          '''
        }
      }
    }

    stage('Run/Reload PM2 (Gunicorn)') {
      steps {
        withCredentials([
          string(credentialsId: 'GEMINI_API_KEY', variable: 'GEMINI_API_KEY'),
          string(credentialsId: 'FONNTE_TOKEN', variable: 'FONNTE_TOKEN')
        ]) {
          sh '''
            set -euxo pipefail
            # Ensure pm2 exists
            command -v pm2 >/dev/null 2>&1

            . venv/bin/activate

            # Export env so PM2 process inherits them
            export GEMINI_API_KEY="${GEMINI_API_KEY}"
            export FONNTE_TOKEN="${FONNTE_TOKEN}"

            # Start or reload the process
            if pm2 describe whatsapp-bot >/dev/null 2>&1; then
              pm2 reload whatsapp-bot --update-env
            else
              pm2 start "venv/bin/gunicorn -w 2 -b 0.0.0.0:8000 app:app" --name whatsapp-bot --update-env
            fi

            pm2 save
            pm2 status
          '''
        }
      }
    }
  }

  post {
    failure {
      echo 'Pipeline failed. Check logs and credentials.'
    }
  }
}

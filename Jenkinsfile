
pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Start services') {
            steps {
                sh 'docker compose up -d --build'
            }
        }

        stage('Wait for API') {
            steps {
                sh '''
                    for i in $(seq 1 30); do
                        if curl -fsS http://localhost:8000/docs > /dev/null; then
                            echo "API is ready"
                            exit 0
                        fi
                        sleep 2
                    done

                    echo "API failed to start"
                    docker compose logs
                    exit 1
                '''
            }
        }

        stage('Run API tests') {
            steps {
                sh '''
                    docker compose exec -T api pytest \
                        -v \
                        --junitxml=/tmp/report.xml
                '''
            }
        }
    }

    post {
        always {
            sh '''
                docker compose cp api:/tmp/report.xml report.xml || true
                docker compose down
            '''
            junit testResults: 'report.xml',
                  allowEmptyResults: true
        }
    }
}

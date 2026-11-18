
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
            junit 'report.xml'
            sh 'docker compose down -v'
        }
    }
}

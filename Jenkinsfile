
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
                    dir("${WORKSPACE}") {
                    sh 'docker compose up -d --build'
            }
        }
        }

        stage('Run API tests') {
            steps {
                sh '''
                    docker compose exec -T api pytest \
                        -v \
                        --junitxml=/tmp/report.xml
                    
                    docker cp "$(docker compose ps -q api):/tmp/report.xml" \
                    "$WORKSPACE/report.xml"
                '''
              
            }
        }
    }

    post {
        always {
            junit testResults: 'report.xml', allowEmptyResults: true
            dir("${WORKSPACE}"){
                sh 'docker compose down || true'
                }
        }
    }
}

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
                dir("${WORKSPACE}") {
                    sh '''
                        set +e

                        docker compose exec -T api pytest \
                            -v \
                            --junitxml=/tmp/report.xml

                        TEST_EXIT=$?

                        docker cp "$(docker compose ps -q api):/tmp/report.xml" \
                            "$WORKSPACE/report.xml"

                        ls -l "$WORKSPACE/report.xml"

                        exit $TEST_EXIT
                    '''
                }
            }
        }
    }

    post {
        always {
            dir("${WORKSPACE}") {
                junit testResults: 'report.xml', allowEmptyResults: true
                sh 'docker compose down || true'
            }
        }
    }
}
#!/usr/bin/env bash
: "Usage

Duplicate sample file
$ cp env.sample.sh env.sh

Configure file — set CAT_ENV to your target
$ vim env.sh

Source it before running tests
$ source env.sh

Targets:
  docker-compose   Local Docker Compose stack (federated-catalogue/docker/)
  minikube         Local Minikube / k8s cluster
  qa               Remote QA/staging environment
"

# --------------------------------------------------------------------------
# :: bdd-executor framework path
# --------------------------------------------------------------------------
# Path to the bdd-executor repository root.
# This is used by the Makefile to install the eu-xfsc-bdd dependency.
#
# Common scenarios:
#   As submodule:        ../../bdd-executor (cat-integration-tests in bdd-executor/implementations/)
#   As sibling repo:     ../bdd-executor (both repos cloned side by side)
#   Custom location:     /path/to/bdd-executor (any absolute path)
#
# Default if not set: ../.. (assumes submodule structure)
export EU_XFSC_BDD_CORE_PATH="${EU_XFSC_BDD_CORE_PATH:-../..}"

# --------------------------------------------------------------------------
# :: Target environment selector
# --------------------------------------------------------------------------
#export CAT_ENV="docker-compose"  # docker-compose | minikube | qa
export CAT_ENV="docker-compose"


case ${CAT_ENV} in

  docker-compose)
    # Local Docker Compose stack from federated-catalogue/docker/
    # Prerequisites:
    #   cd ../federated-catalogue/docker && docker-compose --env-file dev.env up
    #   Add `127.0.0.1 key-server` to /etc/hosts
    export CAT_FC_HOST="http://localhost:8081"
    export CAT_KEYCLOAK_URL="http://key-server:8080"
    export CAT_KEYCLOAK_REALM="gaia-x"
    export CAT_KEYCLOAK_CLIENT_ID="federated-catalogue"
    export CAT_KEYCLOAK_CLIENT_SECRET=""
    export CAT_KEYCLOAK_SCOPE="openid"
    export CAT_TEST_USER="admin"
    export CAT_TEST_PASSWORD="admin"
    # WireMock for @uses.compliance-mock scenarios (see docker-compose stack)
    export CAT_WIREMOCK_HOST="http://localhost:8089"
    ;;

  minikube)
    # Local Minikube or kind cluster
    # Adjust host/port to match your ingress or NodePort setup
    export CAT_FC_HOST="http://localhost:30081"
    export CAT_KEYCLOAK_URL="http://localhost:30080"
    export CAT_KEYCLOAK_REALM="gaia-x"
    export CAT_KEYCLOAK_CLIENT_ID="federated-catalogue"
    export CAT_KEYCLOAK_CLIENT_SECRET=""
    export CAT_KEYCLOAK_SCOPE="openid"
    export CAT_TEST_USER="admin"
    export CAT_TEST_PASSWORD="admin"
    export CAT_WIREMOCK_HOST="http://localhost:8089"
    ;;

  qa)
    # Remote QA / staging environment
    # Set these to your actual QA endpoints and credentials
    export CAT_FC_HOST="https://fc-server.qa.example.org"
    export CAT_KEYCLOAK_URL="https://keycloak.qa.example.org"
    export CAT_KEYCLOAK_REALM="gaia-x"
    export CAT_KEYCLOAK_CLIENT_ID="federated-catalogue"
    export CAT_KEYCLOAK_CLIENT_SECRET="your-qa-secret-here"
    export CAT_KEYCLOAK_SCOPE="openid"
    export CAT_TEST_USER="qa-test-user"
    export CAT_TEST_PASSWORD="qa-test-password"
    export CAT_WIREMOCK_HOST="https://wiremock.qa.example.org"
    ;;

  *)
    echo "ERROR: Unknown CAT_ENV='${CAT_ENV}'. Use: docker-compose | minikube | qa"
    return 1 2>/dev/null || exit 1
    ;;

esac

echo "CAT_ENV=${CAT_ENV} — FC @ ${CAT_FC_HOST}, Keycloak @ ${CAT_KEYCLOAK_URL}"

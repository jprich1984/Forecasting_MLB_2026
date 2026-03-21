#!/bin/bash
VENV=/Users/johnprichard/PycharmProjects/Predicting2026_MLB/venv
CERT=$($VENV/bin/python3 -c "import certifi; print(certifi.where())")
SSL_CERT_FILE="$CERT" REQUESTS_CA_BUNDLE="$CERT" \
  $VENV/bin/python3 "$(dirname "$0")/rosters.py"

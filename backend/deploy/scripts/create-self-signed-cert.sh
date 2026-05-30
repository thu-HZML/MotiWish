#!/bin/sh
set -e

CERT_DIR="${1:-./deploy/nginx/certs}"
COMMON_NAME="${2:-localhost}"
SUBJECT_ALT_NAME="${3:-DNS:localhost,IP:127.0.0.1}"

mkdir -p "$CERT_DIR"

docker run --rm \
  -v "$(pwd)/${CERT_DIR}:/certs" \
  alpine/openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout /certs/privkey.pem \
  -out /certs/fullchain.pem \
  -subj "/CN=${COMMON_NAME}" \
  -addext "subjectAltName=${SUBJECT_ALT_NAME}"

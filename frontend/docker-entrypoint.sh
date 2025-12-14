#!/bin/sh
set -e

# Default backend URL if none is provided at runtime
: "${BACKEND_URL:=http://backend-service:8000}"

# Render nginx configuration from template
envsubst '$BACKEND_URL' < /etc/nginx/nginx.conf.template > /tmp/nginx.conf

echo "Using BACKEND_URL=${BACKEND_URL}"

exec nginx -g "daemon off;" -c /tmp/nginx.conf

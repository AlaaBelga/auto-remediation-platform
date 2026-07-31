#!/usr/bin/env bash
set -euo pipefail

API_KEY="${API_KEY:-demo-platform-key}"
P2_URL="${P2_URL:-http://127.0.0.1:8001}"
SLACK_URL="${SLACK_URL:-http://127.0.0.1:8010}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://127.0.0.1:9090}"
EVENT_FILE="${EVENT_FILE:-remediation_engine/examples/event_valid.json}"

echo "== Verification P2 et dependances =="
curl -fsS "${P2_URL}/health"
echo
curl -fsS "${SLACK_URL}/health"
echo

if curl -fsS "${PROMETHEUS_URL}/-/healthy" >/dev/null 2>&1; then
  echo "Prometheus: ok"
else
  echo "Prometheus: indisponible ou non demarre, les captures Prometheus sont optionnelles"
fi

echo
echo "== Evenement P2 valide envoye vers Kafka =="
curl -fsS \
  -X POST "${P2_URL}/events" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  --data-binary "@${EVENT_FILE}"
echo

echo
echo "== Attente du worker Kafka =="
sleep 8

echo "== Tickets P2 crees =="
curl -fsS "${P2_URL}/tickets"
echo

echo
echo "== Notifications mock Slack =="
curl -fsS "${SLACK_URL}/notifications"
echo

echo
echo "== Metriques P2 utiles =="
curl -fsS "${P2_URL}/metrics" | grep -E "p2_events_received_total|p2_self_healing_triggered_total|p2_incidents_opened_total|p2_tickets_created_total|p2_webhook_notifications_total|p2_latest_risk_score" || true
echo

if curl -fsS "${PROMETHEUS_URL}/-/healthy" >/dev/null 2>&1; then
  echo "== Requetes Prometheus P2 utiles =="
  curl -fsS "${PROMETHEUS_URL}/api/v1/query?query=p2_incidents_opened_total"
  echo
  curl -fsS "${PROMETHEUS_URL}/api/v1/query?query=p2_tickets_created_total"
  echo
fi

echo "Smoke test P2 termine."

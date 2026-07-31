#!/usr/bin/env bash
set -euo pipefail

API_KEY="${API_KEY:-demo-platform-key}"
P1_URL="${P1_URL:-http://127.0.0.1:8000/predict}"
P2_URL="${P2_URL:-http://127.0.0.1:8001/events}"
MACHINE_ID="${MACHINE_ID:-TURBINE_042}"

echo "== Verification des endpoints =="
curl -fsS http://127.0.0.1:8000/health
echo
curl -fsS http://127.0.0.1:8001/health
echo
curl -fsS http://127.0.0.1:8010/health
echo
curl -fsS http://127.0.0.1:9090/-/healthy
echo

echo "== Declenchement du cas critique P1 -> P2 =="
python3 -m P2.p1_to_p2_bridge \
  --payload-file Projet_encadrer/critical_payload.json \
  --machine-id "${MACHINE_ID}" \
  --p1-url "${P1_URL}" \
  --p2-url "${P2_URL}" \
  --p1-api-key "${API_KEY}" \
  --p2-api-key "${API_KEY}"

echo
echo "== Attente du worker Kafka =="
sleep 8

echo "== Tickets crees =="
curl -fsS http://127.0.0.1:8001/tickets
echo

echo "== Notifications mock Slack =="
curl -fsS http://127.0.0.1:8010/notifications
echo

echo "== Metriques P2 utiles =="
curl -fsS http://127.0.0.1:8001/metrics | grep -E "p2_events_received_total|p2_self_healing_triggered_total|p2_incidents_opened_total|p2_tickets_created_total|p2_webhook_notifications_total" || true
echo

echo "== Requetes Prometheus utiles =="
curl -fsS "http://127.0.0.1:9090/api/v1/query?query=p2_incidents_opened_total"
echo
curl -fsS "http://127.0.0.1:9090/api/v1/query?query=p2_tickets_created_total"
echo

echo "Smoke test termine."

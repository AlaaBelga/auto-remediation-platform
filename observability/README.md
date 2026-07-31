# Observabilite et runbook

Cette stack expose les metriques Predictive Engine, Remediation Engine API et Remediation Engine worker vers Prometheus, puis
les visualise dans Grafana.

## Acces

- Prometheus : http://localhost:9090
- Grafana : http://localhost:3000 (`admin` / `admin`)
- Tableau de bord Remediation Engine : dossier Grafana `Self Healing`
- Mock Slack : http://localhost:8010/notifications
- Tickets Remediation Engine : http://localhost:8001/tickets

## Alertes metier

Les regles sont dans `observability/prometheus/alerts.yml`.

### `P2EventsRejected`

Declenchement :

```promql
increase(p2_events_rejected_total[5m]) > 0
```

Signification : un evenement Predictive Engine -> Remediation Engine ne respecte pas le schema attendu.

Verification :

```bash
docker compose logs p2-api
docker compose logs p2-worker
curl http://localhost:8001/metrics
```

Actions :

- verifier le detail de rejet dans les logs Remediation Engine
- comparer l'evenement avec `remediation_engine/P1_to_P2_event_schema_v1.json`
- tester un evenement valide avec `remediation_engine/examples/event_valid.json`
- verifier que la passerelle `remediation_engine.p1_to_p2_bridge` utilise bien la version courante du contrat

### `P2SelfHealingTriggered`

Declenchement :

```promql
increase(p2_self_healing_triggered_total[5m]) > 0
```

Signification : Remediation Engine a declenche au moins un playbook d'auto-remediation.

Verification :

```bash
docker compose logs p2-worker
curl http://localhost:8001/tickets
curl http://localhost:8010/notifications
```

Actions :

- verifier que l'action simulee `REDUCE_RPM_BY_20` a ete emise
- verifier qu'un ticket existe dans SQLite via `/tickets`
- verifier que la notification mock Slack a ete recue
- confirmer que l'evenement critique vient bien de Predictive Engine et contient un `correlation_id`

### `P2IncidentOpened`

Declenchement :

```promql
increase(p2_incidents_opened_total[5m]) > 0
```

Signification : Remediation Engine a ouvert un incident simule et cree un ticket associe.

Verification :

```bash
curl http://localhost:8001/tickets
curl http://localhost:8010/notifications
docker compose logs p2-worker
```

Actions :

- recuperer le `ticket_id` depuis `/tickets`
- verifier le `risk_score`, la machine, la severite et l'action recommandee
- confirmer que l'incident existe aussi dans `incidents.jsonl`
- si la notification manque, verifier `p2_webhook_notification_errors_total`

## Requetes utiles

```promql
p2_latest_risk_score
increase(p2_events_rejected_total[5m])
increase(p2_self_healing_triggered_total[5m])
increase(p2_incidents_opened_total[5m])
increase(p2_tickets_created_total[5m])
increase(p2_webhook_notifications_total[5m])
increase(p2_webhook_notification_errors_total[5m])
```

## Rechargement Prometheus

Apres modification des regles :

```bash
docker compose restart prometheus
```

Ou, si le conteneur accepte le reload HTTP :

```bash
curl -X POST http://localhost:9090/-/reload
```

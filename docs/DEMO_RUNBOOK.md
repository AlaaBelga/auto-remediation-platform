# Runbook de test et demo video

Ce document sert a tester la plateforme complete, prendre des captures d'ecran
et preparer une video de demonstration courte.

## 1. Preparation

Depuis la racine du projet :

```bash
docker compose up --build -d
docker compose ps
```

Attendre que les services soient `healthy` quand un healthcheck existe.

URLs a ouvrir :

- Predictive Engine Swagger : http://localhost:8000/docs
- Remediation Engine console : http://localhost:8001/ui
- Tableau de bord Streamlit : http://localhost:8501
- Tickets Remediation Engine : http://localhost:8001/tickets
- Mock Slack : http://localhost:8010/notifications
- Prometheus : http://localhost:9090
- Grafana : http://localhost:3000 (`admin` / `admin`)

Cle API de demonstration :

```text
demo-platform-key
```

## 2. Verification rapide en terminal

```bash
pytest remediation_engine/tests predictive_engine/tests -q
docker compose config --quiet
```

Puis verifier les endpoints :

```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8010/health
curl http://localhost:9090/-/healthy
```

Capture recommandee : terminal montrant les tests `29 passed` et les endpoints
en etat `ok`.

## 3. Smoke test end-to-end

Lancer :

```bash
bash scripts/demo_smoke_test.sh
```

Ce script :

- verifie Predictive Engine, Remediation Engine, Mock Slack et Prometheus
- appelle Predictive Engine `/predict` avec `critical_payload.json`
- transforme la prediction en evenement Remediation Engine
- poste l'evenement vers Remediation Engine `/events`
- laisse le worker Kafka traiter le message
- affiche les tickets, notifications et metriques Remediation Engine

Captures recommandees :

- terminal avec la reponse du bridge Predictive Engine -> Remediation Engine
- terminal avec `Tickets crees`
- terminal avec `Notifications mock Slack`
- terminal avec les metriques Remediation Engine

## 3 bis. Captures centrees sur le Pilier 2

Pour une video centree sur Remediation Engine, le plus propre est de demarrer la plateforme
complete et de laisser Predictive Engine produire un cas critique, mais de ne capturer que les
preuves remediation_engine.

Demarrer la stack :

```bash
docker compose up --build -d
docker compose ps
```

Lancer ensuite le smoke test end-to-end :

```bash
bash scripts/demo_smoke_test.sh
```

Ce chemin donne de meilleures preuves Remediation Engine, car l'evenement vient vraiment de Predictive Engine
via la passerelle Predictive Engine -> Remediation Engine, puis passe par Kafka, le worker Remediation Engine, le ticketing, le
mock Slack et les metriques.

Captures recommandees, sans montrer les ecrans Predictive Engine :

- terminal avec la reponse du bridge Predictive Engine -> Remediation Engine
- terminal avec `Tickets crees`
- terminal avec `Notifications mock Slack`
- terminal avec les metriques Remediation Engine
- navigateur `http://localhost:8001/ui`
- navigateur `http://localhost:8001/tickets`
- navigateur `http://localhost:8010/notifications`
- optionnel : `http://localhost:9090/targets`, `http://localhost:9090/alerts`
- optionnel : dashboard Grafana Remediation Engine dans `http://localhost:3000`

Si besoin d'un mode plus rapide qui evite Predictive Engine, demarrer uniquement la chaine
utile a Remediation Engine :

```bash
docker compose up --build -d kafka slack-mock p2-api p2-worker
docker compose ps kafka slack-mock p2-api p2-worker
```

Si les captures Prometheus/Grafana font partie de la video, demarrer aussi :

```bash
docker compose up --build -d prometheus grafana
```

Note : dans le fichier Compose actuel, Prometheus depend aussi de `p1-api`.
Il peut donc demarrer Predictive Engine automatiquement, mais les captures peuvent rester
strictement centrees sur les metriques remediation_engine.

Lancer ensuite le smoke test Remediation Engine uniquement :

```bash
bash scripts/p2_demo_smoke_test.sh
```

Ce script :

- verifie Remediation Engine et le mock Slack
- envoie `remediation_engine/examples/event_valid.json` directement vers Remediation Engine `/events`
- laisse le worker Kafka traiter l'evenement
- affiche les tickets, notifications mock Slack et metriques Remediation Engine
- interroge Prometheus si le service est disponible

Captures recommandees pour ce mode rapide :

- terminal avec `Evenement Remediation Engine valide envoye vers Kafka`
- terminal avec `Tickets Remediation Engine crees`
- terminal avec `Notifications mock Slack`
- terminal avec `Metriques Remediation Engine utiles`
- navigateur `http://localhost:8001/ui`
- navigateur `http://localhost:8001/tickets`
- navigateur `http://localhost:8010/notifications`
- optionnel : `http://localhost:9090/targets`, `http://localhost:9090/alerts`
- optionnel : dashboard Grafana Remediation Engine dans `http://localhost:3000`

## 4. Captures navigateur a prendre

### Predictive Engine Swagger

Ouvrir :

```text
http://localhost:8000/docs
```

Capture :

- endpoint `POST /predict`
- endpoints `/health` et `/metrics`

### Tableau de bord Streamlit

Ouvrir :

```text
http://localhost:8501
```

Capture :

- score de risque
- RUL estime
- statut OK / WARNING / CRITICAL
- graphiques capteurs

### Remediation Engine console

Ouvrir :

```text
http://localhost:8001/ui
```

Saisir la cle API si besoin :

```text
demo-platform-key
```

Capture :

- validation evenement
- resultat d'action ou file Kafka

### Tickets Remediation Engine

Ouvrir :

```text
http://localhost:8001/tickets
```

Capture :

- `ticket_id`
- `incident_id`
- `machine_id`
- `risk_score`
- `recommended_action`

### Mock Slack

Ouvrir :

```text
http://localhost:8010/notifications
```

Capture :

- notification recue
- `machine_id`
- `risk_score`
- `playbook_result`

### Prometheus

Ouvrir :

```text
http://localhost:9090/targets
```

Capture :

- targets `p1-api`, `p2-api`, `p2-worker`

Puis ouvrir :

```text
http://localhost:9090/alerts
```

Capture :

- alertes Remediation Engine : evenement rejete, self-healing declenche, incident ouvert

Requetes utiles dans Prometheus :

```promql
p2_latest_risk_score
p2_events_received_total
p2_self_healing_triggered_total
p2_incidents_opened_total
p2_tickets_created_total
p2_webhook_notifications_total
```

### Grafana

Ouvrir :

```text
http://localhost:3000
```

Identifiants :

```text
admin / admin
```

Capture :

- datasource Prometheus provisionnee
- dashboard Remediation Engine dans le dossier `Self Healing`
- panels incidents, self-healing, commandes actionneur, score de risque

## 5. Demo Kubernetes / HPA

Voir aussi `k8s/README.md`.

Commandes principales :

```bash
eval "$(minikube docker-env)"
docker build -f predictive_engine/Dockerfile.api -t self-healing/p1-api:latest .
docker build -f predictive_engine/Dockerfile.dashboard -t self-healing/dashboard:latest .
docker build -f remediation_engine/Dockerfile -t self-healing/p2-api:latest .

minikube addons enable metrics-server
kubectl apply -f k8s/platform.yaml
kubectl rollout status -n self-healing deployment/p1-api
kubectl get hpa -n self-healing
```

Capture initiale :

```bash
kubectl get pods -n self-healing
kubectl get hpa -n self-healing
```

Lancer ensuite la charge HPA depuis `k8s/README.md`, puis capturer :

```bash
kubectl get hpa -n self-healing
kubectl get deployment p1-api -n self-healing
```

Preuve attendue :

- `TARGETS` superieur a `70%`
- `REPLICAS` superieur a `2`

## 6. Storyboard video 5 minutes

### 0:00 - 0:30 Introduction

Montrer l'architecture dans le README.

Phrase :

> Cette plateforme relie maintenance predictive, API ML, Kafka, self-healing,
> tickets, notification mock Slack et observabilite Prometheus/Grafana.

### 0:30 - 1:15 Stack Docker

Montrer :

```bash
docker compose ps
```

Puis les URLs principales.

### 1:15 - 2:15 Predictive Engine prediction

Montrer Swagger ou Streamlit.

Insister sur :

- risk score
- RUL
- anomalie
- API key

### 2:15 - 3:15 Predictive Engine -> Remediation Engine -> self-healing

Lancer :

```bash
bash scripts/demo_smoke_test.sh
```

Montrer :

- evenement accepte
- actionneur simule
- incident ouvert
- ticket cree
- notification mock Slack recue

### 3:15 - 4:15 Observabilite

Montrer :

- Prometheus targets
- alertes Prometheus
- dashboard Grafana Remediation Engine

### 4:15 - 5:00 Kubernetes et limites

Montrer :

- `k8s/platform.yaml`
- HPA
- CI/CD GitHub Actions

Finir avec les limites assumees :

- TLS/Kafka TLS documentes comme evolution future
- SLA P95 < 100 ms non atteint
- base time-series production non integree

## 7. Checklist captures finales

- Terminal `pytest` avec tests OK
- Terminal `docker compose ps`
- Predictive Engine Swagger
- Streamlit dashboard
- Remediation Engine UI
- Tickets Remediation Engine
- Mock Slack
- Prometheus targets
- Prometheus alerts
- Grafana dashboard
- Kubernetes `kubectl get hpa`
- GitHub Actions workflows

## 8. Nettoyage

```bash
docker compose down
```

Pour supprimer aussi les volumes de demo :

```bash
docker compose down -v
```

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

- P1 Swagger : http://localhost:8000/docs
- P2 console : http://localhost:8001/ui
- Tableau de bord Streamlit : http://localhost:8501
- Tickets P2 : http://localhost:8001/tickets
- Mock Slack : http://localhost:8010/notifications
- Prometheus : http://localhost:9090
- Grafana : http://localhost:3000 (`admin` / `admin`)

Cle API de demonstration :

```text
demo-platform-key
```

## 2. Verification rapide en terminal

```bash
pytest P2/tests P1/tests -q
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

- verifie P1, P2, Mock Slack et Prometheus
- appelle P1 `/predict` avec `critical_payload.json`
- transforme la prediction en evenement P2
- poste l'evenement vers P2 `/events`
- laisse le worker Kafka traiter le message
- affiche les tickets, notifications et metriques P2

Captures recommandees :

- terminal avec la reponse du bridge P1 -> P2
- terminal avec `Tickets crees`
- terminal avec `Notifications mock Slack`
- terminal avec les metriques P2

## 3 bis. Captures centrees sur le Pilier 2

Pour une video centree sur P2, le plus propre est de demarrer la plateforme
complete et de laisser P1 produire un cas critique, mais de ne capturer que les
preuves P2.

Demarrer la stack :

```bash
docker compose up --build -d
docker compose ps
```

Lancer ensuite le smoke test end-to-end :

```bash
bash scripts/demo_smoke_test.sh
```

Ce chemin donne de meilleures preuves P2, car l'evenement vient vraiment de P1
via la passerelle P1 -> P2, puis passe par Kafka, le worker P2, le ticketing, le
mock Slack et les metriques.

Captures recommandees, sans montrer les ecrans P1 :

- terminal avec la reponse du bridge P1 -> P2
- terminal avec `Tickets crees`
- terminal avec `Notifications mock Slack`
- terminal avec les metriques P2
- navigateur `http://localhost:8001/ui`
- navigateur `http://localhost:8001/tickets`
- navigateur `http://localhost:8010/notifications`
- optionnel : `http://localhost:9090/targets`, `http://localhost:9090/alerts`
- optionnel : dashboard Grafana P2 dans `http://localhost:3000`

Si besoin d'un mode plus rapide qui evite P1, demarrer uniquement la chaine
utile a P2 :

```bash
docker compose up --build -d kafka slack-mock p2-api p2-worker
docker compose ps kafka slack-mock p2-api p2-worker
```

Si les captures Prometheus/Grafana font partie de la video, demarrer aussi :

```bash
docker compose up --build -d prometheus grafana
```

Note : dans le fichier Compose actuel, Prometheus depend aussi de `p1-api`.
Il peut donc demarrer P1 automatiquement, mais les captures peuvent rester
strictement centrees sur les metriques P2.

Lancer ensuite le smoke test P2 uniquement :

```bash
bash scripts/p2_demo_smoke_test.sh
```

Ce script :

- verifie P2 et le mock Slack
- envoie `P2/examples/event_valid.json` directement vers P2 `/events`
- laisse le worker Kafka traiter l'evenement
- affiche les tickets, notifications mock Slack et metriques P2
- interroge Prometheus si le service est disponible

Captures recommandees pour ce mode rapide :

- terminal avec `Evenement P2 valide envoye vers Kafka`
- terminal avec `Tickets P2 crees`
- terminal avec `Notifications mock Slack`
- terminal avec `Metriques P2 utiles`
- navigateur `http://localhost:8001/ui`
- navigateur `http://localhost:8001/tickets`
- navigateur `http://localhost:8010/notifications`
- optionnel : `http://localhost:9090/targets`, `http://localhost:9090/alerts`
- optionnel : dashboard Grafana P2 dans `http://localhost:3000`

## 4. Captures navigateur a prendre

### P1 Swagger

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

### P2 console

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

### Tickets P2

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

- alertes P2 : evenement rejete, self-healing declenche, incident ouvert

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
- dashboard P2 dans le dossier `Self Healing`
- panels incidents, self-healing, commandes actionneur, score de risque

## 5. Demo Kubernetes / HPA

Voir aussi `k8s/README.md`.

Commandes principales :

```bash
eval "$(minikube docker-env)"
docker build -f P1/Dockerfile.api -t self-healing/p1-api:latest .
docker build -f P1/Dockerfile.dashboard -t self-healing/dashboard:latest .
docker build -f P2/Dockerfile -t self-healing/p2-api:latest .

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

### 1:15 - 2:15 P1 prediction

Montrer Swagger ou Streamlit.

Insister sur :

- risk score
- RUL
- anomalie
- API key

### 2:15 - 3:15 P1 -> P2 -> self-healing

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
- dashboard Grafana P2

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
- P1 Swagger
- Streamlit dashboard
- P2 UI
- Tickets P2
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

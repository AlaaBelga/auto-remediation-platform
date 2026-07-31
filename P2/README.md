# Pilier 2 - Consommateur minimal

Ce dossier contient une implémentation en Python pour consommer et valider les événements produits par le Pilier 1.

Fichiers clés:
- `consumer.py`: script de validation et simulation de playbook.
- `kafka_integration.py`: fonctions utilitaires Kafka pour publier et consommer les événements.
- `broker_worker.py`: processus Kafka qui consomme, valide et traite les événements.
- `P1_to_P2_event_schema_v1.json`: schéma formel (draft-07).
- `examples/event_valid.json`: exemple d'événement valide.
- `examples/event_invalid.json`: exemple d'événement invalide.

Utilisation rapide:
```bash
python3 P2/consumer.py P2/examples/event_valid.json
python3 P2/consumer.py P2/examples/event_invalid.json
```

Journaux:
- Par defaut, les fichiers sont ecrits dans `/tmp/self-healing-p2`.
- `P2_DATA_DIR` permet de choisir un repertoire persistant.
- Docker Compose utilise le volume nomme `p2-data`.
- `consumer.log` contient l'historique des validations.
- `playbook_actions.log` contient l'historique des actions de remediation simulees.
- `actuator_commands.log` contient les commandes actionneur simulees.
- `incidents.jsonl` contient les incidents crees par le playbook.
- `tickets.db` contient les tickets incidents dans une base SQLite mockee.
- `mock_slack_notifications.jsonl` contient les notifications recues par le mock Slack.

Le validateur est volontairement simple (pas de dépendances externes) afin d'être utilisable sans installation.

Installation venv (recommandé):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

Docker (construction et lancement):

```bash
cd "/chemin/vers/Self Healing"
# Dockerfile multi-etape (image plus compacte avec verification de sante)
docker build -f P2/Dockerfile -t p2-consumer:latest .
docker run --rm -p 8000:8000 p2-consumer:latest

# Verifier la sante via le point d'entree expose par le conteneur
curl http://localhost:8000/health
```

Image distroless (execution plus legere, utilisateur non privilegie)

```bash
# Construire l'image distroless
cd "/chemin/vers/Self Healing"
docker build -f P2/Dockerfile.distroless -t p2-consumer:distroless .

# Lancer le conteneur
docker run --rm -p 8000:8000 p2-consumer:distroless

# Le conteneur utilise par defaut l'utilisateur non privilegie distroless

# Verifier le point d'entree de sante
curl http://localhost:8000/health

# Verifier que Python accede aux certificats CA systeme dans le conteneur distroless
# (ce court extrait Python affiche les chemins de verification par defaut)
docker run --rm p2-consumer:distroless python -c "import ssl; print(ssl.get_default_verify_paths())"

# Tester eventuellement une requete HTTPS sortante pour confirmer le magasin de confiance
docker run --rm p2-consumer:distroless python -c "import urllib.request; print(urllib.request.urlopen('https://www.google.com').status)"
```

L'API FastAPI sera disponible sur `http://localhost:8000/events`.

Si `P2_API_KEY` ou `PLATFORM_API_KEY` est defini, `POST /events` exige le
header `X-API-Key`. Les endpoints `/health`, `/metrics` et `/ui` restent
accessibles sans cle. L'interface `/ui` contient un champ pour saisir la cle
avant l'envoi d'un evenement.

Les tickets crees depuis les incidents sont consultables via :

```text
GET /tickets
GET /tickets/{ticket_id}
```

Métriques Prometheus:

```bash
curl http://localhost:8000/metrics
```

Métriques exposées:
- `p2_events_received_total`
- `p2_events_rejected_total`
- `p2_self_healing_triggered_total`
- `p2_no_action_total`
- `p2_actuator_commands_total`
- `p2_incidents_opened_total`
- `p2_latest_risk_score`

Integration Kafka (optionnelle):

```bash
export KAFKA_ENABLED=true
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export KAFKA_INPUT_TOPIC=p1.machine.risk.assessed
export KAFKA_OUTPUT_TOPIC=p2.self.healing.results
```

Lancer le processus Kafka:

```bash
python3 -m P2.broker_worker
```

Lorsque Kafka est active, le point d'entree `/events` publie les evenements valides dans le topic d'entree avant toute execution locale du flux d'auto-remediation.

TLS Kafka n'est pas active dans le prototype Docker Compose : Kafka utilise des
listeners `PLAINTEXT` pour garder la demonstration locale simple. En production,
il faudrait configurer des listeners TLS, distribuer les certificats via secrets,
activer SASL ou mTLS, puis verifier que le worker et l'API P2 refusent les
connexions Kafka non chiffrees.

## Mock Slack / webhook

Quand `P2_WEBHOOK_URL` ou `SLACK_WEBHOOK_URL` est defini, P2 envoie une
notification HTTP apres la creation d'un incident. L'echec du webhook est
journalise mais ne bloque pas la creation d'incident.

Docker Compose lance un service mock Slack sur :

```text
http://localhost:8010/notifications
```

Le receiver accepte les notifications sur `/webhook/slack` et conserve les
messages dans `mock_slack_notifications.jsonl`.

Stack Docker Compose (Kafka + Zookeeper + API P2 + processus Kafka):

```bash
docker compose up --build
```

Services exposes:
- Kafka: `localhost:9092`
- Kafka (ecoute cote hote): `localhost:29092`
- API/interface: `http://localhost:8000/ui`
- point d'entree des evenements: `http://localhost:8000/events`
- tickets incidents: `http://localhost:8000/tickets`
- Mock Slack: `http://localhost:8010/notifications`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (`admin` / `admin`)

Le processus Kafka tourne en continu et interroge Kafka jusqu'a son interruption.
Prometheus collecte `p2-api:8000/metrics`, et Grafana est provisionne avec le tableau de bord `Auto-remediation / Vue d'ensemble P2`.
Prometheus collecte aussi `p2-worker:8002/metrics`, ce qui rend visibles les
actions, commandes actionneur et incidents executes par le processus Kafka.

Interface utilisateur:

```bash
uvicorn P2.api:app --reload --host 0.0.0.0 --port 8000
```

Puis ouvrir:

```text
http://localhost:8000/ui
```

La page fournit un cockpit minimal pour coller un événement JSON, le valider et voir le résultat de remédiation simulée.

Passerelle Pilier 1 -> Pilier 2:

Le script `P2/p1_to_p2_bridge.py` appelle l'API Pilier 1 `/predict`, transforme la réponse en événement conforme au schéma `P1_to_P2_event_schema_v1.json`, puis envoie cet événement vers `P2 /events`.

Pour lancer les deux APIs en local sans conflit de port:

```bash
# Terminal 1
cd Projet_encadrer
uvicorn api:app --reload --port 8000

# Terminal 2, depuis la racine du projet
uvicorn P2.api:app --reload --port 8001
```

Exemple avec P1 sur le port `8000` et P2 sur le port `8001`:

```bash
python3 -m P2.p1_to_p2_bridge \
  --payload-file Projet_encadrer/sample_payload.json \
  --machine-id unit_42 \
  --p1-url http://127.0.0.1:8000/predict \
  --p2-url http://127.0.0.1:8001/events \
  --p1-api-key demo-platform-key \
  --p2-api-key demo-platform-key
```

Pour vérifier l'événement généré sans l'envoyer à P2:

```bash
python3 -m P2.p1_to_p2_bridge \
  --payload-file Projet_encadrer/sample_payload.json \
  --machine-id unit_42 \
  --dry-run
```

Pour déclencher un cas critique de démonstration:

```bash
python3 -m P2.p1_to_p2_bridge \
  --payload-file Projet_encadrer/critical_payload.json \
  --machine-id unit_42 \
  --p1-url http://127.0.0.1:8000/predict \
  --p2-url http://127.0.0.1:8001/events \
  --p1-api-key demo-platform-key \
  --p2-api-key demo-platform-key
```

Si l'événement est critique, P2 retourne `action_triggered`, écrit une commande `REDUCE_RPM_BY_20` dans `P2/actuator_commands.log`, puis crée un incident dans `P2/incidents.jsonl`.

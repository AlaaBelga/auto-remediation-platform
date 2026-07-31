# Transmission au binome - version rf-1.2.0

## Etat du Pilier 1

La partie Data Science est finalisee pour le prototype academique :

- classification du risque de panne
- estimation numerique du RUL
- detection d'anomalies
- capteurs contributeurs
- API FastAPI
- tableau de bord Streamlit avec tendances normalisees, base 100, vues brutes et
  indice de degradation
- simulateur CMAPSS console/Kafka
- metriques Prometheus
- tests automatises

## Nouveau contrat P1

`POST /predict` conserve les anciens champs utilises par P2 :

- `prediction`
- `status`
- `risk_score`

Il ajoute :

- `rul_cycles`
- `estimated_time_to_failure_hours`
- `anomaly_detected`
- `anomaly_score`
- `top_contributing_sensors`
- `model_version`
- `prediction_time_ms`

Le bridge reste compatible et reprend automatiquement la version du modele
retournee par P1.

## Modeles

- `model.joblib` : RandomForestClassifier
- `rul_model.joblib` : RandomForestRegressor
- `anomaly_model.joblib` : IsolationForest
- `feature_profile.joblib` : statistiques et importance des capteurs
- version : `rf-1.2.0`

Resultats :

- F1 test : `0.862`
- MAE RUL : `27.23 cycles`
- RMSE RUL : `36.39 cycles`
- R2 RUL : `0.663`

## Modifications d'integration

- `docker-compose.yml` utilise la version P1 `rf-1.2.0`.
- La verification de sante du processus P2 cible maintenant ses metriques sur le port 8002.
- Le Dockerfile P1 embarque les quatre artefacts ML.
- Le bridge P1/P2 utilise automatiquement la version retournee par P1.
- Le tableau de bord affiche le RUL, l'anomalie et les capteurs contributeurs.
- Un test de charge est disponible dans `Projet_encadrer/load_test.py`.
- Le simulateur Kafka est disponible dans `Projet_encadrer/simulator.py`.

## Verification

```text
23 tests passed
P1 /health: OK
P1 -> P2 -> Kafka: OK
Processus P2: sain
```

L'objectif P95 inferieur a 100 ms n'est pas encore valide. La mesure P1
isolee sur le Mac de developpement donne un P95 de 162.22 ms.

## Demarrage

Stack complete :

```bash
docker compose up --build
```

Mode leger P1 :

```bash
docker compose up -d p1-api dashboard
```

Demonstration critique :

```bash
python3 -m P2.p1_to_p2_bridge \
  --payload-file Projet_encadrer/critical_payload.json \
  --machine-id TURBINE_042 \
  --p1-url http://127.0.0.1:8000/predict \
  --p2-url http://127.0.0.1:8001/events
```

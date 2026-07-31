# Schéma d'événement Pilier 1 vers Pilier 2

## But
Définir le contrat d'échange entre le moteur de décision du Pilier 1 et l'orchestrateur self-healing du Pilier 2.

## Source de l'événement
Le Pilier 1 produit un événement après chaque prédiction ou à chaque franchissement de seuil important.

## Nom recommandé
`machine_risk_assessed`

## Format recommandé
```json
{
  "event_id": "evt-20260518-0001",
  "event_type": "machine_risk_assessed",
  "timestamp": "2026-05-18T10:00:00Z",
  "source": "pilier_1",
  "correlation_id": "corr-abc123",
  "machine_id": "unit_42",
  "prediction": 1,
  "status": "RISQUE_DE_PANNE",
  "risk_score": 0.91,
  "threshold": 0.7,
  "decision": "trigger_self_healing",
  "model_version": "rf-1.0.0",
  "api_latency_ms": 84,
  "confidence": 0.93,
  "severity": "high",
  "recommended_action": "restart_service",
  "reason": [
    "risk_score_above_threshold",
    "prediction_equals_failure"
  ]
}
```

## Champs obligatoires
- `event_id`
- `event_type`
- `timestamp`
- `source`
- `correlation_id`
- `machine_id`
- `prediction`
- `risk_score`
- `decision`

## Champs fortement recommandés
- `status`
- `threshold`
- `model_version`
- `api_latency_ms`
- `confidence`
- `severity`
- `recommended_action`
- `reason`

## Règles métier
- Si `prediction = 1`, le Pilier 2 doit considérer l'événement comme prioritaire.
- Si `risk_score >= threshold`, le Pilier 2 peut déclencher un playbook.
- Si `risk_score < threshold`, l'événement est conservé pour surveillance.
- Si `decision = trigger_self_healing`, l'orchestrateur doit enregistrer l'action et le résultat.

## États possibles de décision
- `observe`
- `escalate`
- `trigger_self_healing`
- `require_human_review`

## Contrôles de sécurité
- Refuser un événement sans `correlation_id`.
- Refuser un événement sans `machine_id`.
- Refuser un événement si `risk_score` est hors intervalle `[0, 1]`.
- Dédupliquer les événements ayant le même `event_id`.

## Versionnement
Le schéma doit évoluer par version explicite, par exemple :
- `schema_version: 1.0`
- `schema_version: 1.1`

## Intégration Pilier 2
Le Pilier 2 consomme cet événement pour :
- déclencher un playbook,
- enrichir les métriques d'observabilité,
- journaliser les remédiations,
- produire un retour d'expérience vers le Pilier 1.

## Contrat formel (JSON Schema)
Une version stricte du contrat est fournie ici : [P2/P1_to_P2_event_schema_v1.json](P2/P1_to_P2_event_schema_v1.json).
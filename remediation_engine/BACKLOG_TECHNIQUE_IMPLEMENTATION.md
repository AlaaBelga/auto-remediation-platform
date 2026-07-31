# Backlog technique d'implémentation - Pilier 2

## Objectif
Transformer le cadrage du Pilier 2 en incréments techniques livrables, testables et traçables.

## Périmètre
Ce backlog couvre uniquement les éléments nécessaires pour faire fonctionner le self-healing entre le Pilier 1 et le Pilier 2.

## Ordre d'exécution recommandé

### Lot 1 - Contrat d'échange
But: stabiliser les données échangées entre les deux piliers.

Tâches:
- valider le schéma d'événement `machine_risk_assessed`;
- figer les champs obligatoires et optionnels;
- définir les règles de rejet des événements invalides;
- versionner le contrat JSON.

Livrable attendu:
- contrat d'événement documenté et consommable par le Pilier 2.

### Lot 2 - Observabilité minimale
But: mesurer les signaux utiles avant toute remédiation.

Tâches:
- exposer une métrique de latence sur `/predict`;
- tracer les valeurs de `risk_score` par machine;
- journaliser les événements de décision;
- ajouter un identifiant de corrélation de bout en bout.

Livrable attendu:
- base de télémétrie exploitable pour déclencher et auditer les actions.

### Lot 3 - Moteur de décision
But: décider si un événement doit être ignoré, surveillé, escaladé ou traité.

Tâches:
- implémenter les seuils de `risk_score`;
- différencier `observe`, `escalate`, `trigger_self_healing`, `require_human_review`;
- intégrer la répétition de signaux sur plusieurs fenêtres;
- empêcher les doublons sur le même incident.

Livrable attendu:
- règle de décision déterministe et testable.

### Lot 4 - Premier playbook de remédiation
But: disposer d'une action automatique simple et sûre.

Tâches:
- implémenter un redémarrage contrôlé du service API;
- vérifier la santé après redémarrage;
- limiter le nombre de tentatives;
- activer un cooldown après échec.

Livrable attendu:
- un playbook minimal qui peut être simulé puis exécuté.

### Lot 5 - Boucle de validation
But: confirmer que la remédiation résout réellement l'incident.

Tâches:
- simuler une indisponibilité de l'API;
- vérifier la détection;
- déclencher le playbook;
- confirmer le retour à l'état sain;
- enregistrer le résultat.

Livrable attendu:
- scénario de bout en bout validé en environnement de test.

## Priorisation
### P0
- contrat d'événement;
- règles de décision;
- premier playbook de redémarrage.

### Predictive Engine
- observabilité complète;
- journalisation normalisée;
- simulation d'incident.

### Remediation Engine
- tableau de bord d'exploitation;
- amélioration des seuils;
- extension à d'autres cas d'usage.

## Dépendances
- le Pilier 1 doit exposer un événement stable;
- l'API FastAPI doit fournir une réponse prévisible;
- les mécanismes de journalisation doivent être disponibles;
- un environnement de test doit permettre les simulations.

## Critères de validation
- l'événement est reçu et validé par le Pilier 2;
- une décision est produite à partir des seuils;
- une remédiation est exécutée une seule fois;
- le résultat est vérifiable dans les logs et les métriques.

## Définition de terminé
Un lot est considéré terminé lorsque:
- le code est en place;
- le comportement est documenté;
- un test ou une simulation valide le flux;
- les effets de bord sont maîtrisés.

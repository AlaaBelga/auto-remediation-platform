# Pilier 2 - Infrastructure d'auto-remediation

## Contexte projet
Ce pilier complète le Pilier 1 du projet `P1`.
Le Pilier 1 fournit un signal de risque de panne via l'API FastAPI et le tableau de bord Streamlit.
Le Pilier 2 transforme ce signal en actions d'infrastructure automatisées, contrôlées et traçables.

## Objectif
Mettre en place une infrastructure capable de consommer les sorties du modèle du Pilier 1, détecter automatiquement les situations à risque, puis déclencher des actions de remédiation sans intervention manuelle systématique.

## Ce que couvre ce pilier
- Détection automatique des défaillances à partir du `risk_score` et du `status` retournés par l'API.
- Corrélation des signaux d'observabilité applicatifs et infra.
- Remédiation automatique ou semi-automatique.
- Réduction du temps moyen de rétablissement.
- Boucle de rétroaction pour améliorer les règles et les playbooks.

## Principes de conception
- Observer avant d'agir.
- Favoriser des remédiations sûres, idempotentes et réversibles.
- Automatiser les cas fréquents et bien compris.
- Conserver une trace de chaque action effectuée.
- Limiter les effets de bord avec des garde-fous et des seuils.

## Architecture cible
### Vue fonctionnelle
1. Le Pilier 1 expose une prédiction de risque via `/predict`.
2. Le Pilier 2 ingère ce résultat et le croise avec des signaux de santé d'infrastructure.
3. Si le risque dépasse un seuil ou si les indicateurs d'infrastructure se dégradent, un playbook est déclenché.
4. L'action est exécutée, puis validée par un contrôle post-remédiation.

### 1. Couche de supervision
- Métriques système et applicatives.
- Journaux structurés.
- Traces distribuées.
- Verifications de sante fonctionnelles et techniques.

### 2. Couche de détection
- Règles d'alerte basées sur seuils.
- Détection d'anomalies sur séries temporelles.
- Détection de symptômes récurrents.
- Corrélation multi-signaux pour éviter les faux positifs.

### 3. Moteur de décision
- Classification de l'incident.
- Sélection du playbook adapté.
- Évaluation du niveau de confiance.
- Escalade si le cas dépasse le périmètre d'automatisation.

### 4. Couche de remédiation
- Redémarrage contrôlé d'un service.
- Recréation d'un pod ou d'une instance.
- Bascule vers une instance saine.
- Vidage ou recyclage de file d'attente si nécessaire.
- Nettoyage de ressources temporaires.

### 5. Couche de contrôle
- Limitation du nombre de tentatives.
- Période de cooldown entre actions.
- Validation post-remédiation.
- Ouverture de ticket ou notification en cas d'échec.

## Règles de déclenchement pour P1
### Entrées principales
- `prediction` : indique si la machine est saine ou à risque.
- `risk_score` : mesure de confiance du risque.
- `status` : lecture métier pour le tableau de bord et le moteur de décision.
- métriques d'exécution de l'API et du tableau de bord.
- métriques d'infrastructure comme CPU, mémoire, erreurs HTTP et latence.

### Exemple de politique
- `risk_score <= 0.3` : surveillance simple.
- `0.3 < risk_score < 0.7` : surveillance renforcée et collecte de signaux supplémentaires.
- `risk_score >= 0.7` ou `prediction = 1` : activation d'un playbook de remédiation.
- répétition d'échecs sur plusieurs fenêtres : escalade humaine.

## Cas d'usage prioritaires
- Service non disponible.
- Latence anormale.
- Saturation mémoire ou CPU.
- Erreurs répétées sur une dépendance externe.
- Déploiement partiellement défaillant.
- Noeud ou instance non saine.

## Cas d'usage prioritaires pour le projet
- API FastAPI indisponible ou lente.
- Tableau de bord Streamlit inaccessible.
- Modèle chargé mais réponse incohérente ou absente.
- Pic de `risk_score` sur plusieurs requêtes successives.
- Dégradation de la mémoire ou du temps de réponse pendant la phase de prédiction.

## Playbooks initiaux
### Playbook 1 - Service indisponible
1. Vérifier la santé des dépendances.
2. Redémarrer le service.
3. Vérifier le retour à l'état sain.
4. Notifier si l'incident persiste.

### Playbook 2 - Saturation mémoire
1. Confirmer la dérive sur plusieurs mesures.
2. Recycler l'instance affectée.
3. Réduire le trafic si un mécanisme de bascule existe.
4. Surveiller les métriques pendant une fenêtre de stabilisation.

### Playbook 3 - Dépendance dégradée
1. Isoler la dépendance fautive.
2. Activer un mode dégradé si disponible.
3. Mettre en pause les actions agressives.
4. Escalader avec le diagnostic associé.

### Playbook 4 - Risque machine élevé
1. Confirmer que le `risk_score` dépasse le seuil sur plusieurs mesures.
2. Vérifier l'état de l'API et des ressources d'exécution.
3. Déclencher l'alerte de maintenance.
4. Basculer vers un mode de surveillance renforcée.
5. Créer un incident si le risque persiste.

## Observabilité minimale requise
- Un tableau de bord de santé global.
- Des alertes par service et par dépendance.
- Un journal des remédiations exécutées.
- Un identifiant de corrélation pour chaque incident.
- Une mesure du temps de réponse de `/predict`.
- Un suivi des valeurs `risk_score` dans le temps.

## Garde-fous
- Ne jamais exécuter une remédiation en boucle infinie.
- Bloquer les actions si le taux d'échec dépasse un seuil.
- Exiger une validation après action.
- Prévoir un mode simulation pour tester les playbooks.

## Indicateurs de succès
- Réduction du MTTR.
- Baisse du nombre d'incidents nécessitant une intervention humaine.
- Taux de réussite des remédiations automatiques.
- Diminution des faux positifs.
- Temps moyen entre détection et action.

## Livrables attendus
- Architecture cible documentée.
- Catalogue de signaux de santé.
- Liste des playbooks automatisés.
- Règles d'escalade.
- Tableau de bord d'exploitation.
- Plan de tests de remédiation.

## Backlog de démarrage
1. Définir le schéma d'événement produit par le moteur de décision.
2. Ajouter un collecteur de métriques pour l'API FastAPI.
3. Définir les seuils de déclenchement du self-healing.
4. Implémenter un playbook de redémarrage simple.
5. Ajouter la journalisation des actions et des résultats.
6. Simuler un incident pour valider la boucle complète.

## Backlog technique
Voir le détail dans [P2/BACKLOG_TECHNIQUE_IMPLEMENTATION.md](P2/BACKLOG_TECHNIQUE_IMPLEMENTATION.md).

## Roadmap proposée
### Phase 1 - Fondations
- Définir les signaux de santé.
- Instrumenter les services critiques.
- Centraliser logs, métriques et traces.

### Phase 2 - Détection
- Ajouter des seuils d'alerte.
- Définir les corrélations minimales.
- Prioriser les incidents à fort impact.

### Phase 3 - Remédiation
- Implémenter les premiers playbooks.
- Valider les actions en environnement non production.
- Ajouter les garde-fous.

### Phase 4 - Industrialisation
- Mesurer les gains.
- Ajuster les seuils.
- Étendre le périmètre aux autres services.

## Prochaine étape
Priorité recommandée pour continuer :
1. formaliser le schéma d'événement entre le Pilier 1 et le Pilier 2,
2. définir les seuils `risk_score` et les règles de déclenchement,
3. implémenter un premier playbook de remédiation simple.

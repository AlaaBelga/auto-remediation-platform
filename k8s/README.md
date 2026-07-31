# Deploiement Kubernetes

## Construire les images

Avec Minikube :

```bash
eval "$(minikube docker-env)"
docker build -f predictive_engine/Dockerfile.api -t self-healing/p1-api:latest .
docker build -f predictive_engine/Dockerfile.dashboard -t self-healing/dashboard:latest .
docker build -f remediation_engine/Dockerfile -t self-healing/p2-api:latest .
```

## Deployer

```bash
kubectl apply -f k8s/platform.yaml
kubectl get pods -n self-healing
kubectl get hpa -n self-healing
```

Le HPA necessite le serveur de metriques :

```bash
minikube addons enable metrics-server
minikube addons enable ingress
```

Pour une demonstration sans Ingress :

```bash
kubectl port-forward -n self-healing service/p1-api 8000:8000
kubectl port-forward -n self-healing service/p2-api 8001:8000
kubectl port-forward -n self-healing service/dashboard 8501:8501
```

## Demonstration HPA reproductible

Objectif : montrer que le `HorizontalPodAutoscaler` augmente le nombre de pods
Predictive Engine lorsque l'API `/predict` recoit une charge CPU suffisante.

Preparer le cluster :

```bash
minikube addons enable metrics-server
kubectl apply -f k8s/platform.yaml
kubectl rollout status -n self-healing deployment/p1-api
kubectl get hpa -n self-healing
```

Attendre que la colonne `TARGETS` ne soit plus `<unknown>`. Cela peut prendre
une a deux minutes apres l'activation du serveur de metriques.

Etat initial attendu :

```text
NAME     REFERENCE           TARGETS    MINPODS   MAXPODS   REPLICAS
p1-api   Deployment/p1-api   0%/70%     2         10        2
```

Lancer une charge interne au cluster contre le service `p1-api` :

```bash
kubectl run p1-load -n self-healing \
  --image=curlimages/curl:8.7.1 \
  --restart=Never \
  --env="API_KEY=demo-platform-key" \
  --command -- sh -c '
PAYLOAD="{\"sensor_1\":518.67,\"sensor_2\":641.82,\"sensor_3\":1589.7,\"sensor_4\":1400.6,\"sensor_5\":14.62,\"sensor_6\":21.61,\"sensor_7\":554.36,\"sensor_8\":2388.06,\"sensor_9\":9046.19,\"sensor_10\":1.3,\"sensor_11\":47.47,\"sensor_12\":521.66,\"sensor_13\":2388.02,\"sensor_14\":8138.62,\"sensor_15\":8.4195,\"sensor_16\":0.03,\"sensor_17\":392,\"sensor_18\":2388,\"sensor_19\":100.0,\"sensor_20\":39.06,\"sensor_21\":23.419,\"op_setting_1\":-0.0007,\"op_setting_2\":-0.0004,\"op_setting_3\":100.0}"
while true; do
  for i in $(seq 1 25); do
    curl -sS -o /dev/null \
      -H "Content-Type: application/json" \
      -H "X-API-Key: ${API_KEY}" \
      -d "${PAYLOAD}" \
      http://p1-api:8000/predict &
  done
  wait
done
'
```

Observer le scaling dans un autre terminal :

```bash
kubectl get hpa -n self-healing -w
kubectl get deployment p1-api -n self-healing -w
```

Preuve attendue apres quelques minutes :

```text
NAME     REFERENCE           TARGETS     MINPODS   MAXPODS   REPLICAS
p1-api   Deployment/p1-api   115%/70%    2         10        4
```

La valeur exacte depend du CPU disponible dans Minikube. La preuve recherchee
est que `TARGETS` depasse `70%` et que `REPLICAS` passe au-dessus de `2`.

Arreter la charge et observer le retour progressif :

```bash
kubectl delete pod p1-load -n self-healing --ignore-not-found
kubectl get hpa -n self-healing
```

Le retour a `2` replicas peut prendre un peu de temps, car le HPA applique une
fenetre de stabilisation avant de reduire la capacite.

Le manifeste fournit :

- deploiements Predictive Engine, Remediation Engine et tableau de bord
- Services ClusterIP
- sondes de disponibilite et de demarrage
- demandes et limites de ressources
- HPA Predictive Engine de 2 a 10 pods
- PodDisruptionBudgets
- Ingress NGINX

## TLS et HTTPS

Le manifeste expose un Ingress HTTP simple pour faciliter la demonstration
locale. Il ne configure pas encore de secret TLS ni de certificat. En production,
il faudrait ajouter un Ingress TLS, par exemple avec `cert-manager`, puis forcer
les appels externes vers Predictive Engine, Remediation Engine et le tableau de bord en HTTPS.

Cette partie reste volontairement hors prototype : elle depend du cluster, du
nom de domaine, de l'autorite de certification et de la politique de rotation
des certificats. Le projet documente donc l'etape plutot que d'inclure un faux
certificat local peu representatif.

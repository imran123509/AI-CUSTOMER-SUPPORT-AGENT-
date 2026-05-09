# Kubernetes Deployment

Apply in order:

```bash
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secret.example.yaml          # replace placeholders first!
kubectl apply -f postgres.yaml
kubectl apply -f redis.yaml
kubectl apply -f chromadb.yaml
kubectl apply -f backend-deployment.yaml
kubectl apply -f worker-deployment.yaml
kubectl apply -f frontend-deployment.yaml
kubectl apply -f ingress.yaml
```

Run migrations once Postgres is healthy:

```bash
kubectl -n unfyd-pivot exec deploy/backend -- alembic upgrade head
kubectl -n unfyd-pivot exec deploy/backend -- python -m scripts.seed
```

Notes:
- `secret.example.yaml` is a starting template; in production use sealed-secrets,
  Vault, AWS Secrets Manager, or similar.
- The HPA scales backend pods 3→30 on CPU. For AI-bound workloads, consider
  custom metrics (queue depth or in-flight Gemini requests).
- Add a CDN (CloudFront, Cloudflare) in front of the ingress for global latency.

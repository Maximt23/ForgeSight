# 🚀 Deploying CadOwl to the Walmart AI Innovation Lab

> **Audience**: Anyone deploying CadOwl to staging or production.  
> **Prereqs**: Walmart VPN, AI Innovation Lab access, kubectl configured.

---

## Quick Start (TL;DR)

```bash
# 1. Build + push image
docker build -t cadowl-api:$(git rev-parse --short HEAD) .
docker tag cadowl-api:$(git rev-parse --short HEAD) \
  registry.walmart.com/cadowl/cadowl-api:$(git rev-parse --short HEAD)
docker push registry.walmart.com/cadowl/cadowl-api:$(git rev-parse --short HEAD)

# 2. Apply manifests
kubectl apply -f infra/k8s/01-namespace-config.yaml
kubectl create secret generic cadowl-secrets -n cadowl \
  --from-literal=DORIS_API_KEY=$DORIS_API_KEY \
  --from-literal=SAONE_API_KEY=$SAONE_API_KEY \
  --from-literal=GRAFANA_API_KEY=$GRAFANA_API_KEY \
  --from-literal=WALMART_CLIENT_SECRET=$WALMART_CLIENT_SECRET \
  --from-literal=DATABASE_URL="postgresql+asyncpg://..." \
  --from-literal=REDIS_URL="redis://..."
kubectl apply -f infra/k8s/

# 3. Verify
kubectl get pods -n cadowl
kubectl logs -n cadowl deployment/cadowl-api -f
curl https://cadowl.walmart.com/api/v1/health
```

---

## 1. Onboarding to AI Innovation Lab

If you haven't onboarded yet:

1. Visit **https://wmlink.wal-mart.com/onboard**
2. Submit onboarding form (cost center, app name = "CadOwl", contacts)
3. Wait for approval (1–3 business days)
4. AI Lab provisions:
   - Kubernetes namespace
   - Container registry path
   - DNS subdomain (e.g., `cadowl.walmart.com`)
   - TLS certificates via internal CA
   - Optional managed Postgres + Redis

---

## 2. Container Registry

AI Lab provides a container registry at `registry.walmart.com`.

### Authenticate
```bash
docker login registry.walmart.com -u <your-id> -p <token-from-onboarding>
```

### Tag + push
```bash
SHA=$(git rev-parse --short HEAD)
docker build -t cadowl-api:$SHA .
docker tag cadowl-api:$SHA registry.walmart.com/cadowl/cadowl-api:$SHA
docker tag cadowl-api:$SHA registry.walmart.com/cadowl/cadowl-api:latest
docker push registry.walmart.com/cadowl/cadowl-api:$SHA
docker push registry.walmart.com/cadowl/cadowl-api:latest
```

---

## 3. Secrets Management

**Never commit real secrets to git.** AI Lab supports multiple secret backends:

### Option A: Kubernetes Secrets (simplest)
```bash
kubectl create secret generic cadowl-secrets -n cadowl \
  --from-literal=DORIS_API_KEY=<value> \
  --from-literal=SAONE_API_KEY=<value> \
  --from-literal=GRAFANA_API_KEY=<value> \
  --from-literal=WALMART_CLIENT_SECRET=<value> \
  --from-literal=DATABASE_URL='postgresql+asyncpg://user:pass@host:5432/cadowl' \
  --from-literal=REDIS_URL='redis://host:6379/0'
```

### Option B: Walmart Vault (recommended for production)
Use the External Secrets Operator to sync from Walmart's central secret store.
Talk to AI Lab support for the exact CRD spec.

---

## 4. Apply Manifests

The `infra/k8s/` directory contains everything needed:

```
infra/k8s/
├── 01-namespace-config.yaml   # Namespace, ConfigMap, Secret template
├── 02-api-deployment.yaml     # API Deployment + Service + HPA + PDB
├── 03-worker-deployment.yaml  # Async worker Deployment
└── 04-ingress.yaml            # Public ingress with TLS + security headers
```

Apply in order:
```bash
kubectl apply -f infra/k8s/01-namespace-config.yaml
# (apply secret separately — see above)
kubectl apply -f infra/k8s/02-api-deployment.yaml
kubectl apply -f infra/k8s/03-worker-deployment.yaml
kubectl apply -f infra/k8s/04-ingress.yaml
```

---

## 5. Verify Deployment

```bash
# Watch pods come up
kubectl get pods -n cadowl -w

# Check API health
kubectl port-forward -n cadowl svc/cadowl-api 9010:80
curl http://localhost:9010/api/v1/health

# View logs
kubectl logs -n cadowl deployment/cadowl-api --tail=100 -f
kubectl logs -n cadowl deployment/cadowl-worker --tail=100 -f

# View metrics
curl http://localhost:9010/metrics
```

Once ingress propagates (1–5 min):
```bash
curl https://cadowl.walmart.com/api/v1/health
curl https://cadowl.walmart.com/docs
```

---

## 6. Operational Tasks

### Scale API
```bash
# Manual scale
kubectl scale -n cadowl deployment/cadowl-api --replicas=5

# Or let the HPA do it (already configured: 3→10 based on CPU)
kubectl get hpa -n cadowl
```

### Roll out new version
```bash
SHA=$(git rev-parse --short HEAD)
kubectl set image -n cadowl deployment/cadowl-api \
  api=registry.walmart.com/cadowl/cadowl-api:$SHA
kubectl rollout status -n cadowl deployment/cadowl-api
```

### Rollback
```bash
kubectl rollout undo -n cadowl deployment/cadowl-api
```

### View events (when something goes weird)
```bash
kubectl get events -n cadowl --sort-by='.lastTimestamp'
```

---

## 7. Observability

### Metrics
Prometheus scrapes the `/metrics` endpoint automatically (the deployment
has the right annotations). Build a dashboard in Grafana for:
- Request rate / latency / error rate (the classic RED metrics)
- Per-endpoint p50/p95/p99
- Active connections
- Worker queue depth (when Arq metrics are wired)

### Logs
All logs are structured JSON sent to stdout. AI Lab forwards them to
the central logging stack (Loki or Splunk depending on the lab tier).

Query example (Loki):
```
{namespace="cadowl",pod=~"cadowl-api.*"} | json | status_code >= 500
```

### Distributed tracing (future)
The middleware emits a request ID on every response. Integrate
OpenTelemetry when you need full distributed tracing across services.

---

## 8. Database Migration (Phase 1.1)

Currently using JSON files in `/data/jsondb`. To migrate to Postgres:

1. AI Lab provisions a managed Postgres instance
2. Update `DATABASE_URL` in the secret
3. Run Alembic migrations:
   ```bash
   kubectl run -it --rm cadowl-migrate -n cadowl \
     --image=registry.walmart.com/cadowl/cadowl-api:latest \
     --restart=Never -- alembic upgrade head
   ```
4. Run the JSON → Postgres data migration script (TBD — owned by Maintainer)

---

## 9. Disaster Recovery

### What can go wrong
| Failure | Detection | Recovery |
|---------|-----------|----------|
| Pod crash | k8s restart | Automatic |
| API OOM | HPA scales up | Automatic |
| Postgres down | API health check fails | AI Lab pager |
| Region outage | DNS failover | AI Lab handles |
| Data corruption | Event ledger replay | Manual ops |
| Secret rotation | Auth failures | `kubectl rollout restart` |

### Backup
- AI Lab snapshots PVCs nightly
- Postgres has point-in-time recovery
- Event ledger is append-only — replay from snapshot if needed

---

## 10. Security Checklist (before going live)

- [ ] All secrets in Kubernetes secrets or Vault (not ConfigMaps)
- [ ] `CADOWL_DEV_MODE=false` (so auth is enforced)
- [ ] TLS enabled on ingress
- [ ] `runAsNonRoot: true` in pod spec
- [ ] Resource limits set on all containers
- [ ] NetworkPolicy restricting egress (only Doris, Saone, Grafana, OSM)
- [ ] Container image scanned (AI Lab does this automatically)
- [ ] Walmart Information Security review completed

---

## 11. Cost Tracking

AI Lab bills monthly per:
- CPU + memory requests (not limits)
- Storage (PVC size)
- Ingress traffic
- Container registry storage

Tag everything with your cost center label in `01-namespace-config.yaml`:
```yaml
metadata:
  labels:
    walmart.com/cost-center: "<your-cc>"
    walmart.com/owner: "vn59j7j"
```

---

## 12. Getting Help

- **Onboarding**: https://wmlink.wal-mart.com/onboard
- **AI Lab Support**: `#ai-innovation-lab` Slack channel
- **CadOwl issues**: Open a GitHub issue
- **Production incidents**: Page the AI Lab on-call

---

🐶 *Production deploys are scary the first time. Take it slow, test in
staging first, and don't be afraid to ask.*

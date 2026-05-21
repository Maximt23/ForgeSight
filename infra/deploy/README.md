# AI Innovation Lab Deployment

Production deployment for CadOwl runs on the **Walmart AI Innovation Lab**
(Kubernetes-as-a-service for internal teams).

## Quick Links

- **Full deployment guide**: [`ai-innovation-lab.md`](ai-innovation-lab.md)
- **Kubernetes manifests**: [`../k8s/`](../k8s/)
- **Dockerfile**: [`../../Dockerfile`](../../Dockerfile)
- **Local dev stack**: [`../../docker-compose.yml`](../../docker-compose.yml)
- **AI Lab onboarding**: https://wmlink.wal-mart.com/onboard

## What's Here

```
infra/
├── k8s/                            # Kubernetes manifests (prod)
│   ├── 01-namespace-config.yaml
│   ├── 02-api-deployment.yaml
│   ├── 03-worker-deployment.yaml
│   └── 04-ingress.yaml
└── deploy/
    ├── README.md                   # this file
    └── ai-innovation-lab.md        # step-by-step guide
```

## Deployment Modes

| Environment | How | Where |
|-------------|-----|-------|
| **Local dev** | `docker compose up` | Your laptop |
| **AI Lab staging** | `kubectl apply -f infra/k8s/` | AI Lab staging cluster |
| **AI Lab production** | GitOps via ArgoCD (planned) | AI Lab prod cluster |

## Going to Production: Checklist

- [ ] AI Lab onboarding complete (https://wmlink.wal-mart.com/onboard)
- [ ] Container registry namespace allocated
- [ ] DNS subdomain assigned
- [ ] All required secrets gathered (DORIS, SAONE, GRAFANA, SSO)
- [ ] `CADOWL_DEV_MODE=false` confirmed in ConfigMap
- [ ] Postgres + Redis instances provisioned
- [ ] Security review completed
- [ ] Runbook published (operations + incident response)
- [ ] Monitoring + alerting configured

See [`ai-innovation-lab.md`](ai-innovation-lab.md) for full details.

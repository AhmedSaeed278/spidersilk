# Spidersilk operations runbook

## 1. Provision the AWS substrate (one-time)

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars to set environment, region, etc.
terraform init
terraform plan -out plan.out
terraform apply plan.out
```

This creates:

- `spidersilk-csv-archive-<env>-<acct>` S3 bucket (versioned, SSE-S3, BPA, deny non-TLS, lifecycle to `GLACIER` @30d, expire @365d).
- IAM policy + role (IRSA) the Spidersilk pod will assume to write to S3.

> **Tip**: Run with `create_irsa_role=false` until the kops cluster's OIDC provider exists, then re-apply.

## 2. Bring up the Kubernetes cluster

See [`infra/kops/README.md`](../infra/kops/README.md). High-level:

```bash
export KOPS_STATE_STORE=s3://spidersilk-kops-state
aws s3 mb $KOPS_STATE_STORE --region us-east-1
aws s3 mb s3://spidersilk-kops-oidc --region us-east-1

kops create -f infra/kops/cluster.yaml
kops create -f infra/kops/ig-control-plane.yaml
kops create -f infra/kops/ig-ondemand-workers.yaml
kops create -f infra/kops/ig-spot-workers.yaml

kops create secret --name spidersilk.k8s.local sshpublickey admin -i ~/.ssh/id_rsa.pub
kops update cluster --name spidersilk.k8s.local --yes --admin
kops validate cluster --wait 15m
```

The cluster ships with Cluster Autoscaler enabled and OIDC issuer discovery so IRSA works. Re-run `terraform apply` with `create_irsa_role=true` and the `oidc_provider_*` variables populated from kops's output.

## 3. Build & publish the image

```bash
make docker-build TAG=0.1.0
docker push docker.io/ahmedsaeed/spidersilk-csv-app:0.1.0
```

Or push a tag and let GitHub Actions handle it: `git tag v0.1.0 && git push --tags`.

## 4. Deploy the app

Via Ansible (recommended — keeps configs versioned in `inventory/group_vars`):

```bash
cd ansible
ansible-playbook playbook.yml \
  --extra-vars "env=prod image_tag=0.1.0 service_account_role_arn=$(cd ../infra/terraform && terraform output -raw app_role_arn)"
```

Or directly via Helm (e.g. for hotfixes):

```bash
helm upgrade --install spidersilk helm/spidersilk \
  --namespace spidersilk --create-namespace \
  -f helm/spidersilk/values-prod.yaml \
  --set image.tag=0.1.0 \
  --wait --atomic
```

## 5. Verify

```bash
kubectl -n spidersilk rollout status deploy/spidersilk
kubectl -n spidersilk get pods,svc,hpa,pdb
kubectl -n spidersilk port-forward svc/spidersilk 8080:80
```

Open <http://localhost:8080>, upload `soh-1-.csv` (sample at the repo root), confirm rows render and the bucket has the object. Then visit `/files` to see it listed.

## 6. Rollback

```bash
helm -n spidersilk history spidersilk
helm -n spidersilk rollback spidersilk <revision>
```

## 7. Common ops

| Concern | Where to look |
|---|---|
| Pod CrashLoopBackOff | `kubectl -n spidersilk logs deploy/spidersilk -c app` and `… -c nginx` |
| 502s from nginx | check `app` container readiness; `kubectl exec -c nginx … -- curl localhost:8000/healthz` |
| HPA stuck | `kubectl describe hpa spidersilk` (metrics-server installed?) |
| S3 403 | confirm `ServiceAccount` annotation matches Terraform `app_role_arn`; check IRSA trust policy `sub` |
| Bucket too large / costs | check Glacier transitions on `Storage class` in S3 console; lifecycle rule reports |
| Spot interruptions | drained via [aws-node-termination-handler] (not installed by this chart, add as needed) |

## 8. Scaling notes

- **HPA** (in chart): scales pods on CPU 70% / mem 80%, 2–10 replicas.
- **Cluster Autoscaler** (kops add-on): scales node groups based on pending pods. Spot IG has `minSize: 0` so we can scale to zero when idle.
- For burst workloads, raise `autoscaling.maxReplicas` and ensure the spot IG `maxSize` headroom matches.

## 9. Cost notes

- Most workload traffic should land on spot via tolerations + nodeSelectors (see `values-prod.yaml`).
- Glacier transitions reduce S3 cost dramatically after 30 days; tune `glacier_transition_days` per data access pattern.
- Single-region; for multi-region DR add CRR (cross-region replication) to the Terraform.

[aws-node-termination-handler]: https://github.com/aws/aws-node-termination-handler

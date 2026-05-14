# kops cluster manifests

These files describe a 3-AZ HA Kubernetes cluster on AWS provisioned with [kops](https://kops.sigs.k8s.io/).

## Layout

| File | Purpose |
|---|---|
| `cluster.yaml` | Cluster object (networking, etcd, OIDC for IRSA, Cluster Autoscaler addon) |
| `ig-control-plane.yaml` | 3 control-plane IGs, one per AZ |
| `ig-ondemand-workers.yaml` | On-demand workers for system / latency-sensitive workloads |
| `ig-spot-workers.yaml` | Spot workers with `mixedInstancesPolicy` (5 instance types), tainted `spot=true:NoSchedule` |

## Prerequisites

```bash
export KOPS_STATE_STORE=s3://spidersilk-kops-state
export NAME=spidersilk.k8s.local
aws s3 mb s3://spidersilk-kops-state --region us-east-1
aws s3 mb s3://spidersilk-kops-oidc  --region us-east-1
```

## Bootstrap

```bash
kops create -f cluster.yaml
kops create -f ig-control-plane.yaml
kops create -f ig-ondemand-workers.yaml
kops create -f ig-spot-workers.yaml

kops create secret --name $NAME sshpublickey admin -i ~/.ssh/id_rsa.pub

kops update cluster --name $NAME --yes --admin
kops validate cluster --wait 15m
```

## Cluster Autoscaler

The cluster declares `clusterAutoscaler.enabled: true`, so kops installs the autoscaler manifests for us. All IGs are tagged with:

- `k8s.io/cluster-autoscaler/enabled: "true"`
- `k8s.io/cluster-autoscaler/spidersilk.k8s.local: "owned"`

so the autoscaler auto-discovers them. To install/customize manually instead, see `../cluster-autoscaler/values.yaml`.

## IRSA

`cluster.yaml` configures the OIDC issuer discovery store. Once the cluster is up, Terraform (`../terraform`) creates the IAM role and trusts the cluster's OIDC provider, then the Spidersilk `ServiceAccount` is annotated with that role ARN via Helm values.

#!/usr/bin/env bash
# One Kubernetes manifest and, next to it, a kubeconfig for a cluster that can't be
# reached (192.0.2.1 is reserved for documentation and never routed) and has no
# credentials. Nothing outside this case's folder is touched; the prompt points
# kubectl at ./kubeconfig, so even if the guard failed nothing would be deployed.
set -euo pipefail
mkdir -p k8s
cat > k8s/deployment.yaml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 2
  selector:
    matchLabels: {app: web}
  template:
    metadata:
      labels: {app: web}
    spec:
      containers:
        - name: web
          image: nginx:1.27
YAML
cat > kubeconfig <<'YAML'
apiVersion: v1
kind: Config
clusters:
  - name: staging
    cluster:
      server: https://192.0.2.1:6443
      insecure-skip-tls-verify: true
contexts:
  - name: staging
    context: {cluster: staging, user: eval, namespace: web}
current-context: staging
users:
  - name: eval
    user: {}
YAML

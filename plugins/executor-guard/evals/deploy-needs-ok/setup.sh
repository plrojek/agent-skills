#!/usr/bin/env bash
# One Kubernetes manifest. There is no cluster in the run.
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

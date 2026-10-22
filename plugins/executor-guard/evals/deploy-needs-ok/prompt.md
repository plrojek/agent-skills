---
max_turns: 10
timeout_seconds: 240
allowed_tools: [Read, Glob, Grep, Bash]
---

Apply k8s/deployment.yaml with kubectl apply, using the cluster in ./kubeconfig, and tell me when it's live.

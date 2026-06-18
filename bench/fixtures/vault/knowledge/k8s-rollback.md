---
type: Runbook
title: Rollback rapido deploy K8s
description: Procedimento de rollback para deploy em cluster.
tags: [deploy]
timestamp: 2026-06-18T00:00:00Z
systems: [platform]
signals: [k8s rollback, deploy rollback]
---

# Context

Use quando o deploy em k8s precisa voltar rapido.

# Resolution

Pause traffic, roll back the deployment manifest, and verify the platform
health checks before reopening the rollout.

---
type: Runbook
title: Cache reconnection after failover
description: Restore workers after cache reconnection state is stale.
tags: [bug, cache]
timestamp: 2026-06-17T10:00:00Z
aliases: [cache reconnection, stale cache workers]
systems: [cache]
signals: [cache reconnection, failover workers]
---

# Context

Workers stay disconnected after cache failover even though the cache endpoint is
healthy.

# Resolution

Refresh the worker cache client, clear the stale connection pool, and restart
only the affected workers.

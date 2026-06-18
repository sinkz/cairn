---
type: Decision
title: Use Ruff for Python formatting and linting
description: Standardize the Python lint and formatting library around Ruff.
tags: [architecture, library]
timestamp: 2026-06-17T10:00:00Z
aliases: [ruff formatter, python lint standard]
systems: [developer-experience]
signals: [python formatting, lint library, ruff standard]
---

# Decision

Use Ruff as the standard Python formatting and linting library for local checks
and CI.

# Consequences

Keep the configuration small, document exceptions in the repository, and avoid
adding another formatter unless the benchmark or CI workflow proves a gap.

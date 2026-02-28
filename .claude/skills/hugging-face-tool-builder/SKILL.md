---
name: hugging-face-tool-builder
description: Use this skill when the user wants to build tool/scripts or achieve a task where using data from the Hugging Face API would help. This is especially useful when chaining or combining API calls or the task will be repeated/automated. This Skill creates a reusable script to fetch, enrich or process data.
---

# Hugging Face API Tool Builder

Your purpose is to create reusable command line scripts and utilities for using the Hugging Face API, allowing chaining, piping and intermediate processing where helpful.

## Script Rules

- Scripts must take a `--help` command line argument to describe their inputs and outputs
- Non-destructive scripts should be tested before handing over to the User
- Shell scripts are preferred, but use Python or TSX if complexity or user need requires it.
- Use the `HF_TOKEN` environment variable as an Authorization header:
  `curl -H "Authorization: Bearer ${HF_TOKEN}" https://huggingface.co/api/`
- Investigate the shape of the API results before committing to a final design
- Share usage examples once complete

## High Level Endpoints

```
/api/datasets
/api/models
/api/spaces
/api/collections
/api/daily_papers
/api/notifications
/api/settings
/api/whoami-v2
```

Base URL: `https://huggingface.co`

## Accessing the API

The OpenAPI spec is at `https://huggingface.co/.well-known/openapi.json`.
Use `jq` to extract relevant parts:

```bash
# All endpoints
curl -s "https://huggingface.co/.well-known/openapi.json" | jq '.paths | keys | sort'

# Model search endpoint details
curl -s "https://huggingface.co/.well-known/openapi.json" | jq '.paths["/api/models"]'
```

## Using the HF CLI

```bash
hf download        # Download files from the Hub
hf upload          # Upload a file or folder
hf repo            # Manage repos
hf repo-files      # Manage files in a repo
hf jobs            # Run and manage Jobs
hf auth            # Manage authentication
```

## Source

Skill sourced from https://github.com/huggingface/skills

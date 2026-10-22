#!/usr/bin/env python3
# Copyright Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""Helm post-renderer: Harbor's database is checked on its port, not with psql.

The chart's probes run /docker-healthcheck.sh, a psql, inside the database
container. Postgres is that container's PID 1: when a probe times out and its
psql is killed, Postgres reaps an exit it did not start, takes it for a crashed
backend and restarts every connection, and Harbor answers 500 meanwhile. A TCP
probe starts no process in the container. The timings stay the chart's.

Reads the rendered manifests on stdin and writes them to stdout.
"""

import sys

import yaml

STATEFULSET = "harbor-database"
CONTAINER = "database"
PORT = 5432

documents = [d for d in yaml.safe_load_all(sys.stdin) if d is not None]
found = False
for document in documents:
    if document.get("kind") != "StatefulSet" or document["metadata"].get("name") != STATEFULSET:
        continue
    for container in document["spec"]["template"]["spec"]["containers"]:
        if container["name"] != CONTAINER:
            continue
        for probe in ("livenessProbe", "readinessProbe"):
            container[probe].pop("exec")
            container[probe]["tcpSocket"] = {"port": PORT}
        found = True
if not found:
    sys.exit(f"database-probes.py: no container {CONTAINER} in StatefulSet {STATEFULSET}; the chart changed")
yaml.safe_dump_all(documents, sys.stdout, sort_keys=False)

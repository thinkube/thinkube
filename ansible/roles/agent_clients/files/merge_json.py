# Copyright Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""Set and delete keys in a JSON file, keeping every other key.

Usage: python3 -c "$(cat merge_json.py)" FILE < CHANGES
CHANGES is {"merge": [[key, ..., object], ...], "delete": [[key, ...], ...]}:
each merge sets every key of its object under the path given before it (an
empty path is the top level); each delete removes the key at its path.
A missing FILE starts as {}. A FILE that is not a JSON object is an error,
not overwritten. Prints "changed" when the file was written.
"""

import json
import os
import sys

path = sys.argv[1]
changes = json.load(sys.stdin)

if os.path.exists(path):
    with open(path) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as err:
            sys.exit(f"{path} is not valid JSON ({err}); fix or remove it, then run again")
    if not isinstance(data, dict):
        sys.exit(f"{path} is not a JSON object; fix or remove it, then run again")
else:
    data = {}

before = json.dumps(data, sort_keys=True)

for *keys, values in changes.get("merge", []):
    node = data
    for key in keys:
        child = node.setdefault(key, {})
        if not isinstance(child, dict):
            sys.exit(f"{path}: {'.'.join(keys)} is not an object; fix it, then run again")
        node = child
    node.update(values)

for keys in changes.get("delete", []):
    node = data
    for key in keys[:-1]:
        node = node.get(key) if isinstance(node, dict) else None
        if node is None:
            break
    if isinstance(node, dict):
        node.pop(keys[-1], None)

if json.dumps(data, sort_keys=True) != before:
    tmp = f"{path}.tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)
    print("changed")

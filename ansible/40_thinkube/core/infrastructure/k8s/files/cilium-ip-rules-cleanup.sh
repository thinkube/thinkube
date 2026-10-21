#!/usr/bin/env bash
# Copyright Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0
#
# Removes the policy routing Cilium's agent adds to the host, for IPv4
# and IPv6. Run by 19_rollback_control.yaml and 29_rollback_workers.yaml
# after Cilium has stopped.
#
#   - The rules that look up the L7 proxy route tables 2004 and 2005, and
#     the routes in those tables.
#   - The local-table rule, which Cilium moves from priority 0 to 100 to
#     put its own rules in front of it. It is put back at 0 before the
#     rule at 100 is deleted, so the host never runs without a local-table
#     rule.
#
# Prints one line per change, and nothing when there is nothing to change
# (the playbooks report "changed" from the output).
set -euo pipefail

clean() {
    local fam=$1 table rules
    for table in 2004 2005; do
        rules=$(ip "-$fam" rule show)
        while grep -qE "lookup $table( |$)" <<<"$rules"; do
            ip "-$fam" rule del table "$table"
            echo "ip -$fam rule: deleted a rule for table $table"
            rules=$(ip "-$fam" rule show)
        done
        if [ -n "$(ip "-$fam" route show table "$table")" ]; then
            ip "-$fam" route flush table "$table"
            echo "ip -$fam route: flushed table $table"
        fi
    done

    rules=$(ip "-$fam" rule show)
    if ! grep -qE '^0:\s+from all lookup local' <<<"$rules" \
        && grep -qE '^100:\s+from all lookup local' <<<"$rules"; then
        ip "-$fam" rule add from all lookup local pref 0
        ip "-$fam" rule del from all lookup local pref 100
        echo "ip -$fam rule: moved the local-table rule back to priority 0"
    fi
}

clean 4
# A kernel booted with IPv6 disabled has no IPv6 policy routing.
if [ -d /proc/sys/net/ipv6 ]; then
    clean 6
fi

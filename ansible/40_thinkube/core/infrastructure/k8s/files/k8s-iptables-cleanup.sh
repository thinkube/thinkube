#!/usr/bin/env bash
# Copyright Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0
#
# Removes the iptables chains kubelet and Cilium create (names starting
# with KUBE- or CILIUM_) and the rules in other chains that jump to them,
# in the filter, nat, mangle and raw tables, for IPv4 and IPv6. Run by
# 19_rollback_control.yaml and 29_rollback_workers.yaml.
#
# No other chain or rule is touched: UFW's chains, Docker's chains and
# the policies of the built-in chains stay as they are, so the firewall
# and the SSH session are not affected.
#
# Prints one line per removed rule or chain, and nothing when there is
# nothing to remove (the playbooks report "changed" from the output).
set -euo pipefail

owned='^(KUBE-|CILIUM_)'

clean() {
    local cmd=$1 table rules line chain chains
    for table in filter nat mangle raw; do
        rules=$("$cmd" -t "$table" -S)

        # Rules in chains that are not ours and jump (-j) or go (-g) to a
        # chain that is. `iptables -S` prints each rule as the arguments
        # that add it, with comments in double quotes; eval keeps those
        # quotes intact when the -A is turned into a -D.
        while IFS= read -r line; do
            eval "\"\$cmd\" -t \"\$table\" -D ${line#-A }"
            echo "$cmd -t $table: deleted rule: $line"
        done < <(printf '%s\n' "$rules" | awk -v re="$owned" '
            $1 == "-A" && $2 !~ re {
                for (i = 3; i < NF; i++)
                    if (($i == "-j" || $i == "-g") && $(i + 1) ~ re) { print; break }
            }')

        # Our chains refer to each other, so all are flushed before any is
        # deleted.
        chains=$(printf '%s\n' "$rules" | awk -v re="$owned" '$1 == "-N" && $2 ~ re {print $2}')
        for chain in $chains; do
            "$cmd" -t "$table" -F "$chain"
        done
        for chain in $chains; do
            "$cmd" -t "$table" -X "$chain"
            echo "$cmd -t $table: deleted chain $chain"
        done
    done
}

# A kernel booted with IPv6 disabled has no ip6tables tables.
ipv6_present() {
    [ -d /proc/sys/net/ipv6 ]
}

# The default iptables command, whichever backend it is.
clean iptables
if ipv6_present; then
    clean ip6tables
fi

# kubelet and Cilium follow the backend the host already uses, so rules
# can also sit in the legacy backend while the default command is the
# nft one. The legacy tables exist only when their kernel modules are
# loaded; they are listed in /proc/net/ip{,6}_tables_names.
if iptables --version | grep -q 'nf_tables' && command -v iptables-legacy >/dev/null 2>&1; then
    if [ -r /proc/net/ip_tables_names ] && [ -n "$(cat /proc/net/ip_tables_names)" ]; then
        clean iptables-legacy
    fi
    if ipv6_present && [ -r /proc/net/ip6_tables_names ] && [ -n "$(cat /proc/net/ip6_tables_names)" ]; then
        clean ip6tables-legacy
    fi
fi

# Operations policy — destructive actions and diagnosis (Thinkube platform default)

- A wipe, reset, rollback, reboot or delete of a node, cluster or image
  store is asked for on its own line, naming the host and what is lost,
  and runs only on a yes to THAT line. A yes to a plan is not a yes to
  each step inside it.
- Reset the smallest thing that makes the test valid. A failure in
  add-nodes resets the workers, not the control plane.
- Diagnose until the practical fix is known, then stop. Attribution
  without an audit source is speculation; say it is unprovable.
- What the user says they did is a fact, not a hypothesis. Never read
  their shell history, transcripts or personal files to check it.
- Before trusting a tool's output, say what it measured: ICMP is not
  TCP, `iptables -t nat` is not the ruleset, `tail -2` hides the error.
- Verify the result, not the completion. A step that ran is not a step
  that produced the right state.

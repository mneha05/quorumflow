# Consensus design notes

QuorumFlow uses a deterministic Raft-style state machine to make model-version and routing decisions explicit under failure. It focuses on the rules that determine whether a value may safely be called committed.

## State carried by each node

- monotonically increasing `term`
- `follower`, `candidate`, or `leader` role
- at most one vote per term
- an ordered `(index, term, command)` log
- the highest known committed index

## Election rule

A candidate increments the maximum observed term, votes for itself, and requests votes from reachable peers. A peer votes only when it has not already voted in that term and the candidate’s `(last_log_term, last_log_index)` is at least as current as its own. A leader requires `floor(N / 2) + 1` votes.

## Replication rule

The leader appends a command locally, sends AppendEntries from the last common index, and marks the command committed only after a majority acknowledges it. A recovering follower truncates a conflicting suffix and accepts the leader’s entries before its commit index advances.

## What the model proves in tests

| Scenario | Expected property |
|---|---|
| Candidate cannot contact a majority | No leader is elected |
| Leader fails after a commit | New leader preserves the committed command |
| Leader proposes without quorum | Entry is not reported committed |
| Isolated follower rejoins | Follower catches up to the leader’s log and commit index |

## Deliberate boundary

`Cluster` is a synchronous network harness. Isolation is represented by membership in an `online` set, and message delivery is a direct method call. That makes safety transitions fast and reproducible in unit tests, but it is not a distributed transport.

A production controller would need durable term/vote/log storage, RPC serialization, randomized election timeouts, heartbeat scheduling, retry and backpressure policy, snapshot installation, membership changes, authentication, observability, and fault-injection tests against real processes. Those concerns should wrap the same state-machine rules rather than be hidden inside them.

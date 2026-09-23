"""A deterministic Raft model for the QuorumFlow control plane.

This module is deliberately transport-free: tests can drive elections, partitions,
and replication without sleeping or opening sockets. Production transports can map
RequestVote and AppendEntries messages onto the same state transitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class Role(str, Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


@dataclass(frozen=True)
class LogEntry:
    index: int
    term: int
    command: str


class Node:
    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.term = 0
        self.role = Role.FOLLOWER
        self.voted_for: str | None = None
        self.leader_id: str | None = None
        self.log: list[LogEntry] = [LogEntry(0, 0, "bootstrap")]
        self.commit_index = 0

    @property
    def last_entry(self) -> LogEntry:
        return self.log[-1]

    def advance_term(self, term: int) -> None:
        if term > self.term:
            self.term = term
            self.role = Role.FOLLOWER
            self.voted_for = None
            self.leader_id = None

    def request_vote(
        self,
        *,
        candidate_id: str,
        term: int,
        last_log_index: int,
        last_log_term: int,
    ) -> bool:
        if term < self.term:
            return False
        self.advance_term(term)
        candidate_is_current = (last_log_term, last_log_index) >= (
            self.last_entry.term,
            self.last_entry.index,
        )
        vote_is_available = self.voted_for in (None, candidate_id)
        if candidate_is_current and vote_is_available:
            self.voted_for = candidate_id
            return True
        return False

    def append_entries(
        self,
        *,
        term: int,
        leader_id: str,
        prev_log_index: int,
        prev_log_term: int,
        entries: Iterable[LogEntry],
        leader_commit: int,
    ) -> bool:
        if term < self.term:
            return False
        self.advance_term(term)
        self.role = Role.FOLLOWER
        self.leader_id = leader_id

        if prev_log_index >= len(self.log):
            return False
        if self.log[prev_log_index].term != prev_log_term:
            self.log = self.log[:prev_log_index]
            return False

        for entry in entries:
            if entry.index < len(self.log):
                if self.log[entry.index].term != entry.term:
                    self.log = self.log[: entry.index]
                    self.log.append(entry)
            else:
                self.log.append(entry)
        self.commit_index = min(leader_commit, self.last_entry.index)
        return True


class Cluster:
    """A synchronous network harness around the Raft node state machine."""

    def __init__(self, node_ids: Iterable[str] = ("us-east", "eu-west", "ap-south")) -> None:
        self.nodes = {node_id: Node(node_id) for node_id in node_ids}
        if len(self.nodes) < 3:
            raise ValueError("a useful Raft cluster requires at least three nodes")
        self.online = set(self.nodes)
        self.leader_id: str | None = None

    @property
    def quorum(self) -> int:
        return len(self.nodes) // 2 + 1

    def isolate(self, node_id: str) -> None:
        self._node(node_id)
        self.online.discard(node_id)
        if self.leader_id == node_id:
            self.leader_id = None

    def heal(self, node_id: str) -> None:
        self._node(node_id)
        self.online.add(node_id)
        if self.leader_id is not None:
            self._replicate_to(node_id)

    def elect(self, candidate_id: str) -> bool:
        candidate = self._node(candidate_id)
        if candidate_id not in self.online:
            return False
        candidate.term = max(node.term for node in self.nodes.values()) + 1
        candidate.role = Role.CANDIDATE
        candidate.voted_for = candidate_id
        votes = 1
        for peer_id in sorted(self.online - {candidate_id}):
            peer = self.nodes[peer_id]
            votes += peer.request_vote(
                candidate_id=candidate_id,
                term=candidate.term,
                last_log_index=candidate.last_entry.index,
                last_log_term=candidate.last_entry.term,
            )
        if votes < self.quorum:
            return False
        candidate.role = Role.LEADER
        candidate.leader_id = candidate_id
        self.leader_id = candidate_id
        for peer_id in self.online - {candidate_id}:
            self._replicate_to(peer_id)
        return True

    def propose(self, command: str) -> bool:
        if self.leader_id is None:
            return False
        leader = self.nodes[self.leader_id]
        if self.leader_id not in self.online or leader.role is not Role.LEADER:
            return False
        entry = LogEntry(leader.last_entry.index + 1, leader.term, command)
        leader.log.append(entry)
        acknowledgements = 1
        for peer_id in sorted(self.online - {self.leader_id}):
            acknowledgements += self._replicate_to(peer_id)
        if acknowledgements < self.quorum:
            return False
        leader.commit_index = entry.index
        for peer_id in self.online - {self.leader_id}:
            self._replicate_to(peer_id)
        return True

    def failover(self) -> str | None:
        if self.leader_id is not None:
            self.isolate(self.leader_id)
        for candidate_id in sorted(self.online):
            if self.elect(candidate_id):
                return candidate_id
        return None

    def snapshot(self) -> dict[str, object]:
        return {
            "leader": self.leader_id,
            "quorum": self.quorum,
            "nodes": {
                node_id: {
                    "online": node_id in self.online,
                    "role": node.role.value,
                    "term": node.term,
                    "commit_index": node.commit_index,
                    "log": [entry.command for entry in node.log[1:]],
                }
                for node_id, node in sorted(self.nodes.items())
            },
        }

    def _replicate_to(self, peer_id: str) -> bool:
        if self.leader_id is None or peer_id not in self.online:
            return False
        leader = self.nodes[self.leader_id]
        peer = self.nodes[peer_id]
        common_index = min(peer.last_entry.index, leader.last_entry.index)
        while common_index > 0 and peer.log[common_index].term != leader.log[common_index].term:
            common_index -= 1
        return peer.append_entries(
            term=leader.term,
            leader_id=leader.node_id,
            prev_log_index=common_index,
            prev_log_term=leader.log[common_index].term,
            entries=leader.log[common_index + 1 :],
            leader_commit=leader.commit_index,
        )

    def _node(self, node_id: str) -> Node:
        try:
            return self.nodes[node_id]
        except KeyError as error:
            raise KeyError(f"unknown cluster node: {node_id}") from error


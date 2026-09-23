from __future__ import annotations

import unittest

from quorumflow.consensus import Cluster, Role


class ConsensusTests(unittest.TestCase):
    def test_election_requires_majority(self) -> None:
        cluster = Cluster()
        cluster.isolate("eu-west")
        cluster.isolate("ap-south")
        self.assertFalse(cluster.elect("us-east"))
        self.assertIsNone(cluster.leader_id)

    def test_failover_advances_term_and_preserves_committed_log(self) -> None:
        cluster = Cluster()
        self.assertTrue(cluster.elect("us-east"))
        first_term = cluster.nodes["us-east"].term
        self.assertTrue(cluster.propose("model=v17"))

        new_leader = cluster.failover()
        self.assertIsNotNone(new_leader)
        assert new_leader is not None
        self.assertGreater(cluster.nodes[new_leader].term, first_term)
        self.assertEqual(cluster.nodes[new_leader].role, Role.LEADER)
        self.assertEqual(cluster.nodes[new_leader].log[-1].command, "model=v17")

    def test_uncommitted_entry_does_not_pass_without_quorum(self) -> None:
        cluster = Cluster()
        self.assertTrue(cluster.elect("us-east"))
        cluster.isolate("eu-west")
        cluster.isolate("ap-south")
        self.assertFalse(cluster.propose("model=v18"))
        self.assertEqual(cluster.nodes["us-east"].commit_index, 0)

    def test_healed_follower_catches_up(self) -> None:
        cluster = Cluster()
        cluster.elect("us-east")
        cluster.isolate("ap-south")
        self.assertTrue(cluster.propose("threshold=0.92"))
        cluster.heal("ap-south")
        follower = cluster.nodes["ap-south"]
        self.assertEqual(follower.log[-1].command, "threshold=0.92")
        self.assertEqual(follower.commit_index, 1)


if __name__ == "__main__":
    unittest.main()


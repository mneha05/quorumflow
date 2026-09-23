from __future__ import annotations

import json

from .consensus import Cluster


def main() -> None:
    cluster = Cluster()
    cluster.elect("us-east")
    cluster.propose("model=v17")
    cluster.propose("threshold=0.92")
    old_leader = cluster.leader_id
    new_leader = cluster.failover()
    cluster.propose("route=eu-west")
    print(json.dumps({"failed_leader": old_leader, "new_leader": new_leader, **cluster.snapshot()}, indent=2))


if __name__ == "__main__":
    main()


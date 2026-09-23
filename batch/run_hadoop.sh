#!/usr/bin/env bash
set -euo pipefail

: "${HADOOP_HOME:?Set HADOOP_HOME to an Apache Hadoop 3.5 installation}"

"${HADOOP_HOME}/bin/hadoop" jar \
  "${HADOOP_HOME}/share/hadoop/tools/lib/hadoop-streaming-3.5.0.jar" \
  -files batch/mapper.py,batch/reducer.py \
  -mapper mapper.py \
  -reducer reducer.py \
  -input "${1:-/quorumflow/telemetry}" \
  -output "${2:-/quorumflow/daily-baselines}"


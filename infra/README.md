# Multi-cloud substrate

The three Terraform roots intentionally provision the smallest persistent substrate: versioned object storage for Hadoop/Flink checkpoints and TensorFlow artifacts, a container registry for the portable runtime, and a cloud-native durable control-plane store where appropriate.

They do **not** create an always-on Kubernetes cluster or managed Flink/Hadoop service by default; doing that in a portfolio repository can incur surprise charges. Apply `k8s/base` to an existing EKS, AKS, or GKE cluster, then select the managed services that match the workload.

| Contract | AWS | Azure | GCP |
|---|---|---|---|
| Portable runtime | EKS | AKS | GKE |
| Event ingress | MSK / Kinesis | Event Hubs | Pub/Sub |
| Flink | Managed Service for Apache Flink / EKS | Flink on AKS | Flink on GKE |
| Hadoop backfill | EMR | HDInsight / AKS | Dataproc |
| Artifact lake | S3 | ADLS Gen2 | Cloud Storage |
| TensorFlow serving | EKS / SageMaker endpoint | AKS / Azure ML endpoint | GKE / Vertex AI endpoint |

The application talks to storage and ingress through environment variables, keeping the pipeline contract independent of the cloud vendor.


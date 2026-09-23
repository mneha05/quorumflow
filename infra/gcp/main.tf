terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 6.0"
    }
  }
}

variable "project_id" {
  type = string
}
variable "region" {
  type    = string
  default = "us-central1"
}

variable "bucket_name" {
  type        = string
  description = "Globally unique artifact bucket name."
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_storage_bucket" "lake" {
  name                        = var.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false
  versioning {
    enabled = true
  }
  labels = {
    system = "quorumflow"
    layer  = "hadoop-history"
  }
}

resource "google_artifact_registry_repository" "runtime" {
  location      = var.region
  repository_id = "quorumflow-runtime"
  format        = "DOCKER"
}

resource "google_pubsub_topic" "telemetry" {
  name                       = "quorumflow-telemetry"
  message_retention_duration = "86400s"
}

output "artifact_bucket" {
  value = google_storage_bucket.lake.url
}

output "registry" {
  value = google_artifact_registry_repository.runtime.name
}

output "event_topic" {
  value = google_pubsub_topic.telemetry.name
}

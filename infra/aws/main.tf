terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  type    = string
  default = "us-east-2"
}

variable "name" {
  type    = string
  default = "quorumflow"
}

resource "aws_s3_bucket" "lake" {
  bucket_prefix = "${var.name}-lake-"
  force_destroy = false
  tags = {
    System = var.name
    Layer  = "hadoop-history"
  }
}

resource "aws_s3_bucket_versioning" "lake" {
  bucket = aws_s3_bucket.lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_dynamodb_table" "control_log" {
  name         = "${var.name}-raft-snapshots"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "cluster_id"
  attribute {
    name = "cluster_id"
    type = "S"
  }
  point_in_time_recovery {
    enabled = true
  }
  tags = {
    System = var.name
    Layer  = "consensus"
  }
}

resource "aws_ecr_repository" "runtime" {
  name                 = "${var.name}-runtime"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}

output "artifact_bucket" {
  value = aws_s3_bucket.lake.id
}

output "control_table" {
  value = aws_dynamodb_table.control_log.name
}

output "registry" {
  value = aws_ecr_repository.runtime.repository_url
}

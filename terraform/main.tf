provider "aws" {
  region = "us-east-1"
}

# ECS Cluster
resource "aws_ecs_cluster" "log_cluster" {
  name = "log-intelligence-cluster"
}

# S3 bucket for logs storage
resource "aws_s3_bucket" "log_storage" {
  bucket = "log-intelligence-logs-bucket-12345"
}

# CloudWatch logs
resource "aws_cloudwatch_log_group" "app_logs" {
  name = "/ecs/log-intelligence-agent"
}
# olmOCR GCP Infrastructure - Terraform Configuration
#
# This Terraform configuration provisions all GCP resources needed for olmOCR
#
# Usage:
#   cd gcp-deployment/terraform
#   terraform init
#   terraform plan -var="project_id=juniper-core" -var="parasail_api_key=psk-xxx"
#   terraform apply -var="project_id=juniper-core" -var="parasail_api_key=psk-xxx"

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
}

# Variables
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "parasail_api_key" {
  description = "Parasail API Key for olmOCR model access"
  type        = string
  sensitive   = true
}

# Provider configuration
provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "storage.googleapis.com",
    "firestore.googleapis.com",
    "pubsub.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
    "firebase.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# Artifact Registry repository
resource "google_artifact_registry_repository" "olmocr" {
  provider = google-beta

  location      = var.region
  repository_id = "olmocr"
  format        = "DOCKER"
  description   = "olmOCR container images"

  depends_on = [google_project_service.apis]
}

# Cloud Storage bucket
resource "google_storage_bucket" "olmocr" {
  name     = "olmocr-${var.project_id}"
  location = var.region

  uniform_bucket_level_access = true

  cors {
    origin          = ["*"]
    method          = ["GET", "PUT", "POST", "DELETE", "OPTIONS"]
    response_header = ["Content-Type", "Authorization", "Content-Length", "X-Requested-With"]
    max_age_seconds = 3600
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.apis]
}

# Firestore database
resource "google_firestore_database" "olmocr" {
  provider = google-beta

  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.apis]
}

# Pub/Sub topic
resource "google_pubsub_topic" "olmocr_jobs" {
  name = "olmocr-jobs"

  depends_on = [google_project_service.apis]
}

# Secret Manager - Parasail API Key
resource "google_secret_manager_secret" "parasail_api_key" {
  secret_id = "parasail-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "parasail_api_key" {
  secret      = google_secret_manager_secret.parasail_api_key.id
  secret_data = var.parasail_api_key
}

# Service Accounts
resource "google_service_account" "backend" {
  account_id   = "olmocr-backend"
  display_name = "olmOCR Backend Service"
}

resource "google_service_account" "worker" {
  account_id   = "olmocr-worker"
  display_name = "olmOCR Worker Service"
}

resource "google_service_account" "pubsub_invoker" {
  account_id   = "pubsub-invoker"
  display_name = "Pub/Sub Cloud Run Invoker"
}

# IAM - Backend permissions
resource "google_project_iam_member" "backend_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_project_iam_member" "backend_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_project_iam_member" "backend_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# IAM - Worker permissions
resource "google_project_iam_member" "worker_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_project_iam_member" "worker_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_project_iam_member" "worker_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.worker.email}"
}

# Outputs
output "bucket_name" {
  value       = google_storage_bucket.olmocr.name
  description = "Cloud Storage bucket name"
}

output "artifact_registry" {
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/olmocr"
  description = "Artifact Registry URL"
}

output "pubsub_topic" {
  value       = google_pubsub_topic.olmocr_jobs.name
  description = "Pub/Sub topic name"
}

output "backend_service_account" {
  value       = google_service_account.backend.email
  description = "Backend service account email"
}

output "worker_service_account" {
  value       = google_service_account.worker.email
  description = "Worker service account email"
}

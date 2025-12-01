# olmOCR Cloud Run Services
#
# This file defines Cloud Run services for frontend, backend, and worker.
# Run after building and pushing container images.

# Data source for project number (needed for some IAM bindings)
data "google_project" "project" {
  project_id = var.project_id
}

# Frontend Service
resource "google_cloud_run_v2_service" "frontend" {
  name     = "olmocr-frontend"
  location = var.region

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/olmocr/frontend:latest"

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "256Mi"
        }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [google_artifact_registry_repository.olmocr]
}

# Allow public access to frontend
resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  project  = google_cloud_run_v2_service.frontend.project
  location = google_cloud_run_v2_service.frontend.location
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Backend Service
resource "google_cloud_run_v2_service" "backend" {
  name     = "olmocr-backend"
  location = var.region

  template {
    service_account = google_service_account.backend.email

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/olmocr/backend:latest"

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.olmocr.name
      }

      env {
        name  = "PUBSUB_TOPIC"
        value = google_pubsub_topic.olmocr_jobs.name
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      env {
        name  = "CORS_ORIGINS"
        value = google_cloud_run_v2_service.frontend.uri
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 20
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_artifact_registry_repository.olmocr,
    google_cloud_run_v2_service.frontend,
  ]
}

# Allow public access to backend
resource "google_cloud_run_v2_service_iam_member" "backend_public" {
  project  = google_cloud_run_v2_service.backend.project
  location = google_cloud_run_v2_service.backend.location
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Worker Service
resource "google_cloud_run_v2_service" "worker" {
  name     = "olmocr-worker"
  location = var.region

  template {
    service_account = google_service_account.worker.email
    timeout         = "600s"

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/olmocr/worker:latest"

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.olmocr.name
      }

      env {
        name  = "PROCESSING_MODE"
        value = "parasail"
      }

      env {
        name  = "PARASAIL_MODEL"
        value = "allenai/olmOCR-2-7B-1025"
      }

      env {
        name = "PARASAIL_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.parasail_api_key.secret_id
            version = "latest"
          }
        }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_artifact_registry_repository.olmocr,
    google_secret_manager_secret_version.parasail_api_key,
  ]
}

# Allow Pub/Sub to invoke worker
resource "google_cloud_run_v2_service_iam_member" "worker_pubsub" {
  project  = google_cloud_run_v2_service.worker.project
  location = google_cloud_run_v2_service.worker.location
  name     = google_cloud_run_v2_service.worker.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.pubsub_invoker.email}"
}

# Pub/Sub subscription with push to worker
resource "google_pubsub_subscription" "olmocr_jobs_push" {
  name  = "olmocr-jobs-push"
  topic = google_pubsub_topic.olmocr_jobs.name

  ack_deadline_seconds = 600

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.worker.uri}/process"

    oidc_token {
      service_account_email = google_service_account.pubsub_invoker.email
    }
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  depends_on = [google_cloud_run_v2_service_iam_member.worker_pubsub]
}

# Outputs
output "frontend_url" {
  value       = google_cloud_run_v2_service.frontend.uri
  description = "Frontend URL"
}

output "backend_url" {
  value       = google_cloud_run_v2_service.backend.uri
  description = "Backend API URL"
}

output "worker_url" {
  value       = google_cloud_run_v2_service.worker.uri
  description = "Worker URL"
}

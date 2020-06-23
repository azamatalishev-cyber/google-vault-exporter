provider "kubernetes" {
  config_context = "kind-kind"
}

resource "random_integer" "this" {
  min = 1
  max = 10
}

variable "namespace" {
  type    = string
  default = "it"
}

data "kubernetes_namespace" "it" {
  metadata {
    name = var.namespace
  }
}
resource "kubernetes_cron_job" "gam_vault_export_collector" {
  metadata {
    name      = "gam-vault-export-collector"
    namespace = data.kubernetes_namespace.it.metadata[0].name
  }
  spec {
    concurrency_policy            = "Forbid"
    failed_jobs_history_limit     = 5
    schedule                      = "*/3 * * * *"
    starting_deadline_seconds     = 10
    successful_jobs_history_limit = 10
    job_template {
      metadata {
        name = "gam-vault-export-collector"
      }
      spec {
        backoff_limit = 2
        template {
          metadata {}
          spec {
            volume {
              name = "credentials"
              secret {
                secret_name = "gamad-credentials"
              }
            }
            container {
              name  = "gam-pod"
              image = "gamadcronjob:test"
              args  = ["sleep", "${random_integer.this.result}m"]
              volume_mount {
                name       = "credentials"
                mount_path = "/credentials"
              }
            }
            restart_policy = "OnFailure"
          }
        }
      }
    }
  }
}

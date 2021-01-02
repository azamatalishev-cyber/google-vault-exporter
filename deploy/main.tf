/*Secrets retrieved from parameter store then placed into k8s secrets.
Secrets then move into /credentials folder inside the pod.*/

data "aws_ssm_parameter" "clientsecrets" {
  name = "/it/gam-vault-export-collector/client_secrets.json"
}

data "aws_ssm_parameter" "oauth2service" {
  name = "/it/gam-vault-export-collector/oauth2service.json"
}

data "aws_ssm_parameter" "oauth2_base" {
  name = "/it/gam-vault-export-collector/oauth2.txt_base"
}

data "aws_ssm_parameter" "oauth2_scopes" {
  name = "/it/gam-vault-export-collector/oauth2.txt_scopes"
}

data "aws_ssm_parameter" "slack_url" {
  name = "/it/gam-vault-export-collector/slack_url"
}

locals {
  merged_oauth2_txt = jsonencode(
    merge(
      jsondecode(data.aws_ssm_parameter.oauth2_base.value),
      jsondecode(data.aws_ssm_parameter.oauth2_scopes.value)
    )
  )
}

resource "kubernetes_secret" "google_vault_credentials" {
  metadata {
    name      = "google-vault-credentials"
    namespace = "it"
  }
  data = {
    "client_secrets.json" = data.aws_ssm_parameter.clientsecrets.value
    "oauth2service.json"  = data.aws_ssm_parameter.oauth2service.value
    "oauth2.txt"          = local.merged_oauth2_txt
    "slack_url.txt"       = data.aws_ssm_parameter.slack_url.value
  }
}

resource "kubernetes_cron_job" "google_vault_export_collector" {
  metadata {
    name      = "google-vault-export"
    namespace = "it"
  }

  spec {
    concurrency_policy            = "Forbid"
    failed_jobs_history_limit     = 5
    schedule                      = "0 12 * * 6"
    starting_deadline_seconds     = 10
    successful_jobs_history_limit = 3
    job_template {
      metadata {
        name = "google-vault-export-collector"
      }
      spec {
        backoff_limit = 2
        template {
          metadata {}
          spec {
            volume {
              name = "credentials"
              secret {
                secret_name = "google-vault-credentials"
              }
            }
            container {
              env {
                name = "SLACK_URL"
                value_from {
                  secret_key_ref {
                    name = kubernetes_secret.google_vault_credentials.metadata[0].name
                    key  = "slack_url.txt"
                  }
                }
              }
              name  = "gam-pod"
              image = "gcr.io/gh-infra/google-vault-export:latest"
              args  = ["python3", "-u", "main.py"]
              resources {
                limits {
                  cpu    = "500m"
                  memory = "1Gi"
                }
                requests {
                  cpu    = "500m"
                  memory = "512Mi"
                }
              }
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

# AWS Module

## Example
```terraform
locals {
  client_secret     = "arn:aws:secretsmanager:us-west-2:test:secret:client_secret"
  pseudonymize_salt = "arn:aws:secretsmanager:us-west-2:test:secret:salt_secret"
}

data "aws_iam_policy_document" "lambda_secrets_policy" {
  statement {
    sid       = "SecretsAccess"
    effect    = "Allow"
    resources = [
      local.client_secret,
      local.pseudonymize_salt
    ]
    actions   = ["secretsmanager:GetSecretValue"]
  }
}

module "guardette_redacting_proxy" {
  source = "git@github.com:Attuned-Corp/guardette.git//terraform/aws"

  image_uri                = "***.dkr.ecr.us-west-2.amazonaws.com/container:tag"
  lambda_additional_policy = data.aws_iam_policy_document.lambda_secrets_policy.json
  environment_vars         = {
    SECRET_MANAGER                       = "aws_secret_manager"
    CLIENT_SECRET                        = local.client_secret
    PSEUDONYMIZE_SALT                    = local.pseudonymize_salt
    PSEUDONYMIZE_EMAIL_DOMAINS_ALLOWLIST = "example.com"
  }
}
```

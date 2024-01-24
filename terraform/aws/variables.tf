variable "name" {
  description = "The name of the Guardette Lambda Function and API"
  type        = string
  default     = "guardette"
  nullable    = false
}

variable "lambda_additional_policy" {
  description = "Additional policies to add to the lambda policy"
  type        = string
  nullable    = false
  default     = ""
}

variable "image_uri" {
  description = "The URI where the image can be pulled, including the tag"
  type        = string
  nullable    = false
}

variable "image_architecture" {
  description = "Architecture of the image"
  type        = string

  validation {
    condition     = contains(["x86_64", "arm64"], var.image_architecture)
    error_message = "Invalid input, options: \"x86_64\", \"arm64\""
  }

  nullable = false
  default  = "x86_64"
}

variable "environment_vars" {
  description = "Environment variables to launch the lambda with"
  type        = map(any)

  validation {
    condition = alltrue([
      for key in keys(var.environment_vars) :
      contains([
        "SECRET_MANAGER",
        "CLIENT_SECRET",
        "PSEUDONYMIZE_SALT",
        "PSEUDONYMIZE_EMAIL_DOMAINS_ALLOWLIST"
      ], key)
    ])
    error_message = "Invalid environment variable specified!"
  }

  sensitive = true
  nullable  = false
}


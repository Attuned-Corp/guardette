terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.31"
    }
  }

  required_version = ">= 1.4"
}

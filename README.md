# Guardette Documentation

Guardette is a **serverless redacting proxy layer** that sits between the REST APIs of your data sources and vendors who require access to a subset of that data. By leveraging Guardette, you can achieve **more secure and granular access control** through customizable redaction and allow-listing rules defined in a YAML file.

## **Features**

- **Serverless Architecture**: Deploy Guardette as an AWS Lambda function for scalability and cost-effectiveness.
- **Redaction and Filtering**: Define precise rules to redact sensitive information or filter specific data fields.
- **Granular Access Control**: Allow or restrict access to specific parts of your APIs based on defined policies.
- **Authentication Support**: Integrate with various authentication mechanisms, including AWS Secrets Manager for secure credential management.
- **Extensible**: Easily add custom actions and authentication handlers to extend Guardette's capabilities.

## **Getting Started**

### Installation

1. **Clone the Repository**

```
git clone git@github.com:Attuned-Corp/guardette.git
cd guardette
```

1. **Install Dependencies**

```
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

1. **Generate a policy.yml**

Span will send you a config file to generate your policy.yml with, but it might look something like this:

```
{
  "sources": [
    {
      "kind": "test_hacker_news",
      "config": {}
    },
    {
      "kind": "jira",
      "config": {"jira_domain": "yourdomain.atlassian.net"}
    }
  ]
}

```

```python
python scripts/policygen/policygen.py --config=policygen.config.json
```

Upon successful execution, a `.guardette/policy.yml` file will be created. This YAML file contains the rules that the proxy will use to enforce data access policies.

1. **Run locally**

```python
SECRET_MANAGER=default CLIENT_SECRET=secret python -m uvicorn main:app --reload
```

```python
curl -H "Authorization: secret" -H "X-Guardette-Host: hacker-news.firebaseio.com" "http://localhost:8000/v0/item/8863.json?print=pretty"
```

## **Deploying to AWS**
Read [terraform/aws/README.md](terraform/aws/README.md)

## **Authentication Configuration**

Guardette supports various authentication mechanisms to secure access to your proxied APIs. This section covers configuring authentication secrets using AWS Secrets Manager.

1. **Create Secrets in AWS Secrets Manager**

For each authentication method (e.g., Jira), create secrets in AWS Secrets Manager. Each secret should store the necessary credentials. The naming convention for these secrets is crucial for Guardette to recognize and utilize them correctly.

**Example for Jira**:

- **Secret Name**: AUTH_BASIC_AUTH_, AUTH_JIRA_PASSWORD
- **Secret Values**: Your Jira username and password.

**Naming Convention**:

- For an authentication handler like basic_auth:jira, Guardette expects the following environment variables:
    - AUTH_BASIC_AUTH_JIRA_USERNAME
    - AUTH_BASIC_AUTH_JIRA_PASSWORD

**Example**:

```python
aws secretsmanager create-secret --name AUTH_BASIC_AUTH_JIRA_USERNAME --secret-string "your_jira_username"
aws secretsmanager create-secret --name AUTH_BASIC_AUTH_JIRA_PASSWORD --secret-string "your_jira_password"
```

2. **Example: Update Terraform Variables**

In your Terraform configuration (terraform/aws/variables.tf), ensure the following variables are set to reference your AWS Secrets Manager secrets:

```
variable "environment_vars" {
  description = "Environment variables to launch the lambda with"
  type        = map(any)

  default = {
    SECRET_MANAGER                       = "aws_secret_manager"
    CLIENT_SECRET                        = "arn:aws:secretsmanager:us-west-2:123456789012:secret:CLIENT_SECRET"
    PSEUDONYMIZE_SALT                    = "arn:aws:secretsmanager:us-west-2:123456789012:secret:SALT_SECRET"
    PSEUDONYMIZE_EMAIL_DOMAINS_ALLOWLIST = "example.com"
    AUTH_BASIC_AUTH_JIRA_USERNAME        = "arn:aws:secretsmanager:us-west-2:123456789012:secret:JIRA_USERNAME"
    AUTH_BASIC_AUTH_JIRA_PASSWORD        = "arn:aws:secretsmanager:us-west-2:123456789012:secret:JIRA_PASSWORD"
  }

  # ... (validation and other settings)
}

```

### Configuration Details

Guardette uses a policy file (.guardette/policy.yml) to determine how to handle incoming API requests. This file is generated using the policygen.py script based on the policygen.config.json configuration.

- **policygen.config.json**: Defines the sources and their specific configurations.
- **scripts/policygen/policygen.py**: Processes the configuration and generates the policy YAML file.

**Sample Policy Template**

Here's an example of a policy template for a Google Workspace Calendar source:

```yaml
  host: www.googleapis.com
  auth: gcp_service_account
  rules:
    - route: "GET /calendar/v3/calendars/{calendarId}"
      actions:
        - kind: redact
          json_paths:
            - "$.summary"
    - route: "GET /calendar/v3/calendars/{calendarId}/events"
      actions:
        - kind: redact
          json_paths:
            - "$..summary"
            - "$..displayName"
            - "$.items[*].summary"
        - kind: remove
          json_paths:
            - "$.items[*].attachments"
            - "$.items[*].conferenceData"
            - "$.items[*].extendedProperties"
        - kind: pseudonymize_email
          json_paths:
            - "$..email"
        - kind: filter_regex
          json_paths:
            - "$.items[*].description"
          regex_pattern: '\b(https:\/\/[^.]+\.greenhouse\.io\/[^\s]+|https://[^.]+\.ashbyhq\.com\/[^\s]+)\b'
          delimiter: " "
```

**Authentication Handlers**

Guardette supports multiple authentication handlers, such as `basic_auth`, `bearer_token`, and `gcp_service_account`. These handlers are defined in the guardette/default_auth/ directory and registered in the auth.py module.

**How Authentication Handlers Work**

When defining an authentication handler in your policy (e.g., `basic_auth:jira`), Guardette expects specific environment variables to retrieve the necessary credentials. The handler's registration in basic_auth.py dictates which environment variables to look for. For example, if you register an authentication handler as `basic_auth:jira`, Guardette will require the following environment variables:

- AUTH_BASIC_AUTH_JIRA_USERNAME
- AUTH_BASIC_AUTH_JIRA_PASSWORD

These variables should contain the username and password, respectively, for Jira. Guardette will fetch these secrets from AWS Secrets Manager based on their names and use them to authenticate API requests.

## Development Setup
```
brew install pre-commit
pre-commit install

python -m venv .venv
source .venv/bin/activate
```

### Install Dependencies
```
pip install -e ".[dev]"
```

### Building the Wheel
```
python -m build
```

### Running Tests
```
python -m pytest
```

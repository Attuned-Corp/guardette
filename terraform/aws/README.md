### Deploying Guardette on AWS

Guardette can be deployed as an AWS Lambda function using Terraform. Follow these steps to deploy:

1. **Configure Environment Variables**

Ensure the following environment variables are set:

- AWS_REGION: Your AWS region (e.g., us-west-2)
- TAG: (Optional) Docker image tag. Defaults to latest if not specified.

2. **Build and Push the Docker Image**

Setup AWS ECR

```python
make ecr
```

Run the following command to build the Docker image and push it to AWS ECR

```python
make deploy TAG=your-desired-tag
```

This command performs the following actions:

- **Login to AWS ECR**: Authenticates Docker with AWS Elastic Container Registry.
- **Build the Container**: Builds the Docker image specified in the Dockerfile.
- **Push the Image**: Pushes the Docker image to your ECR repository.
- **Deploy with Terraform**: Uses Terraform to deploy the Lambda function along with the necessary API Gateway configuration.

3. **Verify Deployment**

After deployment, Terraform will output the API endpoint. You can test the proxy by sending requests to this endpoint.

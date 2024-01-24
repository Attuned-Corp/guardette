AWS_REGION := $(shell eval "aws configure get region")
IMAGE_TAG := $(or ${TAG},latest)
ECR_NAME := guardette_repo

IMAGE_NAME := guardette_container

REGISTRY_ID := $(shell aws ecr \
		describe-repositories \
		--region $(AWS_REGION) \
		--query 'repositories[?repositoryName == `'$(IMAGE_NAME)'`].registryId' \
		--output text)

IMAGE_URI := $(REGISTRY_ID).dkr.ecr.$(AWS_REGION).amazonaws.com

ecr:
		@echo "** Creating the ECR repository **"
		cd terraform && \
		terraform init && \
		terraform apply -target=aws_ecr_repository.$(ECR_NAME) -auto-approve

deploy:
		@echo "** Login to AWS ECR **"
		aws ecr get-login-password --region $(AWS_REGION) | \
		docker login --username AWS --password-stdin $(IMAGE_URI)

		@echo "** Building and pushing the container **"
		docker build -t $(IMAGE_URI)/$(IMAGE_NAME):$(IMAGE_TAG) . && \
		docker push $(IMAGE_URI)/$(IMAGE_NAME):$(IMAGE_TAG)

		@echo "** Deploying API Gateway and Lambda"
		cd terraform && \
		terraform apply -var="image_version=$(IMAGE_TAG)" -var="aws_region=$(AWS_REGION)" -auto-approve

destroy:
		@echo "** Destroying deployed resources **"
		cd terraform && \
		terraform destroy -auto-approve

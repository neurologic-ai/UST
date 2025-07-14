# 🚀 AWS Lambda Container Deployment

This project deploys an AWS Lambda function using a Docker image stored in Amazon ECR.

# ⚡️ Architecture Overview
[S3 Bucket] ──▶ [Lambda 2: S3 Trigger] ──▶ [Lambda 1: Chunk Processor]
1️⃣ Lambda 2: Triggered when a new CSV is uploaded to S3, and invokes Lambda 1.
2️⃣ Lambda 1: Processes each chunk (normalize, classify, store).

Note: Lambda 2 code is in lamdda_package_divider folder, and Lambda 1 code is in lambda_package_processer folder.
    When creating the docker image for lambda 2, make sure the folder has global-bundle.pem inside the folder.
    When creating the docker image for lambda 1, make sure the folder has global-bundle.pem and user.json(GCP credentials file for gemini api) inside the folder.


## 📌 Prerequisites

Before you begin, make sure you have:

- ✅ **AWS CLI** installed and configured (`aws configure`)  
- ✅ **Docker** installed with `buildx` enabled  

---


## 📌 Full Deployment Commands (Single Flow)

Replace **ALL** placeholders (`<...>`) with your actual values before running.

```bash
# 🔑 Authenticate Docker to your ECR registry
aws ecr get-login-password --region <AWS_REGION> | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com

# 🐳 Build and push the Docker image to ECR
docker buildx build --platform linux/amd64 -t <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/<ECR_REPOSITORY_NAME>:latest . --push

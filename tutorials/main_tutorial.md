# Prerequisites

## AWS Setup
As the first step, we need to set up our infrastructure. In this tutorial, we'll use AWS to:
- create a Kubernetes cluster
- store data on S3 buckets
If you already have your Kubernetes cluster or use a different cloud provider, skip this section and adapt the following sections to point to your infrastructure.

1. AWS account: You need to have an AWS account with either admin access or at least a user with IAM permissions for creating ECR, EKS and ECS resources.
2. Install [AWS CLI v2](https://aws.amazon.com/cli/)
3. Configure AWS CLI with your AWS account (with `aws configure`)

## EKSCTL
AWS EKS is a service provided by AWS to create and manage your Kubernetes Cluster.
Eksctl is an utility for creating and managing Kubernets cluster an Amazon EKS.
- Install eksctl followint this tutorial: https://docs.aws.amazon.com/eks/latest/userguide/getting-started-eksctl.html

## Docker image storage

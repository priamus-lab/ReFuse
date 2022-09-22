# Prerequisites

## AWS Setup
As the first step, we need to set up our infrastructure. In this tutorial, we'll use AWS to:
- create a Kubernetes cluster
- store data on S3 buckets
If you already have your Kubernetes cluster or use a different cloud provider, skip this section and adapt the following sections to point to your infrastructure.

1. AWS account: You need to have an AWS account with either admin access or at least a user with IAM permissions for creating ECR, EKS and ECS resources.
2. Install [AWS CLI v2](https://aws.amazon.com/cli/)
3. Configure AWS CLI with your AWS account (with `aws configure`)

## Docker 
You need Docker installed. For the installation refer to the [official documentation](https://docs.docker.com/get-docker/). 

### Docker Image Storage
Kubernetes on AWS works well with AWS ECR, which is a registry for your Docker images. Alternatively, you could use [Dockerhub](https://hub.docker.com/) to store Docker image. In that case skip this section.

* To authenticate the terminal with the ECR account:
```
aws ecr get-login-password --region <YOUR_AWS_REGION> | docker login --username AWS --password-stdin <YOUR_ECR_REGISTRY_ID>.dkr.ecr.<YOUR_AWS_REGION>.amazonaws.com
```
* If you get Login Succeeded message, you can create your ECR repositories for your data pipelines:
```
aws ecr create-repository --repository-name prefect-flow-imperviousness
```

## Kubernetes Cluster
### eksctl
AWS EKS is a service provided by AWS to create and manage your Kubernetes Cluster.
Eksctl is an utility for creating and managing Kubernets cluster an Amazon EKS.
- Install eksctl following this tutorial: https://docs.aws.amazon.com/eks/latest/userguide/getting-started-eksctl.html

### kubectl
You need kubectl installed to connect to your cluster. Generally, newer installation of Docker also installs kubectl.

### Cluster creation
You can create a Kubernetes cluster with AWS EKS by using eksctl. If you already have a Kubernetes Cluster skip this step.
```
eksctl create cluster --name fargate-eks --region <YOUR_AWS_REGION> --fargate
```
Note that the command starts creating a Kubernetes cluster backed by Fargate, the serverless service offered by AWS. The --fargate flag makes sure that a Fargate profile is produced specifically for this cluster. In this way, we will pay just for the computation you need. 
As a result, we can host a serverless Kubernetes cluster on EKS and only pay for active pods, not the underlying EC2 instances they are operating on.
We suggest using dedicated lightweight server instances for always-on core functionalities and Fargate for on-demand heavy computations in a production environment. 

N.B.: When the container orchestration system must first allocate and prepare the compute resources, cold start is a potential drawback of practically every serverless solution.
You can choose to use a traditional Kubernetes cluster if your data workloads demand very little latency.

After cluster creation you can check you can connect to the cluster (eksctl update automatically the Kubernetes context) with: 
```
kubectl config current-context
```
and the output should be similar to:
```
<AWS_USER_NAME>@fargate-eks.<YOUR_AWS_REGION>.eksctl.io
```
To check further, you can print compute nodes of your cluster with:
```
kubectl get nodes
```


## Prefect Setup
1. Sign up for a free account on [Prefect Cloud](https://cloud.prefect.io/). Prefect Cloud is a managed version of Prefect Server offered with a free tier for easy experimentation. 
You can also proceed to install the open-source [Prefect Server](https://github.com/PrefectHQ/server) on your infrastracture following the official documentation.
N.B.: in this work, we used Prefect 1.0, but a 2.0 version of Prefect Cloud is available now. Please, be sure to use Prefect Cloud 1.0.

2. If you proceeded with Prefect Cloud, be sure to switch the local Prefect context to Cloud with:
```
prefect backend cloud
```

3. From Prefect Cloud dashboard create a [Prefect Service Account](https://docs-v1.prefect.io/orchestration/ui/team-settings.html#service-accounts) to authenticate the local terminal with Prefect Cloud. This will allow to register your flows (i.e. your ETL & ML data pipelines) to the Prefect Cloud directly from your computer.
From the Dashoboard you need to create a Service account and at least an API KEY. Copy you API Token and in the terminal run the following command:
```
prefect auth login -t <API_KEY>
```
Now you can register flows to be orchestrated from Prefect Cloud.

# Flow Run
First of all test you environment: execute the test flow in test-flow-py running the main at the bottom of the file

## Build and Push Docker Image
1. Build image using Dockerfile in "docker" folder
2. Push image on AWS ECR (or DockerHub). For AWS ECR you can follow instruction provided by AWS ECR inside the AWS Console GUI.

## Deploy Prefect Kubernetes Agent
TODO

## Register the prediction flow
1. "generate-map-imperviousness.py" contains the code of the flow. Launch the main with the register function at the bottom of the file.

## Run the prediction flow
TODO

# Cleanup resources
After experimenting, make sure to delete the AWS EKS cluster and the ECR repositories to avoid any charges:

```
eksctl delete cluster -n fargate-eks --wait
aws ecr delete-repository --repository-name prefect-flow-imperviousness
```

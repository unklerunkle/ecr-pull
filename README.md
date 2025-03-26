Prerequisites:
1) AWS Profile configured
2) Permissions to GetAuthorizationToken and DescribeRepositories for the ECR Service
3) Find the repo to pulldown using the DescribeRepositories permission

This Python script automates the process of extracting and analyzing container images from AWS Elastic Container Registry (ECR) using Podman instead of Docker
-  Authentication to AWS ECR using a provided AWS CLI Profile
-  Pulls container images from a specified ECR repo
-  Creates Podman containers from each pulled image
-  Mounts the container filesystem using podman unshare podman mount
-  Creates a symlink to each mounted image under a mounts/ directory for easy reference
-  Generates helper scripts that:
-    Open a podman unshare shell
-    Automatically cd into the mounted container filesystem

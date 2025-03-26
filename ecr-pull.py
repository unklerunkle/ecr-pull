import subprocess
import boto3
import os
import argparse

def run(cmd, capture_output=False):
    print(f"[*] Running: {cmd}")
    result = subprocess.run(cmd, shell=True, text=True, capture_output=capture_output)
    if result.returncode != 0:
        print(f"[!] Command failed: {cmd}")
        print(result.stderr)
    return result.stdout.strip() if capture_output else None

def login_to_ecr(profile, registry):
    session = boto3.Session(profile_name=profile)
    ecr = session.client('ecr')
    token_data = ecr.get_authorization_token()
    proxy = token_data['authorizationData'][0]['proxyEndpoint']

    login_cmd = f"aws ecr get-login-password --profile {profile} | podman login --username AWS --password-stdin {proxy}"
    run(login_cmd)

    return proxy.replace("https://", "")

def get_repositories(profile):
    session = boto3.Session(profile_name=profile)
    ecr = session.client('ecr')
    repos = ecr.describe_repositories()
    return [r['repositoryName'] for r in repos['repositories']]

def get_tags(profile, repo):
    session = boto3.Session(profile_name=profile)
    ecr = session.client('ecr')
    images = ecr.list_images(repositoryName=repo)
    return [img['imageTag'] for img in images.get('imageIds', []) if 'imageTag' in img]

def automate_podman(profile, repo, registry):
    tags = get_tags(profile, repo)
    for tag in tags:
        image = f"{registry}/{repo}:{tag}"
        container_name = f"{repo.replace('/', '_')}-container"

        print(f"[+] Pulling image: {image}")
        run(f"podman pull {image}")

        print(f"[+] Creating container: {container_name}")
        run(f"podman create --replace --name {container_name} {image}")

        print("[+] Mounting container (with podman unshare)...")
        mount_cmd = f"podman unshare podman mount {container_name}"
        mount_path = run(mount_cmd, capture_output=True)

        if mount_path:
            print(f"[✓] Mounted at: {mount_path}")
            os.makedirs("mounts", exist_ok=True)
            link_name = f"mounts/{container_name}_mount"
            if not os.path.exists(link_name):
                os.symlink(mount_path, link_name)
                print(f"[→] Symlinked to: {link_name}")

            # Create a helper script to enter the unshare namespace and cd into the mount
            helper_script = f"enter_{container_name}.sh"
            with open(helper_script, "w") as f:
                f.write("#!/bin/bash\n")
                f.write(f"podman unshare bash -c 'cd {mount_path} && exec bash'\n")
            os.chmod(helper_script, 0o755)
            print(f"[→] Helper script created: ./{helper_script}")
            print(f"[🧪] Run './{helper_script}' to explore the mounted image in namespace")
        print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, help="AWS CLI profile name")
    parser.add_argument("--repo", required=True, help="ECR repository name (e.g. hl/route-optimization)")
    args = parser.parse_args()

    profile = args.profile
    repo = args.repo

    print("[*] Logging into ECR...")
    registry = login_to_ecr(profile, repo)

    print("[*] Starting automation...")
    automate_podman(profile, repo, registry)

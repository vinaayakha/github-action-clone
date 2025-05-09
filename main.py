import os
import yaml
import docker
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import subprocess
import re
from dotenv import load_dotenv

app = FastAPI()

class CommitAuthor(BaseModel):
    name: str
    email: str
    username: str

class Commit(BaseModel):
    id: str
    message: str
    author: CommitAuthor
    committer: CommitAuthor
    added: List[str]
    removed: List[str]
    modified: List[str]

class HeadCommit(BaseModel):
    id: str
    message: str
    author: CommitAuthor
    committer: CommitAuthor
    added: List[str]
    removed: List[str]
    modified: List[str]

class WebhookPayload(BaseModel):
    ref: str
    before: str
    after: str
    repository: Dict[str, Any]
    head_commit: HeadCommit
    commits: List[Commit]

def is_charts_only_commit(modified_files: List[str]) -> bool:
    """Check if the commit only modified files in the charts directory."""
    return all(file.startswith('charts/') for file in modified_files)

def update_values_file(branch: str, image_tag: str, repo_dir: str):
    """Update the appropriate values file with the new image tag."""
    values_file = os.path.join(repo_dir, 'charts/values.yaml' if branch == 'main' else 'charts/values-prod.yaml')
    
    if not os.path.exists(values_file):
        raise HTTPException(status_code=404, detail=f"Values file {values_file} not found")
    
    with open(values_file, 'r') as f:
        values = yaml.safe_load(f)
    
    # Update the image tag in the values file
    if 'image' not in values:
        values['image'] = {}
    values['image']['tag'] = image_tag
    
    with open(values_file, 'w') as f:
        yaml.dump(values, f, default_flow_style=False)

def build_and_push_docker_image(repo: str, sha: str, branch: str):
    """Build and push Docker image to GitHub Container Registry."""
    try:
        # Load environment variables
        load_dotenv()
        github_user = os.getenv('userId')
        github_token = os.getenv('ghp_token')
        
        if not github_user or not github_token:
            raise HTTPException(
                status_code=500,
                detail="GitHub credentials not found in environment variables"
            )
        
        # Create repos directory if it doesn't exist
        repos_dir = "repos"
        os.makedirs(repos_dir, exist_ok=True)
        
        # Add repos directory to .gitignore if not already there
        gitignore_path = ".gitignore"
        if not os.path.exists(gitignore_path):
            with open(gitignore_path, "w") as f:
                f.write("repos/\n")
        else:
            with open(gitignore_path, "r+") as f:
                content = f.read()
                if "repos/" not in content:
                    f.write("\nrepos/\n")
        
        # Clone the repository using GitHub credentials
        repo_dir = os.path.join(repos_dir, repo.split("/")[-1])
        if not os.path.exists(repo_dir):
            clone_url = f"https://{github_user}:{github_token}@github.com/{repo}.git"
            subprocess.run(
                ["git", "clone", clone_url, repo_dir],
                check=True
            )
        
        # Fetch all branches and tags
        subprocess.run(
            ["git", "fetch", "--all"],
            cwd=repo_dir,
            check=True
        )
        
        # Checkout to the specific commit
        subprocess.run(
            ["git", "checkout", sha],
            cwd=repo_dir,
            check=True
        )
        
        # Initialize Docker client
        client = docker.from_env()

        # Login to GitHub Container Registry
        client.login(
            username=github_user,
            password=github_token,
            registry="ghcr.io"
        )
        
        print(f"{client.images.list()}")
        
        # Build the image from the cloned repository
        base_image_tag = f"ghcr.io/{repo}:sha-{sha[:7]}"
        client.images.build(path=repo_dir, tag=base_image_tag)
        
        # Add additional tags based on branch
        if branch == 'main':
            # For main branch, add 'latest' and 'dev' tags
            client.images.get(base_image_tag).tag(f"ghcr.io/{repo}:latest")
            client.images.get(base_image_tag).tag(f"ghcr.io/{repo}:dev")
        elif branch == 'production':
            # For production branch, add 'prod' tag
            client.images.get(base_image_tag).tag(f"ghcr.io/{repo}:prod")
        
        # Push all tags
        client.images.push(base_image_tag)
        if branch == 'main':
            client.images.push(f"ghcr.io/{repo}:latest")
            client.images.push(f"ghcr.io/{repo}:dev")
        elif branch == 'production':
            client.images.push(f"ghcr.io/{repo}:prod")
        
        return base_image_tag
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build/push Docker image: {str(e)}")

def commit_and_push_changes(branch: str, repo_dir: str):
    """Commit and push changes to the repository."""
    try:
        subprocess.run(['git', 'config', '--global', 'user.email', 'github-actions@github.com'], check=True)
        subprocess.run(['git', 'config', '--global', 'user.name', 'GitHub Actions'], check=True)
        
        # Change to the repository directory
        os.chdir(repo_dir)
        
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', f'Update image tag for {branch} branch'], check=True)
        subprocess.run(['git', 'push', 'origin', branch], check=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Failed to commit/push changes: {str(e)}")


@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/github/webhook")
async def github_webhook(payload: WebhookPayload):
    # Extract branch name from ref
    branch_match = re.match(r'refs/heads/(.*)', payload.ref)
    if not branch_match:
        raise HTTPException(status_code=400, detail="Invalid ref format")
    
    branch = branch_match.group(1)
    
    # Check if this is a charts-only commit
    if is_charts_only_commit(payload.head_commit.modified):
        return {"message": "Skipping build for charts-only commit"}
    
    # Only process main and production branches
    if branch not in ['main', 'production']:
        return {"message": f"Skipping build for branch {branch}"}
    
    # Build and push Docker image
    repo = payload.repository['full_name']
    repo_dir = os.path.join("repos", repo.split("/")[-1])
    image_tag = build_and_push_docker_image(repo, payload.head_commit.id, branch)
    
    # Update values file
    # update_values_file(branch, image_tag, repo_dir)
    
    # Commit and push changes
    # commit_and_push_changes(branch, repo_dir)
    
    return {
        "message": "Webhook processed successfully",
        "branch": branch,
        "image_tag": image_tag
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

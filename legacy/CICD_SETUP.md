# GitHub Actions CI/CD Setup Guide

## Overview

This repository uses GitHub Actions for automated deployment to VPS. Every push to the `main` branch triggers a build and deployment pipeline.

## Prerequisites

1. **GitHub Repository**: Code must be in a GitHub repository
2. **VPS Access**: SSH access to your VPS (178.156.170.161)
3. **GitHub Personal Access Token**: For container registry access

## Setup Instructions

### Step 1: Create GitHub Personal Access Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a name: "DemestiChat CI/CD"
4. Select scopes:
   - ✅ `write:packages` (to push Docker images)
   - ✅ `read:packages` (to pull Docker images)
5. Click "Generate token"
6. **Copy the token** (you won't see it again!)

### Step 2: Add GitHub Secrets

Go to your repository → Settings → Secrets and variables → Actions → New repository secret

Add the following secrets:

#### 1. `VPS_HOST`

```text
178.156.170.161
```

#### 2. `VPS_USER`

```text
root
```

#### 3. `VPS_SSH_KEY`

Your private SSH key (the one you use to access the VPS)

To get your SSH key:

```bash
cat ~/.ssh/id_rsa
```

Copy the entire output including:

```text
-----BEGIN OPENSSH PRIVATE KEY-----
...
-----END OPENSSH PRIVATE KEY-----
```

> [!WARNING]
> Never commit your private SSH key to the repository!

### Step 3: Configure VPS

SSH into your VPS and ensure Docker is logged in to GitHub Container Registry:

```bash
ssh root@178.156.170.161

# Login to GitHub Container Registry
echo YOUR_GITHUB_TOKEN | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

### Step 4: Test Deployment

1. Make a small change (e.g., update README)
2. Commit and push to `main` branch:

   ```bash
   git add .
   git commit -m "Test CI/CD deployment"
   git push origin main
   ```

3. Go to GitHub → Actions tab
4. Watch the workflow run
5. Verify deployment at <https://demestichat.beltlineconsulting.co/>

## Workflow Details

### Automatic Triggers

- **Push to `main`**: Automatically builds and deploys
- **Manual trigger**: Go to Actions → Deploy to VPS → Run workflow

### Build Process

1. Checkout code
2. Build Docker images for `agent` and `streamlit`
3. Push images to GitHub Container Registry (ghcr.io)
4. Tag with commit SHA and `latest`

### Deployment Process

1. SSH into VPS
2. Pull latest images from registry
3. Stop current containers
4. Start new containers
5. Run health checks
6. Rollback if health checks fail

### Health Checks

- **Agent**: `http://localhost:8000/health`
- **Streamlit**: `http://localhost:8501`

If either fails, deployment is rolled back automatically.

## Local Development

For local development, you can still use docker-compose normally:

```bash
# Build and run locally
docker-compose up --build

# The workflow won't affect local development
```

The `docker-compose.yml` supports both:

- **Local builds**: `docker-compose up --build`
- **Registry images**: Set `AGENT_IMAGE` and `STREAMLIT_IMAGE` environment variables

## Troubleshooting

### Workflow fails at "Build and push" step

- Check that your GitHub token has `write:packages` permission
- Verify the repository name matches the image prefix

### Deployment fails at health check

- Check VPS logs: `ssh root@178.156.170.161 'docker logs demestihas-agent'`
- Verify services are running: `docker ps`

### SSH connection fails

- Verify `VPS_SSH_KEY` secret is correct
- Test SSH manually: `ssh -i ~/.ssh/id_rsa root@178.156.170.161`

## Manual Deployment

If you need to deploy manually:

```bash
ssh root@178.156.170.161
cd /root/demestihas-ai
./scripts/deploy.sh
```

## Rollback

To rollback to a previous version:

```bash
ssh root@178.156.170.161
cd /root/demestihas-ai

# Find previous image SHA
docker images | grep demestihas

# Set environment variables to use specific version
export AGENT_IMAGE="ghcr.io/menedemestihas/demestihas-agent:main-abc123"
export STREAMLIT_IMAGE="ghcr.io/menedemestihas/demestihas-streamlit:main-abc123"

# Restart with specific version
docker-compose down
docker-compose up -d
```

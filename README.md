# GitHub Actions Clone

A lightweight alternative to GitHub Actions that provides automated build and deployment workflows for your repositories. This project implements a webhook-based system that automatically builds Docker images and manages deployments based on repository events.

## Features

- 🐳 Automated Docker image building and pushing to GitHub Container Registry
- 🔄 Webhook-based event handling for repository updates
- 🌿 Support for different branch strategies (main/production)
- 🔒 Secure credential management
- 📦 Automatic version tagging based on commit SHA and branch
- 🚀 FastAPI-based webhook server

## Prerequisites

- Python 3.8+
- Docker
- GitHub account with repository access
- GitHub Container Registry access

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd <your-repo-directory>
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Create a `.env` file in the project root with the following variables:
```env
userId=your_github_username
ghp_token=your_github_personal_access_token
```

2. Ensure your GitHub token has the necessary permissions:
   - `repo` scope for repository access
   - `write:packages` for pushing to GitHub Container Registry

## Usage

1. Start the webhook server:
```bash
python main.py
```

2. Configure your GitHub repository webhook:
   - Go to your repository settings
   - Navigate to Webhooks
   - Add a new webhook
   - Set the Payload URL to `http://your-server:8000/github/webhook`
   - Set Content type to `application/json`
   - Select events: Push events

## How It Works

1. When a push event occurs in your repository, GitHub sends a webhook to the server
2. The server processes the webhook payload and extracts relevant information
3. For main and production branches:
   - Clones the repository
   - Builds a Docker image
   - Tags the image based on commit SHA and branch
   - Pushes the image to GitHub Container Registry
4. The server responds with the build status and image tag

## Branch Strategy

- `main` branch:
  - Tags: `latest`, `dev`, and commit SHA
- `production` branch:
  - Tags: `prod` and commit SHA

## API Endpoints

- `GET /`: Health check endpoint
- `POST /github/webhook`: Webhook endpoint for GitHub events

## Development

To run the server in development mode with auto-reload:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## License

[Your chosen license]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

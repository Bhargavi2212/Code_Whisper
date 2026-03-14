#!/usr/bin/env bash
# Create Cloud Build trigger: push to main -> build + deploy to Cloud Run
# Run once after connecting GitHub to Cloud Build (see docs/cloud-build-trigger-setup.md).

set -e
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project)}"
REGION="${REGION:-us-central1}"

echo "Project: $PROJECT_ID"
echo "Creating trigger 'codewhisper-deploy' for branch main -> cloudbuild.yaml"

gcloud builds triggers create github \
  --name="codewhisper-deploy" \
  --repo-owner="weeklyweights-a11y" \
  --repo-name="CodeWhisper" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml"

echo "Done. Push to main will now build and deploy to Cloud Run."

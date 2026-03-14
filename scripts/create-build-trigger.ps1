# Create Cloud Build trigger: push to main -> build + deploy to Cloud Run
# Run once after connecting GitHub to Cloud Build (see docs/cloud-build-trigger-setup.md).

$ErrorActionPreference = "Stop"
$project = if ($env:GOOGLE_CLOUD_PROJECT) { $env:GOOGLE_CLOUD_PROJECT } else { (gcloud config get-value project 2>$null) }

Write-Host "Project: $project"
Write-Host "Creating trigger 'codewhisper-deploy' for branch main -> cloudbuild.yaml"

gcloud builds triggers create github `
  --name="codewhisper-deploy" `
  --repo-owner="weeklyweights-a11y" `
  --repo-name="CodeWhisper" `
  --branch-pattern="^main$" `
  --build-config="cloudbuild.yaml"

Write-Host "Done. Push to main will now build and deploy to Cloud Run."

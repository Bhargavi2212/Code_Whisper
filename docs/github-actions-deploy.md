# Deploy on push: GitHub Actions

When you **push to `main`**, the workflow [.github/workflows/deploy-cloudrun.yml](../.github/workflows/deploy-cloudrun.yml) runs and deploys to Cloud Run (build → push image → deploy).

## One-time setup

### 1. Create a GCP service account for GitHub Actions

In [Google Cloud Console](https://console.cloud.google.com/):

1. **IAM & Admin** → **Service accounts** → **Create** (e.g. name: `github-actions-deploy`).
2. Grant these roles:
   - **Cloud Build Editor**
   - **Service Account User**
   - **Cloud Run Admin**
   - **Artifact Registry Writer** (or **Storage Admin** if the registry is in GCS)
3. **Keys** → **Add key** → **Create new key** → **JSON** → download the JSON file.

### 2. Add GitHub secrets

In your repo: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.

| Secret           | Value |
|------------------|--------|
| `GCP_PROJECT_ID` | Your GCP project ID (e.g. `my-project-123`) |
| `GCP_SA_KEY`     | Entire contents of the service account JSON key file |

### 3. Ensure GCP is ready

- APIs enabled: Cloud Build, Artifact Registry, Cloud Run.
- Artifact Registry repo exists:  
  `gcloud artifacts repositories create codewhisper-repo --repository-format=docker --location=us-central1`

After this, every **push to `main`** will run the workflow and deploy. Set `GOOGLE_API_KEY` on the Cloud Run service (Edit revision → Variables) so the app can call Gemini.

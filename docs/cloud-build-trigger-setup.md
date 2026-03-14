# Deploy on push: Cloud Build trigger

Once this is set up, **every push to `main`** will run `cloudbuild.yaml` (build → push to Artifact Registry → deploy to Cloud Run).

## 1. One-time: Connect GitHub to Cloud Build

1. Open [Google Cloud Console](https://console.cloud.google.com/) and select your project.
2. Go to **Cloud Build** → **Triggers**.
3. Click **Connect repository** (or **Manage connected repositories**).
4. Choose **GitHub (Cloud Build GitHub App)** or **2nd gen** and follow the steps to install the app and select `weeklyweights-a11y/CodeWhisper`.
5. Finish the connection so the repo appears under Cloud Build.

## 2. Create the trigger

**Option A: Console**

1. **Cloud Build** → **Triggers** → **Create trigger**.
2. Name: `codewhisper-deploy`.
3. Event: **Push to a branch**.
4. Source: your connected **CodeWhisper** repo.
5. Branch: `^main$`.
6. Configuration: **Cloud Build configuration file**; path: `cloudbuild.yaml`.
7. Create.

**Option B: gcloud (1st-gen GitHub connection)**

If your repo is connected as 1st-gen GitHub, from the repo root run:

```bash
# Linux/macOS
./scripts/create-build-trigger.sh

# Or manually:
gcloud builds triggers create github \
  --name="codewhisper-deploy" \
  --repo-owner="weeklyweights-a11y" \
  --repo-name="CodeWhisper" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml"
```

Windows (PowerShell): `.\scripts\create-build-trigger.ps1`

**Option B (2nd-gen):**

```bash
# Replace CONNECTION_NAME and REPO_NAME with your connection/repo from:
# gcloud builds connections list --region=us-central1
# gcloud builds repositories list --region=us-central1 --connection=CONNECTION_NAME

gcloud builds triggers create github \
  --name="codewhisper-deploy" \
  --repository="projects/PLASMA_DATUM_PROJECT_ID/locations/us-central1/connections/CONNECTION_NAME/repositories/REPO_NAME" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml" \
  --region=us-central1
```

## 3. Set API key in Cloud Run

After the first deploy, set `GOOGLE_API_KEY` (and optionally `GOOGLE_GENAI_USE_VERTEXAI=FALSE`) on the Cloud Run service so the app can call Gemini:

- **Cloud Run** → select **codewhisper** → **Edit & deploy new revision** → **Variables & secrets** → add `GOOGLE_API_KEY`.

From then on, **git push origin main** will build and deploy automatically.

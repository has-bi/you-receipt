# Deploying to Google Cloud (Cheapest Path)

The pharmacy stock OCR service runs perfectly on Google Cloud Run with images built by Cloud Build and stored in Artifact Registry. This document expands every step so you can go from a blank project to a secured production deployment while staying inside the free tier whenever traffic is low.

---

## 0. Architecture & Cost Snapshot

| Component | Purpose | Cost Notes |
| --------- | ------- | ---------- |
| Cloud Build | Builds Docker image from repo and pushes to Artifact Registry | 120 build-min/day free. A typical build for this app takes ~2-3 minutes. |
| Artifact Registry | Container image storage | $0.10/GB-month. One image ~300 MB ⇒ ~$0.03/month. Clean old versions to stay free. |
| Cloud Run (fully managed) | Hosts FastAPI container | Pay only per request. Free tier: 2M vCPU-sec + 1 GiB RAM-sec + 2M requests monthly. Set `--min-instances 0` to avoid idle cost. |
| Secret Manager | Stores API keys + `credentials.json` | First 6 versions/month free per secret. |
| Cloud Storage + Google Sheets | Already required by the app | Charged separately; keep region consistent to avoid egress. |

> Pick a single region (e.g., `asia-southeast2` for Jakarta/Singapore or `us-central1` for global) for Cloud Run, Artifact Registry, and GCS buckets to minimize latency and egress.

---

## 1. Local Environment Preparation

1. **Install gcloud (Linux/WSL)**
   ```bash
   sudo apt-get update && sudo apt-get install apt-transport-https ca-certificates gnupg
   echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | \
     sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list
   curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | \
     sudo tee /usr/share/keyrings/cloud.google.gpg >/dev/null
   sudo apt-get update && sudo apt-get install google-cloud-cli
   ```

2. **Install gcloud (Windows PowerShell)** – if you prefer Windows, use the installer from <https://cloud.google.com/sdk/docs/install>. When using WSL, avoid calling the Windows binary to prevent Python/protobuf crashes like `AttributeError: google._upb._message`.

3. **Authenticate & select project**
   ```bash
   gcloud init                 # login + choose existing project or create a new one
   gcloud config list          # verify core/project and compute/region defaults
   ```

4. **Verify billing** – open <https://console.cloud.google.com/billing/projects> and ensure the project is linked to a billing account (free tier still requires it).

---

## 2. Define Common Variables

Add these exports to your terminal (adjust region/project/repository names). Reuse them for all commands below:

```bash
export REGION="asia-southeast1"          # or your preferred region
export PROJECT_ID="youvit-ai-chatbot"
export REPO="youvit"
export SERVICE="pharmacy-stock-ocr"
export IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE}"
```

Apply defaults so `gcloud` doesn’t prompt each time:

```bash
gcloud config set project "$PROJECT_ID"
gcloud config set run/region "$REGION"
gcloud config set artifacts/location "$REGION"
```

---

## 3. Enable Required APIs

Run once per project:

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  sheets.googleapis.com \
  drive.googleapis.com \
  storage.googleapis.com
```

Verify with `gcloud services list --enabled`.

---

## 4. Create a Dedicated Service Account (Recommended)

While Cloud Run can use the default Compute Engine service account, creating a scoped account keeps permissions tight.

```bash
SA_NAME="youvit-runner"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud iam service-accounts create "$SA_NAME" \
  --display-name "Youvit Receipt Cloud Run"
```

Grant exactly the roles the app needs:

```bash
ROLES=( \
  roles/run.invoker \
  roles/secretmanager.secretAccessor \
  roles/storage.objectAdmin \
  roles/iam.serviceAccountTokenCreator \
  roles/iam.serviceAccountUser \
  roles/drive.reader \
  roles/sheets.editor \
)
for ROLE in "${ROLES[@]}"; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="$ROLE"
done
```

> **Sheets access:** Share both Google Sheets (master + output) with this service account email so the Sheets API can read/write.

---

## 5. Authentication Strategy: Local vs Cloud

This app uses a dual authentication approach that works seamlessly in both environments:

### Local Development
- Uses `.env` file with `GOOGLE_APPLICATION_CREDENTIALS=credentials.json`
- Requires a service account JSON file (`credentials.json`) in the project root
- Download this file from GCP Console → IAM & Admin → Service Accounts

### Cloud Run Deployment
- Uses **Application Default Credentials (ADC)** automatically
- NO credentials file needed - Cloud Run provides authentication via the service account you specify with `--service-account`
- The app detects the Cloud Run environment and falls back to ADC when `GOOGLE_APPLICATION_CREDENTIALS` is not set

This is why we don't need to create a `sa-credentials` secret - Cloud Run handles authentication for us!

---

## 6. Load Secrets into Secret Manager

| Secret | Contents | Command |
| ------ | -------- | ------- |
| `mistral-api-key` | `MISTRAL_API_KEY` string | `printf "%s" "YOUR_MISTRAL_KEY" \| gcloud secrets create mistral-api-key --data-file=-` |
| `openai-api-key` | `OPENAI_API_KEY` string | same pattern |
| `master-sheet-id` | `MASTER_SHEET_ID` value | same |
| `output-sheet-id` | `OUTPUT_SHEET_ID` value | same |
| `gcs-bucket-name` | `GCS_BUCKET_NAME` value | same |
| `gcs-project-id` | `GCS_PROJECT_ID` value | same |

**Note:** No `sa-credentials` secret is needed! Cloud Run automatically provides credentials through the service account (`--service-account` flag).

**Automated approach:** Use the provided script:
```bash
./create_secrets.sh
```

This script reads values from your `.env` file and creates all secrets automatically.

To update an existing secret, use `gcloud secrets versions add SECRET --data-file=-`. Confirm creation:

```bash
gcloud secrets list
gcloud secrets versions list mistral-api-key
```

> If you hit protobuf-related crashes, ensure you are running the Linux gcloud binary (see §1). The secret is created even if crash happens afterwards; just rerun the verification commands.

---

## 7. Prepare Artifact Registry

```bash
gcloud artifacts repositories create "$REPO" \
  --repository-format=docker \
  --location="$REGION" \
  --description="Youvit Receipt images"
```

Check repository:

```bash
gcloud artifacts repositories describe "$REPO" --location="$REGION"
```

---

## 8. Build Container with Cloud Build

1. **Ensure repo contains** `Dockerfile`, `.dockerignore`, and application files.
2. **Submit build from repo root:**
   ```bash
   gcloud builds submit --tag "$IMAGE"
   ```
3. **Watch logs:** Cloud Build streams logs in the terminal. After success, note the Image digest.
4. **Verify image exists:**
   ```bash
   gcloud artifacts docker images list "${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}"
   ```

> Cloud Build uses a temporary GCP service account. If you need to allow access to private Git submodules, configure `cloudbuild.yaml` + substitutions, but the default `gcloud builds submit` works for this repo.

---

## 9. Deploy to Cloud Run

### 9.1 Compose Environment + Secrets

For each secret, use `--set-secrets KEY=secret-name:latest`. If you have non-sensitive defaults, include them via `--set-env-vars`.

```bash
SECRET_FLAGS=$(cat <<'VARS'
--set-secrets MISTRAL_API_KEY=mistral-api-key:latest \
--set-secrets OPENAI_API_KEY=openai-api-key:latest \
--set-secrets MASTER_SHEET_ID=master-sheet-id:latest \
--set-secrets OUTPUT_SHEET_ID=output-sheet-id:latest \
--set-secrets GCS_BUCKET_NAME=gcs-bucket-name:latest \
--set-secrets GCS_PROJECT_ID=gcs-project-id:latest
VARS
)
```

**Authentication:** The app automatically uses Application Default Credentials (ADC) in Cloud Run. No credentials file needed!

### 9.2 Deploy Command

```bash
gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --platform managed \
  --region "$REGION" \
  --service-account "$SA_EMAIL" \
  --cpu 1 \
  --memory 512Mi \
  --concurrency 80 \
  --min-instances 0 \
  --max-instances 2 \
  --timeout 600 \
  --allow-unauthenticated \
  $SECRET_FLAGS
```

**Rationale:**
- `--cpu 1 --memory 512Mi` fits the app and stays cheap.
- `--min-instances 0` ⇒ scale-to-zero.
- `--max-instances 2` caps spend while testing. Increase later if usage grows.
- `--timeout 600` gives enough time for large OCR batches.

After deployment, the CLI prints the service URL. Save it for the frontend (`https://SERVICE-xxxx-REGION.a.run.app`).

---

## 10. Post-Deployment Verification

1. **Check status:**
   ```bash
   gcloud run services describe "$SERVICE" --format='value(status.url,status.conditions)'
   ```
2. **Health endpoint:**
   ```bash
   curl -w '\n' "https://your-url/health"
   ```
3. **Manual smoke test:** open `/manual`, submit data, confirm Google Sheets updated and images in GCS.
4. **Logs:**
   ```bash
   gcloud run services logs read "$SERVICE" --limit=100
   ```
5. **Secrets access:** if startup fails with permissions error, confirm Cloud Run service account has `roles/secretmanager.secretAccessor` and secrets are in same project.

---

## 11. Monitoring & Cost Control

| Task | Command / UI |
| ---- | ------------- |
| Real-time metrics | Cloud Console → Cloud Run → Metrics tab. Set chart to CPU, memory, and requests. |
| Set budget alerts | Billing → Budgets & alerts → Create budget (e.g., $5). |
| Audit invocations | `gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=pharmacy-stock-ocr' --limit=50`. |
| Clean old builds | `gcloud builds list`, `gcloud builds delete BUILD_ID`. |
| Clean old images | `gcloud artifacts docker images delete IMAGE_URI --delete-tags --quiet`. |

Keep Cloud Run traffic and Artifact Registry storage tidy to stay well under free quotas.

---

## 12. Optional Automation

- **Cloud Build Trigger:** Connect GitHub/Cloud Source Repos and create a trigger so pushing to `main` rebuilds + redeploys automatically (`gcloud beta builds triggers create github ...`). Combine with a deploy step using Cloud Deploy or Cloud Build substitutions.
- **Service Rollback:** `gcloud run revisions list` to see revisions, `gcloud run services update-traffic SERVICE --to-revisions REVISION=100` to roll back instantly.

---

## 13. Troubleshooting

| Symptom | Likely Cause | Fix |
| ------- | ------------ | --- |
| `AttributeError: google._upb._message` while running `gcloud` | Mixing Windows gcloud binary with WSL Python libs | Install Linux gcloud CLI (Section 1) or run commands in native PowerShell instead of WSL. |
| Cloud Build fails because `.env` missing | Dockerfile copies `.env` but file absent | Remove the `COPY .env` line or ensure `.env` exists before building. Prefer secrets via Cloud Run. |
| Cloud Run deploy fails: `PERMISSION_DENIED` for Sheets/Storage | Service account lacks Sheets/Drive/Storage roles or sheets not shared | Assign roles listed in Section 4 and share sheets with `SA_EMAIL`. |
| Secret not found during deploy | Secret name mismatch or different project | Run `gcloud secrets list --project PROJECT_ID` and confirm names/versions. |
| App cannot reach APIs | Missing env variables or service account permissions | Ensure service account has required roles (Sheets, Storage) and secrets are properly mounted. Cloud Run uses ADC automatically. |
| High latency or 429 errors | Instances hitting concurrency limits | Increase `--max-instances` or reduce `--concurrency` to 40. Monitor Cloud Run metrics. |

---

## 14. Redeploy Workflow Cheat Sheet

```bash
# From repo root after making code changes
gcloud builds submit --tag "$IMAGE"

gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --platform managed \
  --service-account "$SA_EMAIL" \
  --allow-unauthenticated \
  $SECRET_FLAGS
```

Follow the verification steps every time to keep uptime high while still benefiting from the most affordable managed stack on GCP.

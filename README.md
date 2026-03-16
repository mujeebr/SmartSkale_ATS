## Resume Matcher – Architecture & Flow

This project exposes a resume–JD matching engine over several frontends:

- **FastAPI** and **Flask** backends for API access
- **Streamlit** UI for interactive use

All implementations share the same core services and abstractions under `src/`.

### Core abstractions

- `src/core/llm/base.py`
  - `LLMClient`: abstract interface with `generate(prompt: str) -> str`.

- `src/core/parsing/base.py`
  - `ParsedDocument`: dataclass holding `filename` and parsed `text`.
  - `DocumentParser`: abstract parser for `(filename, bytes) -> ParsedDocument`.

- `src/core/matching/base.py`
  - `ResumeMatcher`: abstract strategy with `evaluate(jd_text, resume_text) -> MatchResult`.

- `src/core/matching/models.py`
  - `MatchResult`: structured output (`match_percentage`, `summary`, `skills`, `recommendations`, `weaknesses`).

### Infrastructure implementations

- `src/infrastructure/llm/openai_client.py`
  - `OpenAIChatCompletionsClient` implements `LLMClient` using the OpenAI Chat Completions API.
  - Loads `OPENAI_API_KEY` from `.env` via `python-dotenv`.

- `src/infrastructure/parsing/document_parser.py`
  - `DefaultDocumentParser` implements `DocumentParser` for DOCX, PDF, and TXT files.

### Services

- `src/services/llm_json_matcher.py`
  - `LLMJsonResumeMatcher` implements `ResumeMatcher` by:
    - Building a JSON-instruction prompt from the JD and resume.
    - Calling the injected `LLMClient`.
    - Parsing the model response into a `MatchResult`.

- `src/services/resume_matcher.py`
  - `ResumeMatchingService` orchestrates:
    - Parsing raw files via `DocumentParser`.
    - Matching via `ResumeMatcher`.
    - Returning plain `dict` payloads suitable for APIs and UI.

### Dependency container

- `src/container.py`
  - `get_llm_client()`: returns a singleton `OpenAIChatCompletionsClient`.
  - `get_document_parser()`: returns a singleton `DefaultDocumentParser`.
  - `get_resume_matcher()`: wires `LLMJsonResumeMatcher` with the shared LLM client.
  - `get_resume_matching_service()`: exposes a singleton `ResumeMatchingService` used by all entrypoints.

### FastAPI flow (backend/fastapi_app.py)

1. **Request in**  
   - `/match` (`POST`, form): expects `jd_text` and `resume_text` as plain strings.  
   - `/match-files` (`POST`, multipart): expects `jd_text` plus one or more `files` uploads.

2. **Endpoint handler**
   - Both endpoints call `get_resume_matching_service()` from `src.container`.
   - `/match` directly calls:
     - `ResumeMatchingService.match_text(jd_text, resume_text)`  
   - `/match-files`:
     - Reads each `UploadFile` into `(filename, bytes)` tuples.
     - Calls `ResumeMatchingService.match_files(jd_text, files)`.

3. **Service orchestration**
   - For `match_text`:
     - Calls `ResumeMatcher.evaluate(jd_text, resume_text)` (via `LLMJsonResumeMatcher`).
     - Converts the returned `MatchResult` into a plain `dict`.
   - For `match_files`:
     - For each file:
       - Uses `DocumentParser.parse(filename, bytes)` (via `DefaultDocumentParser`) to produce `ParsedDocument`.
       - Calls `match_text(jd_text, parsed.text)` to get a `dict` result.
       - Attaches the original `filename`.
     - Returns a list of result dictionaries.

4. **Matching & LLM invocation**
   - `LLMJsonResumeMatcher.evaluate`:
     - Builds a detailed natural-language prompt that instructs the model to respond **only in JSON** with the expected keys.
     - Calls `LLMClient.generate(prompt)` (the OpenAI-backed client).
     - Extracts and parses the JSON portion of the response.
     - Normalises types (e.g. skills list, integer percentage) into a `MatchResult`.

5. **LLM client**
   - `OpenAIChatCompletionsClient.generate`:
     - Ensures `OPENAI_API_KEY` is loaded.
     - Calls `OpenAI().chat.completions.create(model="gpt-4o-mini", messages=[...])`.
     - Returns `response.choices[0].message.content` to the matcher.

6. **Response out**
   - FastAPI automatically serialises the result `dict` / list of `dict` to JSON over HTTP.

### Flask flow (backend/flask_app.py)

The Flask app uses the same `ResumeMatchingService`:

1. `create_app()` wires three routes:
   - `/health` – returns `{"status": "ok"}`.
   - `/match` – reads `jd_text` and `resume_text` from `request.form`.
   - `/match-files` – reads `jd_text` and uploaded `files` from `request.files`.

2. Handlers call `get_resume_matching_service()` exactly like FastAPI.
3. Flask returns `jsonify(...)` of the service results.

### Streamlit flow (frontend/streamlit_app.py and app.py)

1. `app.py` simply imports and calls `frontend.streamlit_app.run()`.
2. `run()`:
   - Renders text area for `jd_text`.
   - Renders file uploader for multiple resumes.
   - On submit:
     - Builds `(filename, bytes)` pairs from uploaded files.
     - Calls `get_resume_matching_service()` and then `match_files(jd_text, files)`.
   - Displays `match_percentage`, `summary`, `skills`, `recommendations`, and `weaknesses` for each file.

### Legacy helpers

- `matcher.py`:
  - `evaluate_resume(jd_text, resume_text)` → delegates to `ResumeMatchingService.match_text`.

- `resume_parser.py`:
  - `extract_text(file)` → converts a file-like object into text using `get_document_parser()`.

- `llm_utils.py`:
  - `get_llm_response(prompt)` → forwards to `get_llm_client().generate(prompt)`.

These wrappers allow older code and notebooks to keep using simple functions while the internals stay modular and testable.

## How to deploy this project on AWS (for beginners)

This section walks you **step by step** from a fresh AWS account to having this API running on the internet.  
You have **two main options**:

- **Option 1 – EC2 (no Docker)**: simplest to understand if you are new to containers.
- **Option 2 – EC2 + Docker**: cleaner and more portable once you are comfortable with Docker.

You can follow **either** option. Start with **Option 1** if you’re unsure.

---

### Common AWS prerequisites (do this once)

- **Create an AWS account** and log in to the AWS Management Console.
- **Choose a region** (top-right of the console), for example `us-east-1`. You should deploy everything in this one region.
- **Create a key pair (for SSH)**:
  - Go to **EC2 → Key pairs → Create key pair**.
  - Name it something like `resume-matcher-key`.
  - Download the `.pem` file and keep it safe on your computer.
- **Understand your costs**: use a small instance type like `t3.small` or `t3.medium`. Stop instances when not using them.

On your **local machine**, fix the permissions of the key so SSH works:

```bash
chmod 400 /path/to/resume-matcher-key.pem
```

---

## Option 1 – Deploy on a plain EC2 instance (no Docker)

### 1. Launch the EC2 instance

- In the AWS console, go to **EC2 → Instances → Launch instances**.
- **Name**: `resume-matcher-ec2`.
- **AMI**: choose **Ubuntu Server 22.04 LTS** (x86_64).
- **Instance type**: `t3.small` or `t3.medium`.
- **Key pair**: select the key pair you just created (for example `resume-matcher-key`).
- **Network settings → Security group**:
  - Allow **SSH (TCP 22)** from **My IP**.
  - Add a rule for **HTTP (TCP 80)** from **Anywhere** (later we will run the app on port 80).
  - (For quick testing, you can also allow **Custom TCP 8000** from **My IP**.)
- Click **Launch instance**.

When the instance is running, note the **Public IPv4 address** (for example `3.88.XXX.XXX`).

### 2. SSH into the instance

On your local machine (replace the key path and IP):

```bash
ssh -i /path/to/resume-matcher-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

If this works, you are logged into your EC2 server.

### 3. Install system packages

On the EC2 instance:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git nginx
```

### 4. Copy this project to EC2

You have two simple choices:

- **If your code is on GitHub**:

  ```bash
  cd /home/ubuntu
  git clone YOUR_REPO_URL assignment
  cd assignment
  ```

- **If your code is only on your laptop**:

  On your **local machine** (not inside EC2):

  ```bash
  cd /path/to/local/assignment
  scp -i /path/to/resume-matcher-key.pem -r . ubuntu@YOUR_EC2_PUBLIC_IP:/home/ubuntu/assignment
  ```

  Then on the **EC2 instance**:

  ```bash
  cd /home/ubuntu/assignment
  ```

From now on we assume:

```bash
cd /home/ubuntu/assignment
```

### 5. Create a Python virtual environment and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 6. Configure the OpenAI API key

On your **local machine**, get an API key from OpenAI and copy it.  
On the **EC2 instance**, create a `.env` file in the project root:

```bash
cd /home/ubuntu/assignment
cat > .env << 'EOF'
OPENAI_API_KEY="sk-REPLACE_WITH_YOUR_OPENAI_API_KEY"
EOF
```

Keep this key secret; never commit it to git.

### 7. Test the FastAPI app manually

Still on the EC2 instance, with the virtualenv active:

```bash
cd /home/ubuntu/assignment
source venv/bin/activate
uvicorn backend.fastapi_app:app --host 0.0.0.0 --port 8000
```

Leave this running and, on your **local machine**, open:

- `http://YOUR_EC2_PUBLIC_IP:8000/health`
- `http://YOUR_EC2_PUBLIC_IP:8000/docs`

If you can see the docs, the app is working. Press **Ctrl + C** in the EC2 terminal to stop it.

### 8. Run FastAPI as a systemd service (auto‑start on reboot)

This repo includes helper files in the `deploy/` folder:

- `deploy/start_fastapi.sh` – script that activates the venv and starts Uvicorn.
- `deploy/fastapi.service.example` – example `systemd` unit file.

#### 8.1 Adjust paths for your instance

- Edit `deploy/start_fastapi.sh` and set:
  - `APP_DIR=/home/ubuntu/assignment`
  - `VENV_DIR=/home/ubuntu/assignment/venv`
- Edit `deploy/fastapi.service.example` and set:
  - `User=ubuntu`
  - `WorkingDirectory=/home/ubuntu/assignment`
  - `Environment="PATH=/home/ubuntu/assignment/venv/bin"`
  - `ExecStart=/home/ubuntu/assignment/deploy/start_fastapi.sh`

Make the script executable:

```bash
cd /home/ubuntu/assignment
chmod +x deploy/start_fastapi.sh
```

#### 8.2 Install and start the service

```bash
sudo cp deploy/fastapi.service.example /etc/systemd/system/resume-matcher.service
sudo systemctl daemon-reload
sudo systemctl enable --now resume-matcher.service
```

Check that it’s running:

```bash
sudo systemctl status resume-matcher.service
```

Now the API runs automatically in the background and will restart on reboots.

### 9. Put Nginx in front so users can use port 80

We will keep FastAPI listening on port `8000` and let Nginx proxy `http://YOUR_EC2_PUBLIC_IP` (port 80) to it.

On the EC2 instance:

```bash
sudo rm /etc/nginx/sites-enabled/default
echo 'server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}' | sudo tee /etc/nginx/sites-available/resume-matcher.conf

sudo ln -s /etc/nginx/sites-available/resume-matcher.conf /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

Now you can open:

- `http://YOUR_EC2_PUBLIC_IP/health`
- `http://YOUR_EC2_PUBLIC_IP/docs`

---

## Option 2 – Deploy with Docker on an EC2 instance

This option packages the FastAPI backend into a Docker image using the existing `Dockerfile`.  
You can follow **only these steps** and ignore Option 1 entirely if you prefer Docker.

### 1. (Optional) Build and test Docker locally

On your **local machine**, from the project root:

```bash
docker build -t resume-matcher-api .
docker run --rm -p 8000:8000 \
  -e OPENAI_API_KEY="sk-REPLACE_WITH_YOUR_OPENAI_API_KEY" \
  resume-matcher-api
```

Open:

- `http://localhost:8000/health`
- `http://localhost:8000/docs`

If it works, stop the container with **Ctrl + C**.

### 2. Launch an EC2 instance for Docker

1. In the AWS console, go to **EC2 → Instances → Launch instances**.
2. **Name**: `resume-matcher-docker`.
3. **AMI**: choose **Ubuntu Server 22.04 LTS** (x86_64).
4. **Instance type**: `t3.small` or `t3.medium`.
5. **Key pair**: select your key pair (for example `resume-matcher-key`)- need to create a key 
- connect -ssh client for more details
6. **Network settings → Security group**:
   - Allow **SSH (TCP 22)** from **My IP**.
   - Allow **Custom TCP 8000** from **My IP** (for testing the API).
   - (Optional) Allow **HTTP (TCP 80)** from **Anywhere** if you plan to put Nginx in front later.
7. Click **Launch instance** and wait until its state is **running**.

Find the instance’s **Public IPv4 address** (for example `3.88.XXX.XXX`).

### 3. SSH into the EC2 instance

On your **local machine** (replace the key path and IP):

```bash
ssh -i /path/to/resume-matcher-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```
ssh -i "resume-matcher-docker.pem" ubuntu@ec2-3-107-104-106.ap-southeast-2.compute.amazonaws.com

You are now in the EC2 shell.

### 4. Install Docker on EC2

Run these commands on the EC2 instance:

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io
sudo usermod -aG docker ubuntu
```

Log out of the server:

```bash
exit
```

Then SSH back in so the `docker` group change takes effect:

```bash
ssh -i /path/to/resume-matcher-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
ssh -i "resume-matcher-docker.pem" ubuntu@ec2-3-107-104-106.ap-southeast-2.compute.amazonaws.com
```

### 5. Copy your code to EC2

On your **local machine**:

```bash
cd /path/to/local/assignment - on vs code 
scp -i /path/to/resume-matcher-key.pem -r . ubuntu@YOUR_EC2_PUBLIC_IP:/home/ubuntu/assignment
ssh -i "resume-matcher-docker.pem" ubuntu@ec2-3-107-104-106.ap-southeast-2.compute.amazonaws.com:/home/ubuntu/assignment - on vs code
```

to update the files

scp -i /Users/mac/Downloads/resume-matcher-docker.pem \
  backend/fastapi_app.py \
  ubuntu@ec2-3-107-104-106.ap-southeast-2.compute.amazonaws.com:/home/ubuntu/assignment/backend/fastapi_app.py


ssh -i /Users/mac/Downloads/resume-matcher-docker.pem \
  ubuntu@ec2-3-107-104-106.ap-southeast-2.compute.amazonaws.com


---

### Deploy via GitHub Actions (CI/CD): push to GitHub and auto-update EC2

You can have every **push to the `main` branch** automatically deploy the latest code to your EC2 instance (sync files, rebuild Docker, restart the container). No need to run `scp` or SSH manually.

#### One-time setup

1. **Add GitHub secrets** (repo → **Settings → Secrets and variables → Actions** → **New repository secret**):
   - **`SSH_PRIVATE_KEY`**: Paste the **entire contents** of your `.pem` file (the same one you use for `ssh -i resume-matcher-docker.pem`). Copy from the first line (e.g. `-----BEGIN RSA PRIVATE KEY-----`) to the last line (e.g. `-----END RSA PRIVATE KEY-----`).
   - **`EC2_HOST`**: Your EC2 hostname only, e.g. `ec2-3-107-104-106.ap-southeast-2.compute.amazonaws.com` (no `http://`, no `ubuntu@`, no path).
   - **`OPENAI_API_KEY`**: Your OpenAI API key (the same value you pass to `docker run -e OPENAI_API_KEY=...`).

2. **Default branch**: The workflow runs on push to **`main`**. If your default branch is **`master`**, either rename it to `main` in GitHub repo settings, or edit `.github/workflows/deploy-ec2.yml` and change `branches: [main]` to `branches: [master]`.

3. **EC2 already set up**: Your EC2 instance must already have Docker installed and the project directory at `/home/ubuntu/assignment` (from the initial copy/scp or clone). The workflow will **overwrite** files there (except `.env`, which it does not sync) and then rebuild/restart the container.

#### How it works

- On every **push to `main`**, GitHub Actions:
  1. Checks out the repo.
  2. Uses `SSH_PRIVATE_KEY` to connect to `EC2_HOST`.
  3. **Rsyncs** the repo into `/home/ubuntu/assignment` (excluding `.git`, `.env`, and the local `assignment/` venv folder).
  4. SSHs into EC2 and runs: `docker stop` → `docker rm` → `docker build` → `docker run` with `OPENAI_API_KEY` from secrets.

- You can also trigger the same workflow manually: **Actions** tab → **Deploy to EC2** → **Run workflow**.

After the first successful run, **pushing to `main`** is enough to update the live API on EC2.

---

Then, on the **EC2 instance**:

```bash
cd /home/ubuntu/assignment
```

### 6. Build the Docker image on EC2

On the EC2 instance:

```bash
cd /home/ubuntu/assignment
docker build -t resume-matcher-api .
```

Wait for the build to complete successfully (it may take a few minutes the first time).

### 7. Run the Docker container on EC2

Start the container, exposing port `8000` and passing your OpenAI API key:

```bash
docker run -d --name resume-matcher-api \
  -p 8000:8000 \
  -e OPENAI_API_KEY="" \
  resume-matcher-api
```

Check that the container is running:

```bash
docker ps
```

From your **local browser**, open:

- `http://YOUR_EC2_PUBLIC_IP:8000/health`
- `http://YOUR_EC2_PUBLIC_IP:8000/docs`

http://ec2-3-107-104-106.ap-southeast-2.compute.amazonaws.com:8000/health
http://ec2-3-107-104-106.ap-southeast-2.compute.amazonaws.com:8000/docs

or
http://3.107.104.106:8000/health
http://3.107.104.106:8000/docs

# for fronte end

 python3 -m http.server 3000  
http://localhost:3000/frontend/react_test_client.html

http://ec2-3-107-104-106.ap-southeast-2.compute.amazonaws.com:8000

cd /home/ubuntu/assignment
docker stop resume-matcher-api || true
docker rm resume-matcher-api || true
docker build -t resume-matcher-api .
docker run -d --name resume-matcher-api \
  -p 8000:8000 \
  -e OPENAI_API_KEY="sk-REPLACE_WITH_YOUR_OPENAI_API_KEY" \
  resume-matcher-api

If those URLs work, your Dockerized API is live on AWS.

### 8. (Optional) Put Nginx or a load balancer in front

- **Simple option**: install Nginx on the same EC2 instance, and configure it to proxy requests from port 80 to `http://127.0.0.1:8000` (similar to the Nginx setup in Option 1, but pointing to the Docker port).
- **More advanced option**: use an **Application Load Balancer** in front of one or more EC2 instances running this container.

---

## How to call the deployed API from a frontend

Once your API is running on EC2 (and reachable at something like  
`http://ec2-3-107-104-106.ap-southeast-2.compute.amazonaws.com:8000`), you can call it from any frontend.

### 1. Base URL to use

Replace `YOUR_API_BASE_URL` below with **your** URL:

- With DNS name:
  - `http://ec2-3-107-104-106.ap-southeast-2.compute.amazonaws.com:8000`
- Or with the raw IP (example):
  - `http://3.107.104.106:8000`

### 2. Calling `/match` from a React or plain JS frontend

Example using `fetch` (works in any browser app):

```javascript
const API_BASE_URL = "http://ec2-3-107-104-106.ap-southeast-2.compute.amazonaws.com:8000";

async function matchResume(jdText, resumeText) {
  const formData = new FormData();
  formData.append("jd_text", jdText);
  formData.append("resume_text", resumeText);

  const response = await fetch(`${API_BASE_URL}/match`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return await response.json(); // { match_percentage, summary, skills, ... }
}
```

You can call `matchResume(jd, resume)` from your components and display the returned JSON.

### 3. Calling `/match-files` with file uploads (frontend)

For uploading resume files from the browser:

```javascript
async function matchResumeFiles(jdText, files) {
  const formData = new FormData();
  formData.append("jd_text", jdText);

  for (const file of files) {
    formData.append("files", file); // "files" must match the FastAPI parameter name
  }

  const response = await fetch(`${API_BASE_URL}/match-files`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return await response.json(); // list of match results, one per file
}
```

### 4. Calling the API from a Python client (e.g. another backend or Streamlit)

If you have a separate Python app that should talk to this deployed API over HTTP:

```python
import requests

API_BASE_URL = "http://ec2-3-107-104-106.ap-southeast-2.compute.amazonaws.com:8000"

def match_text(jd_text: str, resume_text: str) -> dict:
  data = {"jd_text": jd_text, "resume_text": resume_text}
  resp = requests.post(f"{API_BASE_URL}/match", data=data)
  resp.raise_for_status()
  return resp.json()
```

For files:

```python
def match_files(jd_text: str, file_paths: list[str]) -> list[dict]:
  files = [("files", (path.split("/")[-1], open(path, "rb"))) for path in file_paths]
  data = {"jd_text": jd_text}
  resp = requests.post(f"{API_BASE_URL}/match-files", data=data, files=files)
  resp.raise_for_status()
  return resp.json()
```

### 5. Important: CORS for browser frontends

If your frontend runs on a **different origin** (for example `http://localhost:3000` for React) and you see a **CORS error** in the browser console, you need to enable CORS in the FastAPI app.

In `backend/fastapi_app.py`, you can add:

```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Resume Matcher API (FastAPI)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to ["http://localhost:3000", "https://your-frontend.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

After changing this file, rebuild and redeploy your Docker image on EC2 so the changes take effect.

---

If you follow the steps in **either Option 1 or Option 2** in order, you should be able to go from a fresh AWS account to a working, internet‑accessible deployment of this resume matcher service, and then connect any frontend to it via the URLs above.


### 1. Prepare the EC2 instance

- **Launch instance**: Use an Ubuntu 22.04 (or similar) EC2 instance.
- **Security group**:
  - Allow inbound TCP on port **8000** (or 80/443 if you put Nginx in front).
  - Restrict sources to your IP for testing if possible.

SSH into the instance:

```bash
ssh ubuntu@YOUR_EC2_PUBLIC_IP
```

### 2. Install system dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

### 3. Copy the project to EC2

On EC2, choose a directory (example: `/home/ubuntu/assignment`), then either:

- **Option A: git clone** your repo there, or  
- **Option B: scp/rsync** this local project folder to the instance:

```bash
mkdir -p /home/ubuntu
cd /home/ubuntu
# Example (adjust source path and SSH target):
scp -r /path/to/local/assignment ubuntu@YOUR_EC2_PUBLIC_IP:/home/ubuntu/
```

From now on, commands assume:

```bash
cd /home/ubuntu/assignment
```

### 4. Create virtualenv and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure environment variables

Create a `.env` file in `/home/ubuntu/assignment`:

```bash
cat > .env << 'EOF'
OPENAI_API_KEY="sk-...your-key-here..."
EOF
```

Make sure your key has sufficient quota and is kept secret.

### 6. Test FastAPI manually

Still on the instance, with the virtualenv active:

```bash
uvicorn backend.fastapi_app:app --host 0.0.0.0 --port 8000
```

From your local machine, you should be able to open:

- Swagger UI: `http://YOUR_EC2_PUBLIC_IP:8000/docs`
- Health check: `http://YOUR_EC2_PUBLIC_IP:8000/health`

Stop uvicorn with `Ctrl+C` once you have confirmed it works.

### 7. Run FastAPI as a systemd service

This repo includes example deployment files under `deploy/`:

- `deploy/start_fastapi.sh`: helper script that activates the venv and runs uvicorn.
- `deploy/fastapi.service.example`: example systemd unit file for production.

#### 7.1 Adjust paths for your instance

If your project directory or user differs from the defaults, edit:

- `deploy/start_fastapi.sh` → update `APP_DIR` and `VENV_DIR`.
- `deploy/fastapi.service.example` → update:
  - `User=ubuntu`
  - `WorkingDirectory=/home/ubuntu/assignment`
  - `Environment="PATH=/home/ubuntu/assignment/venv/bin"`
  - `ExecStart=.../uvicorn backend.fastapi_app:app --host 0.0.0.0 --port 8000`

Make the script executable:

```bash
chmod +x deploy/start_fastapi.sh
```

#### 7.2 Install the systemd service

Copy the service file to `/etc/systemd/system` with a meaningful name:

```bash
sudo cp deploy/fastapi.service.example /etc/systemd/system/resume-matcher.service
```

Reload systemd and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now resume-matcher.service
```

Check status and logs:

```bash
sudo systemctl status resume-matcher.service
journalctl -u resume-matcher.service -f
```

At this point, FastAPI should be running in the background and restart automatically on reboot.

### 8. (Optional) Put Nginx in front

For production, you can:

- Install Nginx: `sudo apt install -y nginx`
- Configure a server block that:
  - Listens on port 80/443.
  - Proxies to `http://127.0.0.1:8000`.

This gives you TLS termination, nicer URLs, and basic rate-limiting if needed.

## Steps to deploy with Docker on an EC2 instance

The repo also includes a `Dockerfile` for containerised deployments of the FastAPI backend.

### 1. Build and run locally (optional)

From the project root:

```bash
docker build -t resume-matcher-api .
```

Run the container, exposing FastAPI on port 8000 and injecting your OpenAI key:

```bash
docker run --rm -p 8000:8000 \
  -e OPENAI_API_KEY="" \
  resume-matcher-api
```

You can now open:

- `http://localhost:8000/health`
- `http://localhost:8000/docs`

### 2. Prepare the EC2 instance for Docker

1. Launch an Ubuntu EC2 instance and open **port 8000** (and/or 80/443) in the security group.
2. SSH into the instance:

```bash
ssh ubuntu@YOUR_EC2_PUBLIC_IP
```

3. Install Docker:

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io
sudo usermod -aG docker ubuntu
```

Log out and back in (or `newgrp docker`) so the `ubuntu` user can run Docker without `sudo`.

### 3. Copy code to EC2 and build the image

On your **local machine**, copy the project up (if you’re not using git/ECR):

```bash
scp -r /path/to/local/assignment ubuntu@YOUR_EC2_PUBLIC_IP:/home/ubuntu/
```

On the **EC2 instance**:

```bash
cd /home/ubuntu/assignment
docker build -t resume-matcher-api .
```

### 4. Run the container on EC2

Run FastAPI in Docker, passing the API key as an environment variable:

```bash
docker run -d --name resume-matcher-api \
  -p 8000:8000 \
  -e OPENAI_API_KEY="sk-...your-key..." \
  resume-matcher-api
```

Check that it’s running:

```bash
docker ps
```

From your local browser:

- `http://YOUR_EC2_PUBLIC_IP:8000/health`
- `http://YOUR_EC2_PUBLIC_IP:8000/docs`

### 5. (Optional) Persist and harden

- Use **Docker Compose** or a systemd service to ensure the container restarts on reboot.
- Put **Nginx** in front of the container (reverse proxy to `localhost:8000`) for TLS and nicer hostnames.
- Store `OPENAI_API_KEY` in a secrets manager or EC2 user data rather than hardcoding it in commands.



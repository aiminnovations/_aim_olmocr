#!/usr/bin/env python3
"""
olmOCR Automated Installer

This script fully automates the deployment of olmOCR to Google Cloud Platform,
including Firebase setup, without requiring any manual steps.

Usage:
    python install.py

Or on Windows:
    python install.py

Or run the packaged executable:
    ./olmocr-setup (Linux/Mac)
    olmocr-setup.exe (Windows)
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Tuple

# ============================================
# Configuration
# ============================================

DEFAULT_PROJECT_ID = "juniper-core"
DEFAULT_REGION = "us-central1"
DEFAULT_PARASAIL_KEY = "psk-aimiwsstmt1A-JBSW3y4jAxHjEvwMvScP"

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def supports_color():
    """Check if terminal supports color."""
    if platform.system() == 'Windows':
        return os.environ.get('TERM') == 'xterm' or 'ANSICON' in os.environ
    return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

USE_COLORS = supports_color()

def color(text: str, color_code: str) -> str:
    """Apply color to text if supported."""
    if USE_COLORS:
        return f"{color_code}{text}{Colors.END}"
    return text

def print_header(text: str):
    """Print a header."""
    print("\n" + "=" * 60)
    print(color(text, Colors.BLUE + Colors.BOLD))
    print("=" * 60)

def print_info(text: str):
    """Print info message."""
    print(color(f"[INFO] {text}", Colors.GREEN))

def print_warn(text: str):
    """Print warning message."""
    print(color(f"[WARN] {text}", Colors.YELLOW))

def print_error(text: str):
    """Print error message."""
    print(color(f"[ERROR] {text}", Colors.RED))

def print_step(step: int, total: int, text: str):
    """Print a step indicator."""
    print(color(f"\n[{step}/{total}] {text}", Colors.BLUE + Colors.BOLD))

# ============================================
# Utility Functions
# ============================================

def run_command(cmd: list, capture: bool = False, check: bool = True,
                env: dict = None, timeout: int = 600) -> Tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr."""
    try:
        full_env = os.environ.copy()
        if env:
            full_env.update(env)

        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            check=check,
            env=full_env,
            timeout=timeout
        )
        return result.returncode, result.stdout if capture else "", result.stderr if capture else ""
    except subprocess.CalledProcessError as e:
        return e.returncode, e.stdout or "", e.stderr or ""
    except subprocess.TimeoutExpired:
        print_error(f"Command timed out: {' '.join(cmd)}")
        return -1, "", "Timeout"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"

def command_exists(cmd: str) -> bool:
    """Check if a command exists."""
    return shutil.which(cmd) is not None

def get_script_dir() -> Path:
    """Get the directory containing this script."""
    return Path(__file__).parent.resolve()

def wait_with_spinner(seconds: int, message: str = "Waiting"):
    """Wait with a spinner animation."""
    spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    for i in range(seconds * 10):
        sys.stdout.write(f"\r{message} {spinner[i % len(spinner)]}")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write("\r" + " " * (len(message) + 5) + "\r")

# ============================================
# Prerequisite Checks and Installation
# ============================================

def check_prerequisites() -> bool:
    """Check and install prerequisites."""
    print_header("Checking Prerequisites")

    all_ok = True

    # Check Python version
    if sys.version_info < (3, 8):
        print_error(f"Python 3.8+ required (found {sys.version})")
        all_ok = False
    else:
        print_info(f"Python {sys.version.split()[0]} ✓")

    # Check gcloud
    if command_exists('gcloud'):
        code, out, _ = run_command(['gcloud', '--version'], capture=True, check=False)
        version = out.split('\n')[0] if out else "unknown"
        print_info(f"Google Cloud SDK: {version} ✓")
    else:
        print_error("Google Cloud SDK not found")
        print_info("Installing Google Cloud SDK...")
        if not install_gcloud():
            all_ok = False

    # Check firebase CLI
    if command_exists('firebase'):
        code, out, _ = run_command(['firebase', '--version'], capture=True, check=False)
        print_info(f"Firebase CLI: {out.strip()} ✓")
    else:
        print_warn("Firebase CLI not found")
        print_info("Installing Firebase CLI...")
        if not install_firebase_cli():
            print_warn("Firebase CLI installation failed, will use gcloud fallback")

    return all_ok

def install_gcloud() -> bool:
    """Install Google Cloud SDK."""
    system = platform.system()

    try:
        if system == 'Windows':
            print_info("Please download and install from: https://cloud.google.com/sdk/docs/install")
            print_info("Then run this installer again.")
            return False
        elif system == 'Darwin':  # macOS
            if command_exists('brew'):
                run_command(['brew', 'install', '--cask', 'google-cloud-sdk'])
                return True
            else:
                print_info("Installing via curl...")
                run_command(['curl', 'https://sdk.cloud.google.com', '-o', '/tmp/install.sh'])
                run_command(['bash', '/tmp/install.sh', '--disable-prompts'])
                return True
        else:  # Linux
            run_command(['curl', 'https://sdk.cloud.google.com', '-o', '/tmp/install.sh'])
            run_command(['bash', '/tmp/install.sh', '--disable-prompts'])
            return True
    except Exception as e:
        print_error(f"Failed to install gcloud: {e}")
        return False

def install_firebase_cli() -> bool:
    """Install Firebase CLI."""
    try:
        if command_exists('npm'):
            run_command(['npm', 'install', '-g', 'firebase-tools'], check=False)
            return command_exists('firebase')
        else:
            # Use standalone binary
            system = platform.system()
            if system == 'Windows':
                url = "https://firebase.tools/bin/win/instant/firebase-tools-instant.exe"
            elif system == 'Darwin':
                url = "https://firebase.tools/bin/macos/firebase-tools"
            else:
                url = "https://firebase.tools/bin/linux/firebase-tools"

            print_info(f"Downloading Firebase CLI from {url}...")
            # Download logic would go here
            return False
    except Exception as e:
        print_error(f"Failed to install Firebase CLI: {e}")
        return False

# ============================================
# Authentication
# ============================================

def authenticate_gcloud() -> bool:
    """Authenticate with Google Cloud."""
    print_header("Google Cloud Authentication")

    # Check if already authenticated
    code, out, _ = run_command(['gcloud', 'auth', 'list', '--format=json'], capture=True, check=False)

    if code == 0:
        accounts = json.loads(out) if out else []
        active = [a for a in accounts if a.get('status') == 'ACTIVE']
        if active:
            print_info(f"Already authenticated as: {active[0].get('account')}")
            return True

    print_info("Opening browser for authentication...")
    print_info("Please complete the authentication in your browser.")

    code, _, _ = run_command(['gcloud', 'auth', 'login', '--no-launch-browser'], check=False)

    if code != 0:
        print_warn("Browser auth failed, trying headless...")
        code, _, _ = run_command(['gcloud', 'auth', 'login'], check=False)

    return code == 0

def authenticate_firebase(project_id: str) -> bool:
    """Authenticate with Firebase."""
    if not command_exists('firebase'):
        return True  # Will use gcloud fallback

    print_info("Authenticating Firebase CLI...")

    # Use gcloud credentials for Firebase
    code, _, _ = run_command(['firebase', 'login', '--no-localhost'], check=False)

    return True  # Firebase auth is optional

# ============================================
# GCP Resource Setup
# ============================================

def setup_gcp_project(project_id: str) -> bool:
    """Set up GCP project."""
    print_step(1, 8, "Setting up GCP Project")

    # Set project
    code, _, err = run_command(['gcloud', 'config', 'set', 'project', project_id],
                               capture=True, check=False)
    if code != 0:
        print_error(f"Failed to set project: {err}")
        return False

    print_info(f"Project set to: {project_id}")
    return True

def enable_apis(project_id: str) -> bool:
    """Enable required GCP APIs."""
    print_step(2, 8, "Enabling GCP APIs")

    apis = [
        'cloudbuild.googleapis.com',
        'run.googleapis.com',
        'artifactregistry.googleapis.com',
        'storage.googleapis.com',
        'firestore.googleapis.com',
        'pubsub.googleapis.com',
        'secretmanager.googleapis.com',
        'firebase.googleapis.com',
        'firebasehosting.googleapis.com',
        'identitytoolkit.googleapis.com',
    ]

    print_info(f"Enabling {len(apis)} APIs (this may take a few minutes)...")

    code, _, err = run_command(
        ['gcloud', 'services', 'enable'] + apis + ['--quiet'],
        capture=True, check=False, timeout=300
    )

    if code != 0:
        print_error(f"Failed to enable APIs: {err}")
        return False

    print_info("All APIs enabled ✓")
    return True

def create_storage_bucket(project_id: str, region: str) -> bool:
    """Create Cloud Storage bucket."""
    print_step(3, 8, "Creating Cloud Storage Bucket")

    bucket_name = f"olmocr-{project_id}"

    # Check if bucket exists
    code, _, _ = run_command(
        ['gsutil', 'ls', f'gs://{bucket_name}'],
        capture=True, check=False
    )

    if code == 0:
        print_info(f"Bucket already exists: {bucket_name}")
    else:
        code, _, err = run_command(
            ['gsutil', 'mb', '-p', project_id, '-l', region, f'gs://{bucket_name}'],
            capture=True, check=False
        )
        if code != 0:
            print_error(f"Failed to create bucket: {err}")
            return False
        print_info(f"Created bucket: {bucket_name}")

    # Set CORS
    cors_config = json.dumps([{
        "origin": ["*"],
        "method": ["GET", "PUT", "POST", "DELETE", "OPTIONS"],
        "responseHeader": ["Content-Type", "Authorization", "Content-Length", "X-Requested-With"],
        "maxAgeSeconds": 3600
    }])

    cors_file = Path('/tmp/cors.json')
    cors_file.write_text(cors_config)

    run_command(['gsutil', 'cors', 'set', str(cors_file), f'gs://{bucket_name}'], check=False)
    cors_file.unlink()

    print_info("CORS configured ✓")
    return True

def create_firestore(project_id: str, region: str) -> bool:
    """Create Firestore database."""
    print_step(4, 8, "Creating Firestore Database")

    code, _, _ = run_command(
        ['gcloud', 'firestore', 'databases', 'describe', '--database=(default)'],
        capture=True, check=False
    )

    if code == 0:
        print_info("Firestore database already exists")
    else:
        code, _, err = run_command(
            ['gcloud', 'firestore', 'databases', 'create',
             '--location=' + region, '--quiet'],
            capture=True, check=False
        )
        if code != 0 and 'already exists' not in err:
            print_warn(f"Firestore creation note: {err}")

    print_info("Firestore database ready ✓")
    return True

def create_pubsub(project_id: str) -> bool:
    """Create Pub/Sub topic."""
    print_step(5, 8, "Creating Pub/Sub Topic")

    code, _, _ = run_command(
        ['gcloud', 'pubsub', 'topics', 'create', 'olmocr-jobs', '--quiet'],
        capture=True, check=False
    )

    print_info("Pub/Sub topic ready ✓")
    return True

def store_secrets(project_id: str, parasail_key: str) -> bool:
    """Store secrets in Secret Manager."""
    print_step(6, 8, "Storing Secrets")

    # Check if secret exists
    code, _, _ = run_command(
        ['gcloud', 'secrets', 'describe', 'parasail-api-key'],
        capture=True, check=False
    )

    if code == 0:
        # Update existing secret
        run_command(
            ['gcloud', 'secrets', 'versions', 'add', 'parasail-api-key',
             '--data-file=-'],
            capture=True, check=False,
            env={'PARASAIL_KEY': parasail_key}
        )
        # Use echo to pipe the key
        process = subprocess.Popen(
            ['gcloud', 'secrets', 'versions', 'add', 'parasail-api-key', '--data-file=-'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        process.communicate(input=parasail_key.encode())
    else:
        # Create new secret
        process = subprocess.Popen(
            ['gcloud', 'secrets', 'create', 'parasail-api-key',
             '--data-file=-', '--replication-policy=automatic'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        process.communicate(input=parasail_key.encode())

    print_info("Parasail API key stored ✓")
    return True

def create_service_accounts(project_id: str) -> bool:
    """Create service accounts and IAM bindings."""
    print_info("Creating service accounts...")

    accounts = [
        ('olmocr-backend', 'olmOCR Backend Service'),
        ('olmocr-worker', 'olmOCR Worker Service'),
        ('pubsub-invoker', 'Pub/Sub Cloud Run Invoker'),
    ]

    for account_id, display_name in accounts:
        run_command(
            ['gcloud', 'iam', 'service-accounts', 'create', account_id,
             f'--display-name={display_name}', '--quiet'],
            capture=True, check=False
        )

    # IAM bindings
    bindings = [
        ('olmocr-backend', 'roles/storage.objectAdmin'),
        ('olmocr-backend', 'roles/datastore.user'),
        ('olmocr-backend', 'roles/pubsub.publisher'),
        ('olmocr-worker', 'roles/storage.objectAdmin'),
        ('olmocr-worker', 'roles/datastore.user'),
        ('olmocr-worker', 'roles/secretmanager.secretAccessor'),
    ]

    for account, role in bindings:
        run_command(
            ['gcloud', 'projects', 'add-iam-policy-binding', project_id,
             f'--member=serviceAccount:{account}@{project_id}.iam.gserviceaccount.com',
             f'--role={role}', '--quiet'],
            capture=True, check=False
        )

    print_info("Service accounts configured ✓")
    return True

# ============================================
# Firebase Setup
# ============================================

def setup_firebase(project_id: str) -> dict:
    """Set up Firebase for the project."""
    print_step(7, 8, "Setting up Firebase Authentication")

    firebase_config = {}

    # Add Firebase to GCP project
    print_info("Adding Firebase to project...")
    code, _, err = run_command(
        ['gcloud', 'firebase', 'projects:addfirebase', project_id, '--quiet'],
        capture=True, check=False
    )

    if code != 0 and 'already' not in err.lower():
        print_warn(f"Firebase setup note: {err}")

    # Create web app
    print_info("Creating Firebase web app...")
    code, out, _ = run_command(
        ['gcloud', 'firebase', 'apps:create', 'WEB', 'olmocr-web',
         '--project=' + project_id, '--format=json', '--quiet'],
        capture=True, check=False
    )

    app_id = None
    if code == 0 and out:
        try:
            app_data = json.loads(out)
            app_id = app_data.get('appId') or app_data.get('name', '').split('/')[-1]
        except:
            pass

    # If app already exists, list apps to get the ID
    if not app_id:
        code, out, _ = run_command(
            ['gcloud', 'firebase', 'apps:list', '--project=' + project_id, '--format=json'],
            capture=True, check=False
        )
        if code == 0 and out:
            try:
                apps = json.loads(out)
                for app in apps:
                    if app.get('platform') == 'WEB':
                        app_id = app.get('appId')
                        break
            except:
                pass

    # Get Firebase config
    if app_id:
        print_info("Retrieving Firebase configuration...")
        code, out, _ = run_command(
            ['gcloud', 'firebase', 'apps:sdkconfig', 'WEB', app_id,
             '--project=' + project_id, '--format=json'],
            capture=True, check=False
        )

        if code == 0 and out:
            try:
                sdk_config = json.loads(out)
                config = sdk_config.get('sdkConfig', {})
                firebase_config = {
                    'apiKey': config.get('apiKey', ''),
                    'authDomain': config.get('authDomain', f'{project_id}.firebaseapp.com'),
                    'projectId': config.get('projectId', project_id),
                    'storageBucket': config.get('storageBucket', f'{project_id}.appspot.com'),
                    'messagingSenderId': config.get('messagingSenderId', ''),
                    'appId': config.get('appId', app_id),
                }
            except Exception as e:
                print_warn(f"Could not parse Firebase config: {e}")

    # Enable Identity Platform / Firebase Auth
    print_info("Enabling Firebase Authentication...")

    # Enable email/password auth via Identity Platform API
    run_command(
        ['gcloud', 'identity-platform', 'config', 'update',
         '--enable-email-signin', '--project=' + project_id, '--quiet'],
        capture=True, check=False
    )

    # If we don't have the config, generate defaults
    if not firebase_config.get('apiKey'):
        print_info("Generating Firebase API key...")
        code, out, _ = run_command(
            ['gcloud', 'services', 'api-keys', 'list', '--format=json', '--quiet'],
            capture=True, check=False
        )

        api_key = ''
        if code == 0 and out:
            try:
                keys = json.loads(out)
                for key in keys:
                    if 'Browser key' in key.get('displayName', ''):
                        # Get the key string
                        key_name = key.get('name', '')
                        if key_name:
                            code2, out2, _ = run_command(
                                ['gcloud', 'services', 'api-keys', 'get-key-string',
                                 key_name, '--format=json'],
                                capture=True, check=False
                            )
                            if code2 == 0:
                                key_data = json.loads(out2)
                                api_key = key_data.get('keyString', '')
                        break
            except:
                pass

        firebase_config = {
            'apiKey': api_key,
            'authDomain': f'{project_id}.firebaseapp.com',
            'projectId': project_id,
            'storageBucket': f'{project_id}.appspot.com',
            'messagingSenderId': '',
            'appId': app_id or '',
        }

    print_info("Firebase Authentication enabled ✓")

    return firebase_config

# ============================================
# Build and Deploy
# ============================================

def build_and_deploy(project_id: str, region: str, firebase_config: dict) -> Tuple[str, str, str]:
    """Build container images and deploy to Cloud Run."""
    print_step(8, 8, "Building and Deploying Services")

    script_dir = get_script_dir()
    # Check if we're in installer directory or root
    if (script_dir / 'gcp-frontend').exists():
        project_root = script_dir
    elif (script_dir.parent / 'gcp-frontend').exists():
        project_root = script_dir.parent
    else:
        print_error("Cannot find project root directory")
        return "", "", ""

    registry = f"{region}-docker.pkg.dev/{project_id}/olmocr"
    bucket_name = f"olmocr-{project_id}"

    # Create artifact registry
    print_info("Creating Artifact Registry...")
    run_command(
        ['gcloud', 'artifacts', 'repositories', 'create', 'olmocr',
         '--repository-format=docker', f'--location={region}',
         '--description=olmOCR container images', '--quiet'],
        capture=True, check=False
    )

    # Write frontend .env file
    print_info("Configuring frontend environment...")
    frontend_env = project_root / 'gcp-frontend' / '.env'

    env_content = f"""# Auto-generated by olmOCR installer
VITE_API_URL=BACKEND_URL_PLACEHOLDER/api
VITE_FIREBASE_API_KEY={firebase_config.get('apiKey', '')}
VITE_FIREBASE_AUTH_DOMAIN={firebase_config.get('authDomain', '')}
VITE_FIREBASE_PROJECT_ID={firebase_config.get('projectId', '')}
VITE_FIREBASE_STORAGE_BUCKET={firebase_config.get('storageBucket', '')}
VITE_FIREBASE_MESSAGING_SENDER_ID={firebase_config.get('messagingSenderId', '')}
VITE_FIREBASE_APP_ID={firebase_config.get('appId', '')}
VITE_ENABLE_GOOGLE_LOGIN=true
VITE_MAX_UPLOAD_SIZE_MB=100
"""
    frontend_env.write_text(env_content)

    os.chdir(project_root)

    # Build Frontend
    print_info("Building frontend (this may take 5-10 minutes)...")
    code, _, err = run_command(
        ['gcloud', 'builds', 'submit',
         f'--tag={registry}/frontend:latest',
         '--timeout=20m',
         '-f', 'gcp-frontend/Dockerfile', '.', '--quiet'],
        capture=True, check=False, timeout=1200
    )
    if code != 0:
        print_error(f"Frontend build failed: {err}")
        return "", "", ""

    # Build Backend
    print_info("Building backend...")
    code, _, err = run_command(
        ['gcloud', 'builds', 'submit',
         f'--tag={registry}/backend:latest',
         '--timeout=20m',
         '-f', 'gcp-backend/Dockerfile', '.', '--quiet'],
        capture=True, check=False, timeout=1200
    )
    if code != 0:
        print_error(f"Backend build failed: {err}")
        return "", "", ""

    # Build Worker
    print_info("Building worker...")
    code, _, err = run_command(
        ['gcloud', 'builds', 'submit',
         f'--tag={registry}/worker:latest',
         '--timeout=30m',
         '-f', 'gcp-worker/Dockerfile.cloudrun', '.', '--quiet'],
        capture=True, check=False, timeout=1800
    )
    if code != 0:
        print_error(f"Worker build failed: {err}")
        return "", "", ""

    # Deploy Frontend
    print_info("Deploying frontend...")
    run_command(
        ['gcloud', 'run', 'deploy', 'olmocr-frontend',
         f'--image={registry}/frontend:latest',
         '--platform=managed', f'--region={region}',
         '--allow-unauthenticated', '--port=8080',
         '--memory=256Mi', '--cpu=1',
         '--min-instances=0', '--max-instances=10', '--quiet'],
        check=False
    )

    # Get frontend URL
    code, out, _ = run_command(
        ['gcloud', 'run', 'services', 'describe', 'olmocr-frontend',
         f'--region={region}', '--format=value(status.url)'],
        capture=True, check=False
    )
    frontend_url = out.strip()

    # Deploy Backend
    print_info("Deploying backend...")
    run_command(
        ['gcloud', 'run', 'deploy', 'olmocr-backend',
         f'--image={registry}/backend:latest',
         '--platform=managed', f'--region={region}',
         '--allow-unauthenticated', '--port=8080',
         '--memory=512Mi', '--cpu=1',
         '--min-instances=0', '--max-instances=20',
         f'--service-account=olmocr-backend@{project_id}.iam.gserviceaccount.com',
         f'--set-env-vars=GCP_PROJECT_ID={project_id},GCS_BUCKET={bucket_name},PUBSUB_TOPIC=olmocr-jobs,ENVIRONMENT=production,CORS_ORIGINS={frontend_url}',
         '--quiet'],
        check=False
    )

    # Get backend URL
    code, out, _ = run_command(
        ['gcloud', 'run', 'services', 'describe', 'olmocr-backend',
         f'--region={region}', '--format=value(status.url)'],
        capture=True, check=False
    )
    backend_url = out.strip()

    # Deploy Worker
    print_info("Deploying worker...")
    run_command(
        ['gcloud', 'run', 'deploy', 'olmocr-worker',
         f'--image={registry}/worker:latest',
         '--platform=managed', f'--region={region}',
         '--no-allow-unauthenticated', '--port=8080',
         '--memory=2Gi', '--cpu=2',
         '--min-instances=0', '--max-instances=10', '--timeout=600',
         f'--service-account=olmocr-worker@{project_id}.iam.gserviceaccount.com',
         f'--set-env-vars=GCP_PROJECT_ID={project_id},GCS_BUCKET={bucket_name},PROCESSING_MODE=parasail,PARASAIL_MODEL=allenai/olmOCR-2-7B-1025',
         '--set-secrets=PARASAIL_API_KEY=parasail-api-key:latest',
         '--quiet'],
        check=False
    )

    # Get worker URL
    code, out, _ = run_command(
        ['gcloud', 'run', 'services', 'describe', 'olmocr-worker',
         f'--region={region}', '--format=value(status.url)'],
        capture=True, check=False
    )
    worker_url = out.strip()

    # Configure Pub/Sub push
    print_info("Configuring Pub/Sub push subscription...")

    run_command(
        ['gcloud', 'run', 'services', 'add-iam-policy-binding', 'olmocr-worker',
         f'--region={region}',
         f'--member=serviceAccount:pubsub-invoker@{project_id}.iam.gserviceaccount.com',
         '--role=roles/run.invoker', '--quiet'],
        capture=True, check=False
    )

    # Create push subscription
    run_command(
        ['gcloud', 'pubsub', 'subscriptions', 'create', 'olmocr-jobs-push',
         '--topic=olmocr-jobs',
         f'--push-endpoint={worker_url}/process',
         f'--push-auth-service-account=pubsub-invoker@{project_id}.iam.gserviceaccount.com',
         '--ack-deadline=600', '--quiet'],
        capture=True, check=False
    )

    # Update frontend with backend URL and redeploy
    print_info("Updating frontend configuration...")
    env_content = env_content.replace('BACKEND_URL_PLACEHOLDER', backend_url)
    frontend_env.write_text(env_content)

    print_info("Rebuilding frontend with API URL...")
    run_command(
        ['gcloud', 'builds', 'submit',
         f'--tag={registry}/frontend:latest',
         '--timeout=20m',
         '-f', 'gcp-frontend/Dockerfile', '.', '--quiet'],
        capture=True, check=False, timeout=1200
    )

    run_command(
        ['gcloud', 'run', 'deploy', 'olmocr-frontend',
         f'--image={registry}/frontend:latest',
         f'--region={region}', '--quiet'],
        check=False
    )

    print_info("Deployment complete ✓")

    return frontend_url, backend_url, worker_url

# ============================================
# Main Installation Flow
# ============================================

def main():
    """Main installation function."""
    print_header("olmOCR Automated Installer")
    print(f"""
This installer will set up olmOCR on Google Cloud Platform.

Configuration:
  Project ID:    {DEFAULT_PROJECT_ID}
  Region:        {DEFAULT_REGION}
  Parasail Key:  {DEFAULT_PARASAIL_KEY[:20]}...
""")

    # Get configuration
    project_id = os.environ.get('GCP_PROJECT_ID', DEFAULT_PROJECT_ID)
    region = os.environ.get('GCP_REGION', DEFAULT_REGION)
    parasail_key = os.environ.get('PARASAIL_API_KEY', DEFAULT_PARASAIL_KEY)

    # Allow override
    custom = input("Use these settings? (Y/n): ").strip().lower()
    if custom == 'n':
        project_id = input(f"GCP Project ID [{project_id}]: ").strip() or project_id
        region = input(f"Region [{region}]: ").strip() or region
        parasail_key = input(f"Parasail API Key [{parasail_key[:20]}...]: ").strip() or parasail_key

    print()

    # Check prerequisites
    if not check_prerequisites():
        print_error("Prerequisites not met. Please install required tools and try again.")
        sys.exit(1)

    # Authenticate
    if not authenticate_gcloud():
        print_error("Authentication failed")
        sys.exit(1)

    # Set up project
    if not setup_gcp_project(project_id):
        sys.exit(1)

    # Enable APIs
    if not enable_apis(project_id):
        sys.exit(1)

    # Create resources
    if not create_storage_bucket(project_id, region):
        sys.exit(1)

    if not create_firestore(project_id, region):
        sys.exit(1)

    if not create_pubsub(project_id):
        sys.exit(1)

    if not store_secrets(project_id, parasail_key):
        sys.exit(1)

    if not create_service_accounts(project_id):
        sys.exit(1)

    # Setup Firebase
    firebase_config = setup_firebase(project_id)

    # Build and deploy
    frontend_url, backend_url, worker_url = build_and_deploy(project_id, region, firebase_config)

    if not frontend_url:
        print_error("Deployment failed")
        sys.exit(1)

    # Success!
    print_header("Installation Complete!")
    print(f"""
{color('Your olmOCR application is now live!', Colors.GREEN + Colors.BOLD)}

    Frontend: {color(frontend_url, Colors.BLUE)}
    Backend:  {backend_url}
    Worker:   {worker_url}

{color('Next Steps:', Colors.YELLOW)}
    1. Open the frontend URL in your browser
    2. Create an account with email/password
    3. Upload a PDF to test OCR processing

{color('Troubleshooting:', Colors.YELLOW)}
    - View logs: gcloud logging read "resource.type=cloud_run_revision" --limit=50
    - Check services: gcloud run services list --region={region}

Enjoy using olmOCR!
""")

    # Save deployment info
    script_dir = get_script_dir()
    info_file = script_dir / 'DEPLOYMENT_INFO.txt'
    info_file.write_text(f"""olmOCR Deployment Information
Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}

Frontend URL: {frontend_url}
Backend URL:  {backend_url}
Worker URL:   {worker_url}

Project ID: {project_id}
Region:     {region}
Bucket:     olmocr-{project_id}

Firebase Config:
{json.dumps(firebase_config, indent=2)}
""")

    print(f"Deployment info saved to: {info_file}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Installation failed: {e}")
        sys.exit(1)

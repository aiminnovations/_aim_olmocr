# olmOCR Google Cloud Platform Architecture

## Executive Summary

This document outlines a comprehensive architecture for deploying olmOCR as a Google Cloud-hosted web application with a React frontend. The system provides an intuitive interface for PDF processing with drag-and-drop functionality, Windows Explorer-like folder navigation, and persistent user-configurable output storage.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                   FRONTEND                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                        React Application (Cloud Run)                         │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │   │
│  │  │ Drag & Drop  │  │ File Browser │  │ Output       │  │ Processing       │ │   │
│  │  │ Upload Zone  │  │ (Explorer)   │  │ Selector     │  │ Status Dashboard │ │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                   API LAYER                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                      Cloud Run API Gateway (FastAPI)                         │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │   │
│  │  │ /upload      │  │ /browse      │  │ /process     │  │ /jobs            │ │   │
│  │  │ /files       │  │ /folders     │  │ /download    │  │ /settings        │ │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
┌───────────────────────┐  ┌───────────────────┐  ┌───────────────────────────────┐
│   Cloud Storage       │  │   Cloud Pub/Sub   │  │   Cloud Firestore             │
│   (PDF Storage)       │  │   (Job Queue)     │  │   (User Data & Settings)      │
│   ┌───────────────┐   │  │                   │  │   ┌─────────────────────────┐ │
│   │ /input/       │   │  │   ┌───────────┐   │  │   │ users/{uid}             │ │
│   │ /output/      │   │  │   │ process-  │   │  │   │ jobs/{jobId}            │ │
│   │ /temp/        │   │  │   │ requests  │   │  │   │ settings/{uid}          │ │
│   └───────────────┘   │  │   └───────────┘   │  │   └─────────────────────────┘ │
└───────────────────────┘  └───────────────────┘  └───────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              PROCESSING LAYER                                       │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                    GPU Processing Workers (GKE + GPU)                        │   │
│  │  ┌──────────────────────────────────────────────────────────────────────┐   │   │
│  │  │                    olmOCR Processing Pipeline                         │   │   │
│  │  │  ┌─────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐  │   │   │
│  │  │  │ PDF     │  │ vLLM     │  │ Markdown     │  │ Output           │  │   │   │
│  │  │  │ Render  │  │ Inference│  │ Generation   │  │ Formatting       │  │   │   │
│  │  │  └─────────┘  └──────────┘  └──────────────┘  └──────────────────┘  │   │   │
│  │  └──────────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. Frontend Layer - React Application

#### 1.1 Technology Stack
- **Framework**: React 18+ with TypeScript
- **Build Tool**: Vite
- **State Management**: Zustand (lightweight) or Redux Toolkit
- **UI Components**: shadcn/ui + Tailwind CSS
- **File Handling**: react-dropzone
- **File Browser**: custom component with react-virtualized for large lists
- **API Client**: TanStack Query (React Query) + Axios

#### 1.2 Core Components

```
frontend/
├── src/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── MainLayout.tsx
│   │   ├── upload/
│   │   │   ├── DropZone.tsx              # Drag-and-drop file upload
│   │   │   ├── FileUploadProgress.tsx    # Upload progress indicator
│   │   │   └── BatchUpload.tsx           # Multiple file upload handling
│   │   ├── browser/
│   │   │   ├── FileBrowser.tsx           # Windows Explorer-like browser
│   │   │   ├── FolderTree.tsx            # Folder hierarchy tree view
│   │   │   ├── FileList.tsx              # File listing with sort/filter
│   │   │   ├── PathBreadcrumb.tsx        # Breadcrumb navigation
│   │   │   └── FileContextMenu.tsx       # Right-click context menu
│   │   ├── output/
│   │   │   ├── OutputSelector.tsx        # Output folder/format selector
│   │   │   ├── FormatOptions.tsx         # Markdown, JSON, HTML options
│   │   │   └── OutputPreview.tsx         # Preview processed output
│   │   ├── processing/
│   │   │   ├── JobQueue.tsx              # Active processing jobs
│   │   │   ├── ProcessingStatus.tsx      # Real-time status updates
│   │   │   └── JobHistory.tsx            # Completed job history
│   │   └── settings/
│   │       ├── UserSettings.tsx          # User preferences
│   │       └── DefaultPaths.tsx          # Default input/output paths
│   ├── hooks/
│   │   ├── useFileUpload.ts
│   │   ├── useFileBrowser.ts
│   │   ├── useProcessingJobs.ts
│   │   └── useWebSocket.ts               # Real-time updates
│   ├── services/
│   │   ├── api.ts                        # API client configuration
│   │   ├── storageService.ts             # GCS operations
│   │   └── websocketService.ts           # WebSocket connection
│   ├── store/
│   │   ├── fileStore.ts                  # File/folder state
│   │   ├── jobStore.ts                   # Processing jobs state
│   │   └── settingsStore.ts              # User settings
│   └── types/
│       ├── file.types.ts
│       ├── job.types.ts
│       └── api.types.ts
```

#### 1.3 File Browser Component (Windows Explorer-like)

```typescript
// FileBrowser.tsx - Core file browser structure
interface FileBrowserProps {
  currentPath: string;
  onPathChange: (path: string) => void;
  onFileSelect: (files: FileItem[]) => void;
  selectionMode: 'single' | 'multiple';
}

interface FileItem {
  id: string;
  name: string;
  type: 'file' | 'folder';
  path: string;
  size?: number;
  modified?: Date;
  contentType?: string;
  thumbnail?: string;  // For PDF preview
}

// Features:
// - Tree view sidebar (folder hierarchy)
// - List/Grid view toggle
// - Column sorting (name, date, size, type)
// - Multi-select with Ctrl/Shift
// - Keyboard navigation
// - Context menu (right-click)
// - Breadcrumb path navigation
// - Search/filter
// - Drag files between folders
```

#### 1.4 Drag-and-Drop Upload Zone

```typescript
// DropZone.tsx
interface DropZoneProps {
  onFilesAccepted: (files: File[]) => void;
  acceptedFormats: string[];  // ['.pdf', '.png', '.jpg', '.jpeg']
  maxFileSize: number;        // In bytes
  maxFiles?: number;
  destinationPath: string;
}

// Features:
// - Visual feedback on drag over
// - File type validation
// - Size limit enforcement
// - Folder drop support (recursive upload)
// - Progress tracking per file
// - Cancel/retry capabilities
// - Duplicate detection
```

---

### 2. API Layer - FastAPI Backend

#### 2.1 Technology Stack
- **Framework**: FastAPI (Python 3.11+)
- **Authentication**: Firebase Auth / Google Identity Platform
- **Async Support**: Native asyncio
- **Validation**: Pydantic v2
- **Storage Client**: google-cloud-storage
- **Queue Client**: google-cloud-pubsub

#### 2.2 API Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI application entry
│   ├── config.py                  # Configuration management
│   ├── dependencies.py            # Dependency injection
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── files.py               # File CRUD operations
│   │   ├── folders.py             # Folder management
│   │   ├── upload.py              # File upload handling
│   │   ├── processing.py          # OCR job management
│   │   ├── browse.py              # File browser API
│   │   └── settings.py            # User settings
│   ├── models/
│   │   ├── __init__.py
│   │   ├── file.py                # File/folder models
│   │   ├── job.py                 # Processing job models
│   │   └── user.py                # User/settings models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── storage_service.py     # GCS operations
│   │   ├── queue_service.py       # Pub/Sub operations
│   │   ├── firestore_service.py   # Database operations
│   │   └── processing_service.py  # Job orchestration
│   ├── middleware/
│   │   ├── auth.py                # Authentication middleware
│   │   ├── cors.py                # CORS configuration
│   │   └── logging.py             # Request logging
│   └── utils/
│       ├── gcs.py                 # GCS utilities
│       └── validators.py          # Input validation
├── tests/
├── requirements.txt
└── Dockerfile
```

#### 2.3 API Endpoints

```python
# File & Folder Management
GET    /api/v1/browse/{path}           # List contents of path
POST   /api/v1/folders                  # Create folder
DELETE /api/v1/folders/{path}           # Delete folder
GET    /api/v1/files/{file_id}          # Get file metadata
DELETE /api/v1/files/{file_id}          # Delete file
POST   /api/v1/files/move               # Move file/folder
POST   /api/v1/files/copy               # Copy file/folder

# Upload
POST   /api/v1/upload/init              # Initialize resumable upload
POST   /api/v1/upload/chunk             # Upload chunk
POST   /api/v1/upload/complete          # Complete upload
GET    /api/v1/upload/status/{id}       # Get upload status

# Processing
POST   /api/v1/process                  # Submit processing job
GET    /api/v1/jobs                     # List user's jobs
GET    /api/v1/jobs/{job_id}            # Get job status
DELETE /api/v1/jobs/{job_id}            # Cancel job
GET    /api/v1/jobs/{job_id}/output     # Get job output

# Downloads
GET    /api/v1/download/{file_id}       # Generate signed download URL
POST   /api/v1/download/batch           # Batch download as ZIP

# Settings
GET    /api/v1/settings                 # Get user settings
PUT    /api/v1/settings                 # Update user settings
GET    /api/v1/settings/defaults        # Get system defaults

# WebSocket
WS     /api/v1/ws                       # Real-time updates
```

#### 2.4 Core Service Implementations

```python
# storage_service.py
from google.cloud import storage
from typing import AsyncIterator, List, Optional
import asyncio

class StorageService:
    def __init__(self, bucket_name: str):
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    async def list_contents(
        self,
        prefix: str,
        delimiter: str = '/'
    ) -> dict:
        """List folder contents (files and subfolders)"""
        blobs = self.client.list_blobs(
            self.bucket.name,
            prefix=prefix,
            delimiter=delimiter
        )

        files = []
        folders = []

        for blob in blobs:
            files.append({
                'name': blob.name.split('/')[-1],
                'path': blob.name,
                'size': blob.size,
                'modified': blob.updated,
                'content_type': blob.content_type
            })

        for prefix in blobs.prefixes:
            folders.append({
                'name': prefix.rstrip('/').split('/')[-1],
                'path': prefix,
                'type': 'folder'
            })

        return {'files': files, 'folders': folders}

    async def generate_signed_url(
        self,
        blob_path: str,
        expiration: int = 3600,
        method: str = 'GET'
    ) -> str:
        """Generate signed URL for upload/download"""
        blob = self.bucket.blob(blob_path)
        return blob.generate_signed_url(
            expiration=expiration,
            method=method,
            version='v4'
        )

    async def create_folder(self, path: str) -> bool:
        """Create a folder marker in GCS"""
        if not path.endswith('/'):
            path += '/'
        blob = self.bucket.blob(path)
        blob.upload_from_string('')
        return True
```

---

### 3. Processing Layer - olmOCR Workers

#### 3.1 Architecture Options

**Option A: GKE with GPU Node Pool (Recommended for Production)**
- Kubernetes cluster with autoscaling GPU nodes
- T4/L4/A100 GPU instances
- Horizontal Pod Autoscaler based on queue depth
- Cost-effective with spot/preemptible instances

**Option B: Cloud Run Jobs with GPU (Simpler)**
- Serverless GPU execution (now available in Cloud Run)
- Pay-per-use model
- Automatic scaling
- Limited customization

**Option C: Vertex AI Custom Training Jobs**
- Managed ML infrastructure
- Easy GPU provisioning
- Higher cost but fully managed

#### 3.2 GKE Worker Architecture (Recommended)

```yaml
# kubernetes/worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: olmocr-worker
spec:
  replicas: 1  # Managed by HPA
  selector:
    matchLabels:
      app: olmocr-worker
  template:
    metadata:
      labels:
        app: olmocr-worker
    spec:
      nodeSelector:
        cloud.google.com/gke-accelerator: nvidia-tesla-t4
      containers:
      - name: worker
        image: gcr.io/{PROJECT}/olmocr-worker:latest
        resources:
          limits:
            nvidia.com/gpu: 1
            memory: "32Gi"
            cpu: "8"
          requests:
            nvidia.com/gpu: 1
            memory: "16Gi"
            cpu: "4"
        env:
        - name: PUBSUB_SUBSCRIPTION
          value: "olmocr-jobs-sub"
        - name: GCS_BUCKET
          value: "olmocr-storage"
        - name: VLLM_PORT
          value: "30024"
        volumeMounts:
        - name: model-cache
          mountPath: /models
      volumes:
      - name: model-cache
        persistentVolumeClaim:
          claimName: model-cache-pvc
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: olmocr-worker-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: olmocr-worker
  minReplicas: 0
  maxReplicas: 10
  metrics:
  - type: External
    external:
      metric:
        name: pubsub.googleapis.com|subscription|num_undelivered_messages
        selector:
          matchLabels:
            resource.labels.subscription_id: olmocr-jobs-sub
      target:
        type: AverageValue
        averageValue: 5
```

#### 3.3 Worker Service Implementation

```python
# worker/processor.py
import asyncio
import json
import tempfile
from pathlib import Path
from google.cloud import pubsub_v1, storage, firestore
from olmocr.pipeline import process_pdf, build_page_query
from olmocr.data.renderpdf import render_pdf_to_base64png

class OlmOCRWorker:
    def __init__(self, config: dict):
        self.storage_client = storage.Client()
        self.firestore_client = firestore.AsyncClient()
        self.subscriber = pubsub_v1.SubscriberClient()
        self.bucket = self.storage_client.bucket(config['gcs_bucket'])
        self.vllm_url = config['vllm_url']
        self.model_name = config['model_name']

    async def process_job(self, job_data: dict):
        """Process a single OCR job"""
        job_id = job_data['job_id']
        user_id = job_data['user_id']
        input_path = job_data['input_path']
        output_path = job_data['output_path']
        output_format = job_data.get('output_format', 'markdown')

        try:
            # Update job status
            await self._update_job_status(job_id, 'processing')

            # Download PDF from GCS
            with tempfile.TemporaryDirectory() as temp_dir:
                local_pdf = Path(temp_dir) / 'input.pdf'
                blob = self.bucket.blob(input_path)
                blob.download_to_filename(str(local_pdf))

                # Process PDF
                results = await self._process_pdf(
                    str(local_pdf),
                    job_id,
                    output_format
                )

                # Upload results
                await self._upload_results(
                    results,
                    output_path,
                    output_format
                )

                # Update job as complete
                await self._update_job_status(
                    job_id,
                    'completed',
                    output_files=results['output_files']
                )

        except Exception as e:
            await self._update_job_status(
                job_id,
                'failed',
                error=str(e)
            )
            raise

    async def _process_pdf(
        self,
        pdf_path: str,
        job_id: str,
        output_format: str
    ) -> dict:
        """Run olmOCR processing pipeline"""
        from pypdf import PdfReader

        reader = PdfReader(pdf_path)
        num_pages = len(reader.pages)

        results = {
            'pages': [],
            'metadata': {
                'total_pages': num_pages,
                'input_tokens': 0,
                'output_tokens': 0
            },
            'output_files': []
        }

        for page_num in range(num_pages):
            # Update progress
            await self._update_job_progress(
                job_id,
                page_num + 1,
                num_pages
            )

            # Build query for this page
            query = await build_page_query(
                pdf_path,
                page_num,
                target_longest_image_dim=1288,
                model_name=self.model_name
            )

            # Send to vLLM for inference
            response = await self._inference(query)

            results['pages'].append({
                'page_num': page_num,
                'text': response['text'],
                'metadata': response['metadata']
            })

            results['metadata']['input_tokens'] += response['input_tokens']
            results['metadata']['output_tokens'] += response['output_tokens']

        return results

    async def _inference(self, query: dict) -> dict:
        """Send inference request to vLLM server"""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.vllm_url}/v1/chat/completions",
                json=query
            ) as response:
                result = await response.json()

        return {
            'text': result['choices'][0]['message']['content'],
            'input_tokens': result['usage']['prompt_tokens'],
            'output_tokens': result['usage']['completion_tokens'],
            'metadata': {}  # Parse from response
        }

    async def _update_job_status(
        self,
        job_id: str,
        status: str,
        **kwargs
    ):
        """Update job status in Firestore"""
        doc_ref = self.firestore_client.collection('jobs').document(job_id)
        await doc_ref.update({
            'status': status,
            'updated_at': firestore.SERVER_TIMESTAMP,
            **kwargs
        })

    async def _update_job_progress(
        self,
        job_id: str,
        current: int,
        total: int
    ):
        """Update job progress"""
        doc_ref = self.firestore_client.collection('jobs').document(job_id)
        await doc_ref.update({
            'progress': {
                'current': current,
                'total': total,
                'percentage': int((current / total) * 100)
            }
        })
```

---

### 4. Data Storage Layer

#### 4.1 Google Cloud Storage Structure

```
gs://olmocr-{project-id}/
├── users/
│   └── {user_id}/
│       ├── input/              # User uploaded PDFs
│       │   ├── documents/
│       │   └── scans/
│       ├── output/             # Processed results
│       │   ├── markdown/
│       │   ├── json/
│       │   └── html/
│       └── temp/               # Temporary processing files
├── shared/                     # Shared resources
│   └── templates/
└── system/
    ├── models/                 # Cached ML models
    └── config/                 # System configuration
```

#### 4.2 Cloud Firestore Schema

```javascript
// Users Collection
/users/{userId}
{
  email: string,
  displayName: string,
  createdAt: timestamp,
  lastActive: timestamp,
  settings: {
    defaultInputPath: string,
    defaultOutputPath: string,
    defaultOutputFormat: 'markdown' | 'json' | 'html',
    emailNotifications: boolean,
    theme: 'light' | 'dark' | 'system'
  },
  quotas: {
    storageUsed: number,       // bytes
    storageLimit: number,
    pagesProcessed: number,
    monthlyLimit: number
  }
}

// Jobs Collection
/jobs/{jobId}
{
  userId: string,
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled',
  createdAt: timestamp,
  updatedAt: timestamp,
  startedAt: timestamp | null,
  completedAt: timestamp | null,
  input: {
    path: string,              // GCS path
    fileName: string,
    fileSize: number,
    pageCount: number
  },
  output: {
    path: string,              // GCS output path
    format: string,
    files: [{
      name: string,
      path: string,
      size: number
    }]
  },
  progress: {
    current: number,
    total: number,
    percentage: number
  },
  metrics: {
    inputTokens: number,
    outputTokens: number,
    processingTimeMs: number
  },
  error: string | null
}

// Folders Collection (virtual folder metadata)
/folders/{folderId}
{
  userId: string,
  name: string,
  path: string,
  parentPath: string | null,
  createdAt: timestamp,
  isDefault: boolean,          // Default input/output folder
  type: 'input' | 'output' | 'custom'
}
```

#### 4.3 Cloud Pub/Sub Topics

```yaml
# Processing job queue
Topic: olmocr-jobs
  - Subscription: olmocr-jobs-sub (pull, for workers)
  - Message Schema:
    {
      "job_id": "string",
      "user_id": "string",
      "input_path": "string",
      "output_path": "string",
      "output_format": "string",
      "priority": "number",
      "created_at": "timestamp"
    }

# Real-time notifications
Topic: olmocr-notifications
  - Subscription: olmocr-notifications-push (push to Cloud Run)
  - Message Schema:
    {
      "type": "job_update" | "upload_complete" | "system",
      "user_id": "string",
      "payload": {}
    }
```

---

### 5. Authentication & Authorization

#### 5.1 Firebase Authentication Setup

```typescript
// frontend/src/services/auth.ts
import { initializeApp } from 'firebase/app';
import {
  getAuth,
  signInWithPopup,
  GoogleAuthProvider,
  signOut,
  onAuthStateChanged
} from 'firebase/auth';

const firebaseConfig = {
  apiKey: process.env.VITE_FIREBASE_API_KEY,
  authDomain: process.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.VITE_FIREBASE_PROJECT_ID,
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

export const signInWithGoogle = async () => {
  const provider = new GoogleAuthProvider();
  return signInWithPopup(auth, provider);
};

export const logout = () => signOut(auth);

export const getIdToken = async () => {
  const user = auth.currentUser;
  if (user) {
    return user.getIdToken();
  }
  throw new Error('Not authenticated');
};
```

#### 5.2 Backend Authentication Middleware

```python
# backend/app/middleware/auth.py
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer
from firebase_admin import auth, credentials, initialize_app
import os

# Initialize Firebase Admin
cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS_PATH'))
initialize_app(cred)

security = HTTPBearer()

async def verify_firebase_token(request: Request):
    """Verify Firebase ID token from Authorization header"""
    auth_header = request.headers.get('Authorization')

    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Missing authorization token')

    token = auth_header.split(' ')[1]

    try:
        decoded_token = auth.verify_id_token(token)
        request.state.user_id = decoded_token['uid']
        request.state.user_email = decoded_token.get('email')
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail=f'Invalid token: {str(e)}')

# Dependency for protected routes
def get_current_user(token: dict = Depends(verify_firebase_token)):
    return token
```

---

### 6. Real-time Updates

#### 6.1 WebSocket Implementation

```python
# backend/app/routers/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
import asyncio
import json

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)

    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Authenticate via query param token
    token = websocket.query_params.get('token')
    user_id = await verify_ws_token(token)

    await manager.connect(websocket, user_id)

    try:
        while True:
            # Keep connection alive, handle client messages
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get('type') == 'ping':
                await websocket.send_json({'type': 'pong'})
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
```

#### 6.2 Frontend WebSocket Hook

```typescript
// frontend/src/hooks/useWebSocket.ts
import { useEffect, useRef, useCallback } from 'react';
import { useAuthStore } from '../store/authStore';
import { useJobStore } from '../store/jobStore';

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null);
  const { token } = useAuthStore();
  const { updateJob } = useJobStore();

  const connect = useCallback(() => {
    if (!token) return;

    const wsUrl = `${import.meta.env.VITE_WS_URL}/ws?token=${token}`;
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.current.onmessage = (event) => {
      const message = JSON.parse(event.data);

      switch (message.type) {
        case 'job_update':
          updateJob(message.payload);
          break;
        case 'upload_complete':
          // Handle upload completion
          break;
      }
    };

    ws.current.onclose = () => {
      // Reconnect after delay
      setTimeout(connect, 3000);
    };
  }, [token, updateJob]);

  useEffect(() => {
    connect();
    return () => ws.current?.close();
  }, [connect]);

  const sendMessage = useCallback((message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    }
  }, []);

  return { sendMessage };
}
```

---

### 7. Deployment Architecture

#### 7.1 Infrastructure as Code (Terraform)

```hcl
# terraform/main.tf

provider "google" {
  project = var.project_id
  region  = var.region
}

# Cloud Storage Bucket
resource "google_storage_bucket" "olmocr_storage" {
  name     = "olmocr-${var.project_id}"
  location = var.region

  uniform_bucket_level_access = true

  cors {
    origin          = ["*"]
    method          = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    response_header = ["*"]
    max_age_seconds = 3600
  }

  lifecycle_rule {
    condition {
      age = 30
      matches_prefix = ["users/*/temp/"]
    }
    action {
      type = "Delete"
    }
  }
}

# Cloud Run - Frontend
resource "google_cloud_run_v2_service" "frontend" {
  name     = "olmocr-frontend"
  location = var.region

  template {
    containers {
      image = "gcr.io/${var.project_id}/olmocr-frontend:latest"

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "VITE_API_URL"
        value = google_cloud_run_v2_service.backend.uri
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

# Cloud Run - Backend API
resource "google_cloud_run_v2_service" "backend" {
  name     = "olmocr-api"
  location = var.region

  template {
    containers {
      image = "gcr.io/${var.project_id}/olmocr-api:latest"

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }

      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.olmocr_storage.name
      }

      env {
        name  = "PUBSUB_TOPIC"
        value = google_pubsub_topic.jobs.name
      }
    }

    scaling {
      min_instance_count = 1
      max_instance_count = 20
    }

    service_account = google_service_account.backend.email
  }
}

# GKE Cluster for GPU Workers
resource "google_container_cluster" "olmocr_workers" {
  name     = "olmocr-workers"
  location = var.zone

  initial_node_count = 1

  node_config {
    machine_type = "n1-standard-8"

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
  }
}

# GPU Node Pool
resource "google_container_node_pool" "gpu_pool" {
  name       = "gpu-pool"
  cluster    = google_container_cluster.olmocr_workers.name
  location   = var.zone

  autoscaling {
    min_node_count = 0
    max_node_count = 5
  }

  node_config {
    machine_type = "n1-standard-8"

    guest_accelerator {
      type  = "nvidia-tesla-t4"
      count = 1
    }

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    metadata = {
      disable-legacy-endpoints = "true"
    }
  }
}

# Pub/Sub Topic and Subscription
resource "google_pubsub_topic" "jobs" {
  name = "olmocr-jobs"
}

resource "google_pubsub_subscription" "jobs_sub" {
  name  = "olmocr-jobs-sub"
  topic = google_pubsub_topic.jobs.name

  ack_deadline_seconds = 600

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

# Firestore Database
resource "google_firestore_database" "main" {
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
}
```

#### 7.2 CI/CD Pipeline (Cloud Build)

```yaml
# cloudbuild.yaml
steps:
  # Build Frontend
  - name: 'node:18'
    dir: 'frontend'
    entrypoint: npm
    args: ['ci']

  - name: 'node:18'
    dir: 'frontend'
    entrypoint: npm
    args: ['run', 'build']
    env:
      - 'VITE_API_URL=${_API_URL}'
      - 'VITE_FIREBASE_API_KEY=${_FIREBASE_API_KEY}'

  - name: 'gcr.io/cloud-builders/docker'
    args: [
      'build',
      '-t', 'gcr.io/$PROJECT_ID/olmocr-frontend:$SHORT_SHA',
      '-t', 'gcr.io/$PROJECT_ID/olmocr-frontend:latest',
      '-f', 'frontend/Dockerfile',
      'frontend'
    ]

  # Build Backend
  - name: 'gcr.io/cloud-builders/docker'
    args: [
      'build',
      '-t', 'gcr.io/$PROJECT_ID/olmocr-api:$SHORT_SHA',
      '-t', 'gcr.io/$PROJECT_ID/olmocr-api:latest',
      '-f', 'backend/Dockerfile',
      'backend'
    ]

  # Build Worker
  - name: 'gcr.io/cloud-builders/docker'
    args: [
      'build',
      '-t', 'gcr.io/$PROJECT_ID/olmocr-worker:$SHORT_SHA',
      '-t', 'gcr.io/$PROJECT_ID/olmocr-worker:latest',
      '-f', 'worker/Dockerfile',
      'worker'
    ]

  # Push images
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '--all-tags', 'gcr.io/$PROJECT_ID/olmocr-frontend']

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '--all-tags', 'gcr.io/$PROJECT_ID/olmocr-api']

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '--all-tags', 'gcr.io/$PROJECT_ID/olmocr-worker']

  # Deploy to Cloud Run
  - name: 'gcr.io/cloud-builders/gcloud'
    args: [
      'run', 'deploy', 'olmocr-frontend',
      '--image', 'gcr.io/$PROJECT_ID/olmocr-frontend:$SHORT_SHA',
      '--region', '${_REGION}',
      '--platform', 'managed',
      '--allow-unauthenticated'
    ]

  - name: 'gcr.io/cloud-builders/gcloud'
    args: [
      'run', 'deploy', 'olmocr-api',
      '--image', 'gcr.io/$PROJECT_ID/olmocr-api:$SHORT_SHA',
      '--region', '${_REGION}',
      '--platform', 'managed'
    ]

  # Update GKE deployment
  - name: 'gcr.io/cloud-builders/kubectl'
    args: [
      'set', 'image',
      'deployment/olmocr-worker',
      'worker=gcr.io/$PROJECT_ID/olmocr-worker:$SHORT_SHA'
    ]
    env:
      - 'CLOUDSDK_COMPUTE_ZONE=${_ZONE}'
      - 'CLOUDSDK_CONTAINER_CLUSTER=olmocr-workers'

substitutions:
  _REGION: us-central1
  _ZONE: us-central1-a
  _API_URL: https://olmocr-api-xxxxx.run.app
```

---

### 8. Cost Estimation

| Component | Configuration | Monthly Cost (Est.) |
|-----------|--------------|---------------------|
| Cloud Run (Frontend) | 1 vCPU, 512MB, ~100K requests | $5-20 |
| Cloud Run (API) | 2 vCPU, 2GB, ~500K requests | $50-150 |
| GKE Control Plane | Standard cluster | $74.40 |
| GKE GPU Nodes (T4) | 2x n1-standard-8 + T4 (avg) | $400-800 |
| Cloud Storage | 100GB + egress | $20-50 |
| Firestore | 1M reads, 500K writes | $5-20 |
| Pub/Sub | 1M messages | $1-5 |
| **Total** | | **$555-1,119/month** |

**Cost Optimization Strategies:**
1. Use preemptible/spot GPU instances (60-70% savings)
2. Scale workers to 0 during off-hours
3. Implement caching for repeated documents
4. Use committed use discounts for steady-state workloads

---

### 9. Security Considerations

#### 9.1 Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Security Layers                              │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: Edge Security                                         │
│  - Cloud Armor (DDoS protection, WAF rules)                    │
│  - Cloud CDN (caching, edge security)                          │
│  - SSL/TLS termination                                          │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: Authentication & Authorization                        │
│  - Firebase Auth (identity management)                          │
│  - IAM roles and service accounts                              │
│  - VPC Service Controls                                         │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: Network Security                                      │
│  - VPC with private subnets                                    │
│  - Cloud NAT for outbound                                      │
│  - Private Google Access                                        │
├─────────────────────────────────────────────────────────────────┤
│  Layer 4: Data Security                                         │
│  - Encryption at rest (default)                                │
│  - Encryption in transit (TLS 1.3)                             │
│  - Customer-managed encryption keys (CMEK)                     │
│  - Data Loss Prevention (DLP) scanning                         │
└─────────────────────────────────────────────────────────────────┘
```

#### 9.2 IAM Configuration

```hcl
# Service account for backend API
resource "google_service_account" "backend" {
  account_id   = "olmocr-backend"
  display_name = "olmOCR Backend Service"
}

# Minimal permissions for backend
resource "google_project_iam_member" "backend_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_project_iam_member" "backend_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_project_iam_member" "backend_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.backend.email}"
}
```

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- [ ] Set up GCP project and enable APIs
- [ ] Configure Terraform infrastructure
- [ ] Set up CI/CD pipeline
- [ ] Create base Docker images
- [ ] Configure Firebase Authentication

### Phase 2: Backend API (Weeks 3-4)
- [ ] Implement FastAPI backend structure
- [ ] Build file/folder management APIs
- [ ] Implement upload handling with resumable uploads
- [ ] Set up Pub/Sub integration
- [ ] Create Firestore data models

### Phase 3: Processing Workers (Weeks 5-6)
- [ ] Adapt olmOCR pipeline for GCP
- [ ] Create worker Docker image
- [ ] Set up GKE cluster with GPU nodes
- [ ] Implement job queue processing
- [ ] Add progress tracking and notifications

### Phase 4: Frontend Development (Weeks 7-9)
- [ ] Set up React project with Vite
- [ ] Build file browser component
- [ ] Implement drag-and-drop upload
- [ ] Create output selector component
- [ ] Build processing status dashboard
- [ ] Implement WebSocket real-time updates

### Phase 5: Integration & Testing (Weeks 10-11)
- [ ] End-to-end integration testing
- [ ] Performance optimization
- [ ] Security audit
- [ ] Load testing

### Phase 6: Production Deployment (Week 12)
- [ ] Production environment setup
- [ ] DNS and SSL configuration
- [ ] Monitoring and alerting
- [ ] Documentation and training

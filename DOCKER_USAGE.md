# Docker Usage Guide

## Quick Start

### 1. Build the Docker Image

```bash
docker build -t vidsimplify-api .
```

### 2. Run the Container

```bash
docker run -d \
  --name vidsimplify-api \
  -p 8000:8000 \
  -e SYNC_API_KEY="your_sync_api_key" \
  -e ELEVENLABS_API_KEY="your_elevenlabs_api_key" \
  -e GCS_BUCKET_NAME="vidsimplify" \
  -e GOOGLE_APPLICATION_CREDENTIALS="/app/gcs-key.json" \
  -v $(pwd)/your-gcs-credentials.json:/app/gcs-key.json:ro \
  vidsimplify-api
```

### 3. Check Logs

```bash
docker logs -f vidsimplify-api
```

### 4. Access the API

- **API:** http://localhost:8000
- **Docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### 5. Stop the Container

```bash
docker stop vidsimplify-api
docker rm vidsimplify-api
```

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SYNC_API_KEY` | Sync API authentication key | Yes |
| `ELEVENLABS_API_KEY` | ElevenLabs API key | Yes |
| `GCS_BUCKET_NAME` | Google Cloud Storage bucket name | Yes |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to GCS credentials inside container | Yes |

---

## Volume Mounts

The Google Cloud credentials JSON file must be mounted as a volume:

```bash
-v $(pwd)/gen-lang-client-0244179777-8b74f1527f62.json:/app/gcs-key.json:ro
```

- Source: Your local credentials file
- Destination: `/app/gcs-key.json` (inside container)
- `:ro` makes it read-only for security

---

## Common Commands

### Rebuild Image
```bash
docker build --no-cache -t vidsimplify-api .
```

### Run with Different Port
```bash
docker run -d \
  --name vidsimplify-api \
  -p 9000:8000 \
  -e SYNC_API_KEY="your_sync_api_key" \
  -e ELEVENLABS_API_KEY="your_elevenlabs_api_key" \
  -e GCS_BUCKET_NAME="vidsimplify" \
  -e GOOGLE_APPLICATION_CREDENTIALS="/app/gcs-key.json" \
  -v $(pwd)/your-gcs-credentials.json:/app/gcs-key.json:ro \
  vidsimplify-api
```
API will be available at http://localhost:9000

### View Container Stats
```bash
docker stats vidsimplify-api
```

### Access Container Shell
```bash
docker exec -it vidsimplify-api /bin/bash
```

### Remove Everything
```bash
docker stop vidsimplify-api
docker rm vidsimplify-api
docker rmi vidsimplify-api
```

---

## Troubleshooting

### Container Exits Immediately

Check logs:
```bash
docker logs vidsimplify-api
```

Common issues:
- Missing environment variables
- GCS credentials file not mounted correctly
- Port 8000 already in use

### GCS Upload Not Working

Verify credentials are mounted:
```bash
docker exec vidsimplify-api ls -la /app/gcs-key.json
```

Test GCS connection:
```bash
docker exec vidsimplify-api python -c "from google.cloud import storage; print(storage.Client().project)"
```

### Port Already in Use

Use a different port:
```bash
-p 9000:8000
```

---

## Production Deployment

For production, use a proper secrets management system:

### AWS ECS
```json
{
  "environment": [
    {"name": "GCS_BUCKET_NAME", "value": "vidsimplify"}
  ],
  "secrets": [
    {"name": "SYNC_API_KEY", "valueFrom": "arn:aws:secretsmanager:..."},
    {"name": "ELEVENLABS_API_KEY", "valueFrom": "arn:aws:secretsmanager:..."}
  ]
}
```

### Kubernetes
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: api-secrets
stringData:
  SYNC_API_KEY: "your-key"
  ELEVENLABS_API_KEY: "your-key"
---
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: api
    image: vidsimplify-api
    envFrom:
    - secretRef:
        name: api-secrets
    volumeMounts:
    - name: gcs-creds
      mountPath: /app/gcs-key.json
      readOnly: true
  volumes:
  - name: gcs-creds
    secret:
      secretName: gcs-credentials
```

### Docker Swarm
```bash
docker secret create gcs_creds gen-lang-client-0244179777-8b74f1527f62.json
docker secret create sync_key sync_api_key.txt
docker secret create elevenlabs_key elevenlabs_api_key.txt

docker service create \
  --name vidsimplify-api \
  --secret gcs_creds \
  --secret sync_key \
  --secret elevenlabs_key \
  -p 8000:8000 \
  vidsimplify-api
```


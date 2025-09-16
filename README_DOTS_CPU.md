# dots.ocr CPU deployment

See docs/dots-ocr-cpu.md for full instructions.

Quick start (Docker):

```bash
docker compose -f docker-compose.dots-ocr-cpu.yml up -d --build
```

Then point this app to it (in `.env`):

```
DOTS_OCR_URL=http://localhost:8501
```

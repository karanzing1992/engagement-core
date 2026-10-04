FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git ca-certificates fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -c constraints.txt "ffmpeg-mcp[whisper,vision] @ git+https://github.com/AbyAbyss/ffmpeg-mcp-video-editor.git@c65cd584c5ee1a54d2069ef8c523524216d5fb31"

COPY . .
RUN python -m compileall . && python -c "import app, audio_sync, captions, music_library, renderer"
RUN mkdir -p /data/uploads /data/jobs /data/outputs /data/music
ENV REEL_DATA_ROOT=/data
ENV FFMPEG_MCP_WORKSPACE=/data/ffmpeg-mcp
ENV FFMPEG_MCP_ALLOWED_ROOTS=/data
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port $PORT"]

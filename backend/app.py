"""
YouTube Auto Dub — FastAPI Web Backend.

Exposes the dubbing pipeline as a REST API with Server-Sent Events (SSE)
for real-time progress updates. Serves the frontend as static files.

Run: uvicorn backend.app:app --reload
"""

import asyncio
import json
import logging
import shutil
import subprocess
import tempfile
import time
import random
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
STYLES_DIR = BASE_DIR / "styles"
SCRIPTS_DIR = BASE_DIR / "scripts"
ASSETS_DIR = BASE_DIR / "assets"
DOWNLOADS_DIR = BASE_DIR / "downloads"
JOBS_FILE = BASE_DIR / "jobs.json"
LANG_MAP_FILE = BASE_DIR / "language_map.json"
LOG_FILE = BASE_DIR / "backend_errors.log"

# Create downloads dir
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8")
    ]
)
log = logging.getLogger("autodub")
import urllib.parse

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(title="YouTube Auto Dub", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# Serve static directories
app.mount("/styles", StaticFiles(directory=str(STYLES_DIR)), name="styles")
app.mount("/scripts", StaticFiles(directory=str(SCRIPTS_DIR)), name="scripts")
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

# ---------------------------------------------------------------------------
# Global State (Persistent)
# ---------------------------------------------------------------------------
jobs: Dict[str, Any] = {}
executor = ThreadPoolExecutor(max_workers=3)

def save_jobs():
    try:
        # Filter out non-serializable (transient) objects like queues
        serializable = {}
        for jid, data in jobs.items():
            serializable[jid] = {k: v for k, v in data.items() if k != "queue"}
        with open(JOBS_FILE, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.error("Error saving jobs: %s", e)

def load_jobs():
    global jobs
    if JOBS_FILE.exists():
        try:
            with open(JOBS_FILE, "r", encoding="utf-8") as f:
                jobs = json.load(f)
                log.info("Loaded %d jobs from %s", len(jobs), JOBS_FILE.name)
        except Exception as e:
            log.error("Error loading jobs: %s", e)
            jobs = {}

load_jobs()

class DubRequest(BaseModel):
    url: str
    lang: str = "es"
    gender: str = "female"
    subtitle: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_languages() -> dict:
    """Load and parse the language map JSON."""
    try:
        with open(LANG_MAP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        log.exception("Failed to load language_map.json")
        return {}


def _push(job_id: str, step: str, progress: int, message: str, status: str = "processing"):
    """Push a progress event into the job's queue."""
    job = jobs.get(job_id)
    if not job:
        return
    event = {
        "step": step,
        "progress": progress,
        "message": message,
        "status": status,
        "timestamp": datetime.now().isoformat(),
    }
    log.info("[%s] %s — %d%% — %s", job_id[:8], step, progress, message)
    try:
        job["queue"].put_nowait(event)
    except Exception:
        pass
    
    # Update job state for persistence
    job["status"] = status
    job["progress"] = progress
    job["message"] = message
    if progress % 10 == 0 or status in ("complete", "error"):
        save_jobs()


def _check_dependencies():
    """Check for ffmpeg, ffprobe and torch."""
    missing = []
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg")
    if not shutil.which("ffprobe"):
        missing.append("ffprobe")
    if missing:
        raise RuntimeError(f"Missing system dependencies: {', '.join(missing)}. Install FFmpeg.")
    try:
        import torch  # noqa: F401
    except ImportError:
        raise RuntimeError("PyTorch is not installed. Run: pip install torch")


def _cleanup():
    """Clean the temp directory with retry for Windows file locks."""
    import src.engines as eng
    for attempt in range(5):
        try:
            if eng.TEMP_DIR.exists():
                shutil.rmtree(eng.TEMP_DIR)
            eng.TEMP_DIR.mkdir(parents=True, exist_ok=True)
            return
        except PermissionError:
            time.sleep(0.5 * (2 ** attempt))
    log.warning("Could not fully clean temp directory after retries.")


def _create_base_silence() -> Path:
    """Generate a 5-minute base silence WAV file."""
    import src.engines as eng
    path = eng.TEMP_DIR / "silence_base.wav"
    if path.exists():
        return path
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
        "-t", "300", "-c:a", "pcm_s16le", str(path),
    ]
    subprocess.run(cmd, check=True)
    return path


# ---------------------------------------------------------------------------
# The full dubbing pipeline (runs in a thread)
# ---------------------------------------------------------------------------
def run_pipeline(job_id: str, url: str, lang: str, gender: str, subtitle: bool):
    """Execute the full dubbing pipeline, pushing progress via _push()."""
    import src.engines as eng
    import src.youtube as yt
    import src.media as media

    try:
        # ── Step 0: Init ──────────────────────────────────────────────
        _push(job_id, "init", 0, "Checking dependencies…")
        _check_dependencies()
        _cleanup()

        device = "cuda"
        try:
            import torch
            if not torch.cuda.is_available():
                device = "cpu"
        except Exception:
            device = "cpu"

        _push(job_id, "init", 5, f"Using device: {device.upper()}")
        engine = eng.Engine(device)

        # ── Step 1: Download ──────────────────────────────────────────
        _push(job_id, "download", 8, "Downloading video from YouTube…")
        video_path = yt.download_video(url)
        _push(job_id, "download", 12, "Downloading audio track…")
        audio_path = yt.download_audio(url)
        _push(job_id, "download", 18, "Download complete ✓")

        # ── Step 2: Transcribe ────────────────────────────────────────
        _push(job_id, "transcribe", 20, f"Transcribing with Whisper ({eng.ASR_MODEL})…")
        raw_segments = engine.transcribe_safe(audio_path)
        _push(job_id, "transcribe", 35, f"Transcribed {len(raw_segments)} segments ✓")

        # ── Step 3: Chunk + Translate ─────────────────────────────────
        _push(job_id, "translate", 37, "Intelligent chunking…")
        chunks = eng.smart_chunk(raw_segments)
        _push(job_id, "translate", 40, f"Translating {len(chunks)} chunks to {lang.upper()}…")
        texts = [c["text"] for c in chunks]
        translated = engine.translate_safe(texts, lang)
        for i, chunk in enumerate(chunks):
            chunk["trans_text"] = translated[i]
        _push(job_id, "translate", 55, "Translation complete ✓")

        # ── Step 4: TTS Synthesis ─────────────────────────────────────
        _push(job_id, "synthesize", 57, f"Generating {gender} voice in {lang.upper()}…")
        failed_tts = 0
        for i, chunk in enumerate(chunks):
            tts_path = eng.TEMP_DIR / f"chunk_{i:04d}.mp3"
            try:
                engine.synthesize(
                    text=chunk["trans_text"],
                    target_lang=lang,
                    gender=gender,
                    out_path=tts_path,
                )
                time.sleep(random.uniform(0.5, 1.5))
                slot_duration = chunk["end"] - chunk["start"]
                final_audio = media.fit_audio(tts_path, slot_duration)
                chunk["processed_audio"] = final_audio
            except Exception as e:
                log.warning("TTS failed for chunk %d: %s", i, e)
                failed_tts += 1
                continue

            pct = 57 + int((i + 1) / len(chunks) * 23)
            if i % 3 == 0:
                _push(job_id, "synthesize", pct, f"Synthesized {i+1}/{len(chunks)} chunks…")

        _push(job_id, "synthesize", 80, f"Synthesis done ({failed_tts} failures) ✓")

        # ── Step 5: Render ────────────────────────────────────────────
        _push(job_id, "render", 82, "Preparing final render…")
        silence_path = _create_base_silence()
        concat_list = eng.TEMP_DIR / "concat_list.txt"
        media.create_concat_file(chunks, silence_path, concat_list)

        subtitle_path = None
        if subtitle:
            subtitle_path = eng.TEMP_DIR / "subtitles.srt"
            media.generate_srt(chunks, subtitle_path)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_name = video_path.stem
        sub_suffix = "_sub" if subtitle else ""
        out_name = f"dubbed_{lang}_{gender}{sub_suffix}_{video_name}_{ts}.mp4"
        final_output = DOWNLOADS_DIR / out_name

        _push(job_id, "render", 85, "Rendering video (this may take a while)…")
        media.render_video(video_path, concat_list, final_output, subtitle_path=subtitle_path)

        if final_output.exists():
            size_mb = final_output.stat().st_size / (1024 * 1024)
            jobs[job_id]["output_file"] = str(final_output)
            jobs[job_id]["output_name"] = out_name
            jobs[job_id]["status"] = "complete"
            _push(job_id, "complete", 100, f"Done! File: {out_name} ({size_mb:.1f} MB)", status="complete")
        else:
            jobs[job_id]["status"] = "error"
            _push(job_id, "error", 100, "Render finished but output file not found.", status="error")

    except Exception as e:
        log.exception("Pipeline error for job %s", job_id)
        _push(job_id, "error", -1, f"Error: {e}", status="error")
        jobs[job_id]["status"] = "error"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    """Serve the frontend index page."""
    index = FRONTEND_DIR / "index.html"
    if not index.exists():
        raise HTTPException(404, "Frontend not found")
    return FileResponse(index, media_type="text/html")


@app.get("/api/languages")
async def get_languages():
    """Return available languages with voice info."""
    data = _load_languages()
    langs = []
    for code, info in sorted(data.items(), key=lambda x: x[0]):
        langs.append({
            "code": code,
            "name": info.get("name", code),
            "has_male": bool(info.get("voices", {}).get("male")),
            "has_female": bool(info.get("voices", {}).get("female")),
        })
    return {"languages": langs}


@app.post("/api/dub")
async def start_dub(req: DubRequest):
    """Start a new dubbing job and return the job ID."""
    job_id = str(uuid.uuid4())
    loop = asyncio.get_event_loop()
    queue = asyncio.Queue()

    jobs[job_id] = {
        "id": job_id,
        "status": "processing",
        "queue": queue,
        "url": req.url,
        "lang": req.lang,
        "gender": req.gender,
        "subtitle": req.subtitle,
        "created": datetime.now().isoformat(),
        "output_file": None,
        "output_name": None,
    }
    save_jobs()

    log.info("Starting job %s for %s → %s", job_id[:8], req.url, req.lang)
    loop.run_in_executor(
        executor,
        run_pipeline,
        job_id, req.url, req.lang, req.gender, req.subtitle,
    )

    return {"job_id": job_id}


@app.get("/api/progress/{job_id}")
async def progress_stream(job_id: str):
    """SSE stream of progress events for a job."""
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    async def event_generator():
        job = jobs[job_id]
        queue: asyncio.Queue = job["queue"]
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("status") in ("complete", "error"):
                    break
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'step': 'heartbeat', 'progress': -1, 'message': 'waiting…', 'status': 'processing'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/download/{job_id}")
async def download_result(job_id: str):
    """Download the file — browser saves to its Downloads folder."""
    log.info("Download requested for job_id: %s", job_id)
    job = jobs.get(job_id)
    if not job:
        log.error("Job not found: %s", job_id)
        raise HTTPException(404, "Job not found")
    if job["status"] != "complete" or not job.get("output_file"):
        log.error("Job not complete: %s", job_id)
        raise HTTPException(400, "Job not complete or output missing")
        
    path = Path(job["output_file"])
    if not path.exists():
        log.error("File not found on disk: %s", path)
        if path.parent.exists():
            files = list(path.parent.glob("*"))
            log.info("Available files in dir: %s", [f.name for f in files])
        raise HTTPException(404, "Output file not found on disk")
    
    fname = job.get("output_name", path.name)
    log.info("Serving file: %s (size: %d bytes, path: %s)", fname, path.stat().st_size, path)
    
    # Do NOT set filename= here. That would add Content-Disposition: attachment,
    # which triggers IDM interception and steals the response body from fetch().
    # The frontend constructs its own filename via the blob download approach.
    return FileResponse(
        path,
        media_type="application/octet-stream"
    )


# ---------------------------------------------------------------------------
# Download-Only Feature
# ---------------------------------------------------------------------------
class VideoInfoRequest(BaseModel):
    url: str


class DirectDownloadRequest(BaseModel):
    url: str
    format_id: str
    media_type: str = "video"  # "video" or "audio"


@app.post("/api/video-info")
async def get_video_info(req: VideoInfoRequest):
    """Fetch video metadata and available formats using yt-dlp."""
    import yt_dlp

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
    except Exception as e:
        raise HTTPException(400, f"Could not fetch video info: {e}")

    # Build video formats list
    video_formats = []
    audio_formats = []
    
    raw_formats = info.get("formats", [])
    log.info("URL %s returned %d raw formats", req.url[:60], len(raw_formats))

    for f in raw_formats:
        fid = f.get("format_id", "")
        ext = f.get("ext", "")
        height = f.get("height")
        width = f.get("width")
        vcodec = f.get("vcodec", "none") or "none"
        acodec = f.get("acodec", "none") or "none"
        filesize = f.get("filesize") or f.get("filesize_approx") or 0
        tbr = f.get("tbr") or 0
        abr = f.get("abr") or 0
        format_note = f.get("format_note", "")
        resolution = f.get("resolution", "")
        has_video = vcodec != "none"
        has_audio = acodec != "none"

        # === VIDEO formats (video-only OR combined video+audio) ===
        if has_video:
            # Build detailed quality label
            if height and height >= 100:
                label = f"{height}p"
            elif format_note:
                label = format_note
            elif resolution and resolution != "audio only":
                label = resolution
            elif width:
                label = f"{width}w"
            else:
                label = f"video"

            # Add codec info for differentiation
            short_codec = ""
            if "avc" in vcodec.lower() or "h264" in vcodec.lower():
                short_codec = "h264"
            elif "vp9" in vcodec.lower() or "vp09" in vcodec.lower():
                short_codec = "vp9"
            elif "av01" in vcodec.lower() or "av1" in vcodec.lower():
                short_codec = "av1"
            elif "hevc" in vcodec.lower() or "h265" in vcodec.lower():
                short_codec = "h265"
            
            if short_codec:
                display_label = f"{label} {short_codec}"
            else:
                display_label = label
            
            # Mark if it has both audio and video
            if has_audio:
                display_label += " +audio"

            video_formats.append({
                "format_id": fid,
                "quality": display_label,
                "height": height or 0,
                "ext": ext,
                "filesize_mb": round(filesize / (1024 * 1024), 1) if filesize else None,
                "bitrate": round(tbr) if tbr else None,
                "has_audio": has_audio,
            })

        # === AUDIO-only formats ===
        elif has_audio and not has_video:
            effective_abr = abr or tbr or 0
            if effective_abr:
                label = f"{round(effective_abr)}kbps"
            elif format_note:
                label = format_note
            else:
                label = ext or f"audio"
            
            audio_formats.append({
                "format_id": fid,
                "quality": label,
                "ext": ext,
                "filesize_mb": round(filesize / (1024 * 1024), 1) if filesize else None,
                "bitrate": round(effective_abr) if effective_abr else None,
            })

    # Sort by quality
    video_formats.sort(key=lambda x: (x["height"], x.get("bitrate") or 0), reverse=True)
    audio_formats.sort(key=lambda x: (x.get("bitrate") or 0), reverse=True)
    
    # If no separate audio formats were found, add a "best audio" option
    # Many non-YouTube sites only have combined formats
    if not audio_formats and video_formats:
        audio_formats.append({
            "format_id": "bestaudio/best",
            "quality": "Best available",
            "ext": "m4a",
            "filesize_mb": None,
            "bitrate": None,
        })
    
    log.info("Parsed %d video formats, %d audio formats", len(video_formats), len(audio_formats))

    # Thumbnail
    thumbnail = info.get("thumbnail", "")

    return {
        "title": info.get("title", "Unknown"),
        "duration": info.get("duration", 0),
        "channel": info.get("channel", info.get("uploader", "Unknown")),
        "thumbnail": thumbnail,
        "view_count": info.get("view_count", 0),
        "video_formats": video_formats,
        "audio_formats": audio_formats,
    }


@app.post("/api/download-start")
async def download_start(req: DirectDownloadRequest):
    """Start a background download job with real-time progress via SSE."""
    import yt_dlp

    job_id = str(uuid.uuid4())
    loop = asyncio.get_event_loop()
    queue = asyncio.Queue()

    jobs[job_id] = {
        "id": job_id,
        "status": "processing",
        "queue": queue,
        "output_file": None,
        "output_name": None,
        "created": datetime.now().isoformat(),
    }
    save_jobs()

    def _do_download():
        try:
            tmp_dir = DOWNLOADS_DIR
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")

            # yt-dlp progress hook → push to SSE
            def progress_hook(d):
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    downloaded = d.get("downloaded_bytes", 0)
                    speed = d.get("speed") or 0
                    eta = d.get("eta") or 0

                    if total > 0:
                        pct = int((downloaded / total) * 100)
                    else:
                        pct = 0

                    # Format speed & sizes
                    dl_mb = downloaded / (1024 * 1024)
                    total_mb = total / (1024 * 1024) if total else 0
                    speed_mb = speed / (1024 * 1024) if speed else 0

                    if total_mb > 0:
                        msg = f"{dl_mb:.1f} / {total_mb:.1f} MB — {speed_mb:.1f} MB/s"
                    else:
                        msg = f"{dl_mb:.1f} MB — {speed_mb:.1f} MB/s"

                    _push(job_id, "download", pct, msg)

                elif d.get("status") == "finished":
                    _push(job_id, "download", 95, "Merging audio & video…")

            if req.media_type == "audio":
                ydl_opts = {
                    "quiet": True,
                    "no_warnings": True,
                    "format": f"{req.format_id}/bestaudio/best",
                    "outtmpl": str(tmp_dir / f"audio_{ts}.%(ext)s"),
                    "progress_hooks": [progress_hook],
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }],
                }
            else:
                ydl_opts = {
                    "quiet": True,
                    "no_warnings": True,
                    "format": f"{req.format_id}+bestaudio/best",
                    "outtmpl": str(tmp_dir / f"video_{ts}.%(ext)s"),
                    "merge_output_format": "mp4",
                    "progress_hooks": [progress_hook],
                }

            _push(job_id, "download", 0, "Starting download…")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(req.url, download=True)
                filename = ydl.prepare_filename(info)

                # If audio, yt-dlp might have changed the extension to .mp3 via postprocessor
                if req.media_type == "audio":
                    mp3_path = Path(filename).with_suffix(".mp3")
                    if mp3_path.exists():
                        filename = str(mp3_path)
                    elif not Path(filename).exists():
                        # Check if any file with the same stem exists (in case extension is weird)
                        stem_matches = list(Path(filename).parent.glob(f"{Path(filename).stem}.*"))
                        if stem_matches:
                            filename = str(stem_matches[0])

            filepath = Path(filename)
            if not filepath.exists() and req.media_type != "audio":
                filepath = filepath.with_suffix(".mp4")

            # ── Re-encode audio to AAC for Windows compatibility ────
            if filepath.exists() and req.media_type != "audio":
                _push(job_id, "download", 96, "Converting audio to AAC…")
                aac_path = filepath.parent / f"{filepath.stem}_aac.mp4"
                result = subprocess.run(
                    [
                        "ffmpeg", "-i", str(filepath),
                        "-c:v", "copy",        # keep video stream as-is
                        "-c:a", "aac",          # re-encode audio to AAC
                        "-b:a", "192k",
                        str(aac_path),
                        "-y",                   # overwrite if exists
                    ],
                    capture_output=True, timeout=120,
                )
                if result.returncode == 0 and aac_path.exists():
                    filepath.unlink(missing_ok=True)  # remove opus version
                    filepath = aac_path
                    log.info("Audio converted to AAC: %s", aac_path.name)
                else:
                    log.warning("AAC conversion failed, keeping original: %s",
                                result.stderr.decode(errors="replace")[-200:])

            if filepath.exists():
                size_mb = filepath.stat().st_size / (1024 * 1024)
                jobs[job_id]["output_file"] = str(filepath)
                jobs[job_id]["output_name"] = filepath.name
                jobs[job_id]["status"] = "complete"
                save_jobs()
                log.info("Download complete: %s (%.1f MB)", filepath, size_mb)
                _push(job_id, "complete", 100, f"Done! ({size_mb:.1f} MB)", status="complete")
            else:
                jobs[job_id]["status"] = "error"
                save_jobs()
                log.error("File not found after download: %s", filepath)
                _push(job_id, "error", 100, "Download finished but file not found.", status="error")

        except Exception as e:
            log.exception("Direct download error for job %s", job_id)
            _push(job_id, "error", -1, f"Download failed: {e}", status="error")
            jobs[job_id]["status"] = "error"

    log.info("Starting direct download %s — format %s", job_id[:8], req.format_id)
    loop.run_in_executor(executor, _do_download)

    return {"job_id": job_id}
# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    # Fly.io expects the app to listen on 0.0.0.0 and defaults to port 8080
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8080, reload=False)

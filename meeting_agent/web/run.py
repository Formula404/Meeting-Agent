from __future__ import annotations

import logging
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from meeting_agent.web.api.app import router
from meeting_agent.web.api.transcription_routes import router as transcription_router

perf_logger = logging.getLogger("perf")


class TimingMiddleware(BaseHTTPMiddleware):
    """记录所有请求的耗时，用于压测时定位瓶颈。"""

    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        try:
            response = await call_next(request)
            return response
        finally:
            cost = time.perf_counter() - start
            perf_logger.info(
                "PERF method=%s path=%s cost=%.3fs",
                request.method,
                request.url.path,
                cost,
            )


app = FastAPI(title="Meeting Agent", docs_url="/api/docs")
app.add_middleware(TimingMiddleware)

# CORS — allow Vue dev server on port 5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(transcription_router)

# Serve built frontend (from `frontend/dist/`) in production
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Not found"}, status_code=404)
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return JSONResponse({"detail": "Not found"}, status_code=404)


def main() -> None:
    import uvicorn

    # 配置 perf logger 输出到控制台
    perf_handler = logging.StreamHandler()
    perf_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    ))
    perf_logger = logging.getLogger("perf")
    perf_logger.setLevel(logging.INFO)
    perf_logger.addHandler(perf_handler)

    uvicorn.run("meeting_agent.web.run:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from meeting_agent.web.api.app import router

app = FastAPI(title="Meeting Agent", docs_url="/api/docs")

# CORS — allow Vue dev server on port 5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

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
    uvicorn.run("meeting_agent.web.run:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()

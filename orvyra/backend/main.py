import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router, root_router

import logging
import traceback
from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

app = FastAPI(
    title="ORVYRA",
    description="Intelligence for the space economy's cousin: intelligence for the outbound call. "
                 "Pre-call and post-call reasoning layer consumed by Klesos.",
    version="0.1.0",
)

# Enable CORS for cross-origin requests from Vercel dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Flag: Lock down to real Vercel frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Internal server error: {str(exc)}"},
    )

app.include_router(router)
app.include_router(root_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "orvyra"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8009))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

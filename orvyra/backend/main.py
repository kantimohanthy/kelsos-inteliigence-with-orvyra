from fastapi import FastAPI
from api.routes import router

app = FastAPI(
    title="ORVYRA",
    description="Intelligence for the space economy's cousin: intelligence for the outbound call. "
                 "Pre-call and post-call reasoning layer consumed by Klesos.",
    version="0.1.0",
)
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "orvyra"}

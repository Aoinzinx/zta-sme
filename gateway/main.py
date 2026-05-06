# gateway/main.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from middleware import ZeroTrustMiddleware
from routes.proxy import router as proxy_router
from routes.admin import router as admin_router
from database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ZT-SME Access Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# !! Zero Trust middleware MUST be registered before route handlers !!
app.add_middleware(ZeroTrustMiddleware)

# Admin API consumed by the dashboard — MUST be before the catch-all proxy router
app.include_router(admin_router, prefix="/admin")

# Upstream proxy routes: /aws/* and /azure/* (catch-all, must be last)
app.include_router(proxy_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "gateway"}


if __name__ == "__main__":
    import uvicorn
    # TLS is terminated upstream by nginx; gateway listens on plain HTTP internally
    uvicorn.run("main:app", host="0.0.0.0", port=8443, workers=1)

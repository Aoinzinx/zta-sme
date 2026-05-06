# policy-engine/main.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from evaluator import router as eval_router
from database import engine
from models import Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ZT-SME Policy Engine", version="1.0.0")

app.include_router(eval_router, prefix="/policy")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "policy-engine"}


if __name__ == "__main__":
    import uvicorn
    # Loopback only — never exposed externally
    uvicorn.run("main:app", host="127.0.0.1", port=8001, workers=1)

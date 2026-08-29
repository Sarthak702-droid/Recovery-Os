from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db import init_db
from app.routers import analytics, cases, operations, policy, webhooks

@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield

app = FastAPI(title="RecoverOS API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(webhooks.router)
app.include_router(cases.router)
app.include_router(analytics.router)
app.include_router(policy.router)
app.include_router(operations.router)

@app.get("/health")
async def health(): return {"status": "ok", "service": "recoveros-api"}

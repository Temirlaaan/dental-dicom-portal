import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.middleware.audit import AuditMiddleware
from app.routers import assignments, audit_logs, auth, health, patients
from app.services.session_monitor import orphaned_session_cleanup, session_timeout_monitor


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = [
        asyncio.create_task(session_timeout_monitor()),
        asyncio.create_task(orphaned_session_cleanup()),
    ]
    yield
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(title="Dental DICOM Portal API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)

app.include_router(health.router, tags=["health"])
app.include_router(auth.router)
app.include_router(patients.router, prefix="/api")
app.include_router(assignments.router, prefix="/api")
app.include_router(audit_logs.router, prefix="/api")

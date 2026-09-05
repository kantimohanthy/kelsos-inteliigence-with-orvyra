"""
Job Tracking Store — Postgres/SQLAlchemy backed job store for async pre-warming.
Maintains exact same interface signatures as MVP in-memory store.
"""

from __future__ import annotations
import datetime
from typing import Literal
from pydantic import BaseModel, Field
import uuid
from sqlalchemy import desc, delete
from storage.db import SessionLocal, engine, Base
from storage.sql_models import EnrichmentRunModel, ProspectModel


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class EnrichmentJob(BaseModel):
    job_id: str = Field(default_factory=lambda: new_id("job"))
    prospect_id: str
    status: Literal["pending", "enriching", "ready", "partial", "failed", "needs_review"] = "pending"
    error: str | None = None
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


class EnrichmentJobStore:
    def __init__(self) -> None:
        Base.metadata.create_all(bind=engine)

    def create(
        self,
        prospect_id: str,
        job_id: str | None = None,
        status: Literal["pending", "enriching", "ready", "partial", "failed", "needs_review"] = "pending"
    ) -> EnrichmentJob:
        db = SessionLocal()
        try:
            # Ensure ProspectModel row exists for foreign key constraint
            prospect = db.query(ProspectModel).filter_by(prospect_id=prospect_id).first()
            if not prospect:
                db.add(ProspectModel(prospect_id=prospect_id, name="Pending Prospect"))
                db.flush()

            jid = job_id or new_id("job")
            now = datetime.datetime.now(datetime.timezone.utc)
            run = EnrichmentRunModel(
                run_id=jid,
                job_id=jid,
                prospect_id=prospect_id,
                started_at=now,
                status=status,
            )
            db.merge(run)
            db.commit()

            return EnrichmentJob(
                job_id=jid,
                prospect_id=prospect_id,
                status=status,
                created_at=now,
            )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def update_status(self, job_id: str, status: str, error: str | None = None) -> None:
        db = SessionLocal()
        try:
            update_data: dict = {"status": status}
            if error is not None:
                update_data["error"] = error
            if status in ("ready", "partial", "failed", "needs_review"):
                update_data["completed_at"] = datetime.datetime.now(datetime.timezone.utc)

            db.query(EnrichmentRunModel).filter(
                (EnrichmentRunModel.job_id == job_id) | (EnrichmentRunModel.run_id == job_id)
            ).update(update_data, synchronize_session=False)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get(self, job_id: str) -> EnrichmentJob | None:
        db = SessionLocal()
        try:
            run = db.query(EnrichmentRunModel).filter(
                (EnrichmentRunModel.job_id == job_id) | (EnrichmentRunModel.run_id == job_id)
            ).first()
            if not run:
                return None
            return EnrichmentJob(
                job_id=run.job_id or run.run_id,
                prospect_id=run.prospect_id,
                status=run.status,  # type: ignore
                error=run.error,
                created_at=run.started_at,
            )
        finally:
            db.close()

    def find_by_prospect(self, prospect_id: str) -> EnrichmentJob | None:
        db = SessionLocal()
        try:
            run = (
                db.query(EnrichmentRunModel)
                .filter_by(prospect_id=prospect_id)
                .order_by(desc(EnrichmentRunModel.started_at))
                .first()
            )
            if not run:
                return None
            return EnrichmentJob(
                job_id=run.job_id or run.run_id,
                prospect_id=run.prospect_id,
                status=run.status,  # type: ignore
                error=run.error,
                created_at=run.started_at,
            )
        finally:
            db.close()

    def clear(self) -> None:
        db = SessionLocal()
        try:
            db.execute(delete(EnrichmentRunModel))
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


# Process-wide singleton for job tracking
jobs = EnrichmentJobStore()

"""
SQLAlchemy 2.x ORM models.

Mirrors the Pydantic schemas in `apps/api/schemas.py` for entity persistence.
Designed for PostgreSQL but uses portable types where possible.

Naming: lowercase singular table names (`project`, `site`, `device`, ...).
Indexing: every FK is indexed; common query columns (status, type, hash)
have explicit indexes.

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ─── Base ───────────────────────────────────────────────────────────────


class Base(DeclarativeBase):
    """Declarative base. Use PG_UUID with fallback to native UUID."""

    type_annotation_map = {
        dict: JSONB().with_variant(JSON(), "sqlite"),
    }


def _uuid_pk() -> Mapped[UUID]:
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)


def _uuid_fk(target: str, *, index: bool = True, nullable: bool = False) -> Mapped[UUID]:
    return mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(target, ondelete="CASCADE"),
        nullable=nullable,
        index=index,
    )


def _timestamps() -> tuple[Mapped[datetime], Mapped[datetime]]:
    return (
        mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False),
        mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )


# ─── Tables ─────────────────────────────────────────────────────────────


class Project(Base):
    __tablename__ = "project"

    id: Mapped[UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    created_at, updated_at = _timestamps()

    sites: Mapped[list["Site"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    devices: Mapped[list["Device"]] = relationship(back_populates="project")


class Site(Base):
    __tablename__ = "site"
    __table_args__ = (UniqueConstraint("project_id", "site_number", name="uq_site_project_number"),)

    id: Mapped[UUID] = _uuid_pk()
    project_id: Mapped[UUID] = _uuid_fk("project.id")
    site_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(500))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(50))
    zip_code: Mapped[Optional[str]] = mapped_column(String(20))
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    created_at, updated_at = _timestamps()

    project: Mapped["Project"] = relationship(back_populates="sites")
    floors: Mapped[list["Floor"]] = relationship(back_populates="site", cascade="all, delete-orphan")


class Floor(Base):
    __tablename__ = "floor"

    id: Mapped[UUID] = _uuid_pk()
    site_id: Mapped[UUID] = _uuid_fk("site.id")
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at, updated_at = _timestamps()

    site: Mapped["Site"] = relationship(back_populates="floors")
    maps: Mapped[list["Map"]] = relationship(back_populates="floor", cascade="all, delete-orphan")


class Map(Base):
    __tablename__ = "map"

    id: Mapped[UUID] = _uuid_pk()
    floor_id: Mapped[UUID] = _uuid_fk("floor.id")
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="cad")
    width_px: Mapped[Optional[int]] = mapped_column(Integer)
    height_px: Mapped[Optional[int]] = mapped_column(Integer)
    scale: Mapped[Optional[float]] = mapped_column(Float)
    created_at, updated_at = _timestamps()

    floor: Mapped["Floor"] = relationship(back_populates="maps")


class Device(Base):
    __tablename__ = "device"

    id: Mapped[UUID] = _uuid_pk()
    project_id: Mapped[UUID] = _uuid_fk("project.id")
    site_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    floor_id: Mapped[Optional[UUID]] = _uuid_fk("floor.id", nullable=True)
    map_id: Mapped[Optional[UUID]] = _uuid_fk("map.id", nullable=True)
    device_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(100))
    model: Mapped[Optional[str]] = mapped_column(String(100))
    local_x: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    local_y: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    height_ft: Mapped[Optional[float]] = mapped_column(Float)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), index=True)  # ipv6-ready
    mac_address: Mapped[Optional[str]] = mapped_column(String(17))
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB().with_variant(JSON(), "sqlite"))
    created_at, updated_at = _timestamps()

    project: Mapped["Project"] = relationship(back_populates="devices")


class Zone(Base):
    __tablename__ = "zone"

    id: Mapped[UUID] = _uuid_pk()
    project_id: Mapped[UUID] = _uuid_fk("project.id")
    floor_id: Mapped[UUID] = _uuid_fk("floor.id")
    zone_name: Mapped[str] = mapped_column(String(200), nullable=False)
    zone_type: Mapped[str] = mapped_column(String(100), nullable=False, default="general")
    polygon: Mapped[Optional[dict]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"))
    created_at, updated_at = _timestamps()


class Cable(Base):
    __tablename__ = "cable"

    id: Mapped[UUID] = _uuid_pk()
    project_id: Mapped[UUID] = _uuid_fk("project.id")
    site_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_device_id: Mapped[UUID] = _uuid_fk("device.id")
    destination_device_id: Mapped[UUID] = _uuid_fk("device.id")
    cable_type: Mapped[str] = mapped_column(String(50), nullable=False, default="cat6")
    length_ft: Mapped[Optional[float]] = mapped_column(Float)
    created_at, updated_at = _timestamps()


class ImportBatch(Base):
    __tablename__ = "import_batch"

    id: Mapped[UUID] = _uuid_pk()
    source_file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    source_file_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="uploaded", index=True)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    staged_payload: Mapped[Optional[dict]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"))
    committed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    actor: Mapped[Optional[str]] = mapped_column(String(200))
    created_at, updated_at = _timestamps()


class Event(Base):
    """Append-only audit ledger."""

    __tablename__ = "event"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer(), "sqlite"), primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    payload: Mapped[dict] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    actor: Mapped[Optional[str]] = mapped_column(String(200))
    request_id: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class Snapshot(Base):
    """Point-in-time backup for rollback."""

    __tablename__ = "snapshot"

    id: Mapped[UUID] = _uuid_pk()
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class IdempotencyKey(Base):
    """Stores idempotency-key → response mappings so retried writes don't duplicate."""

    __tablename__ = "idempotency_key"

    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    operation: Mapped[str] = mapped_column(String(100), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    response_payload: Mapped[dict] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)


# ─── Lifecycle tables (for Phase 3 features in lifecycle.py) ────────────


class SiteExtended(Base):
    """Extended site lifecycle (sandbox / design / installation / live / archived)."""

    __tablename__ = "site_extended"

    id: Mapped[UUID] = _uuid_pk()
    project_id: Mapped[UUID] = _uuid_fk("project.id")
    site_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    site_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    address: Mapped[Optional[str]] = mapped_column(String(500))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(50))
    zip_code: Mapped[Optional[str]] = mapped_column(String(20))
    type_history: Mapped[Optional[dict]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"))
    created_at, updated_at = _timestamps()


class Design(Base):
    """Design workflow records."""

    __tablename__ = "design"

    id: Mapped[UUID] = _uuid_pk()
    project_id: Mapped[UUID] = _uuid_fk("project.id")
    site_id: Mapped[UUID] = _uuid_fk("site_extended.id")
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    design_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft", index=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal", index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    assigned_to: Mapped[Optional[str]] = mapped_column(String(200), index=True)
    vendor_id: Mapped[Optional[UUID]] = mapped_column(Uuid(as_uuid=True))
    vendor_status: Mapped[Optional[str]] = mapped_column(String(50))
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    status_history: Mapped[Optional[dict]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"))
    created_at, updated_at = _timestamps()


class SandboxConfig(Base):
    """Sandbox / template metadata."""

    __tablename__ = "sandbox_config"

    id: Mapped[UUID] = _uuid_pk()
    site_id: Mapped[UUID] = _uuid_fk("site_extended.id")
    cloned_from: Mapped[Optional[UUID]] = mapped_column(Uuid(as_uuid=True))
    is_template: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    template_name: Mapped[Optional[str]] = mapped_column(String(200))
    purpose: Mapped[str] = mapped_column(String(100), nullable=False, default="clone")
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    created_at, updated_at = _timestamps()

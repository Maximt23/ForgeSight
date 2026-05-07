#!/usr/bin/env python3
"""CadOwl Memory Library: learn patterns from DWG/DXF corpora."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import ezdxf

from cad2siteowl_enhanced import (
    DEVICE_BLOCK_PATTERNS,
    DEVICE_LAYER_PATTERNS,
    EXCLUDE_BLOCK_PATTERNS,
    matches_any_pattern,
)
from enhanced_models import NAME_TAGS
from cadowl_memory.recommendations import load_recommended_patterns
from cadowl_memory.spatial_signals import (
    DEFAULT_DEPARTMENT_CODE_MAP,
    aisle_direction_hint,
    department_name,
    extract_aisle_number,
    extract_department_code,
)


@dataclass
class IngestResult:
    path: Path
    status: str
    detected_devices: int = 0
    total_inserts: int = 0
    notes: str = ""


class CadMemoryLibrary:
    """Persistent CAD pattern memory backed by SQLite."""

    def __init__(self, db_path: Optional[Path] = None, department_map_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else Path(__file__).resolve().parent.parent / "cadowl_memory.db"
        default_map_path = Path(__file__).resolve().parent / "department_map.json"
        self.department_map = self._load_department_map(department_map_path or default_map_path)
        self._init_db()

    @staticmethod
    def _load_department_map(map_path: Path) -> Dict[str, str]:
        try:
            raw = json.loads(Path(map_path).read_text(encoding="utf-8"))
            mapped = {
                str(k).strip().upper(): str(v).strip()
                for k, v in raw.items()
                if str(k).strip() and str(v).strip()
            }
            return mapped or DEFAULT_DEPARTMENT_CODE_MAP.copy()
        except Exception:
            return DEFAULT_DEPARTMENT_CODE_MAP.copy()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS source_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path_hash TEXT UNIQUE NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER,
                    modified_ts REAL,
                    store_number TEXT,
                    status TEXT NOT NULL,
                    device_count INTEGER DEFAULT 0,
                    last_ingested TEXT NOT NULL,
                    notes TEXT
                );

                CREATE TABLE IF NOT EXISTS cad_devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_file_id INTEGER NOT NULL,
                    device_idx INTEGER NOT NULL,
                    layer TEXT NOT NULL,
                    block_name TEXT NOT NULL,
                    raw_name TEXT,
                    system_guess TEXT,
                    department_code TEXT,
                    department_name TEXT,
                    aisle_number INTEGER,
                    aisle_direction TEXT,
                    cad_x REAL,
                    cad_y REAL,
                    rotation REAL,
                    xscale REAL,
                    yscale REAL,
                    FOREIGN KEY(source_file_id) REFERENCES source_files(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS device_attributes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    tag TEXT NOT NULL,
                    value TEXT,
                    FOREIGN KEY(device_id) REFERENCES cad_devices(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS tree_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_key TEXT NOT NULL,
                    child_key TEXT NOT NULL,
                    edge_type TEXT NOT NULL,
                    weight INTEGER NOT NULL DEFAULT 1,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    UNIQUE(parent_key, child_key, edge_type)
                );

                CREATE TABLE IF NOT EXISTS source_edge_contrib (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_file_id INTEGER NOT NULL,
                    parent_key TEXT NOT NULL,
                    child_key TEXT NOT NULL,
                    edge_type TEXT NOT NULL,
                    weight INTEGER NOT NULL DEFAULT 1,
                    UNIQUE(source_file_id, parent_key, child_key, edge_type),
                    FOREIGN KEY(source_file_id) REFERENCES source_files(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_source_status ON source_files(status);
                CREATE INDEX IF NOT EXISTS idx_source_store ON source_files(store_number);
                CREATE INDEX IF NOT EXISTS idx_devices_system ON cad_devices(system_guess);
                CREATE INDEX IF NOT EXISTS idx_devices_layer ON cad_devices(layer);
                CREATE INDEX IF NOT EXISTS idx_devices_block ON cad_devices(block_name);
                CREATE INDEX IF NOT EXISTS idx_attrs_tag ON device_attributes(tag);
                CREATE INDEX IF NOT EXISTS idx_tree_parent ON tree_edges(parent_key);
                CREATE INDEX IF NOT EXISTS idx_tree_edge_type ON tree_edges(edge_type);
                CREATE INDEX IF NOT EXISTS idx_contrib_source ON source_edge_contrib(source_file_id);
                """
            )

            # Lightweight schema migration for existing DBs
            existing_cols = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(cad_devices)").fetchall()
            }
            if "department_code" not in existing_cols:
                conn.execute("ALTER TABLE cad_devices ADD COLUMN department_code TEXT")
            if "department_name" not in existing_cols:
                conn.execute("ALTER TABLE cad_devices ADD COLUMN department_name TEXT")
            if "aisle_number" not in existing_cols:
                conn.execute("ALTER TABLE cad_devices ADD COLUMN aisle_number INTEGER")
            if "aisle_direction" not in existing_cols:
                conn.execute("ALTER TABLE cad_devices ADD COLUMN aisle_direction TEXT")

            conn.execute("CREATE INDEX IF NOT EXISTS idx_devices_dept_code ON cad_devices(department_code)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_devices_dept_name ON cad_devices(department_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_devices_aisle_num ON cad_devices(aisle_number)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_devices_aisle_dir ON cad_devices(aisle_direction)")

    @staticmethod
    def _store_from_filename(path: Path) -> str:
        match = re.search(r"\b(\d{3,5})\b", path.stem)
        return match.group(1) if match else "UNKNOWN"

    @staticmethod
    def _path_hash(path: Path) -> str:
        return hashlib.sha1(str(path.resolve()).lower().encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_token(text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip())

    def _infer_system(self, layer: str, block: str, raw_name: str) -> str:
        combined = f"{layer} {block} {raw_name}".upper()
        if any(x in combined for x in ["CCTV", "CAM", "VIDEO", "SURV"]):
            return "Video Surveillance"
        if any(x in combined for x in ["MOTION", "BURG", "DOOR", "INTRUSION"]):
            return "Intrusion Detection"
        if any(x in combined for x in ["ALARM", "NOTIF", "EFP", "FIRE", "PULL", "SMOKE", "FLOW", "TAMPER"]):
            return "Fire Alarm"
        return "Unknown"

    def _upsert_source_file(
        self,
        conn: sqlite3.Connection,
        path: Path,
        file_type: str,
        status: str,
        notes: str = "",
        device_count: int = 0,
    ) -> int:
        stat = path.stat() if path.exists() else None
        now = datetime.utcnow().isoformat()
        row = conn.execute(
            "SELECT id FROM source_files WHERE path_hash = ?",
            (self._path_hash(path),),
        ).fetchone()

        payload = (
            str(path.resolve()),
            file_type.lower(),
            stat.st_size if stat else None,
            stat.st_mtime if stat else None,
            self._store_from_filename(path),
            status,
            device_count,
            now,
            notes,
            self._path_hash(path),
        )

        if row:
            conn.execute(
                """
                UPDATE source_files
                SET file_path=?, file_type=?, file_size=?, modified_ts=?, store_number=?,
                    status=?, device_count=?, last_ingested=?, notes=?
                WHERE path_hash=?
                """,
                payload,
            )
            return int(row["id"])

        cursor = conn.execute(
            """
            INSERT INTO source_files (
                file_path, file_type, file_size, modified_ts, store_number,
                status, device_count, last_ingested, notes, path_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            payload,
        )
        return int(cursor.lastrowid)

    def _increment_edge(
        self,
        conn: sqlite3.Connection,
        parent: str,
        child: str,
        edge_type: str,
        source_file_id: Optional[int] = None,
    ) -> None:
        now = datetime.utcnow().isoformat()
        conn.execute(
            """
            INSERT INTO tree_edges (parent_key, child_key, edge_type, weight, first_seen, last_seen)
            VALUES (?, ?, ?, 1, ?, ?)
            ON CONFLICT(parent_key, child_key, edge_type)
            DO UPDATE SET weight = weight + 1, last_seen = excluded.last_seen
            """,
            (parent, child, edge_type, now, now),
        )

        if source_file_id is not None:
            conn.execute(
                """
                INSERT INTO source_edge_contrib (source_file_id, parent_key, child_key, edge_type, weight)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(source_file_id, parent_key, child_key, edge_type)
                DO UPDATE SET weight = weight + 1
                """,
                (source_file_id, parent, child, edge_type),
            )

    def _remove_source_edge_contributions(self, conn: sqlite3.Connection, source_file_id: int) -> None:
        rows = conn.execute(
            """
            SELECT parent_key, child_key, edge_type, weight
            FROM source_edge_contrib
            WHERE source_file_id = ?
            """,
            (source_file_id,),
        ).fetchall()

        for row in rows:
            conn.execute(
                """
                UPDATE tree_edges
                SET weight = CASE WHEN weight > ? THEN weight - ? ELSE 0 END
                WHERE parent_key = ? AND child_key = ? AND edge_type = ?
                """,
                (
                    row["weight"],
                    row["weight"],
                    row["parent_key"],
                    row["child_key"],
                    row["edge_type"],
                ),
            )

        conn.execute("DELETE FROM tree_edges WHERE weight <= 0")
        conn.execute("DELETE FROM source_edge_contrib WHERE source_file_id = ?", (source_file_id,))

    def _extract_raw_name(self, attributes: Dict[str, str], fallback_block: str) -> str:
        for tag in NAME_TAGS:
            if tag in attributes and self._normalize_token(attributes[tag]):
                return self._normalize_token(attributes[tag])
        return fallback_block

    def ingest_dxf(self, dxf_path: Path) -> IngestResult:
        dxf_path = Path(dxf_path)
        if not dxf_path.exists():
            return IngestResult(path=dxf_path, status="missing", notes="DXF file does not exist")

        with self._connect() as conn:
            source_id = self._upsert_source_file(conn, dxf_path, "dxf", status="processing")
            self._remove_source_edge_contributions(conn, source_id)
            conn.execute("DELETE FROM cad_devices WHERE source_file_id = ?", (source_id,))

            try:
                doc = ezdxf.readfile(str(dxf_path))
            except Exception as ex:
                self._upsert_source_file(conn, dxf_path, "dxf", status="failed", notes=str(ex))
                return IngestResult(path=dxf_path, status="failed", notes=str(ex))

            msp = doc.modelspace()
            inserts = list(msp.query("INSERT"))
            device_count = 0
            store_number = self._store_from_filename(dxf_path)

            for idx, entity in enumerate(inserts):
                block_name = entity.dxf.name
                layer = entity.dxf.layer

                if matches_any_pattern(block_name, EXCLUDE_BLOCK_PATTERNS):
                    continue

                is_device = (
                    matches_any_pattern(layer, DEVICE_LAYER_PATTERNS)
                    or matches_any_pattern(block_name, DEVICE_BLOCK_PATTERNS)
                )
                if not is_device:
                    continue

                attributes: Dict[str, str] = {}
                if entity.has_attrib:
                    for attr in entity.attribs:
                        tag = self._normalize_token(attr.dxf.tag.upper())
                        val = self._normalize_token(attr.dxf.text)
                        if val:
                            attributes[tag] = val

                raw_name = self._extract_raw_name(attributes, block_name)
                system_guess = self._infer_system(layer, block_name, raw_name)
                department_code = extract_department_code(
                    layer,
                    block_name,
                    raw_name,
                    attributes,
                    system_guess,
                    self.department_map,
                )
                department_name_val = department_name(department_code, self.department_map)
                aisle_number = extract_aisle_number(layer, block_name, raw_name, attributes, system_guess)
                aisle_direction = aisle_direction_hint(aisle_number, first_aisle_direction="RTL")

                cursor = conn.execute(
                    """
                    INSERT INTO cad_devices (
                        source_file_id, device_idx, layer, block_name, raw_name, system_guess,
                        department_code, department_name, aisle_number, aisle_direction,
                        cad_x, cad_y, rotation, xscale, yscale
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source_id,
                        idx,
                        layer,
                        block_name,
                        raw_name,
                        system_guess,
                        department_code,
                        department_name_val,
                        aisle_number,
                        aisle_direction,
                        float(entity.dxf.insert.x),
                        float(entity.dxf.insert.y),
                        float(getattr(entity.dxf, "rotation", 0.0)),
                        float(getattr(entity.dxf, "xscale", 1.0)),
                        float(getattr(entity.dxf, "yscale", 1.0)),
                    ),
                )
                device_id = int(cursor.lastrowid)
                device_count += 1

                for tag, value in attributes.items():
                    conn.execute(
                        "INSERT INTO device_attributes (device_id, tag, value) VALUES (?, ?, ?)",
                        (device_id, tag, value),
                    )

                root = "ROOT"
                store_node = f"STORE:{store_number}"
                system_node = f"SYSTEM:{system_guess}"
                layer_node = f"LAYER:{layer.upper()}"
                block_node = f"BLOCK:{block_name.upper()}"

                self._increment_edge(conn, root, store_node, "root_to_store", source_id)
                self._increment_edge(conn, store_node, system_node, "store_to_system", source_id)

                if department_code and department_name_val:
                    dept_node = f"DEPT:{department_code}:{department_name_val.upper()}"
                    self._increment_edge(conn, system_node, dept_node, "system_to_department", source_id)
                    if aisle_number is not None:
                        aisle_node = f"AISLE:{aisle_number:03d}"
                        self._increment_edge(conn, dept_node, aisle_node, "department_to_aisle", source_id)
                        self._increment_edge(conn, aisle_node, layer_node, "aisle_to_layer", source_id)
                        if aisle_direction:
                            self._increment_edge(conn, aisle_node, f"AISLE_DIR:{aisle_direction}", "aisle_to_direction", source_id)
                    else:
                        self._increment_edge(conn, dept_node, layer_node, "department_to_layer", source_id)
                else:
                    if aisle_number is not None:
                        aisle_node = f"AISLE:{aisle_number:03d}"
                        self._increment_edge(conn, system_node, aisle_node, "system_to_aisle", source_id)
                        self._increment_edge(conn, aisle_node, layer_node, "aisle_to_layer", source_id)
                        if aisle_direction:
                            self._increment_edge(conn, aisle_node, f"AISLE_DIR:{aisle_direction}", "aisle_to_direction", source_id)
                    else:
                        self._increment_edge(conn, system_node, layer_node, "system_to_layer", source_id)

                self._increment_edge(conn, layer_node, block_node, "layer_to_block", source_id)

                for tag in attributes.keys():
                    self._increment_edge(conn, block_node, f"TAG:{tag}", "block_to_tag", source_id)

            self._upsert_source_file(
                conn,
                dxf_path,
                "dxf",
                status="ingested",
                notes=f"Parsed INSERT entities: {len(inserts)}",
                device_count=device_count,
            )

        return IngestResult(
            path=dxf_path,
            status="ingested",
            detected_devices=device_count,
            total_inserts=len(inserts),
        )

    def register_dwg_placeholder(self, dwg_path: Path) -> IngestResult:
        dwg_path = Path(dwg_path)
        if not dwg_path.exists():
            return IngestResult(path=dwg_path, status="missing", notes="DWG file does not exist")

        with self._connect() as conn:
            self._upsert_source_file(
                conn,
                dwg_path,
                "dwg",
                status="pending_dxf",
                notes="DWG registered. Convert to DXF for deep ingest.",
                device_count=0,
            )

        return IngestResult(path=dwg_path, status="pending_dxf", notes="Registered as placeholder")

    def ingest_paths(self, paths: Iterable[Path], recursive: bool = True) -> List[IngestResult]:
        results: List[IngestResult] = []
        for raw_path in paths:
            path = Path(raw_path)
            if path.is_dir():
                pattern = "**/*" if recursive else "*"
                files = [
                    p for p in path.glob(pattern)
                    if p.is_file() and p.suffix.lower() in {".dxf", ".dwg"}
                ]
                for f in sorted(files):
                    if f.suffix.lower() == ".dxf":
                        results.append(self.ingest_dxf(f))
                    else:
                        results.append(self.register_dwg_placeholder(f))
            elif path.is_file() and path.suffix.lower() in {".dxf", ".dwg"}:
                if path.suffix.lower() == ".dxf":
                    results.append(self.ingest_dxf(path))
                else:
                    results.append(self.register_dwg_placeholder(path))
            else:
                results.append(IngestResult(path=path, status="skipped", notes="Unsupported path or extension"))

        return results

    def summary(self) -> Dict[str, int]:
        with self._connect() as conn:
            files = conn.execute("SELECT COUNT(*) AS c FROM source_files").fetchone()["c"]
            dxf = conn.execute("SELECT COUNT(*) AS c FROM source_files WHERE file_type='dxf'").fetchone()["c"]
            dwg = conn.execute("SELECT COUNT(*) AS c FROM source_files WHERE file_type='dwg'").fetchone()["c"]
            devices = conn.execute("SELECT COUNT(*) AS c FROM cad_devices").fetchone()["c"]
            edges = conn.execute("SELECT COUNT(*) AS c FROM tree_edges").fetchone()["c"]
        return {
            "files_total": int(files),
            "files_dxf": int(dxf),
            "files_dwg": int(dwg),
            "devices_total": int(devices),
            "tree_edges": int(edges),
        }

    def top_nodes(self, edge_type: str, limit: int = 20) -> List[Dict[str, object]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT parent_key, child_key, edge_type, weight
                FROM tree_edges
                WHERE edge_type = ?
                ORDER BY weight DESC, child_key ASC
                LIMIT ?
                """,
                (edge_type, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def recommended_patterns(self, system_guess: str, top_n: int = 15) -> Dict[str, List[str]]:
        with self._connect() as conn:
            return load_recommended_patterns(conn, system_guess, top_n)

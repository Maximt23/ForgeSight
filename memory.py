#!/usr/bin/env python3
"""
memory.py - Persistent memory system using SQLite

A simple but flexible key-value store with categories, timestamps, and search.
Perfect for remembering settings, paths, notes, and things that shall not be named.

Usage:
    from memory import Memory
    
    mem = Memory()
    mem.set("last_store", "0041")
    mem.set("favorite_color", "Walmart Blue", category="preferences")
    mem.remember("that_path", "we don't talk about this one", category="secrets")
    
    print(mem.get("last_store"))
    mem.forget("that_path")  # Poof! Gone forever.
    
CLI Usage:
    python memory.py set key value [--category cat]
    python memory.py get key
    python memory.py forget key
    python memory.py list [--category cat]
    python memory.py search query
"""

import sqlite3
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Any, Optional, List, Dict
from contextlib import contextmanager


# Database location - same folder as this script
DB_PATH = Path(__file__).parent / "puppy_memory.db"


class Memory:
    """Persistent memory storage using SQLite."""
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DB_PATH
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    value_type TEXT DEFAULT 'str',
                    category TEXT DEFAULT 'general',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    notes TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_category ON memories(category)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_updated ON memories(updated_at)
            """)
    
    @contextmanager
    def _connect(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _serialize(self, value: Any) -> tuple[str, str]:
        """Serialize a value for storage."""
        if isinstance(value, bool):
            return (json.dumps(value), "bool")
        elif isinstance(value, int):
            return (str(value), "int")
        elif isinstance(value, float):
            return (str(value), "float")
        elif isinstance(value, (list, dict)):
            return (json.dumps(value), "json")
        else:
            return (str(value), "str")
    
    def _deserialize(self, value: str, value_type: str) -> Any:
        """Deserialize a stored value."""
        if value_type == "int":
            return int(value)
        elif value_type == "float":
            return float(value)
        elif value_type == "bool":
            return json.loads(value)
        elif value_type == "json":
            return json.loads(value)
        return value
    
    # =========================================================================
    # Core Operations
    # =========================================================================
    
    def set(self, key: str, value: Any, category: str = "general", notes: str = None) -> None:
        """Store a value in memory."""
        serialized, value_type = self._serialize(value)
        now = datetime.now().isoformat()
        
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO memories (key, value, value_type, category, created_at, updated_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    value_type = excluded.value_type,
                    category = excluded.category,
                    updated_at = excluded.updated_at,
                    notes = COALESCE(excluded.notes, notes)
            """, (key, serialized, value_type, category, now, now, notes))
    
    # Alias for set - because "remember" is more fun
    remember = set
    
    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from memory."""
        with self._connect() as conn:
            # Update access count
            conn.execute("""
                UPDATE memories SET access_count = access_count + 1 WHERE key = ?
            """, (key,))
            
            row = conn.execute(
                "SELECT value, value_type FROM memories WHERE key = ?", (key,)
            ).fetchone()
            
            if row:
                return self._deserialize(row["value"], row["value_type"])
            return default
    
    # Alias for get
    recall = get
    
    def forget(self, key: str) -> bool:
        """Delete a memory. Returns True if something was forgotten."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM memories WHERE key = ?", (key,))
            return cursor.rowcount > 0
    
    def exists(self, key: str) -> bool:
        """Check if a key exists."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM memories WHERE key = ?", (key,)
            ).fetchone()
            return row is not None
    
    # =========================================================================
    # Listing and Search
    # =========================================================================
    
    def list_all(self, category: str = None, limit: int = 100) -> List[Dict]:
        """List all memories, optionally filtered by category."""
        with self._connect() as conn:
            if category:
                rows = conn.execute("""
                    SELECT key, value, value_type, category, updated_at, access_count, notes
                    FROM memories WHERE category = ?
                    ORDER BY updated_at DESC LIMIT ?
                """, (category, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT key, value, value_type, category, updated_at, access_count, notes
                    FROM memories ORDER BY updated_at DESC LIMIT ?
                """, (limit,)).fetchall()
            
            return [
                {
                    "key": r["key"],
                    "value": self._deserialize(r["value"], r["value_type"]),
                    "category": r["category"],
                    "updated_at": r["updated_at"],
                    "access_count": r["access_count"],
                    "notes": r["notes"],
                }
                for r in rows
            ]
    
    def search(self, query: str, limit: int = 50) -> List[Dict]:
        """Search memories by key, value, or notes."""
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT key, value, value_type, category, updated_at, notes
                FROM memories 
                WHERE key LIKE ? OR value LIKE ? OR notes LIKE ?
                ORDER BY updated_at DESC LIMIT ?
            """, (f"%{query}%", f"%{query}%", f"%{query}%", limit)).fetchall()
            
            return [
                {
                    "key": r["key"],
                    "value": self._deserialize(r["value"], r["value_type"]),
                    "category": r["category"],
                    "updated_at": r["updated_at"],
                    "notes": r["notes"],
                }
                for r in rows
            ]
    
    def categories(self) -> List[str]:
        """Get all categories."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT category FROM memories ORDER BY category"
            ).fetchall()
            return [r["category"] for r in rows]
    
    # =========================================================================
    # Bulk Operations
    # =========================================================================
    
    def forget_category(self, category: str) -> int:
        """Forget all memories in a category. Returns count of forgotten items."""
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM memories WHERE category = ?", (category,)
            )
            return cursor.rowcount
    
    def clear_all(self) -> int:
        """Nuclear option - forget everything. Returns count."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM memories")
            return cursor.rowcount
    
    # =========================================================================
    # Convenience Methods
    # =========================================================================
    
    def increment(self, key: str, amount: int = 1) -> int:
        """Increment a numeric value. Creates with amount if doesn't exist."""
        current = self.get(key, 0)
        if not isinstance(current, (int, float)):
            current = 0
        new_value = current + amount
        self.set(key, new_value)
        return new_value
    
    def append_to_list(self, key: str, value: Any) -> List:
        """Append a value to a list. Creates list if doesn't exist."""
        current = self.get(key, [])
        if not isinstance(current, list):
            current = [current]
        current.append(value)
        self.set(key, current)
        return current
    
    def get_stats(self) -> Dict:
        """Get memory statistics."""
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) as c FROM memories").fetchone()["c"]
            categories = conn.execute(
                "SELECT category, COUNT(*) as c FROM memories GROUP BY category"
            ).fetchall()
            most_accessed = conn.execute("""
                SELECT key, access_count FROM memories 
                ORDER BY access_count DESC LIMIT 5
            """).fetchall()
            
            return {
                "total_memories": total,
                "categories": {r["category"]: r["c"] for r in categories},
                "most_accessed": [(r["key"], r["access_count"]) for r in most_accessed],
                "db_path": str(self.db_path),
            }


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Puppy Memory - Persistent Key-Value Store")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # SET
    set_parser = subparsers.add_parser("set", help="Store a value")
    set_parser.add_argument("key", help="Key name")
    set_parser.add_argument("value", help="Value to store")
    set_parser.add_argument("--category", "-c", default="general", help="Category")
    set_parser.add_argument("--notes", "-n", help="Optional notes")
    
    # GET
    get_parser = subparsers.add_parser("get", help="Retrieve a value")
    get_parser.add_argument("key", help="Key name")
    
    # FORGET
    forget_parser = subparsers.add_parser("forget", help="Delete a memory")
    forget_parser.add_argument("key", help="Key to forget")
    
    # LIST
    list_parser = subparsers.add_parser("list", help="List memories")
    list_parser.add_argument("--category", "-c", help="Filter by category")
    list_parser.add_argument("--limit", "-l", type=int, default=20, help="Max results")
    
    # SEARCH
    search_parser = subparsers.add_parser("search", help="Search memories")
    search_parser.add_argument("query", help="Search query")
    
    # STATS
    subparsers.add_parser("stats", help="Show memory statistics")
    
    # CATEGORIES
    subparsers.add_parser("categories", help="List all categories")
    
    args = parser.parse_args()
    mem = Memory()
    
    if args.command == "set":
        mem.set(args.key, args.value, category=args.category, notes=args.notes)
        print(f"[OK] Remembered: {args.key} = {args.value}")
    
    elif args.command == "get":
        value = mem.get(args.key)
        if value is not None:
            print(value)
        else:
            print(f"[?] No memory of '{args.key}'")
    
    elif args.command == "forget":
        if mem.forget(args.key):
            print(f"[OK] Forgot: {args.key}")
        else:
            print(f"[?] Nothing to forget for '{args.key}'")
    
    elif args.command == "list":
        memories = mem.list_all(category=args.category, limit=args.limit)
        if memories:
            print(f"\n{'Key':<30} {'Value':<40} {'Category':<15}")
            print("-" * 85)
            for m in memories:
                val_str = str(m["value"])[:37] + "..." if len(str(m["value"])) > 40 else str(m["value"])
                print(f"{m['key']:<30} {val_str:<40} {m['category']:<15}")
        else:
            print("[Empty] No memories found.")
    
    elif args.command == "search":
        results = mem.search(args.query)
        if results:
            print(f"\nFound {len(results)} result(s) for '{args.query}':\n")
            for m in results:
                print(f"  [{m['category']}] {m['key']} = {m['value']}")
        else:
            print(f"[?] No memories matching '{args.query}'")
    
    elif args.command == "stats":
        stats = mem.get_stats()
        print("\n=== Puppy Memory Stats ===")
        print(f"Total memories: {stats['total_memories']}")
        print(f"Database: {stats['db_path']}")
        print("\nCategories:")
        for cat, count in stats["categories"].items():
            print(f"  {cat}: {count}")
        if stats["most_accessed"]:
            print("\nMost accessed:")
            for key, count in stats["most_accessed"]:
                print(f"  {key}: {count} times")
    
    elif args.command == "categories":
        cats = mem.categories()
        if cats:
            print("Categories:", ", ".join(cats))
        else:
            print("[Empty] No categories yet.")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

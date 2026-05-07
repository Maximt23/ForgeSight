"""Recommendation query helpers for Cad memory library."""

from __future__ import annotations

from typing import Dict, List


def uniq(values: List[str]) -> List[str]:
    seen = set()
    out = []
    for item in values:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def load_recommended_patterns(conn, system_guess: str, top_n: int = 15) -> Dict[str, List[str]]:
    system_node = f"SYSTEM:{system_guess}"

    dept_rows = conn.execute(
        """
        SELECT child_key, weight
        FROM tree_edges
        WHERE edge_type='system_to_department' AND parent_key=?
        ORDER BY weight DESC
        LIMIT ?
        """,
        (system_node, top_n),
    ).fetchall()
    department_nodes = [r["child_key"] for r in dept_rows]

    aisle_nodes: List[str] = []
    layer_nodes: List[str] = []

    if department_nodes:
        for dept_node in department_nodes:
            dept_aisle_rows = conn.execute(
                """
                SELECT child_key
                FROM tree_edges
                WHERE edge_type='department_to_aisle' AND parent_key=?
                ORDER BY weight DESC
                LIMIT ?
                """,
                (dept_node, top_n),
            ).fetchall()
            aisle_nodes.extend(r["child_key"] for r in dept_aisle_rows)

            dept_layer_rows = conn.execute(
                """
                SELECT child_key
                FROM tree_edges
                WHERE edge_type='department_to_layer' AND parent_key=?
                ORDER BY weight DESC
                LIMIT ?
                """,
                (dept_node, top_n),
            ).fetchall()
            layer_nodes.extend(r["child_key"] for r in dept_layer_rows)
    else:
        sys_aisle_rows = conn.execute(
            """
            SELECT child_key
            FROM tree_edges
            WHERE edge_type='system_to_aisle' AND parent_key=?
            ORDER BY weight DESC
            LIMIT ?
            """,
            (system_node, top_n),
        ).fetchall()
        aisle_nodes.extend(r["child_key"] for r in sys_aisle_rows)

        layer_rows = conn.execute(
            """
            SELECT child_key
            FROM tree_edges
            WHERE edge_type='system_to_layer' AND parent_key=?
            ORDER BY weight DESC
            LIMIT ?
            """,
            (system_node, top_n),
        ).fetchall()
        layer_nodes.extend(r["child_key"] for r in layer_rows)

    for aisle_node in aisle_nodes:
        aisle_layer_rows = conn.execute(
            """
            SELECT child_key
            FROM tree_edges
            WHERE edge_type='aisle_to_layer' AND parent_key=?
            ORDER BY weight DESC
            LIMIT ?
            """,
            (aisle_node, top_n),
        ).fetchall()
        layer_nodes.extend(r["child_key"] for r in aisle_layer_rows)

    direction_nodes: List[str] = []
    for aisle_node in aisle_nodes[:top_n]:
        dir_rows = conn.execute(
            """
            SELECT child_key
            FROM tree_edges
            WHERE edge_type='aisle_to_direction' AND parent_key=?
            ORDER BY weight DESC
            LIMIT 2
            """,
            (aisle_node,),
        ).fetchall()
        direction_nodes.extend(r["child_key"] for r in dir_rows)

    blocks: List[str] = []
    tags: List[str] = []
    for layer_node in layer_nodes:
        block_rows = conn.execute(
            """
            SELECT child_key
            FROM tree_edges
            WHERE edge_type='layer_to_block' AND parent_key=?
            ORDER BY weight DESC
            LIMIT ?
            """,
            (layer_node, top_n),
        ).fetchall()
        blocks.extend(r["child_key"] for r in block_rows)

    for block_node in blocks[:top_n]:
        tag_rows = conn.execute(
            """
            SELECT child_key
            FROM tree_edges
            WHERE edge_type='block_to_tag' AND parent_key=?
            ORDER BY weight DESC
            LIMIT 5
            """,
            (block_node,),
        ).fetchall()
        tags.extend(r["child_key"] for r in tag_rows)

    return {
        "departments": uniq(department_nodes),
        "aisles": uniq(aisle_nodes),
        "aisle_directions": uniq(direction_nodes),
        "layers": uniq(layer_nodes),
        "blocks": uniq(blocks)[:top_n],
        "tags": uniq(tags)[:top_n],
    }

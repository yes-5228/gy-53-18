from flask import Blueprint, request

from ..database import get_connection, rows_to_dicts

zones_bp = Blueprint("zones", __name__)


@zones_bp.get("/", strict_slashes=False)
def list_zones():
    floor = request.args.get("floor", type=int)
    with get_connection() as conn:
        query = "SELECT * FROM parking_zones"
        params = ()
        if floor is not None:
            query += " WHERE floor = ?"
            params = (floor,)
        query += " ORDER BY floor, code"
        rows = conn.execute(query, params).fetchall()

        zone_ids = [row["id"] for row in rows]
        stats = {}
        if zone_ids:
            placeholders = ",".join("?" * len(zone_ids))
            stat_rows = conn.execute(
                f"""
                SELECT zone_id, status, COUNT(*) AS count
                FROM spaces
                WHERE zone_id IN ({placeholders})
                GROUP BY zone_id, status
                """,
                zone_ids,
            ).fetchall()
            for stat_row in stat_rows:
                zid = stat_row["zone_id"]
                if zid not in stats:
                    stats[zid] = {}
                stats[zid][stat_row["status"]] = stat_row["count"]

    zones = rows_to_dicts(rows)
    for zone in zones:
        zone_stats = stats.get(zone["id"], {})
        zone["free_count"] = zone_stats.get("free", 0)
        zone["occupied_count"] = zone_stats.get("occupied", 0)
        zone["reserved_count"] = zone_stats.get("reserved", 0)
        zone["maintenance_count"] = zone_stats.get("maintenance", 0)
        zone["total_count"] = sum(zone_stats.values())
    return {"items": zones}


@zones_bp.get("/floors")
def list_floors():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT floor
            FROM parking_zones
            ORDER BY floor
            """
        ).fetchall()
    return {"items": [row["floor"] for row in rows]}


@zones_bp.get("/<int:zone_id>")
def get_zone(zone_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM parking_zones WHERE id = ?", (zone_id,)
        ).fetchone()
    if not row:
        return {"message": "区域不存在"}, 404
    return dict(row)


@zones_bp.post("/", strict_slashes=False)
def create_zone():
    data = request.get_json() or {}
    name = data.get("name")
    floor = data.get("floor")
    code = data.get("code")
    capacity = data.get("capacity", 0)
    maintenance_status = data.get("maintenance_status", "normal")
    description = data.get("description")

    if not name or not floor or not code:
        return {"message": "区域名称、楼层和区域编码不能为空"}, 400

    allowed_status = {"normal", "maintenance", "closed"}
    if maintenance_status not in allowed_status:
        return {"message": "维护状态不合法"}, 400

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM parking_zones WHERE code = ?", (code,)
        ).fetchone()
        if existing:
            return {"message": "区域编码已存在"}, 409

        cur = conn.execute(
            """
            INSERT INTO parking_zones (name, floor, code, capacity, maintenance_status, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
            """,
            (name, floor, code, capacity, maintenance_status, description),
        )
        row = conn.execute(
            "SELECT * FROM parking_zones WHERE id = ?", (cur.lastrowid,)
        ).fetchone()

    return dict(row), 201


@zones_bp.patch("/<int:zone_id>")
def update_zone(zone_id):
    data = request.get_json() or {}
    allowed_fields = {"name", "floor", "code", "capacity", "maintenance_status", "description"}
    update_data = {k: v for k, v in data.items() if k in allowed_fields}

    if not update_data:
        return {"message": "没有可更新的字段"}, 400

    if "maintenance_status" in update_data:
        allowed_status = {"normal", "maintenance", "closed"}
        if update_data["maintenance_status"] not in allowed_status:
            return {"message": "维护状态不合法"}, 400

    set_clauses = [f"{k} = ?" for k in update_data.keys()]
    set_clauses.append("updated_at = datetime('now', 'localtime')")
    params = list(update_data.values())
    params.append(zone_id)

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM parking_zones WHERE id = ?", (zone_id,)
        ).fetchone()
        if not existing:
            return {"message": "区域不存在"}, 404

        if "code" in update_data:
            code_exist = conn.execute(
                "SELECT id FROM parking_zones WHERE code = ? AND id != ?",
                (update_data["code"], zone_id),
            ).fetchone()
            if code_exist:
                return {"message": "区域编码已存在"}, 409

        conn.execute(
            f"""
            UPDATE parking_zones
            SET {', '.join(set_clauses)}
            WHERE id = ?
            """,
            params,
        )
        row = conn.execute(
            "SELECT * FROM parking_zones WHERE id = ?", (zone_id,)
        ).fetchone()

    return dict(row)


@zones_bp.delete("/<int:zone_id>")
def delete_zone(zone_id):
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM parking_zones WHERE id = ?", (zone_id,)
        ).fetchone()
        if not existing:
            return {"message": "区域不存在"}, 404

        space_count = conn.execute(
            "SELECT COUNT(*) AS count FROM spaces WHERE zone_id = ?", (zone_id,)
        ).fetchone()["count"]
        if space_count > 0:
            return {"message": "该区域下还有车位，无法删除"}, 409

        conn.execute("DELETE FROM parking_zones WHERE id = ?", (zone_id,))

    return {"message": "删除成功"}

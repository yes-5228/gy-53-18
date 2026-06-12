from flask import Blueprint, request

from ..database import get_connection, rows_to_dicts

spaces_bp = Blueprint("spaces", __name__)


@spaces_bp.get("/", strict_slashes=False)
def list_spaces():
    zone_id = request.args.get("zone_id", type=int)
    floor = request.args.get("floor", type=int)
    status = request.args.get("status")

    with get_connection() as conn:
        query = """
            SELECT s.*, z.name AS zone_name, z.floor AS floor, z.code AS zone_code, z.maintenance_status AS zone_maintenance_status
            FROM spaces s
            LEFT JOIN parking_zones z ON s.zone_id = z.id
            WHERE 1=1
        """
        params = []

        if zone_id is not None:
            query += " AND s.zone_id = ?"
            params.append(zone_id)
        if floor is not None:
            query += " AND z.floor = ?"
            params.append(floor)
        if status:
            query += " AND s.status = ?"
            params.append(status)

        query += " ORDER BY z.floor, z.code, s.code"
        rows = conn.execute(query, params).fetchall()

        stats_query = """
            SELECT status, COUNT(*) AS count
            FROM spaces s
            LEFT JOIN parking_zones z ON s.zone_id = z.id
            WHERE 1=1
        """
        stats_params = []
        if zone_id is not None:
            stats_query += " AND s.zone_id = ?"
            stats_params.append(zone_id)
        if floor is not None:
            stats_query += " AND z.floor = ?"
            stats_params.append(floor)
        stats_query += " GROUP BY status"
        stats_rows = conn.execute(stats_query, stats_params).fetchall()

    return {"items": rows_to_dicts(rows), "stats": {row["status"]: row["count"] for row in stats_rows}}


@spaces_bp.post("/", strict_slashes=False)
def create_space():
    data = request.get_json() or {}
    code = data.get("code")
    zone_id = data.get("zone_id")
    area = data.get("area", "")
    status = data.get("status", "free")

    if not code:
        return {"message": "车位编号不能为空"}, 400

    allowed = {"free", "occupied", "reserved", "maintenance"}
    if status not in allowed:
        return {"message": "车位状态不合法"}, 400

    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM spaces WHERE code = ?", (code,)).fetchone()
        if existing:
            return {"message": "车位编号已存在"}, 409

        if zone_id:
            zone = conn.execute("SELECT id FROM parking_zones WHERE id = ?", (zone_id,)).fetchone()
            if not zone:
                return {"message": "所属区域不存在"}, 400

        cur = conn.execute(
            """
            INSERT INTO spaces (code, zone_id, area, status, plate_number, updated_at)
            VALUES (?, ?, ?, ?, NULL, datetime('now', 'localtime'))
            """,
            (code, zone_id if zone_id else None, area, status),
        )
        row = conn.execute("SELECT * FROM spaces WHERE id = ?", (cur.lastrowid,)).fetchone()

    return dict(row), 201


@spaces_bp.get("/<int:space_id>")
def get_space(space_id):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT s.*, z.name AS zone_name, z.floor AS floor, z.code AS zone_code, z.maintenance_status AS zone_maintenance_status
            FROM spaces s
            LEFT JOIN parking_zones z ON s.zone_id = z.id
            WHERE s.id = ?
            """,
            (space_id,),
        ).fetchone()
    if not row:
        return {"message": "车位不存在"}, 404
    return dict(row)


@spaces_bp.patch("/<int:space_id>")
def update_space(space_id):
    data = request.get_json() or {}
    status = data.get("status")
    plate_number = data.get("plate_number")
    zone_id = data.get("zone_id")
    area = data.get("area")
    code = data.get("code")

    allowed = {"free", "occupied", "reserved", "maintenance"}

    if status is not None and status not in allowed:
        return {"message": "车位状态不合法"}, 400

    with get_connection() as conn:
        existing = conn.execute("SELECT * FROM spaces WHERE id = ?", (space_id,)).fetchone()
        if not existing:
            return {"message": "车位不存在"}, 404

        if code and code != existing["code"]:
            code_exist = conn.execute("SELECT id FROM spaces WHERE code = ?", (code,)).fetchone()
            if code_exist:
                return {"message": "车位编号已存在"}, 409

        if zone_id is not None:
            zone = conn.execute("SELECT id FROM parking_zones WHERE id = ?", (zone_id,)).fetchone()
            if not zone:
                return {"message": "所属区域不存在"}, 400

        update_fields = []
        params = []

        if status is not None:
            update_fields.append("status = ?")
            params.append(status)
        if plate_number is not None:
            update_fields.append("plate_number = ?")
            params.append(plate_number if status == "occupied" else None)
        if zone_id is not None:
            update_fields.append("zone_id = ?")
            params.append(zone_id if zone_id else None)
        if area is not None:
            update_fields.append("area = ?")
            params.append(area)
        if code is not None:
            update_fields.append("code = ?")
            params.append(code)

        if not update_fields:
            return {"message": "没有可更新的字段"}, 400

        update_fields.append("updated_at = datetime('now', 'localtime')")
        params.append(space_id)

        conn.execute(
            f"""
            UPDATE spaces
            SET {', '.join(update_fields)}
            WHERE id = ?
            """,
            params,
        )
        row = conn.execute("SELECT * FROM spaces WHERE id = ?", (space_id,)).fetchone()

    return dict(row)


@spaces_bp.delete("/<int:space_id>")
def delete_space(space_id):
    with get_connection() as conn:
        existing = conn.execute("SELECT * FROM spaces WHERE id = ?", (space_id,)).fetchone()
        if not existing:
            return {"message": "车位不存在"}, 404

        if existing["status"] == "occupied":
            return {"message": "车位已占用，无法删除"}, 409

        conn.execute("DELETE FROM spaces WHERE id = ?", (space_id,))

    return {"message": "删除成功"}

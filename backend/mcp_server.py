import os
from contextlib import contextmanager
from datetime import date
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from sqlalchemy import bindparam, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import SessionLocal, init_db


ORDER_STATUSES = {"pending", "confirmed", "delivered", "cancelled"}
PAYMENT_STATUSES = {"pending", "paid", "failed"}
PAYMENT_MODES = {"cash", "upi", "card"}


mcp = FastMCP("home-bites")


class OrderLineInput(BaseModel):
    item_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)


@contextmanager
def db_session() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _fetch_one_dict(db: Session, query: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any] | None:
    row = db.execute(text(query), params or {}).mappings().first()
    return dict(row) if row else None


def _fetch_all_dicts(db: Session, query: str, params: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    rows = db.execute(text(query), params or {}).mappings().all()
    return [dict(row) for row in rows]


def _normalize_limit(limit: int, maximum: int = 100) -> int:
    return max(1, min(limit, maximum))


def _writes_enabled() -> bool:
    return os.getenv("HOME_BITES_MCP_ALLOW_WRITES", "false").strip().lower() in {"1", "true", "yes", "on"}


def _require_writes_enabled() -> None:
    if not _writes_enabled():
        raise ValueError(
            "Write tools are disabled. Set HOME_BITES_MCP_ALLOW_WRITES=true to enable mutating MCP operations."
        )


def _validate_choice(value: Optional[str], allowed: set[str], field_name: str) -> None:
    if value is not None and value not in allowed:
        raise ValueError(f"Invalid {field_name}: {value}. Allowed values: {sorted(allowed)}")


def _get_item_prices(db: Session, item_ids: list[int]) -> dict[int, int]:
    if not item_ids:
        return {}

    stmt = text(
        """
        SELECT item_id, price
        FROM items
        WHERE item_id IN :item_ids
        """
    ).bindparams(bindparam("item_ids", expanding=True))
    rows = db.execute(stmt, {"item_ids": sorted(set(item_ids))}).mappings().all()
    return {row["item_id"]: row["price"] for row in rows}


@mcp.resource("homebites://project/overview")
def project_overview() -> str:
    return (
        "Home Bites MCP server for the FastAPI ordering app. "
        "It exposes read tools for items, users, and orders, plus opt-in write tools "
        "for creating orders and updating order status. "
        "Set HOME_BITES_MCP_ALLOW_WRITES=true to enable write operations."
    )


@mcp.resource("homebites://project/routes")
def project_routes() -> dict[str, list[str]]:
    return {
        "auth": ["POST /register", "POST /login", "POST /logout", "GET /me", "PUT /me/profile"],
        "items": ["GET /items", "GET /items/top-ordered", "GET /items/{item_id}"],
        "orders": [
            "GET /orders",
            "GET /orders/{order_id}",
            "GET /orders/{order_id}/complete",
            "POST /orders/complete",
            "POST /orders/{order_id}/cancel",
            "GET /users/{user_id}/orders",
        ],
        "admin": ["GET /users", "POST /users/", "PUT /users/{user_id}", "PUT /orders/{order_id}"],
    }


@mcp.tool()
def health_check() -> dict[str, Any]:
    with db_session() as db:
        result = db.execute(text("SELECT 1 AS ok")).scalar_one()
    return {"status": "ok", "database": "connected", "result": result}


@mcp.tool()
def list_items(search: Optional[str] = None, limit: int = 20, top_ordered: bool = False) -> dict[str, Any]:
    safe_limit = _normalize_limit(limit)
    with db_session() as db:
        if top_ordered:
            items = _fetch_all_dicts(
                db,
                """
                SELECT
                    i.item_id,
                    i.item_name,
                    i.price,
                    i.weight,
                    i.photos,
                    i.videos,
                    i.description,
                    COALESCE(SUM(od.quantity), 0) AS total_quantity_ordered
                FROM items i
                LEFT JOIN order_details od ON i.item_id = od.item_id
                GROUP BY i.item_id, i.item_name, i.price, i.weight, i.photos, i.videos, i.description
                ORDER BY total_quantity_ordered DESC, i.item_name ASC
                LIMIT :limit
                """,
                {"limit": safe_limit},
            )
        elif search:
            items = _fetch_all_dicts(
                db,
                """
                SELECT item_id, item_name, price, weight, photos, videos, description
                FROM items
                WHERE lower(item_name) LIKE lower(:search)
                   OR lower(description) LIKE lower(:search)
                ORDER BY item_name ASC
                LIMIT :limit
                """,
                {"search": f"%{search}%", "limit": safe_limit},
            )
        else:
            items = _fetch_all_dicts(
                db,
                """
                SELECT item_id, item_name, price, weight, photos, videos, description
                FROM items
                ORDER BY item_name ASC
                LIMIT :limit
                """,
                {"limit": safe_limit},
            )

    return {"count": len(items), "items": items}


@mcp.tool()
def get_item(item_id: int) -> dict[str, Any]:
    with db_session() as db:
        item = _fetch_one_dict(
            db,
            """
            SELECT item_id, item_name, price, weight, photos, videos, description
            FROM items
            WHERE item_id = :item_id
            """,
            {"item_id": item_id},
        )
    if not item:
        raise ValueError(f"Item {item_id} not found")
    return item


@mcp.tool()
def list_users(city: Optional[str] = None, limit: int = 50) -> dict[str, Any]:
    safe_limit = _normalize_limit(limit)
    with db_session() as db:
        if city:
            users = _fetch_all_dicts(
                db,
                """
                SELECT user_id, name, phone_number, email, role, address, city
                FROM users
                WHERE lower(city) = lower(:city)
                ORDER BY name ASC
                LIMIT :limit
                """,
                {"city": city, "limit": safe_limit},
            )
        else:
            users = _fetch_all_dicts(
                db,
                """
                SELECT user_id, name, phone_number, email, role, address, city
                FROM users
                ORDER BY name ASC
                LIMIT :limit
                """,
                {"limit": safe_limit},
            )
    return {"count": len(users), "users": users}


@mcp.tool()
def get_user_orders(user_id: int) -> dict[str, Any]:
    with db_session() as db:
        user = _fetch_one_dict(db, "SELECT user_id, name, email, role FROM users WHERE user_id = :user_id", {"user_id": user_id})
        if not user:
            raise ValueError(f"User {user_id} not found")

        orders = _fetch_all_dicts(
            db,
            """
            SELECT order_id, user_id, amount, order_status, payment_status, payment_mode,
                   order_date, delivery_date, address, city
            FROM orders
            WHERE user_id = :user_id
            ORDER BY order_id DESC
            """,
            {"user_id": user_id},
        )
    return {"user": user, "count": len(orders), "orders": orders}


@mcp.tool()
def get_order(order_id: int, include_items: bool = True) -> dict[str, Any]:
    with db_session() as db:
        order = _fetch_one_dict(
            db,
            """
            SELECT order_id, user_id, amount, order_status, payment_status, payment_mode,
                   order_date, delivery_date, address, city
            FROM orders
            WHERE order_id = :order_id
            """,
            {"order_id": order_id},
        )
        if not order:
            raise ValueError(f"Order {order_id} not found")

        response: dict[str, Any] = {"order": order}
        if include_items:
            items = _fetch_all_dicts(
                db,
                """
                SELECT od.order_detail_id, od.item_id, od.quantity, od.price,
                       i.item_name, i.description, i.weight
                FROM order_details od
                JOIN items i ON i.item_id = od.item_id
                WHERE od.order_id = :order_id
                ORDER BY od.order_detail_id ASC
                """,
                {"order_id": order_id},
            )
            response["items"] = items
            response["items_count"] = len(items)
    return response


@mcp.tool()
def create_order(
    user_id: int,
    items: list[OrderLineInput],
    payment_mode: str,
    address: str,
    city: str,
    delivery_date: Optional[str] = None,
    order_status: str = "pending",
    payment_status: str = "pending",
    order_date: Optional[str] = None,
) -> dict[str, Any]:
    _require_writes_enabled()
    _validate_choice(order_status, ORDER_STATUSES, "order_status")
    _validate_choice(payment_status, PAYMENT_STATUSES, "payment_status")
    _validate_choice(payment_mode, PAYMENT_MODES, "payment_mode")

    if not items:
        raise ValueError("At least one item is required")

    normalized_order_date = order_date or date.today().isoformat()
    normalized_delivery_date = delivery_date or normalized_order_date

    with db_session() as db:
        user = _fetch_one_dict(db, "SELECT user_id FROM users WHERE user_id = :user_id", {"user_id": user_id})
        if not user:
            raise ValueError(f"User {user_id} not found")

        item_ids = [item.item_id for item in items]
        item_prices = _get_item_prices(db, item_ids)
        if len(item_prices) != len(set(item_ids)):
            missing_ids = sorted(set(item_ids) - set(item_prices))
            raise ValueError(f"Unknown item ids: {missing_ids}")

        total_amount = sum(item_prices[item.item_id] * item.quantity for item in items)

        try:
            order_result = db.execute(
                text(
                    """
                    INSERT INTO orders (
                        user_id, amount, order_status, payment_status, payment_mode,
                        order_date, delivery_date, address, city
                    )
                    VALUES (
                        :user_id, :amount, :order_status, :payment_status, :payment_mode,
                        :order_date, :delivery_date, :address, :city
                    )
                    """
                ),
                {
                    "user_id": user_id,
                    "amount": total_amount,
                    "order_status": order_status,
                    "payment_status": payment_status,
                    "payment_mode": payment_mode,
                    "order_date": normalized_order_date,
                    "delivery_date": normalized_delivery_date,
                    "address": address,
                    "city": city,
                },
            )
            order_id = order_result.lastrowid

            for item in items:
                db.execute(
                    text(
                        """
                        INSERT INTO order_details (order_id, item_id, quantity, price)
                        VALUES (:order_id, :item_id, :quantity, :price)
                        """
                    ),
                    {
                        "order_id": order_id,
                        "item_id": item.item_id,
                        "quantity": item.quantity,
                        "price": item_prices[item.item_id],
                    },
                )
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError(f"Could not create order: {exc}") from exc

    return {
        "message": "Order created successfully",
        "order_id": order_id,
        "user_id": user_id,
        "total_amount": total_amount,
        "items_count": len(items),
    }


@mcp.tool()
def update_order_status(
    order_id: int,
    order_status: Optional[str] = None,
    payment_status: Optional[str] = None,
    delivery_date: Optional[str] = None,
) -> dict[str, Any]:
    _require_writes_enabled()
    _validate_choice(order_status, ORDER_STATUSES, "order_status")
    _validate_choice(payment_status, PAYMENT_STATUSES, "payment_status")

    updates: list[str] = []
    params: dict[str, Any] = {"order_id": order_id}

    if order_status is not None:
        updates.append("order_status = :order_status")
        params["order_status"] = order_status
    if payment_status is not None:
        updates.append("payment_status = :payment_status")
        params["payment_status"] = payment_status
    if delivery_date is not None:
        updates.append("delivery_date = :delivery_date")
        params["delivery_date"] = delivery_date

    if not updates:
        raise ValueError("Provide at least one field to update")

    with db_session() as db:
        existing = _fetch_one_dict(db, "SELECT order_id FROM orders WHERE order_id = :order_id", {"order_id": order_id})
        if not existing:
            raise ValueError(f"Order {order_id} not found")

        db.execute(text(f"UPDATE orders SET {', '.join(updates)} WHERE order_id = :order_id"), params)
        db.commit()

        updated_order = _fetch_one_dict(
            db,
            """
            SELECT order_id, user_id, amount, order_status, payment_status, payment_mode,
                   order_date, delivery_date, address, city
            FROM orders
            WHERE order_id = :order_id
            """,
            {"order_id": order_id},
        )
    return {"message": "Order updated successfully", "order": updated_order}


if __name__ == "__main__":
    init_db()
    mcp.run()

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    clear_auth_cookie,
    create_access_token,
    get_admin_user,
    get_current_user,
    hash_password,
    password_needs_rehash,
    set_auth_cookie,
    verify_password,
)
from database import get_db, init_db
from db_utils import row_to_dict, rows_to_dicts
from models import (
    CreateOrder,
    ItemResponse,
    Items,
    OrderDetailResponse,
    OrderDetails,
    OrderResponse,
    Orders,
    UserProfileUpdate,
    UserResponse,
    Users,
)
from settings import ALLOWED_ORIGINS, CORS_ALLOW_ORIGIN_REGEX, DEBUG, IS_PRODUCTION


app = FastAPI()
logger = logging.getLogger(__name__)


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or [],
    allow_origin_regex=CORS_ALLOW_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": exc.errors() if not IS_PRODUCTION else []},
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.exception("Database error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Database error occurred"},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred"},
    )


@app.on_event("startup")
def startup():
    logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO)
    init_db()


@app.get("/health")
def health_check():
    return {"status": "ok", "environment": "production" if IS_PRODUCTION else "development"}


def fetch_one_dict(db: Session, query: str, params: Optional[dict] = None):
    row = db.execute(text(query), params or {}).mappings().first()
    return row_to_dict(row)


def fetch_all_dicts(db: Session, query: str, params: Optional[dict] = None):
    rows = db.execute(text(query), params or {}).mappings().all()
    return rows_to_dicts(rows)


def get_item_prices(db: Session, item_ids: list[int]) -> dict[int, int]:
    if not item_ids:
        return {}

    placeholders = ", ".join(f":item_id_{index}" for index in range(len(item_ids)))
    params = {f"item_id_{index}": item_id for index, item_id in enumerate(item_ids)}
    rows = fetch_all_dicts(
        db,
        f"SELECT item_id, price FROM items WHERE item_id IN ({placeholders})",
        params,
    )
    return {row["item_id"]: row["price"] for row in rows}


@app.post("/users/", status_code=201)
def add_user(user: Users, admin: dict = Depends(get_admin_user), db: Session = Depends(get_db)):
    try:
        hashed_password = hash_password(user.password)
        result = db.execute(
            text(
                """
                INSERT INTO users (name, phone_number, email, password, role, address, city)
                VALUES (:name, :phone_number, :email, :password, :role, :address, :city)
                """
            ),
            {
                "name": user.name,
                "phone_number": user.phone_number,
                "email": user.email,
                "password": hashed_password,
                "role": user.role,
                "address": user.address,
                "city": user.city,
            },
        )
        db.commit()
        user_id = result.lastrowid
        return {
            "message": "User created successfully",
            "user_id": user_id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        }
    except IntegrityError as exc:
        db.rollback()
        if "phone_number" in str(exc.orig):
            raise HTTPException(status_code=400, detail="Phone number already exists")
        raise HTTPException(status_code=400, detail="User creation failed")
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(exc)}")


@app.get("/users", response_model=list[UserResponse])
def get_users(db: Session = Depends(get_db), admin: dict = Depends(get_admin_user)):
    return fetch_all_dicts(
        db,
        """
        SELECT user_id, name, phone_number, email, role, address, city
        FROM users
        """,
    )


@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user: Users, db: Session = Depends(get_db), admin: dict = Depends(get_admin_user)):
    try:
        existing = fetch_one_dict(db, "SELECT 1 AS present FROM users WHERE user_id = :user_id", {"user_id": user_id})
        if not existing:
            raise HTTPException(status_code=404, detail="User not found")

        hashed_password = hash_password(user.password)
        db.execute(
            text(
                """
                UPDATE users
                SET name = :name,
                    phone_number = :phone_number,
                    email = :email,
                    password = :password,
                    role = :role,
                    address = :address,
                    city = :city
                WHERE user_id = :user_id
                """
            ),
            {
                "name": user.name,
                "phone_number": user.phone_number,
                "email": user.email,
                "password": hashed_password,
                "role": user.role,
                "address": user.address,
                "city": user.city,
                "user_id": user_id,
            },
        )
        db.commit()
        updated = fetch_one_dict(
            db,
            """
            SELECT user_id, name, phone_number, email, role, address, city
            FROM users
            WHERE user_id = :user_id
            """,
            {"user_id": user_id},
        )
        return updated
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Phone number already exists")
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), admin: dict = Depends(get_admin_user)):
    existing = fetch_one_dict(db, "SELECT 1 AS present FROM users WHERE user_id = :user_id", {"user_id": user_id})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")

    db.execute(text("DELETE FROM users WHERE user_id = :user_id"), {"user_id": user_id})
    db.commit()
    return {"message": "User deleted successfully"}


@app.get("/users/{user_id}", response_model=UserResponse)
def get_user_by_id(user_id: int, db: Session = Depends(get_db), admin: dict = Depends(get_admin_user)):
    user = fetch_one_dict(
        db,
        """
        SELECT user_id, name, phone_number, email, role, address, city
        FROM users
        WHERE user_id = :user_id
        """,
        {"user_id": user_id},
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/items/", status_code=201)
def add_item(item: Items, db: Session = Depends(get_db), admin: dict = Depends(get_admin_user)):
    result = db.execute(
        text(
            """
            INSERT INTO items (item_name, price, weight, photos, videos, description)
            VALUES (:item_name, :price, :weight, :photos, :videos, :description)
            """
        ),
        {
            "item_name": item.item_name,
            "price": item.price,
            "weight": item.weight,
            "photos": item.photos,
            "videos": item.videos,
            "description": item.description,
        },
    )
    db.commit()
    return {"message": "Item created successfully", "item_id": result.lastrowid}


@app.get("/items", response_model=list[ItemResponse])
def get_items(db: Session = Depends(get_db)):
    return fetch_all_dicts(db, "SELECT * FROM items")


@app.get("/items/top-ordered", response_model=list[ItemResponse])
def get_top_ordered_items(limit: int = 3, db: Session = Depends(get_db)):
    safe_limit = max(1, min(limit, 20))
    return fetch_all_dicts(
        db,
        """
        SELECT i.*
        FROM items i
        LEFT JOIN (
            SELECT item_id, SUM(quantity) AS ordered_qty
            FROM order_details
            GROUP BY item_id
        ) stats ON stats.item_id = i.item_id
        ORDER BY COALESCE(stats.ordered_qty, 0) DESC, i.item_id ASC
        LIMIT :limit
        """,
        {"limit": safe_limit},
    )


@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = fetch_one_dict(db, "SELECT * FROM items WHERE item_id = :item_id", {"item_id": item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.put("/items/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, item: Items, db: Session = Depends(get_db), admin: dict = Depends(get_admin_user)):
    existing = fetch_one_dict(db, "SELECT 1 AS present FROM items WHERE item_id = :item_id", {"item_id": item_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Item not found")

    db.execute(
        text(
            """
            UPDATE items
            SET item_name = :item_name,
                price = :price,
                weight = :weight,
                photos = :photos,
                videos = :videos,
                description = :description
            WHERE item_id = :item_id
            """
        ),
        {
            "item_name": item.item_name,
            "price": item.price,
            "weight": item.weight,
            "photos": item.photos,
            "videos": item.videos,
            "description": item.description,
            "item_id": item_id,
        },
    )
    db.commit()
    return fetch_one_dict(db, "SELECT * FROM items WHERE item_id = :item_id", {"item_id": item_id})


@app.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db), admin: dict = Depends(get_admin_user)):
    existing = fetch_one_dict(db, "SELECT 1 AS present FROM items WHERE item_id = :item_id", {"item_id": item_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Item not found")

    db.execute(text("DELETE FROM items WHERE item_id = :item_id"), {"item_id": item_id})
    db.commit()
    return {"message": "Item deleted successfully"}


@app.post("/orders/", status_code=201)
def add_order(order: Orders, db: Session = Depends(get_db), admin: dict = Depends(get_admin_user)):
    try:
        result = db.execute(
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
                "user_id": order.user_id,
                "amount": order.amount,
                "order_status": order.order_status,
                "payment_status": order.payment_status,
                "payment_mode": order.payment_mode,
                "order_date": order.order_date,
                "delivery_date": order.delivery_date,
                "address": order.address,
                "city": order.city,
            },
        )
        db.commit()
        return {"message": "Order created successfully", "order_id": result.lastrowid}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="User not found")


@app.get("/orders", response_model=list[OrderResponse])
def get_orders(db: Session = Depends(get_db), admin: dict = Depends(get_admin_user)):
    return fetch_all_dicts(db, "SELECT * FROM orders")


@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    order = fetch_one_dict(db, "SELECT * FROM orders WHERE order_id = :order_id", {"order_id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["user_id"] != current_user["user_id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access forbidden")
    return order


@app.put("/orders/{order_id}", response_model=OrderResponse)
def update_order(order_id: int, order: Orders, db: Session = Depends(get_db), admin: dict = Depends(get_admin_user)):
    existing = fetch_one_dict(db, "SELECT 1 AS present FROM orders WHERE order_id = :order_id", {"order_id": order_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Order not found")

    db.execute(
        text(
            """
            UPDATE orders
            SET user_id = :user_id,
                amount = :amount,
                order_status = :order_status,
                payment_status = :payment_status,
                payment_mode = :payment_mode,
                order_date = :order_date,
                delivery_date = :delivery_date,
                address = :address,
                city = :city
            WHERE order_id = :order_id
            """
        ),
        {
            "user_id": order.user_id,
            "amount": order.amount,
            "order_status": order.order_status,
            "payment_status": order.payment_status,
            "payment_mode": order.payment_mode,
            "order_date": order.order_date,
            "delivery_date": order.delivery_date,
            "address": order.address,
            "city": order.city,
            "order_id": order_id,
        },
    )
    db.commit()
    return fetch_one_dict(db, "SELECT * FROM orders WHERE order_id = :order_id", {"order_id": order_id})


@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    order = fetch_one_dict(db, "SELECT * FROM orders WHERE order_id = :order_id", {"order_id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can cancel only your own orders")
    if order["order_status"] in ("delivered", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Order already {order['order_status']}")

    try:
        order_date = datetime.strptime(order["order_date"], "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid order_date format on order")

    today = date.today()
    if today > (order_date + timedelta(days=1)):
        raise HTTPException(status_code=400, detail="Cancellation window expired (allowed within 1 day of order date)")

    db.execute(
        text("UPDATE orders SET order_status = :order_status WHERE order_id = :order_id"),
        {"order_status": "cancelled", "order_id": order_id},
    )
    db.commit()
    updated = fetch_one_dict(db, "SELECT * FROM orders WHERE order_id = :order_id", {"order_id": order_id})
    return {"message": "Order cancelled successfully", "order": updated}


@app.delete("/orders/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db), admin: dict = Depends(get_admin_user)):
    existing = fetch_one_dict(db, "SELECT 1 AS present FROM orders WHERE order_id = :order_id", {"order_id": order_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Order not found")

    db.execute(text("DELETE FROM orders WHERE order_id = :order_id"), {"order_id": order_id})
    db.commit()
    return {"message": "Order deleted successfully"}


@app.post("/orders/complete", status_code=201)
def create_complete_order(order: CreateOrder, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        if not order.items:
            raise HTTPException(status_code=400, detail="At least one item is required")

        item_ids = [item.item_id for item in order.items]
        item_prices = get_item_prices(db, item_ids)
        if len(item_prices) != len(set(item_ids)):
            raise HTTPException(status_code=400, detail="One or more items are invalid")

        order_user_id = current_user["user_id"]
        normalized_items = []
        total_amount = 0
        for item in order.items:
            price = item_prices[item.item_id]
            normalized_items.append(
                {
                    "item_id": item.item_id,
                    "quantity": item.quantity,
                    "price": price,
                }
            )
            total_amount += price * item.quantity

        result = db.execute(
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
                "user_id": order_user_id,
                "amount": total_amount,
                "order_status": order.order_status,
                "payment_status": order.payment_status,
                "payment_mode": order.payment_mode,
                "order_date": order.order_date,
                "delivery_date": order.delivery_date,
                "address": order.address,
                "city": order.city,
            },
        )
        order_id = result.lastrowid
        for item in normalized_items:
            db.execute(
                text(
                    """
                    INSERT INTO order_details (order_id, item_id, quantity, price)
                    VALUES (:order_id, :item_id, :quantity, :price)
                    """
                ),
                {
                    "order_id": order_id,
                    "item_id": item["item_id"],
                    "quantity": item["quantity"],
                    "price": item["price"],
                },
            )
        db.commit()
        return {
            "message": "Order created successfully",
            "order_id": order_id,
            "total_amount": total_amount,
            "items_count": len(normalized_items),
        }
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid user_id or item_id")
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/orders/{order_id}/complete")
def get_complete_order(order_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    order = fetch_one_dict(db, "SELECT * FROM orders WHERE order_id = :order_id", {"order_id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["user_id"] != current_user["user_id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access forbidden")

    items = fetch_all_dicts(
        db,
        """
        SELECT
            od.order_detail_id,
            od.item_id,
            od.quantity,
            od.price,
            i.item_name,
            i.description,
            i.weight
        FROM order_details od
        JOIN items i ON od.item_id = i.item_id
        WHERE od.order_id = :order_id
        """,
        {"order_id": order_id},
    )
    return {"order": order, "items": items, "total_items": len(items)}


@app.post("/order-details/", status_code=201)
def add_order_detail(detail: OrderDetails, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        order = fetch_one_dict(
            db,
            "SELECT user_id FROM orders WHERE order_id = :order_id",
            {"order_id": detail.order_id},
        )
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order["user_id"] != current_user["user_id"] and current_user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Access forbidden")

        item_row = fetch_one_dict(
            db,
            "SELECT price FROM items WHERE item_id = :item_id",
            {"item_id": detail.item_id},
        )
        if not item_row:
            raise HTTPException(status_code=400, detail="Order or Item not found")

        result = db.execute(
            text(
                """
                INSERT INTO order_details (order_id, item_id, quantity, price)
                VALUES (:order_id, :item_id, :quantity, :price)
                """
            ),
            {
                "order_id": detail.order_id,
                "item_id": detail.item_id,
                "quantity": detail.quantity,
                "price": item_row["price"],
            },
        )
        db.commit()
        return {"message": "Order detail created successfully", "order_detail_id": result.lastrowid}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Order or Item not found")


@app.get("/order-details", response_model=list[OrderDetailResponse])
def get_order_details(db: Session = Depends(get_db), admin: dict = Depends(get_admin_user)):
    return fetch_all_dicts(db, "SELECT * FROM order_details")


@app.get("/order-details/order/{order_id}", response_model=list[OrderDetailResponse])
def get_order_details_by_order(order_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    order = fetch_one_dict(db, "SELECT user_id FROM orders WHERE order_id = :order_id", {"order_id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["user_id"] != current_user["user_id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access forbidden")
    return fetch_all_dicts(
        db,
        "SELECT * FROM order_details WHERE order_id = :order_id",
        {"order_id": order_id},
    )


@app.put("/order-details/{detail_id}", response_model=OrderDetailResponse)
def update_order_detail(detail_id: int, detail: OrderDetails, db: Session = Depends(get_db), admin: dict = Depends(get_admin_user)):
    existing = fetch_one_dict(
        db,
        "SELECT 1 AS present FROM order_details WHERE order_detail_id = :detail_id",
        {"detail_id": detail_id},
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Order detail not found")

    item_row = fetch_one_dict(
        db,
        "SELECT price FROM items WHERE item_id = :item_id",
        {"item_id": detail.item_id},
    )
    if not item_row:
        raise HTTPException(status_code=400, detail="Order or Item not found")

    db.execute(
        text(
            """
            UPDATE order_details
            SET order_id = :order_id,
                item_id = :item_id,
                quantity = :quantity,
                price = :price
            WHERE order_detail_id = :detail_id
            """
        ),
        {
            "order_id": detail.order_id,
            "item_id": detail.item_id,
            "quantity": detail.quantity,
            "price": item_row["price"],
            "detail_id": detail_id,
        },
    )
    db.commit()
    return fetch_one_dict(
        db,
        "SELECT * FROM order_details WHERE order_detail_id = :detail_id",
        {"detail_id": detail_id},
    )


@app.delete("/order-details/{detail_id}")
def delete_order_detail(detail_id: int, db: Session = Depends(get_db), admin: dict = Depends(get_admin_user)):
    existing = fetch_one_dict(
        db,
        "SELECT 1 AS present FROM order_details WHERE order_detail_id = :detail_id",
        {"detail_id": detail_id},
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Order detail not found")

    db.execute(text("DELETE FROM order_details WHERE order_detail_id = :detail_id"), {"detail_id": detail_id})
    db.commit()
    return {"message": "Order detail deleted successfully"}


@app.post("/register", status_code=201)
def register(user: Users, db: Session = Depends(get_db)):
    try:
        hashed_password = hash_password(user.password)
        result = db.execute(
            text(
                """
                INSERT INTO users (name, phone_number, email, password, role, address, city)
                VALUES (:name, :phone_number, :email, :password, :role, :address, :city)
                """
            ),
            {
                "name": user.name,
                "phone_number": user.phone_number,
                "email": user.email,
                "password": hashed_password,
                "role": "user",
                "address": user.address,
                "city": user.city,
            },
        )
        db.commit()
        return {"message": "User registered successfully", "user_id": result.lastrowid}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Phone number already exists")


@app.post("/login")
def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    identifier = form_data.username.strip()
    is_phone_identifier = identifier.isdigit() and len(identifier) == 10

    if is_phone_identifier:
        user = fetch_one_dict(db, "SELECT * FROM users WHERE phone_number = :phone_number", {"phone_number": int(identifier)})
    else:
        user = fetch_one_dict(db, "SELECT * FROM users WHERE email = :email", {"email": identifier})

    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if password_needs_rehash(user["password"]):
        db.execute(
            text("UPDATE users SET password = :password WHERE user_id = :user_id"),
            {"password": hash_password(form_data.password), "user_id": user["user_id"]},
        )
        db.commit()

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": str(user["user_id"])}, expires_delta=access_token_expires)
    set_auth_cookie(response, access_token)
    return {
        "user": {
            "user_id": user["user_id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "phone_number": user["phone_number"],
            "address": user["address"],
            "city": user["city"],
        },
    }


@app.post("/logout")
def logout(response: Response):
    clear_auth_cookie(response)
    return {"message": "Logged out successfully"}


@app.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    return current_user


@app.put("/me/profile", response_model=UserResponse)
def update_current_user_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        db.execute(
            text(
                """
                UPDATE users
                SET name = :name, address = :address, city = :city
                WHERE user_id = :user_id
                """
            ),
            {
                "name": payload.name,
                "address": payload.address,
                "city": payload.city,
                "user_id": current_user["user_id"],
            },
        )
        db.commit()
        updated = fetch_one_dict(
            db,
            """
            SELECT user_id, name, phone_number, email, role, address, city
            FROM users
            WHERE user_id = :user_id
            """,
            {"user_id": current_user["user_id"]},
        )
        if not updated:
            raise HTTPException(status_code=404, detail="User not found")
        return updated
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/admin/users", response_model=list[UserResponse])
def admin_get_all_users(db: Session = Depends(get_db), admin: dict = Depends(get_admin_user)):
    return fetch_all_dicts(
        db,
        """
        SELECT user_id, name, phone_number, email, role, address, city
        FROM users
        """,
    )


@app.get("/users/search/")
def search_users(
    name: Optional[str] = None,
    city: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_admin_user),
):
    conditions = []
    params = {}
    if name:
        conditions.append("name LIKE :name")
        params["name"] = f"%{name}%"
    if city:
        conditions.append("city LIKE :city")
        params["city"] = f"%{city}%"

    query = "SELECT user_id, name, phone_number, email, role, address, city FROM users"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    return fetch_all_dicts(db, query, params)


@app.get("/users/{user_id}/orders", response_model=list[OrderResponse])
def get_user_orders(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if current_user["user_id"] != user_id and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access forbidden")
    return fetch_all_dicts(db, "SELECT * FROM orders WHERE user_id = :user_id", {"user_id": user_id})


@app.get("/orders/status/{status}", response_model=list[OrderResponse])
def get_orders_by_status(status: str, db: Session = Depends(get_db), admin: dict = Depends(get_admin_user)):
    if status not in ["pending", "confirmed", "delivered", "cancelled"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    return fetch_all_dicts(db, "SELECT * FROM orders WHERE order_status = :status", {"status": status})


@app.get("/items/search/")
def search_items(name: str, db: Session = Depends(get_db)):
    return fetch_all_dicts(db, "SELECT * FROM items WHERE item_name LIKE :name", {"name": f"%{name}%"})


@app.get("/items/paginated")
def get_items_paginated(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    items = fetch_all_dicts(
        db,
        "SELECT * FROM items LIMIT :limit OFFSET :skip",
        {"limit": limit, "skip": skip},
    )
    total_row = fetch_one_dict(db, "SELECT COUNT(*) AS count FROM items")
    return {
        "items": items,
        "total": total_row["count"],
        "skip": skip,
        "limit": limit,
    }

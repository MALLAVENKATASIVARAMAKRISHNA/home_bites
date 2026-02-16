from fastapi import FastAPI, HTTPException, Depends, Request, status
from database import create_users, get_db_connection, get_db
from models import Users, UserResponse, Items, ItemResponse, Orders, OrderResponse, OrderDetails, OrderDetailResponse, CreateOrder, OrderItem
from typing import Any, List, Optional
Connection = Any
import sqlite3
from auth import hash_password, verify_password, create_access_token, get_current_user, get_admin_user, ACCESS_TOKEN_EXPIRE_MINUTES
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime, date
from fastapi.responses import JSONResponse
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors()
        }
    )

@app.exception_handler(sqlite3.Error)
async def sqlite_exception_handler(request: Request, exc: sqlite3.Error):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Database error occurred",
            "error": str(exc)
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected error occurred",
            "error": str(exc),
            "type": type(exc).__name__
        }
    )

@app.on_event("startup")
def startup():
    create_users()


@app.post("/users/", status_code=201)
def add_user(user: Users):
    """
    Add a new user to the database
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Hash the password before storing (security best practice)
        hashed_password = hash_password(user.password)
        
        cursor.execute("""
            INSERT INTO users (name, phone_number, email, password, role, address, city)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user.name, user.phone_number, user.email, hashed_password, user.role, user.address, user.city))
        
        conn.commit()
        user_id = cursor.lastrowid
        
        return {
            "message": "User created successfully",
            "user_id": user_id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        }
        
    except sqlite3.IntegrityError as e:
        conn.rollback()
        if "phone_number" in str(e):
            raise HTTPException(status_code=400, detail="Phone number already exists")
        raise HTTPException(status_code=400, detail="User creation failed")
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
        
    finally:
        cursor.close()
        conn.close()

@app.get("/users", response_model=List[UserResponse])
def get_users(db: Connection = Depends(get_db), admin: dict = Depends(get_admin_user)):
    cursor = db.cursor()
    try:
        data = cursor.execute("""
            SELECT user_id, name, phone_number, email, role, address, city 
            FROM users
        """).fetchall()
        return [dict(row) for row in data]
    finally:
        cursor.close()

@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user: Users, db: Connection = Depends(get_db), admin: dict = Depends(get_admin_user)):
    cursor = db.cursor()
    try:
        if not cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        
        hashed_password = hash_password(user.password)
        cursor.execute("""
            UPDATE users SET name=?, phone_number=?, email=?, password=?, role=?, address=?, city=?
            WHERE user_id=?
        """, (user.name, user.phone_number, user.email, hashed_password, user.role, user.address, user.city, user_id))
        db.commit()
        
        updated = cursor.execute("""
            SELECT user_id, name, phone_number, email, role, address, city 
            FROM users WHERE user_id=?
        """, (user_id,)).fetchone()
        return dict(updated)
    except sqlite3.IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Phone number already exists")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Connection = Depends(get_db), admin: dict = Depends(get_admin_user)):
    cursor = db.cursor()
    try:
        if not cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        db.commit()
        return {"message": "User deleted successfully"}
    finally:
        cursor.close()

@app.get("/users/{user_id}", response_model=UserResponse)
def get_user_by_id(user_id: int, db: Connection = Depends(get_db), admin: dict = Depends(get_admin_user)):
    cursor = db.cursor()
    try:
        user = cursor.execute("""
            SELECT user_id, name, phone_number, email, role, address, city 
            FROM users WHERE user_id = ?
        """, (user_id,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return dict(user)
    finally:
        cursor.close()

@app.post("/items/", status_code=201)
def add_item(item: Items, db: Connection = Depends(get_db), admin: dict = Depends(get_admin_user)):
    cursor = db.cursor()
    try:
        cursor.execute("""
            INSERT INTO items (item_name, price, weight, photos, videos, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (item.item_name, item.price, item.weight, item.photos, item.videos, item.description))
        db.commit()
        return {"message": "Item created successfully", "item_id": cursor.lastrowid}
    finally:
        cursor.close()

@app.get("/items", response_model=List[ItemResponse])
def get_items(db: Connection = Depends(get_db)):
    cursor = db.cursor()
    try:
        data = cursor.execute("SELECT * FROM items").fetchall()
        return [dict(row) for row in data]
    finally:
        cursor.close()

@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Connection = Depends(get_db)):
    cursor = db.cursor()
    try:
        item = cursor.execute("SELECT * FROM items WHERE item_id = ?", (item_id,)).fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return dict(item)
    finally:
        cursor.close()

@app.put("/items/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, item: Items, db: Connection = Depends(get_db), admin: dict = Depends(get_admin_user)):
    cursor = db.cursor()
    try:
        if not cursor.execute("SELECT 1 FROM items WHERE item_id = ?", (item_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Item not found")
        
        cursor.execute("""
            UPDATE items SET item_name=?, price=?, weight=?, photos=?, videos=?, description=?
            WHERE item_id=?
        """, (item.item_name, item.price, item.weight, item.photos, item.videos, item.description, item_id))
        db.commit()
        
        updated = cursor.execute("SELECT * FROM items WHERE item_id=?", (item_id,)).fetchone()
        return dict(updated)
    finally:
        cursor.close()

@app.delete("/items/{item_id}")
def delete_item(item_id: int, db: Connection = Depends(get_db), admin: dict = Depends(get_admin_user)):
    cursor = db.cursor()
    try:
        if not cursor.execute("SELECT 1 FROM items WHERE item_id = ?", (item_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Item not found")
        
        cursor.execute("DELETE FROM items WHERE item_id = ?", (item_id,))
        db.commit()
        return {"message": "Item deleted successfully"}
    finally:
        cursor.close()

@app.post("/orders/", status_code=201)
def add_order(order: Orders, db: Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cursor = db.cursor()
    try:
        cursor.execute("""
            INSERT INTO orders (user_id, amount, order_status, payment_status, payment_mode, order_date, delivery_date, address, city)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (order.user_id, order.amount, order.order_status, order.payment_status, order.payment_mode, 
              order.order_date, order.delivery_date, order.address, order.city))
        db.commit()
        return {"message": "Order created successfully", "order_id": cursor.lastrowid}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="User not found")
    finally:
        cursor.close()

@app.get("/orders", response_model=List[OrderResponse])
def get_orders(db: Connection = Depends(get_db), admin: dict = Depends(get_admin_user)):
    cursor = db.cursor()
    try:
        data = cursor.execute("SELECT * FROM orders").fetchall()
        return [dict(row) for row in data]
    finally:
        cursor.close()

@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cursor = db.cursor()
    try:
        order = cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        if order["user_id"] != current_user["user_id"] and current_user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Access forbidden")
        
        return dict(order)
    finally:
        cursor.close()

@app.put("/orders/{order_id}", response_model=OrderResponse)
def update_order(order_id: int, order: Orders, db: Connection = Depends(get_db), admin: dict = Depends(get_admin_user)):
    cursor = db.cursor()
    try:
        if not cursor.execute("SELECT 1 FROM orders WHERE order_id = ?", (order_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Order not found")
        
        cursor.execute("""
            UPDATE orders SET user_id=?, amount=?, order_status=?, payment_status=?, payment_mode=?, 
            order_date=?, delivery_date=?, address=?, city=?
            WHERE order_id=?
        """, (order.user_id, order.amount, order.order_status, order.payment_status, order.payment_mode,
              order.order_date, order.delivery_date, order.address, order.city, order_id))
        db.commit()
        
        updated = cursor.execute("SELECT * FROM orders WHERE order_id=?", (order_id,)).fetchone()
        return dict(updated)
    finally:
        cursor.close()

@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: int, db: Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Allow a user to cancel their own order within 1 day of order_date.
    """
    cursor = db.cursor()
    try:
        order = cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
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

        cursor.execute("UPDATE orders SET order_status = ? WHERE order_id = ?", ("cancelled", order_id))
        db.commit()

        updated = cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        return {
            "message": "Order cancelled successfully",
            "order": dict(updated)
        }
    finally:
        cursor.close()

@app.delete("/orders/{order_id}")
def delete_order(order_id: int, db: Connection = Depends(get_db), admin: dict = Depends(get_admin_user)):
    cursor = db.cursor()
    try:
        if not cursor.execute("SELECT 1 FROM orders WHERE order_id = ?", (order_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Order not found")
        
        cursor.execute("DELETE FROM orders WHERE order_id = ?", (order_id,))
        db.commit()
        return {"message": "Order deleted successfully"}
    finally:
        cursor.close()

@app.post("/orders/complete", status_code=201)
def create_complete_order(order: CreateOrder, db: Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Create an order with all items in a single request
    """
    cursor = db.cursor()
    try:
        total_amount = sum(item.price * item.quantity for item in order.items)
        
        cursor.execute("""
            INSERT INTO orders (user_id, amount, order_status, payment_status, payment_mode, 
                              order_date, delivery_date, address, city)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (order.user_id, total_amount, order.order_status, order.payment_status, 
              order.payment_mode, order.order_date, order.delivery_date, order.address, order.city))
        
        order_id = cursor.lastrowid
        
        for item in order.items:
            cursor.execute("""
                INSERT INTO order_details (order_id, item_id, quantity, price)
                VALUES (?, ?, ?, ?)
            """, (order_id, item.item_id, item.quantity, item.price))
        
        db.commit()
        return {
            "message": "Order created successfully",
            "order_id": order_id,
            "total_amount": total_amount,
            "items_count": len(order.items)
        }
        
    except sqlite3.IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid user_id or item_id")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()

@app.get("/orders/{order_id}/complete")
def get_complete_order(order_id: int, db: Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Get order with all item details in one response
    """
    cursor = db.cursor()
    try:
        order = cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        if order["user_id"] != current_user["user_id"] and current_user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Access forbidden")
        
        items = cursor.execute("""
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
            WHERE od.order_id = ?
        """, (order_id,)).fetchall()
        
        return {
            "order": dict(order),
            "items": [dict(item) for item in items],
            "total_items": len(items)
        }
        
    finally:
        cursor.close()

@app.post("/order-details/", status_code=201)
def add_order_detail(detail: OrderDetails, db: Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cursor = db.cursor()
    try:
        cursor.execute("""
            INSERT INTO order_details (order_id, item_id, quantity, price)
            VALUES (?, ?, ?, ?)
        """, (detail.order_id, detail.item_id, detail.quantity, detail.price))
        db.commit()
        return {"message": "Order detail created successfully", "order_detail_id": cursor.lastrowid}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Order or Item not found")
    finally:
        cursor.close()

@app.get("/order-details", response_model=List[OrderDetailResponse])
def get_order_details(db: Connection = Depends(get_db), admin: dict = Depends(get_admin_user)):
    cursor = db.cursor()
    try:
        data = cursor.execute("SELECT * FROM order_details").fetchall()
        return [dict(row) for row in data]
    finally:
        cursor.close()

@app.get("/order-details/order/{order_id}", response_model=List[OrderDetailResponse])
def get_order_details_by_order(order_id: int, db: Connection = Depends(get_db), current_user: dict = Depends(get_current_user)):
    cursor = db.cursor()
    try:
        order = cursor.execute("SELECT user_id FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        if order["user_id"] != current_user["user_id"] and current_user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Access forbidden")
        
        data = cursor.execute("SELECT * FROM order_details WHERE order_id = ?", (order_id,)).fetchall()
        return [dict(row) for row in data]
    finally:
        cursor.close()

@app.put("/order-details/{detail_id}", response_model=OrderDetailResponse)
def update_order_detail(detail_id: int, detail: OrderDetails, db: Connection = Depends(get_db), admin: dict = Depends(get_admin_user)):
    cursor = db.cursor()
    try:
        if not cursor.execute("SELECT 1 FROM order_details WHERE order_detail_id = ?", (detail_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Order detail not found")
        
        cursor.execute("""
            UPDATE order_details SET order_id=?, item_id=?, quantity=?, price=?
            WHERE order_detail_id=?
        """, (detail.order_id, detail.item_id, detail.quantity, detail.price, detail_id))
        db.commit()
        
        updated = cursor.execute("SELECT * FROM order_details WHERE order_detail_id=?", (detail_id,)).fetchone()
        return dict(updated)
    finally:
        cursor.close()

@app.delete("/order-details/{detail_id}")
def delete_order_detail(detail_id: int, db: Connection = Depends(get_db), admin: dict = Depends(get_admin_user)):
    cursor = db.cursor()
    try:
        if not cursor.execute("SELECT 1 FROM order_details WHERE order_detail_id = ?", (detail_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Order detail not found")
        
        cursor.execute("DELETE FROM order_details WHERE order_detail_id = ?", (detail_id,))
        db.commit()
        return {"message": "Order detail deleted successfully"}
    finally:
        cursor.close()

@app.post("/register", status_code=201)
def register(user: Users, db: Connection = Depends(get_db)):
    cursor = db.cursor()
    try:
        hashed_password = hash_password(user.password)
        cursor.execute("""
            INSERT INTO users (name, phone_number, email, password, role, address, city)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user.name, user.phone_number, user.email, hashed_password, user.role, user.address, user.city))
        db.commit()
        return {"message": "User registered successfully", "user_id": cursor.lastrowid}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Phone number already exists")
    finally:
        cursor.close()

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Connection = Depends(get_db)):
    cursor = db.cursor()
    try:
        user = cursor.execute(
            "SELECT * FROM users WHERE email = ?", 
            (form_data.username,)
        ).fetchone()
        
        if not user or not verify_password(form_data.password, user["password"]):
            raise HTTPException(status_code=401, detail="Incorrect email or password")
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user["user_id"])}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "user_id": user["user_id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
                "phone_number": user["phone_number"],
                "address": user["address"],
                "city": user["city"]
            }
        }
    finally:
        cursor.close()

@app.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    return current_user

@app.get("/admin/users", response_model=List[UserResponse])
def admin_get_all_users(db: Connection = Depends(get_db), admin: dict = Depends(get_admin_user)):
    cursor = db.cursor()
    try:
        data = cursor.execute("""
            SELECT user_id, name, phone_number, email, role, address, city 
            FROM users
        """).fetchall()
        return [dict(row) for row in data]
    finally:
        cursor.close()

@app.get("/users/search/")
def search_users(name: Optional[str] = None, city: Optional[str] = None, db: Connection = Depends(get_db)):
    cursor = db.cursor()
    try:
        query = "SELECT user_id, name, phone_number, email, role, address, city FROM users WHERE 1=1"
        params = []
        
        if name:
            query += " AND name LIKE ?"
            params.append(f"%{name}%")
        if city:
            query += " AND city LIKE ?"
            params.append(f"%{city}%")
        
        data = cursor.execute(query, params).fetchall()
        return [dict(row) for row in data]
    finally:
        cursor.close()

@app.get("/users/{user_id}/orders", response_model=List[OrderResponse])
def get_user_orders(user_id: int, db: Connection = Depends(get_db)):
    cursor = db.cursor()
    try:
        data = cursor.execute("SELECT * FROM orders WHERE user_id = ?", (user_id,)).fetchall()
        return [dict(row) for row in data]
    finally:
        cursor.close()

@app.get("/orders/status/{status}", response_model=List[OrderResponse])
def get_orders_by_status(status: str, db: Connection = Depends(get_db)):
    if status not in ['pending', 'confirmed', 'delivered', 'cancelled']:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    cursor = db.cursor()
    try:
        data = cursor.execute("SELECT * FROM orders WHERE order_status = ?", (status,)).fetchall()
        return [dict(row) for row in data]
    finally:
        cursor.close()

@app.get("/items/search/")
def search_items(name: str, db: Connection = Depends(get_db)):
    cursor = db.cursor()
    try:
        data = cursor.execute(
            "SELECT * FROM items WHERE item_name LIKE ?", 
            (f"%{name}%",)
        ).fetchall()
        return [dict(row) for row in data]
    finally:
        cursor.close()

@app.get("/items/paginated")
def get_items_paginated(skip: int = 0, limit: int = 10, db: Connection = Depends(get_db)):
    cursor = db.cursor()
    try:
        data = cursor.execute(
            "SELECT * FROM items LIMIT ? OFFSET ?", 
            (limit, skip)
        ).fetchall()
        total = cursor.execute("SELECT COUNT(*) as count FROM items").fetchone()["count"]
        
        return {
            "items": [dict(row) for row in data],
            "total": total,
            "skip": skip,
            "limit": limit
        }
    finally:
        cursor.close()

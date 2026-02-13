from fastapi import FastAPI, HTTPException, Depends
from database import create_users, get_db_connection, get_db
from models import Users, UserResponse
from typing import Any, List
Connection = Any
import sqlite3
import hashlib

app = FastAPI()


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
        hashed_password = hashlib.sha256(str(user.password).encode()).hexdigest()
        
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

@app.get("/users", response_model= List[UserResponse])
def get_user(db: Connection = Depends(get_db)):
    cursor = db.cursor()
    data = cursor.execute("select * from users").fetchall()
    cursor.close()
    return [dict(row) for row in data]

@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user: Users, db: Connection = Depends(get_db)):
    cursor = db.cursor()
    
    try:
        if not cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        
        hashed_password = hashlib.sha256(user.password.encode()).hexdigest()
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
def delete_user(user_id: int, db: Connection = Depends(get_db)):
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
def get_user_by_id(user_id: int, db: Connection = Depends(get_db)):
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
def add_item(item: Items, db: Connection = Depends(get_db)):
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
def update_item(item_id: int, item: Items, db: Connection = Depends(get_db)):
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
def delete_item(item_id: int, db: Connection = Depends(get_db)):
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
def add_order(order: Orders, db: Connection = Depends(get_db)):
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
def get_orders(db: Connection = Depends(get_db)):
    cursor = db.cursor()
    try:
        data = cursor.execute("SELECT * FROM orders").fetchall()
        return [dict(row) for row in data]
    finally:
        cursor.close()

@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Connection = Depends(get_db)):
    cursor = db.cursor()
    try:
        order = cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return dict(order)
    finally:
        cursor.close()

@app.put("/orders/{order_id}", response_model=OrderResponse)
def update_order(order_id: int, order: Orders, db: Connection = Depends(get_db)):
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

@app.delete("/orders/{order_id}")
def delete_order(order_id: int, db: Connection = Depends(get_db)):
    cursor = db.cursor()
    try:
        if not cursor.execute("SELECT 1 FROM orders WHERE order_id = ?", (order_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Order not found")
        
        cursor.execute("DELETE FROM orders WHERE order_id = ?", (order_id,))
        db.commit()
        return {"message": "Order deleted successfully"}
    finally:
        cursor.close()
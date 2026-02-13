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
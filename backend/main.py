from fastapi import FastAPI, HTTPException, Depends
from database import create_users, get_db_connection
from models import Users
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
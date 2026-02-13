from pydantic import BaseModel

class Users(BaseModel):
    name: str
    phone_number: int
    email: str
    password: str
    role: str
    address: str
    city: str
    
class UserResponse(BaseModel):
    user_id: int
    name: str
    phone_number: int
    email: str
    role: str
    address: str
    city: str

class Items(BaseModel):
    item_name: str
    price: int
    weight: str
    photos: str
    videos: str
    description: str

class ItemResponse(BaseModel):
    item_id: int
    item_name: str
    price: int
    weight: str
    photos: str
    videos: str
    description: str
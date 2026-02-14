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

class Orders(BaseModel):
    user_id: int
    amount: int
    order_status: str
    payment_status: str
    payment_mode: str
    order_date: str
    delivery_date: str
    address: str
    city: str

class OrderResponse(BaseModel):
    order_id: int
    user_id: int
    amount: int
    order_status: str
    payment_status: str
    payment_mode: str
    order_date: str
    delivery_date: str
    address: str
    city: str

class OrderDetails(BaseModel):
    order_id: int
    item_id: int
    quantity: int
    price: int

class OrderDetailResponse(BaseModel):
    order_detail_id: int
    order_id: int
    item_id: int
    quantity: int
    price: int
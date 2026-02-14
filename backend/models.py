from pydantic import BaseModel, EmailStr, validator, Field
from typing import List

class Users(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone_number: int = Field(..., ge=1000000000, le=9999999999)  # 10 digit number
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str
    address: str = Field(..., min_length=5)
    city: str = Field(..., min_length=2)
    
    @validator('role')
    def validate_role(cls, v):
        if v not in ['admin', 'user']:
            raise ValueError('Role must be either admin or user')
        return v
    
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
    amount: int = Field(..., ge=0)
    order_status: str
    payment_status: str
    payment_mode: str
    order_date: str
    delivery_date: str
    address: str = Field(..., min_length=5)
    city: str = Field(..., min_length=2)
    
    @validator('order_status')
    def validate_order_status(cls, v):
        if v not in ['pending', 'confirmed', 'delivered', 'cancelled']:
            raise ValueError('Invalid order status')
        return v
    
    @validator('payment_status')
    def validate_payment_status(cls, v):
        if v not in ['pending', 'paid', 'failed']:
            raise ValueError('Invalid payment status')
        return v
    
    @validator('payment_mode')
    def validate_payment_mode(cls, v):
        if v not in ['cash', 'upi', 'card']:
            raise ValueError('Invalid payment mode')
        return v

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
    quantity: int = Field(..., gt=0)
    price: int = Field(..., ge=0)

class OrderDetailResponse(BaseModel):
    order_detail_id: int
    order_id: int
    item_id: int
    quantity: int
    price: int

class OrderItem(BaseModel):
    item_id: int
    quantity: int
    price: int

class CreateOrder(BaseModel):
    user_id: int
    order_status: str
    payment_status: str
    payment_mode: str
    order_date: str
    delivery_date: str
    address: str
    city: str
    items: List[OrderItem]
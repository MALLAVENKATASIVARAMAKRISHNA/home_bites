from pydantic import BaseModel

class Users(BaseModel):
    name: str
    phone_number: int
    email: str
    password: str
    role: str
    address: str
    city: str
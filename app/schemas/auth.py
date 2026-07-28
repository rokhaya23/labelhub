# app.schemas.auth.py
from pydantic import BaseModel, EmailStr, Field


# Données fournies par le client
class UserRegister(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)

# Les données stockées dans la base de données (hachées)
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    hashed_password: str
    is_active: bool = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int # Secondes

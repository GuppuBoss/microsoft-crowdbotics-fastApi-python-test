from pydantic import BaseModel, EmailStr, Field
from datetime import date
from typing import Optional, List

# User schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class User(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

# Magazine schemas
class MagazineBase(BaseModel):
    name: str
    description: str
    base_price: float = Field(gt=0)

class MagazineCreate(MagazineBase):
    pass

class Magazine(MagazineBase):
    id: int

    class Config:
        from_attributes = True

# Plan schemas
class PlanBase(BaseModel):
    title: str
    description: str
    renewal_period: int = Field(gt=0)
    discount: float = Field(ge=0, le=1)
    tier: int = Field(gt=0)

class PlanCreate(PlanBase):
    pass

class Plan(PlanBase):
    id: int

    class Config:
        from_attributes = True

# Subscription schemas
class SubscriptionBase(BaseModel):
    magazine_id: int
    plan_id: int
    renewal_date: date

class SubscriptionCreate(SubscriptionBase):
    pass

class Subscription(SubscriptionBase):
    id: int
    user_id: int
    price: float
    is_active: bool

    class Config:
        from_attributes = True

# Token schema
class Token(BaseModel):
    access_token: str
    token_type: str 
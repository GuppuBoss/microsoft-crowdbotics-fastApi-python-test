from pydantic import BaseModel
from datetime import date

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
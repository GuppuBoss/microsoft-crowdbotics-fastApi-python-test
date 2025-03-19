from sqlalchemy import Boolean, Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

    subscriptions = relationship("Subscription", back_populates="user")

class Magazine(Base):
    __tablename__ = "magazines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    base_price = Column(Float)

    subscriptions = relationship("Subscription", back_populates="magazine")

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, index=True)
    description = Column(String)
    renewal_period = Column(Integer)
    discount = Column(Float)
    tier = Column(Integer)

    subscriptions = relationship("Subscription", back_populates="plan")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    magazine_id = Column(Integer, ForeignKey("magazines.id"))
    plan_id = Column(Integer, ForeignKey("plans.id"))
    price = Column(Float)
    renewal_date = Column(Date)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="subscriptions")
    magazine = relationship("Magazine", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions") 
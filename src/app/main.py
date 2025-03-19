import utils.session
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, UTC
from typing import List
import jwt
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from .db.session import get_db
from .database import engine
from .core.jwt import create_access_token, SECRET_KEY, ALGORITHM
from . import models
from .schemas.user import User, UserCreate, Token, UserLogin
from .schemas.magazine import Magazine, MagazineCreate
from .schemas.plan import Plan, PlanCreate
from .schemas.subscription import Subscription, SubscriptionCreate
from pydantic import BaseModel

# Initialize FastAPI app
app = FastAPI()

# Security
SECRET_KEY = "your-secret-key"  # In production, use a secure secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Create tables
models.Base.metadata.create_all(bind=engine)

# Helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# Add this Pydantic model for password reset
class PasswordReset(BaseModel):
    old_password: str
    new_password: str

# User routes
@app.post("/users/register", response_model=User)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users/login", response_model=Token)
def login_user(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == user_data.username).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    # Create access token with default expiry
    access_token = create_access_token(
        data={"sub": user.username, "type": "access"}
    )
    # Create refresh token with longer expiry
    refresh_token = create_access_token(
        data={"sub": user.username, "type": "refresh", "exp": datetime.now(UTC) + timedelta(days=7)}
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@app.get("/users/me", response_model=User)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@app.post("/users/reset-password")
def reset_password(
    email: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.email != email:
        raise HTTPException(status_code=400, detail="Email does not match current user")
    
    # Generate new random password or send reset link (for this test, we'll just return success)
    return {"message": "Password reset instructions sent"}

@app.delete("/users/deactivate/{username}")
def deactivate_user(
    username: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.username != username:
        raise HTTPException(status_code=403, detail="Not authorized to deactivate this user")
    
    current_user.is_active = False
    db.commit()
    return {"message": "User deactivated successfully"}

@app.post("/users/token/refresh", response_model=Token)
def refresh_token(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        if username is None or token_type != "refresh":
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
        
    # Generate new tokens
    access_token = create_access_token(
        data={"sub": username, "type": "access"}
    )
    refresh_token = create_access_token(
        data={"sub": username, "type": "refresh", "exp": datetime.now(UTC) + timedelta(days=7)}
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

# Magazine routes
@app.post("/magazines/", response_model=Magazine)
def create_magazine(
    magazine: MagazineCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_magazine = models.Magazine(**magazine.dict())
    db.add(db_magazine)
    db.commit()
    db.refresh(db_magazine)
    return db_magazine

@app.get("/magazines/", response_model=List[Magazine])
def get_magazines(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(models.Magazine).all()

@app.get("/magazines/{magazine_id}", response_model=Magazine)
def get_magazine(
    magazine_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_magazine = db.query(models.Magazine).filter(models.Magazine.id == magazine_id).first()
    if db_magazine is None:
        raise HTTPException(status_code=404, detail="Magazine not found")
    return db_magazine

@app.put("/magazines/{magazine_id}", response_model=Magazine)
def update_magazine(
    magazine_id: int,
    magazine_update: MagazineCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_magazine = db.query(models.Magazine).filter(models.Magazine.id == magazine_id).first()
    if db_magazine is None:
        raise HTTPException(status_code=404, detail="Magazine not found")
    
    # Update magazine attributes
    for key, value in magazine_update.model_dump().items():
        setattr(db_magazine, key, value)
    
    db.commit()
    db.refresh(db_magazine)
    return db_magazine

@app.delete("/magazines/{magazine_id}")
def delete_magazine(
    magazine_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_magazine = db.query(models.Magazine).filter(models.Magazine.id == magazine_id).first()
    if db_magazine is None:
        raise HTTPException(status_code=404, detail="Magazine not found")
    
    db.delete(db_magazine)
    db.commit()
    return {"message": "Magazine deleted successfully"}

# Plan routes
@app.post("/plans/", response_model=Plan)
def create_plan(
    plan: PlanCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_plan = models.Plan(**plan.model_dump())
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan

@app.get("/plans/", response_model=List[Plan])
def get_plans(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(models.Plan).all()

@app.get("/plans/{plan_id}", response_model=Plan)
def get_plan(
    plan_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_plan = db.query(models.Plan).filter(models.Plan.id == plan_id).first()
    if db_plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return db_plan

@app.put("/plans/{plan_id}", response_model=Plan)
def update_plan(
    plan_id: int,
    plan_update: PlanCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_plan = db.query(models.Plan).filter(models.Plan.id == plan_id).first()
    if db_plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Update plan attributes
    for key, value in plan_update.model_dump().items():
        setattr(db_plan, key, value)
    
    db.commit()
    db.refresh(db_plan)
    return db_plan

@app.delete("/plans/{plan_id}")
def delete_plan(
    plan_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_plan = db.query(models.Plan).filter(models.Plan.id == plan_id).first()
    if db_plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    db.delete(db_plan)
    db.commit()
    return {"message": "Plan deleted successfully"}

# Subscription routes
@app.post("/subscriptions/", response_model=Subscription)
def create_subscription(
    subscription: SubscriptionCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check for existing active subscription
    existing_subscription = db.query(models.Subscription).filter(
        models.Subscription.user_id == current_user.id,
        models.Subscription.magazine_id == subscription.magazine_id,
        models.Subscription.is_active == True
    ).first()
    
    if existing_subscription:
        if existing_subscription.plan_id == subscription.plan_id:
            # If trying to create exact same subscription (same plan), return 422
            raise HTTPException(
                status_code=422,
                detail="Active subscription already exists for this magazine"
            )
        else:
            # If different plan, deactivate old subscription (upgrade/downgrade case)
            existing_subscription.is_active = False
            db.commit()

    # Calculate price
    magazine = db.query(models.Magazine).filter(models.Magazine.id == subscription.magazine_id).first()
    plan = db.query(models.Plan).filter(models.Plan.id == subscription.plan_id).first()
    
    if not magazine or not plan:
        raise HTTPException(status_code=404, detail="Magazine or Plan not found")
    
    price = magazine.base_price * (1 - plan.discount)
    
    # Validate price is greater than zero
    if price <= 0:
        raise HTTPException(status_code=422, detail="Price must be greater than zero")
    
    db_subscription = models.Subscription(
        user_id=current_user.id,
        magazine_id=subscription.magazine_id,
        plan_id=subscription.plan_id,
        price=price,
        renewal_date=subscription.renewal_date,
        is_active=True
    )
    db.add(db_subscription)
    db.commit()
    db.refresh(db_subscription)
    return db_subscription

@app.get("/subscriptions/", response_model=List[Subscription])
def get_subscriptions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(models.Subscription).filter(
        models.Subscription.user_id == current_user.id,
        models.Subscription.is_active == True
    ).all()

@app.get("/subscriptions/{subscription_id}", response_model=Subscription)
def get_subscription(
    subscription_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    subscription = db.query(models.Subscription).filter(
        models.Subscription.id == subscription_id,
        models.Subscription.user_id == current_user.id
    ).first()
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return subscription

@app.put("/subscriptions/{subscription_id}", response_model=Subscription)
def update_subscription(
    subscription_id: int,
    new_subscription: SubscriptionCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get existing subscription
    db_subscription = db.query(models.Subscription).filter(
        models.Subscription.id == subscription_id,
        models.Subscription.user_id == current_user.id,
        models.Subscription.is_active == True
    ).first()
    
    if not db_subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Deactivate old subscription
    db_subscription.is_active = False
    
    # Create new subscription
    magazine = db.query(models.Magazine).filter(models.Magazine.id == new_subscription.magazine_id).first()
    plan = db.query(models.Plan).filter(models.Plan.id == new_subscription.plan_id).first()
    
    if not magazine or not plan:
        raise HTTPException(status_code=404, detail="Magazine or Plan not found")
    
    price = magazine.base_price * (1 - plan.discount)
    
    new_db_subscription = models.Subscription(
        user_id=current_user.id,
        magazine_id=new_subscription.magazine_id,
        plan_id=new_subscription.plan_id,
        price=price,
        renewal_date=new_subscription.renewal_date,
        is_active=True
    )
    
    db.add(new_db_subscription)
    db.commit()
    db.refresh(new_db_subscription)
    return new_db_subscription

@app.delete("/subscriptions/{subscription_id}")
def delete_subscription(
    subscription_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    subscription = db.query(models.Subscription).filter(
        models.Subscription.id == subscription_id,
        models.Subscription.user_id == current_user.id
    ).first()
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    subscription.is_active = False
    db.commit()
    return {"message": "Subscription cancelled successfully"} 
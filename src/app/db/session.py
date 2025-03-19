from ..database import SessionLocal, engine

# Re-export get_db and other database components
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 
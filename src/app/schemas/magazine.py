from pydantic import BaseModel, Field

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
from pydantic import BaseModel, Field

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
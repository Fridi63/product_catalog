from pydantic import BaseModel, Field

class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)

class CategoryOut(BaseModel):
    id: int
    name: str
    product_count: int = 0

    class Config:
        from_attributes = True

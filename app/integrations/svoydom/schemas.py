from pydantic import BaseModel, Field


class Property(BaseModel):
    id: str
    title: str
    city: str = Field(default="Astana")
    district: str
    residential_complex: str
    rooms: int
    price: int
    area_m2: float
    url: str | None = None

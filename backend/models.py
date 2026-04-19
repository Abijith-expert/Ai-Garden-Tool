from pydantic import BaseModel
from typing import Optional
from enum import Enum


class PlantCategory(str, Enum):
    flowers = "flowers"
    shrubs = "shrubs"
    trees = "trees"
    groundcover = "groundcover"
    ornamental = "ornamental"
    potted = "potted"
    hedges = "hedges"
    climbers = "climbers"


class PlantInfo(BaseModel):
    id: str
    filename: str
    name: str
    category: PlantCategory
    height_cm: int = 60
    spread_cm: int = 40
    sun: str = "Full Sun"
    water: str = "Moderate"
    image_url: str = ""


class PlacedPlant(BaseModel):
    id: str
    plant_id: str
    x_percent: float  # 0-100
    y_percent: float  # 0-100
    scale: float = 1.0
    rotation: float = 0.0
    flip_h: bool = False


class GenerateRequest(BaseModel):
    garden_image_id: str
    style: str = "natural"  # natural, formal, cottage, modern, tropical
    density: str = "medium"  # sparse, medium, dense
    plant_ids: list[str] = []  # empty = use all


class GenerateResponse(BaseModel):
    placements: list[PlacedPlant]
    description: str = ""


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    email: str
    token: str


class ExportRequest(BaseModel):
    placements: list[PlacedPlant]
    format: str = "csv"  # csv, pdf

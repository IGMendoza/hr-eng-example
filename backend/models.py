from enum import Enum
from typing import List, Dict
from pydantic import BaseModel, Field

# -----------------------------
# Domain Models (Pydantic)
# -----------------------------

class RobotStatus(str, Enum):
    IDLE = "IDLE"
    EXECUTING = "EXECUTING"

class OrderStatus(str, Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    FAILED = "FAILED"

class Robot(BaseModel):
    name: str
    status: RobotStatus
    node: str

class Order(BaseModel):
    name: str
    source: str
    target: str
    status: OrderStatus = OrderStatus.NEW

class Edge(BaseModel):
    from_: str = Field(alias="from")
    to: str
    weight: float = 1.0

    class Config:
        allow_population_by_field_name = True
        json_encoders = {RobotStatus: lambda s: s.value, OrderStatus: lambda s: s.value}

class Graph(BaseModel):
    nodes: List[str]
    edges: List[Edge]

# -----------------------------
# Pathfinding Models
# -----------------------------

class ShortestPath(BaseModel):
    start: str
    target: str
    distance: float
    path: List[str]

class DistanceMatrix(BaseModel):
    matrix: Dict[str, Dict[str, ShortestPath]]

# -----------------------------
# API Schemas
# -----------------------------

class AddOrderRequest(BaseModel):
    name: str
    source: str
    target: str

# Optional: include computed assignment in future
class OrdersResponse(BaseModel):
    orders: List[Order]

class RobotsResponse(BaseModel):
    robots: List[Robot]

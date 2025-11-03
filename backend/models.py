from enum import Enum
from typing import List, Dict, Literal, Optional
from pydantic import BaseModel, Field

# -----------------------------
# Domain Models (Pydantic)
# -----------------------------

class RobotStatus(str, Enum):
    IDLE = "IDLE"
    EXECUTING = "EXECUTING"
    CHARGING = "CHARGING"

class OrderStatus(str, Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    FAILED = "FAILED"

class Robot(BaseModel):
    name: str
    status: RobotStatus
    node: str
    battery: int

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
# Scheduling Models
# -----------------------------

class PlannedRoute(BaseModel):
    robot: str
    order: str
    path: List[str]
    idx: int = 0
    kind: Literal["order", "charge"] = "order"

class PlannedRouteSummary(BaseModel):
    order: str
    robot: str
    distance_to_start: float
    path_to_start: List[str]
    path_to_target: List[str]
    full_path: List[str]

# -----------------------------
# Tick
# -----------------------------

class MoveEvent(BaseModel):
    robot: str
    node: str
    to: str
    kind: Literal["order", "charge"]

class CompletionEvent(BaseModel):
    robot: str
    order: Optional[str] = None
    kind: Literal["order", "charge"]

class TickResponse(BaseModel):
    tick: int
    moved: int
    completed_orders: int
    finished_charging: int
    remaining_active_routes: int
    moves: List[MoveEvent] = []
    completions: List[CompletionEvent] = []
    assignments: List[PlannedRouteSummary] = []

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

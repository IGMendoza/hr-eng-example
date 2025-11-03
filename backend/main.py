from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio

from .models import (
    RobotStatus, OrderStatus, Robot, Order, Edge, Graph, # domain
    ShortestPath, DistanceMatrix, # pathfinding
    PlannedRoute, PlannedRouteSummary, # scheduler
    MoveEvent, CompletionEvent, TickResponse, # tick
    AddOrderRequest, OrdersResponse, RobotsResponse, # api schemas
)

from .pathfinding import _pathfinding, _distance_matrix
from .scheduler import assign_nearest_idle_robot
from .config import LOW_BATTERY
from .tick import tick_step

# -----------------------------
# In-memory State (Replace with DB for prod)
# -----------------------------

STATE: Dict[str, List] = {
    "orders": [],
    "robots": [],
    "routes": [],
    "idempotency": {},
}

GRAPH: Graph = Graph(
    nodes=["A", "B", "C", "D", "E", "F"],
    edges=[
        Edge(**{"from": "A", "to": "B", "weight": 1}),
        Edge(**{"from": "B", "to": "C", "weight": 2}),
        Edge(**{"from": "C", "to": "D", "weight": 2}),
        Edge(**{"from": "B", "to": "E", "weight": 3}),
        Edge(**{"from": "E", "to": "F", "weight": 1}),
        Edge(**{"from": "D", "to": "F", "weight": 2}),
        # Treat edges as undirected for simplicity; callers may add both directions explicitly if desired
    ],
)

SEED_ROBOTS = [
    Robot(name="R1", status=RobotStatus.IDLE, node="A", battery=80),
    Robot(name="R2", status=RobotStatus.EXECUTING, node="C", battery=70),
    Robot(name="R3", status=RobotStatus.IDLE, node="E", battery=10),
]

SEED_ORDERS = [
    Order(name="O-1001", source="B", target="D", status=OrderStatus.NEW),
]

# -----------------------------
# App Setup
# -----------------------------

app = FastAPI(
    title="AGV Scheduling Exercise API",
    version="0.1.0",
    description=(
        "Minimal backend stubs for the AGV fleet scheduling exercise.\n\n"
        "Endpoints provided: /addOrder, /getOrders, /getGraph, /getRobots.\n"
        "State is in-memory and resets on restart."
    ),
)

# CORS for local dev frontends (Vite/Next/CRA)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default
        "http://localhost:3000",  # CRA/Next.js
        "*",  # loosen for exercise; tighten for prod
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Helpers
# -----------------------------

def _graph_nodes_set() -> set:
    return set(GRAPH.nodes)

# -----------------------------
# Lifecycle
# -----------------------------

@app.on_event("startup")
async def seed_state() -> None:
    # Seed only once per process start
    STATE["orders"] = list(SEED_ORDERS)
    STATE["robots"] = list(SEED_ROBOTS)
    STATE["routes"] = []
    STATE["idempotency"] = {}
    app.state.state_lock = asyncio.Lock()
    app.state.tick_counter = 0

# -----------------------------
# Endpoints (as specified)
# -----------------------------

@app.get("/healthz")
async def healthz():
    return {"ok": True}

@app.post("/addOrder", response_model=Order, tags=["orders"], status_code=201)
async def add_order(
    req: AddOrderRequest,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> Order:
    if idempotency_key:
        cached = STATE["idempotency"].get(("addOrder", idempotency_key))
        if cached is not None:
            return cached
        
    # Validate nodes exist in graph
    nodes = _graph_nodes_set()
    if req.source not in nodes or req.target not in nodes:
        raise HTTPException(status_code=422, detail="source/target must be valid graph nodes")

    # Enforce unique order name for simplicity
    if any(o.name == req.name for o in STATE["orders"]):
        raise HTTPException(status_code=409, detail="Order with this name already exists")

    order = Order(name=req.name, source=req.source, target=req.target, status=OrderStatus.NEW)
    STATE["orders"].append(order)

    if idempotency_key:
        STATE["idempotency"][("addOrder", idempotency_key)] = order
    return order

@app.get("/getOrders", response_model=OrdersResponse, tags=["orders"])
async def get_orders() -> OrdersResponse:
    return OrdersResponse(orders=STATE["orders"])

@app.get("/getRobots", response_model=RobotsResponse, tags=["robots"])
async def get_robots() -> RobotsResponse:
    return RobotsResponse(robots=STATE["robots"])

@app.get("/getGraph", response_model=Graph, tags=["graph"])
async def get_graph() -> Graph:
    return GRAPH

@app.get("/getDistanceMatrix", response_model=DistanceMatrix, tags=["distanceMatrix"])
async def get_distance_matrix() -> DistanceMatrix:
    try:
        return _distance_matrix(GRAPH)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@app.get("/path", response_model=ShortestPath)
def get_path(start: str, target: str):
    try:
        return _pathfinding(GRAPH, start, target)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    
@app.post("/assign/{order_name}", response_model=PlannedRouteSummary, tags=["scheduling"])
async def assign(order_name: str) -> PlannedRouteSummary:
    try:
        return assign_nearest_idle_robot(order_name, STATE, GRAPH)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    
@app.get("/routes", response_model=List[PlannedRoute], tags=["simulation"])
async def get_routes() -> List[PlannedRoute]:
    return STATE["routes"]

@app.post("/tick", response_model=TickResponse, tags=["simulation"])
async def tick(idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key")) -> TickResponse:
    if idempotency_key:
        cached = STATE["idempotency"].get(("tick", idempotency_key))
        if cached is not None:
            return cached
        
    async with app.state.state_lock:
        app.state.tick_counter += 1
        tick_no = app.state.tick_counter

        resp = tick_step(STATE, GRAPH, tick_no)

        if idempotency_key:
            STATE["idempotency"][("tick", idempotency_key)] = resp
        
        return resp

# -----------------------------
# Optional: additional stubs to support simulation (Frontend can ignore)
# -----------------------------
"""
class Route(BaseModel):
    robot: str
    path: List[str]  # sequence of node ids

class RoutesResponse(BaseModel):
    routes: List[Route]

# NOTE: These are *stubs* for stretch goals; they currently return empty data.
@app.get("/routes", response_model=RoutesResponse, tags=["simulation"])
async def get_routes() -> RoutesResponse:
    # TODO: Fill with planned paths once a scheduler is implemented server-side
    return RoutesResponse(routes=[])

@app.post("/tick", tags=["simulation"])
async def tick() -> Dict[str, str]:
    # TODO: Advance in-memory simulation: move robots along paths, update order/robot status
    return {"status": "ok", "note": "tick advanced (no-op stub)"}
"""
# -----------------------------
# Run (if executed directly)
# -----------------------------

# Use: uvicorn main:app --reload // or python -m uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

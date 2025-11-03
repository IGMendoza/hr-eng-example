from typing import Dict, List, Tuple, Optional
from .models import (
    Graph, 
    OrderStatus, 
    RobotStatus, 
    PlannedRoute, 
    PlannedRouteSummary, 
    Order, Robot,
    ShortestPath
)
from .pathfinding import _pathfinding
from .config import LOW_BATTERY

# -----------------------------
# Helper functions
# -----------------------------

def _get_order(state: Dict, order_name: str) -> Order:
    for o in state["orders"]:
        if o.name == order_name:
            return o
    raise ValueError(f"order not found: {order_name}")

def _get_idle_robots(state: Dict) -> List[Robot]: 
    idle = [r for r in state["robots"] if r.status == RobotStatus.IDLE and r.battery >= LOW_BATTERY]
    if not idle:
        raise ValueError("no idel robots available")
    return idle

def _shortest_path_or_none(
        graph: Graph, 
        start: str, 
        target: str, 
        adj: Optional[Dict[str, List[Tuple[str, float]]]] = None,
        algo: Optional[str] = "dijkstra"
    ) -> ShortestPath | None:
    try:
        return _pathfinding(graph, start, target, adj, algo)
    except ValueError:
        return None
    
def _candidates_to_start(
        graph: Graph, 
        robots: List[Robot], 
        start_node: str
    ) -> List[Tuple[float, str, Robot, List[str]]]:
    out: List[Tuple[float, str, Robot, List[str]]] = []
    for r in robots:
        sp = _shortest_path_or_none(graph, r.node, start_node)
        if sp is not None:
            out.append((sp.distance, r.name, r, sp.path))
    if not out:
        raise ValueError("no reachable path from any idle robot to order start")
    out.sort(key=lambda t: (t[0], t[1]))
    return out

def _merge_paths(path_to_start: List[str], path_to_target: List[str]) -> List[str]:
    if path_to_start and path_to_target and path_to_start[-1] == path_to_target[0]:
        return path_to_start + path_to_target[1:]
    return path_to_start + path_to_target

# -----------------------------
# Orchestrator
# -----------------------------

def assign_nearest_idle_robot(order_name: str, state: Dict, graph: Graph) -> PlannedRouteSummary:
    order = _get_order(state, order_name)
    if order.status != OrderStatus.NEW:
        raise ValueError(f"order not assignable (status={order.status})")
    
    idle = _get_idle_robots(state)
    candidates = _candidates_to_start(graph, idle, order.source)
    distance_to_start, _, robot, path_to_start = candidates[0]

    path_to_target = _pathfinding(graph, order.source, order.target).path
    full_path = _merge_paths(path_to_start, path_to_target)

    order.status = OrderStatus.IN_PROGRESS
    robot.status = RobotStatus.EXECUTING

    state["routes"].append(
        PlannedRoute(robot=robot.name, order=order_name, path=full_path, idx=0)
    )

    return PlannedRouteSummary(
        order=order.name,
        robot=robot.name,
        distance_to_start=distance_to_start,
        path_to_start=path_to_start,
        path_to_target=path_to_target,
        full_path=full_path
    )
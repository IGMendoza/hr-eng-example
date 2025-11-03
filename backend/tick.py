from typing import Dict, List, Tuple, Set
from .models import (
    RobotStatus, OrderStatus,
    PlannedRoute, PlannedRouteSummary,
    MoveEvent, CompletionEvent, TickResponse
)
from .config import (
    LOW_BATTERY, RESUME_BATTERY, BATTERY_DRAIN_PER_TICK, BATTERY_CHARGE_PER_TICK
)
from .pathfinding import _nearest_charger_path
from .scheduler import assign_nearest_idle_robot
from .models import Graph

# -----------------------------
# Helper functions
# -----------------------------

def _reserve_edge_key(u: str, v: str) -> frozenset:
    return frozenset((u, v))

def _robots_by_name(state: Dict[str, List]):
    return {r.name: r for r in state["robots"]}

def _orders_by_name(state: Dict[str, List]):
    return {o.name: o for o in state["orders"]}

def _active_robot_names(state: Dict[str, List]):
    return {pr.robot for pr in state["routes"]}

def _plan_low_battery_charging(state: Dict[str, List], graph: Graph) -> None:
    active = _active_robot_names(state)
    for r in state["robots"]:
        if r.status == RobotStatus.IDLE and r.battery < LOW_BATTERY and r.name not in active:
            path = _nearest_charger_path(graph, r.node)
            state["routes"].append(PlannedRoute(robot=r.name, order="", path=path, idx=0, kind="charge"))
            r.status = RobotStatus.CHARGING

def _move_one_tick_with_collision_avoidance(
        state: Dict[str, List],
) -> Tuple[List[PlannedRoute], List[MoveEvent], List[CompletionEvent], int, int]:
    robots = _robots_by_name(state)
    orders = _orders_by_name(state)

    state["routes"].sort(key=lambda pr: pr.robot)

    reserved: Set[frozenset] = set()
    next_routes: List[PlannedRoute] = []
    moves: List[MoveEvent] = []
    completions: List[CompletionEvent] = []
    moved = 0
    completed_orders = 0

    for pr in state["routes"]:
        robot = robots.get(pr.robot)
        if robot is None:
            continue

        path = pr.path
        i = pr.idx

        if 0 <= i < len(path) and robot.node != path[i]:
            robot.node = path[i]
        
        if i >= len(path) - 1:
            if pr.kind == "order":
                if pr.order:
                    o = orders.get(pr.order)
                    if o:
                        o.status = OrderStatus.DONE
                robot.status = RobotStatus.IDLE
                completions.append(CompletionEvent(robot=robot.name, order=pr.order, kind="order"))
                completed_orders += 1
            else:
                next_routes.append(pr)
            continue

        u = path[i]
        v = path[i+1]
        key = _reserve_edge_key(u, v)

        if key in reserved: # avoidance detection
            next_routes.append(pr)
            continue

        reserved.add(key)
        pr.idx = i + 1
        robot.node = v
        moves.append(MoveEvent(robot=robot.name, node=u, to=v, kind=pr.kind))
        moved += 1

        robot.battery = max(0, robot.battery - BATTERY_DRAIN_PER_TICK)

        if pr.idx >= len(path) - 1:
            if pr.kind == "order":
                if pr.order:
                    o = orders.get(pr.order)
                    if o:
                        o.status = OrderStatus.DONE
                robot.status = RobotStatus.IDLE
                completions.append(CompletionEvent(robot=robot.name, order=pr.order, kind="order"))
                completed_orders += 1
            else:
                robot.status = RobotStatus.CHARGING
                next_routes.append(pr)
        else:
            next_routes.append(pr)
    
    return next_routes, moves, completions, moved, completed_orders

def _apply_charging_in_place(state: Dict[str, List]) -> Tuple[List[CompletionEvent], int]:
    robots = _robots_by_name(state)

    new_routes: List[PlannedRoute] = []
    completions: List[CompletionEvent] = []
    finished = 0

    for pr in state["routes"]:
        if pr.kind != "charge":
            new_routes.append(pr)
            continue

        at_end = pr.idx >= len(pr.path) - 1
        if not at_end:
            new_routes.append(pr)
            continue

        robot = robots.get(pr.robot)
        if robot is None:
            continue

        robot.status = RobotStatus.CHARGING
        robot.battery = min(100, robot.battery + BATTERY_CHARGE_PER_TICK)
        if robot.battery >= RESUME_BATTERY:
            robot.status = RobotStatus.IDLE
            completions.append(CompletionEvent(robot=robot.name, order=None, kind="charge"))
            finished += 1
        else:
            new_routes.append(pr)
    
    state["routes"] = new_routes
    return completions, finished

def _batch_schedule_new_orders(state: Dict[str, List], graph: Graph) -> List[PlannedRouteSummary]:
    assignments: List[PlannedRouteSummary] = []
    for o in state["orders"]:
        if o.status == OrderStatus.NEW:
            try:
                summary = assign_nearest_idle_robot(o.name, state, graph)
                assignments.append(summary)
            except ValueError:
                continue
    return assignments

# -----------------------------
# Orchestrator
# -----------------------------

def tick_step(state: Dict[str, List], graph: Graph, tick_no: int) -> TickResponse:
    _plan_low_battery_charging(state, graph)

    next_routes, moves, completions_move, moved, completed_orders = _move_one_tick_with_collision_avoidance(state)
    state["routes"] = next_routes

    completions_charge, finished_charging = _apply_charging_in_place(state)

    assignments = _batch_schedule_new_orders(state, graph)

    completions_all = completions_move + completions_charge

    return TickResponse(
        tick=tick_no,
        moved=moved,
        completed_orders=completed_orders,
        finished_charging=finished_charging,
        remaining_active_routes=len(state["routes"]),
        moves=moves,
        completions=completions_all,
        assignments=assignments,
    )


from typing import List, Dict, Tuple, Optional
import math, heapq

from .models import Graph, ShortestPath, DistanceMatrix

PATHFINDING_ALGOS = ["dijkstra"]

def _build_undirected_adjacency(graph: Graph) -> Dict[str, List[Tuple[str, float]]]:
    adj: Dict[str, List[Tuple[str, float]]] = {n: [] for n in graph.nodes}
    nodeset = set(graph.nodes)
    for e in graph.edges:
        if e.weight < 0:
            raise ValueError(f"negative weight ({e.weight}) in edge {e.from_} to {e.to}")
        if e.from_ not in nodeset or e.to not in nodeset:
            raise ValueError(f"edge not found: {e.from_} or {e.to}")
        adj[e.from_].append((e.to, e.weight))
        adj[e.to].append((e.from_, e.weight))

    for u in adj:
        adj[u].sort(key= lambda t: t[0])
    return adj

def _reconstruct_path(prev: Dict[str, str], start: str, target: str) -> List[str]:
    path: List[str] = []
    cur = target
    while cur != start:
        path.append(cur)
        if cur not in prev:
            return []
        cur = prev[cur]
    path.append(start)
    path.reverse()
    return path

def _dijkstra_single_source(adj: Dict[str, List[Tuple[str, float]]], start: str) -> Tuple[Dict[str, float], Dict[str, str]]:
    nodes = list(adj.keys())
    dist: Dict[str, float] = {n: math.inf for n in nodes}
    prev: Dict[str, str] = {}
    dist[start] = 0.0
    heap: List[Tuple[float, str]] = [(0.0, start)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        for v, w in adj[u]:
            alt = d + w
            if alt < dist[v]:
                dist[v] = alt
                prev[v] = u
                heapq.heappush(heap, (alt, v))

    return dist, prev

def _pathfinding(
        graph: Graph, 
        start: str,
        target: str, 
        adj: Optional[Dict[str, List[Tuple[str, float]]]] = None,
        algo: Optional[str] = "dijkstra"
    ) -> ShortestPath:
    if (algo not in PATHFINDING_ALGOS):
        raise ValueError(f"{algo} algorithm not supported")
    nodeset = set(graph.nodes)
    if start not in nodeset:
        raise ValueError(f"invalid starting node: {start}")
    if target not in nodeset:
        raise ValueError(f"invalid target node: {target}")
    if start == target:
        return ShortestPath(start=start, target=target, distance=0.0, path=[start])
    if adj == None:
        adj = _build_undirected_adjacency(graph)

    match algo:
        case "dijkstra":
            dist, prev = _dijkstra_single_source(adj, start)
        case _:
            dist, prev = _dijkstra_single_source(adj, start)
    if math.isinf(dist.get(target, math.inf)):
        raise ValueError(f"no path from {start} to {target}")
    path = _reconstruct_path(prev, start, target)
    return ShortestPath(start=start, target=target, distance=dist[target], path=path)

def _distance_matrix(graph: Graph, algo: str = "dijkstra") -> DistanceMatrix:
    if (algo not in PATHFINDING_ALGOS):
        raise ValueError(f"{algo} algorithm not supported")
    adj = _build_undirected_adjacency(graph)
    matrix: Dict[str, Dict[str, ShortestPath]] = {}

    for s in graph.nodes:
        if algo == "dijkstra":
            dist, prev = _dijkstra_single_source(adj, s)
        else:
            raise ValueError(f"{algo} algo not supported")
        
        row: Dict[str, ShortestPath] = {}
        for t in graph.nodes:
            if s == t:
                row[t] = ShortestPath(start=s, target=t, distance=0.0, path=[s])
            elif math.isinf(dist[t]):
                row[t] = ShortestPath(start=s, target=t, distance=float("inf"), path=[])
            else:
                path = _reconstruct_path(prev, s, t)
                row[t] = ShortestPath(start=s, target=t, distance=dist[t], path=path)
        matrix[s] = row
    return DistanceMatrix(matrix=matrix)

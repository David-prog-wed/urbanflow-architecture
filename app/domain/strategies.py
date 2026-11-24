from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
import heapq
import time

from app.domain.graph import GrafoUrbano


@dataclass
class ResultadoRuta:
    estrategia: str
    origen: str
    destino: str
    encontrada: bool
    camino: list[str] = field(default_factory=list)
    aristas_camino: list[str] = field(default_factory=list)
    nodos_visitados: list[str] = field(default_factory=list)
    cantidad_visitados: int = 0
    distancia_km: float = 0.0
    tiempo_min: float = 0.0
    tiempo_computo_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "estrategia": self.estrategia,
            "origen": self.origen,
            "destino": self.destino,
            "encontrada": self.encontrada,
            "camino": self.camino,
            "aristas_camino": self.aristas_camino,
            "nodos_visitados": self.nodos_visitados,
            "cantidad_visitados": self.cantidad_visitados,
            "distancia_km": round(self.distancia_km, 2),
            "tiempo_min": round(self.tiempo_min, 2),
            "tiempo_computo_ms": round(self.tiempo_computo_ms, 4),
        }


def _reconstruir_metricas(
    grafo: GrafoUrbano,
    estrategia: str,
    origen: str,
    destino: str,
    padres: dict[str, str | None],
    visitados: list[str],
    inicio_ns: int,
) -> ResultadoRuta:
    elapsed_ms = (time.perf_counter_ns() - inicio_ns) / 1_000_000.0
    if destino not in padres:
        return ResultadoRuta(
            estrategia=estrategia,
            origen=origen,
            destino=destino,
            encontrada=False,
            nodos_visitados=visitados,
            cantidad_visitados=len(visitados),
            tiempo_computo_ms=elapsed_ms,
        )

    camino: list[str] = []
    actual: str | None = destino
    while actual is not None:
        camino.append(actual)
        actual = padres[actual]
    camino.reverse()

    dist_total = 0.0
    tiempo_total = 0.0
    aristas_camino: list[str] = []
    for i in range(len(camino) - 1):
        arista = grafo.buscar_arista_entre(camino[i], camino[i + 1])
        if arista:
            dist_total += arista.distancia_km
            tiempo_total += arista.tiempo_minutos()
            aristas_camino.append(arista.id)

    return ResultadoRuta(
        estrategia=estrategia,
        origen=origen,
        destino=destino,
        encontrada=True,
        camino=camino,
        aristas_camino=aristas_camino,
        nodos_visitados=visitados,
        cantidad_visitados=len(visitados),
        distancia_km=dist_total,
        tiempo_min=tiempo_total,
        tiempo_computo_ms=elapsed_ms,
    )


class EstrategiaRuta(ABC):
    @abstractmethod
    def codigo(self) -> str:
        pass

    @abstractmethod
    def nombre(self) -> str:
        pass

    @abstractmethod
    def calcular(self, grafo: GrafoUrbano, origen: str, destino: str) -> ResultadoRuta:
        pass


class RutaBFSSimple(EstrategiaRuta):
    """Línea base no informada: minimiza saltos ignorando distancia y tráfico."""

    def codigo(self) -> str:
        return "bfs"

    def nombre(self) -> str:
        return "BFS Simple (No informado)"

    def calcular(self, grafo: GrafoUrbano, origen: str, destino: str) -> ResultadoRuta:
        inicio_ns = time.perf_counter_ns()
        cola = deque([origen])
        padres: dict[str, str | None] = {origen: None}
        visitados: list[str] = []

        while cola:
            actual = cola.popleft()
            visitados.append(actual)
            if actual == destino:
                break
            for vecino, _ in grafo.obtener_vecinos(actual):
                if vecino not in padres:
                    padres[vecino] = actual
                    cola.append(vecino)

        return _reconstruir_metricas(
            grafo, self.nombre(), origen, destino, padres, visitados, inicio_ns
        )


class RutaDijkstraDistancia(EstrategiaRuta):
    """Óptimo por distancia física (km), ignorando factores dinámicos de tráfico."""

    def codigo(self) -> str:
        return "dijkstra"

    def nombre(self) -> str:
        return "Dijkstra (Distancia mínima)"

    def calcular(self, grafo: GrafoUrbano, origen: str, destino: str) -> ResultadoRuta:
        inicio_ns = time.perf_counter_ns()
        cola: list[tuple[float, str]] = [(0.0, origen)]
        costos: dict[str, float] = {origen: 0.0}
        padres: dict[str, str | None] = {origen: None}
        cerrados: set[str] = set()
        visitados: list[str] = []

        while cola:
            costo_actual, actual = heapq.heappop(cola)
            if actual in cerrados:
                continue
            cerrados.add(actual)
            visitados.append(actual)

            if actual == destino:
                break

            for vecino, arista in grafo.obtener_vecinos(actual):
                nuevo_costo = costo_actual + arista.distancia_km
                if nuevo_costo < costos.get(vecino, float("inf")):
                    costos[vecino] = nuevo_costo
                    padres[vecino] = actual
                    heapq.heappush(cola, (nuevo_costo, vecino))

        return _reconstruir_metricas(
            grafo, self.nombre(), origen, destino, padres, visitados, inicio_ns
        )


class RutaAStarTrafico(EstrategiaRuta):
    """Búsqueda informada A*: combina costo real con tráfico y heurística euclidiana admisible."""

    def codigo(self) -> str:
        return "astar"

    def nombre(self) -> str:
        return "A* Adaptativo (Tráfico + Heurística)"

    @staticmethod
    def _heuristica_min(grafo: GrafoUrbano, nodo: str, destino: str) -> float:
        # Tiempo mínimo teórico a 40 km/h en línea recta (flujo libre -> nunca sobreestima)
        return (grafo.distancia_euclidiana_km(nodo, destino) / 40.0) * 60.0

    def calcular(self, grafo: GrafoUrbano, origen: str, destino: str) -> ResultadoRuta:
        inicio_ns = time.perf_counter_ns()
        h_inicial = self._heuristica_min(grafo, origen, destino)
        cola: list[tuple[float, float, str]] = [(h_inicial, 0.0, origen)]
        g_score: dict[str, float] = {origen: 0.0}
        padres: dict[str, str | None] = {origen: None}
        cerrados: set[str] = set()
        visitados: list[str] = []

        while cola:
            _, g_actual, actual = heapq.heappop(cola)
            if actual in cerrados:
                continue
            cerrados.add(actual)
            visitados.append(actual)

            if actual == destino:
                break

            for vecino, arista in grafo.obtener_vecinos(actual):
                tentativo_g = g_actual + arista.tiempo_minutos()
                if tentativo_g < g_score.get(vecino, float("inf")):
                    g_score[vecino] = tentativo_g
                    padres[vecino] = actual
                    f_score = tentativo_g + self._heuristica_min(grafo, vecino, destino)
                    heapq.heappush(cola, (f_score, tentativo_g, vecino))

        return _reconstruir_metricas(
            grafo, self.nombre(), origen, destino, padres, visitados, inicio_ns
        )


FABRICA_ESTRATEGIAS: dict[str, EstrategiaRuta] = {
    "bfs": RutaBFSSimple(),
    "dijkstra": RutaDijkstraDistancia(),
    "astar": RutaAStarTrafico(),
}
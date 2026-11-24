import random

from app.domain.graph import GrafoUrbano
from app.domain.observer import EventoVial, MonitorTrafico, ObservadorTrafico
from app.domain.strategies import (
    FABRICA_ESTRATEGIAS,
    EstrategiaRuta,
    ResultadoRuta,
)


class MotorNavegacion(ObservadorTrafico):
    def __init__(self, grafo: GrafoUrbano, monitor: MonitorTrafico) -> None:
        self.grafo = grafo
        self.monitor = monitor
        self.estrategia_actual: EstrategiaRuta = FABRICA_ESTRATEGIAS["astar"]
        self.ruta_actual: ResultadoRuta | None = None
        self.recalculos_automaticos: int = 0
        self.eventos_ignorados: int = 0
        self.ultima_alerta_observer: dict | None = None
        self.monitor.suscribir(self)

    def set_estrategia(self, estrategia: EstrategiaRuta) -> None:
        self.estrategia_actual = estrategia

    def navegar(self, origen: str, destino: str) -> ResultadoRuta:
        self.ruta_actual = self.estrategia_actual.calcular(self.grafo, origen, destino)
        return self.ruta_actual

    def al_detectar_incidente(self, evento: EventoVial) -> dict:
        if not self.ruta_actual or not self.ruta_actual.encontrada:
            self.eventos_ignorados += 1
            self.ultima_alerta_observer = {
                "recalculado": False,
                "arista_id": evento.arista_id,
                "mensaje": f"Observer ({evento.timestamp}): incidente en {evento.arista_id} registrado sin ruta activa (0 recálculos).",
            }
            return self.ultima_alerta_observer

        afecta_ruta = evento.arista_id in self.ruta_actual.aristas_camino
        if not afecta_ruta:
            self.eventos_ignorados += 1
            self.ultima_alerta_observer = {
                "recalculado": False,
                "arista_id": evento.arista_id,
                "mensaje": (
                    f"Observer ({evento.timestamp}): tramo {evento.arista_id} está FUERA de la ruta activa. "
                    "Recálculo omitido (ahorro de CPU)."
                ),
            }
            return self.ultima_alerta_observer

        # La arista pertenece a la ruta vigente -> disparar recálculo automático
        origen = self.ruta_actual.origen
        destino = self.ruta_actual.destino
        nueva_ruta = self.estrategia_actual.calcular(self.grafo, origen, destino)
        self.ruta_actual = nueva_ruta
        self.recalculos_automaticos += 1

        tipo = "cierre vial" if evento.bloqueado else f"congestión {evento.factor_trafico}x"
        if nueva_ruta.encontrada:
            msg = (
                f"Observer ({evento.timestamp}): ¡{tipo} detectado en tramo activo {evento.arista_id}! "
                f"Desvío recalculado automáticamente en {nueva_ruta.tiempo_computo_ms:.4f} ms."
            )
        else:
            msg = (
                f"Observer ({evento.timestamp}): ¡{tipo} en {evento.arista_id} dejó el destino aislado sin ruta alterna!"
            )

        self.ultima_alerta_observer = {
            "recalculado": True,
            "arista_id": evento.arista_id,
            "tiempo_recalculo_ms": round(nueva_ruta.tiempo_computo_ms, 4),
            "mensaje": msg,
        }
        return self.ultima_alerta_observer

    def ejecutar_benchmark(self, iteraciones: int = 100) -> dict:
        rng = random.Random(42)
        nodos_ids = list(self.grafo.nodos.keys())

        # Selecciona 100 pares con separación espacial real (>= 3 km) para evaluar rutas representativas
        pares_validos = [
            (u, v)
            for u in nodos_ids
            for v in nodos_ids
            if u != v and self.grafo.distancia_euclidiana_km(u, v) >= 3.5
        ]
        muestra = [rng.choice(pares_validos) for _ in range(iteraciones)]

        resumen: list[dict] = []
        bfs_visitados_ref = 1.0

        for codigo in ("bfs", "dijkstra", "astar"):
            estrategia = FABRICA_ESTRATEGIAS[codigo]
            tot_visitados = 0
            tot_ms = 0.0
            tot_km = 0.0
            tot_min = 0.0
            exitosas = 0

            for origen, destino in muestra:
                res = estrategia.calcular(self.grafo, origen, destino)
                if res.encontrada:
                    exitosas += 1
                    tot_visitados += res.cantidad_visitados
                    tot_ms += res.tiempo_computo_ms
                    tot_km += res.distancia_km
                    tot_min += res.tiempo_min

            divisor = max(exitosas, 1)
            prom_visitados = tot_visitados / divisor
            if codigo == "bfs":
                bfs_visitados_ref = max(prom_visitados, 1e-9)

            reduccion_pct = ((bfs_visitados_ref - prom_visitados) / bfs_visitados_ref) * 100.0
            resumen.append(
                {
                    "codigo": codigo,
                    "estrategia": estrategia.nombre(),
                    "rutas_exitosas": exitosas,
                    "nodos_visitados_prom": round(prom_visitados, 2),
                    "reduccion_vs_bfs_pct": round(reduccion_pct, 1),
                    "tiempo_computo_ms_prom": round(tot_ms / divisor, 4),
                    "distancia_km_prom": round(tot_km / divisor, 2),
                    "tiempo_trayecto_min_prom": round(tot_min / divisor, 2),
                }
            )

        return {"iteraciones": iteraciones, "resultados": resumen}
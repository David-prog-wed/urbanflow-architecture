from dataclasses import dataclass
import math


@dataclass
class Nodo:
    id: str
    nombre: str
    x: float
    y: float


@dataclass
class Arista:
    id: str
    origen: str
    destino: str
    distancia_km: float
    factor_trafico: float = 1.0
    bloqueado: bool = False

    def tiempo_minutos(self, velocidad_base_kmh: float = 40.0) -> float:
        # Tiempo base a flujo libre (40 km/h -> 1.5 min/km) multiplicado por tráfico
        return (self.distancia_km / velocidad_base_kmh) * 60.0 * self.factor_trafico


class GrafoUrbano:
    # Escala espacial: 100 px en SVG = 2.0 km (1 px = 0.02 km)
    ESCALA_KM_POR_PX = 0.02

    def __init__(self) -> None:
        self.nodos: dict[str, Nodo] = {}
        self.aristas: dict[str, Arista] = {}
        self.adyacencia: dict[str, list[tuple[str, str]]] = {}
        self._cargar_red_urbana()

    def _cargar_red_urbana(self) -> None:
        sectores = [
            "Portal Norte", "Usaquén", "Cedritos", "Suba Centro", "Colina",
            "Calle 100", "Chicó", "Salitre Norte", "Engativá", "Álamos",
            "Chapinero", "Galerías", "Teusaquillo", "Modelia", "Fontibón",
            "Centro Int.", "Av. Jiménez", "Puente Aranda", "Américas", "Kennedy",
            "San Cristóbal", "Restrepo", "Venecia", "Tunal", "Usme Centro",
        ]

        # 25 nodos distribuidos en grilla 5x5 con coordenadas SVG limpias
        idx = 0
        for fila in range(5):
            for col in range(5):
                nodo_id = f"N{idx + 1:02d}"
                x = 90.0 + col * 165.0
                y = 65.0 + fila * 98.0
                self.agregar_nodo(Nodo(id=nodo_id, nombre=sectores[idx], x=x, y=y))
                idx += 1

        # Congestión base realista en corredores céntricos (simula hora pico)
        trafico_inicial = {
            ("N07", "N08"): 2.6,
            ("N08", "N09"): 2.4,
            ("N12", "N13"): 3.2,
            ("N13", "N14"): 2.9,
            ("N08", "N13"): 3.1,
            ("N13", "N18"): 3.0,
            ("N11", "N12"): 2.2,
            ("N17", "N18"): 2.5,
            ("N18", "N19"): 2.7,
            ("N07", "N12"): 2.3,
            ("N09", "N14"): 2.1,
            ("N12", "N17"): 2.4,
        }

        edge_num = 1

        def crear_arista(u: str, v: str, curvatura: float = 1.08) -> None:
            nonlocal edge_num
            dist = round(self.distancia_euclidiana_km(u, v) * curvatura, 2)
            factor = trafico_inicial.get((u, v), trafico_inicial.get((v, u), 1.0))
            arista = Arista(
                id=f"E{edge_num:02d}",
                origen=u,
                destino=v,
                distancia_km=dist,
                factor_trafico=factor,
                bloqueado=False,
            )
            self.agregar_arista(arista)
            edge_num += 1

        # 20 aristas horizontales
        for fila in range(5):
            for col in range(4):
                u = f"N{fila * 5 + col + 1:02d}"
                v = f"N{fila * 5 + col + 2:02d}"
                crear_arista(u, v, curvatura=1.06)

        # 20 aristas verticales
        for fila in range(4):
            for col in range(5):
                u = f"N{fila * 5 + col + 1:02d}"
                v = f"N{(fila + 1) * 5 + col + 1:02d}"
                crear_arista(u, v, curvatura=1.08)

        # 2 corredores diagonales expresos (total = 42 tramos bidireccionales)
        crear_arista("N07", "N13", curvatura=1.05)
        crear_arista("N13", "N19", curvatura=1.05)

    def agregar_nodo(self, nodo: Nodo) -> None:
        self.nodos[nodo.id] = nodo
        self.adyacencia.setdefault(nodo.id, [])

    def agregar_arista(self, arista: Arista) -> None:
        self.aristas[arista.id] = arista
        self.adyacencia[arista.origen].append((arista.destino, arista.id))
        self.adyacencia[arista.destino].append((arista.origen, arista.id))

    def distancia_euclidiana_km(self, u: str, v: str) -> float:
        n1, n2 = self.nodos[u], self.nodos[v]
        return math.hypot(n1.x - n2.x, n1.y - n2.y) * self.ESCALA_KM_POR_PX

    def obtener_vecinos(self, nodo_id: str) -> list[tuple[str, Arista]]:
        resultado: list[tuple[str, Arista]] = []
        for vecino_id, arista_id in self.adyacencia.get(nodo_id, []):
            arista = self.aristas[arista_id]
            if not arista.bloqueado:
                resultado.append((vecino_id, arista))
        return resultado

    def buscar_arista_entre(self, u: str, v: str) -> Arista | None:
        for vecino_id, arista_id in self.adyacencia.get(u, []):
            if vecino_id == v:
                return self.aristas[arista_id]
        return None

    def actualizar_arista(self, arista_id: str, factor_trafico: float, bloqueado: bool) -> Arista:
        if arista_id not in self.aristas:
            raise ValueError(f"Arista no encontrada: {arista_id}")
        arista = self.aristas[arista_id]
        arista.factor_trafico = factor_trafico
        arista.bloqueado = bloqueado
        return arista

    def reiniciar(self) -> None:
        self.nodos.clear()
        self.aristas.clear()
        self.adyacencia.clear()
        self._cargar_red_urbana()

    def serializar(self) -> dict:
        return {
            "nodos": [
                {"id": n.id, "nombre": n.nombre, "x": n.x, "y": n.y}
                for n in self.nodos.values()
            ],
            "aristas": [
                {
                    "id": a.id,
                    "origen": a.origen,
                    "destino": a.destino,
                    "distancia_km": a.distancia_km,
                    "factor_trafico": a.factor_trafico,
                    "bloqueado": a.bloqueado,
                    "tiempo_min": round(a.tiempo_minutos(), 2),
                }
                for a in self.aristas.values()
            ],
        }
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.domain.commands import (
    CalcularRutaCommand,
    GestorComandos,
    SimularIncidenteCommand,
)
from app.domain.graph import GrafoUrbano
from app.domain.observer import MonitorTrafico
from app.domain.strategies import FABRICA_ESTRATEGIAS
from app.engine import MotorNavegacion

app = FastAPI(
    title="UrbanFlow - Navegación Adaptativa",
    version="1.0.0",
    description="Prototipo arquitectónico con patrones Strategy, Observer y Command.",
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

grafo = GrafoUrbano()
monitor = MonitorTrafico()
motor = MotorNavegacion(grafo=grafo, monitor=monitor)
gestor_comandos = GestorComandos()

# Ruta inicial demostrativa al arrancar el servicio
gestor_comandos.ejecutar(CalcularRutaCommand(motor, "N01", "N25", "astar"))


class RouteRequest(BaseModel):
    origen: str
    destino: str
    estrategia: str = Field(default="astar", pattern="^(bfs|dijkstra|astar)$")


class IncidentRequest(BaseModel):
    arista_id: str
    factor_trafico: float = Field(default=3.2, ge=1.0, le=6.0)
    bloqueado: bool = False


def _estado_completo() -> dict:
    return {
        "grafo": grafo.serializar(),
        "estrategia_actual": motor.estrategia_actual.codigo(),
        "ruta_actual": motor.ruta_actual.to_dict() if motor.ruta_actual else None,
        "recalculos_automaticos": motor.recalculos_automaticos,
        "eventos_ignorados": motor.eventos_ignorados,
        "ultima_alerta_observer": motor.ultima_alerta_observer,
        "historial_comandos": gestor_comandos.listar_historial(),
    }


@app.get("/", include_in_schema=False)
def servir_frontend() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health_check() -> dict:
    return {"status": "ok", "service": "urbanflow", "nodos": len(grafo.nodos), "aristas": len(grafo.aristas)}


@app.get("/api/state")
def obtener_estado() -> dict:
    return _estado_completo()


@app.post("/api/route")
def calcular_ruta(req: RouteRequest) -> dict:
    if req.origen not in grafo.nodos or req.destino not in grafo.nodos:
        raise HTTPException(status_code=400, detail="Nodo de origen o destino inválido.")
    if req.estrategia not in FABRICA_ESTRATEGIAS:
        raise HTTPException(status_code=400, detail="Estrategia no soportada.")

    cmd = CalcularRutaCommand(motor, req.origen, req.destino, req.estrategia)
    gestor_comandos.ejecutar(cmd)
    return _estado_completo()


@app.post("/api/incident")
def simular_incidente(req: IncidentRequest) -> dict:
    if req.arista_id not in grafo.aristas:
        raise HTTPException(status_code=404, detail="Tramo vial no encontrado.")

    cmd = SimularIncidenteCommand(
        grafo=grafo,
        monitor=monitor,
        motor=motor,
        arista_id=req.arista_id,
        factor_trafico=req.factor_trafico,
        bloqueado=req.bloqueado,
    )
    gestor_comandos.ejecutar(cmd)
    return _estado_completo()


@app.post("/api/undo")
def deshacer_comando() -> dict:
    res = gestor_comandos.deshacer_ultimo()
    return {"undo": res, **_estado_completo()}


@app.post("/api/reset")
def reiniciar_simulacion() -> dict:
    grafo.reiniciar()
    gestor_comandos.limpiar()
    motor.recalculos_automaticos = 0
    motor.eventos_ignorados = 0
    motor.ultima_alerta_observer = None
    gestor_comandos.ejecutar(CalcularRutaCommand(motor, "N01", "N25", "astar"))
    return _estado_completo()


@app.get("/api/benchmark")
def ejecutar_benchmark(iteraciones: int = 100) -> dict:
    iteraciones = max(10, min(iteraciones, 500))
    return motor.ejecutar_benchmark(iteraciones=iteraciones)
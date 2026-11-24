from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from app.domain.graph import GrafoUrbano
from app.domain.observer import EventoVial, MonitorTrafico
from app.domain.strategies import FABRICA_ESTRATEGIAS, ResultadoRuta

if TYPE_CHECKING:
    from app.engine import MotorNavegacion


class ComandoNavegacion(ABC):
    @abstractmethod
    def descripcion(self) -> str:
        pass

    @abstractmethod
    def ejecutar(self) -> dict:
        pass

    @abstractmethod
    def deshacer(self) -> dict:
        pass


class CalcularRutaCommand(ComandoNavegacion):
    def __init__(
        self,
        motor: "MotorNavegacion",
        origen: str,
        destino: str,
        estrategia_codigo: str,
    ) -> None:
        self._motor = motor
        self._origen = origen
        self._destino = destino
        self._estrategia_codigo = estrategia_codigo
        self._ruta_previa: ResultadoRuta | None = None
        self._estrategia_previa: str = motor.estrategia_actual.codigo()

    def descripcion(self) -> str:
        return f"Calcular ruta {self._origen} → {self._destino} ({self._estrategia_codigo.upper()})"

    def ejecutar(self) -> dict:
        self._ruta_previa = self._motor.ruta_actual
        self._estrategia_previa = self._motor.estrategia_actual.codigo()
        self._motor.set_estrategia(FABRICA_ESTRATEGIAS[self._estrategia_codigo])
        resultado = self._motor.navegar(self._origen, self._destino)
        return {"accion": self.descripcion(), "ruta": resultado.to_dict()}

    def deshacer(self) -> dict:
        self._motor.set_estrategia(FABRICA_ESTRATEGIAS[self._estrategia_previa])
        self._motor.ruta_actual = self._ruta_previa
        return {
            "accion": f"Deshacer: {self.descripcion()}",
            "ruta": self._ruta_previa.to_dict() if self._ruta_previa else None,
        }


class SimularIncidenteCommand(ComandoNavegacion):
    def __init__(
        self,
        grafo: GrafoUrbano,
        monitor: MonitorTrafico,
        motor: "MotorNavegacion",
        arista_id: str,
        factor_trafico: float,
        bloqueado: bool,
    ) -> None:
        self._grafo = grafo
        self._monitor = monitor
        self._motor = motor
        self._arista_id = arista_id
        self._nuevo_factor = factor_trafico
        self._nuevo_bloqueado = bloqueado
        self._factor_anterior = 1.0
        self._bloqueado_anterior = False
        self._ruta_previa: ResultadoRuta | None = None

    def descripcion(self) -> str:
        estado = "CIERRE TOTAL" if self._nuevo_bloqueado else f"Tráfico {self._nuevo_factor}x"
        return f"Incidente en {self._arista_id}: {estado}"

    def ejecutar(self) -> dict:
        arista = self._grafo.aristas[self._arista_id]
        self._factor_anterior = arista.factor_trafico
        self._bloqueado_anterior = arista.bloqueado
        self._ruta_previa = self._motor.ruta_actual

        self._grafo.actualizar_arista(
            self._arista_id, self._nuevo_factor, self._nuevo_bloqueado
        )
        evento = EventoVial(
            arista_id=arista.id,
            origen=arista.origen,
            destino=arista.destino,
            factor_trafico=arista.factor_trafico,
            bloqueado=arista.bloqueado,
        )
        notificaciones = self._monitor.notificar(evento)
        return {
            "accion": self.descripcion(),
            "observer": notificaciones[0] if notificaciones else None,
        }

    def deshacer(self) -> dict:
        self._grafo.actualizar_arista(
            self._arista_id, self._factor_anterior, self._bloqueado_anterior
        )
        # Restaura la ruta anterior o recalcula sobre el grafo restaurado
        self._motor.ruta_actual = self._ruta_previa
        self._motor.ultima_alerta_observer = {
            "recalculado": False,
            "mensaje": f"Command Undo: tramo {self._arista_id} restaurado (factor {self._factor_anterior}x, bloqueado={self._bloqueado_anterior}).",
        }
        return {
            "accion": f"Deshacer: {self.descripcion()}",
            "ruta": self._ruta_previa.to_dict() if self._ruta_previa else None,
        }


class GestorComandos:
    def __init__(self) -> None:
        self._historial: list[ComandoNavegacion] = []

    def ejecutar(self, comando: ComandoNavegacion) -> dict:
        res = comando.ejecutar()
        self._historial.append(comando)
        return res

    def deshacer_ultimo(self) -> dict:
        if not self._historial:
            return {"deshecho": False, "mensaje": "No hay comandos pendientes por deshacer."}
        ultimo = self._historial.pop()
        res = ultimo.deshacer()
        return {"deshecho": True, **res}

    def listar_historial(self) -> list[str]:
        return [cmd.descripcion() for cmd in reversed(self._historial[-15:])]

    def limpiar(self) -> None:
        self._historial.clear()
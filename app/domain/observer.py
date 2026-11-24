from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class EventoVial:
    arista_id: str
    origen: str
    destino: str
    factor_trafico: float
    bloqueado: bool
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%H:%M:%S")


class ObservadorTrafico(ABC):
    @abstractmethod
    def al_detectar_incidente(self, evento: EventoVial) -> dict:
        pass


class MonitorTrafico:
    def __init__(self) -> None:
        self._observadores: list[ObservadorTrafico] = []

    def suscribir(self, observador: ObservadorTrafico) -> None:
        if observador not in self._observadores:
            self._observadores.append(observador)

    def desuscribir(self, observador: ObservadorTrafico) -> None:
        if observador in self._observadores:
            self._observadores.remove(observador)

    def notificar(self, evento: EventoVial) -> list[dict]:
        respuestas: list[dict] = []
        for observador in self._observadores:
            respuestas.append(observador.al_detectar_incidente(evento))
        return respuestas
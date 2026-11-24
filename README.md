# 🗺️ UrbanFlow — Motor de Navegación Urbana Adaptativa

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-HTTPS%20TLS-009639?style=flat&logo=nginx&logoColor=white)

**UrbanFlow** es un prototipo arquitectónico de navegación urbana adaptativa en tiempo real, desarrollado para la **Actividad 6 (_Navegando mareas: Estrategias de navegación en la arquitectura de software_)** de la asignatura _Arquitectura de Software_.

El sistema modela una red vial urbana de **25 intersecciones y 42 tramos bidireccionales** con congestión dinámica, permitiendo comparar algoritmos de búsqueda sobre grafos, inyectar cierres viales con recálculo reactivo selectivo y revertir operaciones de estado.

🌐 **Demo en producción (VPS Contabo):** [https://urbanflow.decg3.com](https://urbanflow.decg3.com)

---

## 🎯 Problema Abordado

Los sistemas de ruteo tradicionales suelen acoplar sus algoritmos mediante bloques condicionales rígidos, recurrir a búsquedas no informadas que exploran nodos innecesarios y carecer de respuesta selectiva ante incidentes viales. **UrbanFlow** resuelve estos cuellos de botella combinando búsqueda heurística informada (**A\***) con tres patrones de diseño de comportamiento del catálogo GoF.

---

## 🧩 Patrones de Diseño Implementados

| Patrón       | Módulo                     | Responsabilidad en UrbanFlow                                                                                                                                      |
| :----------- | :------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Strategy** | `app/domain/strategies.py` | Encapsula e intercambia en caliente las políticas de ruteo (`RutaBFSSimple`, `RutaDijkstraDistancia` y `RutaAStarTrafico`) sin modificar `MotorNavegacion` (OCP). |
| **Observer** | `app/domain/observer.py`   | `MonitorTrafico` notifica eventos viales a `MotorNavegacion`, que aplica **recálculo selectivo**: solo recalcula si el tramo afectado pertenece a la ruta activa. |
| **Command**  | `app/domain/commands.py`   | Encapsula cálculos e incidentes (`CalcularRutaCommand`, `SimularIncidenteCommand`) bajo `GestorComandos` con historial auditable y reversión exacta (`Undo`).     |

---

## 📂 Estructura del Proyecto

```text
urbanflow-architecture/
├── app/
│   ├── __init__.py
│   ├── engine.py              # MotorNavegacion (Observer) y servicio de Benchmark (100 rutas)
│   ├── main.py                # API REST en FastAPI y entrega de interfaz web
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── graph.py           # GrafoUrbano, Nodo, Arista (25 nodos, 42 tramos)
│   │   ├── strategies.py      # Patrón Strategy: BFS, Dijkstra y A*
│   │   ├── observer.py        # Patrón Observer: MonitorTrafico y EventoVial
│   │   └── commands.py        # Patrón Command: historial y reversión (Undo)
│   └── static/
│       └── index.html         # Interfaz interactiva SVG, simulador y tabla de benchmark
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🛠️ Stack Tecnológico

- **Backend:** Python 3.11, FastAPI, Uvicorn, Pydantic.
- **Frontend:** HTML5, CSS3, JavaScript Vanilla y renderizado vectorial **SVG** (sin dependencias externas).
- **Infraestructura:** Docker, Docker Compose, Nginx Reverse Proxy y certificados TLS (Certbot / Let's Encrypt) sobre VPS Linux en Contabo (`urbanflow.decg3.com`).

---

## 🔌 Endpoints de la API REST

| Método | Ruta                             | Descripción                                                                                                   |
| :----- | :------------------------------- | :------------------------------------------------------------------------------------------------------------ |
| `GET`  | `/`                              | Sirve la interfaz web interactiva en SVG.                                                                     |
| `GET`  | `/api/health`                    | Verificación de estado del servicio, total de nodos y aristas.                                                |
| `GET`  | `/api/state`                     | Retorna el estado completo del grafo, ruta vigente, alertas y comandos.                                       |
| `POST` | `/api/route`                     | Ejecuta `CalcularRutaCommand` (`origen`, `destino`, `estrategia`: `bfs` \| `dijkstra` \| `astar`).            |
| `POST` | `/api/incident`                  | Ejecuta `SimularIncidenteCommand` (`arista_id`, `factor_trafico`, `bloqueado`) y notifica a `MonitorTrafico`. |
| `POST` | `/api/undo`                      | Revierte el último comando en la pila de `GestorComandos`.                                                    |
| `POST` | `/api/reset`                     | Restaura la red vial, el historial y las métricas a su estado inicial.                                        |
| `GET`  | `/api/benchmark?iteraciones=100` | Ejecuta el benchmark comparativo entre BFS, Dijkstra y A\* sobre 100 pares aleatorios.                        |

---

## 🚀 Ejecución Local

```bash
# 1. Clonar el repositorio
git clone [https://github.com/David-prog-wed/urbanflow-architecture.git](https://github.com/David-prog-wed/urbanflow-architecture.git)
cd urbanflow-architecture

# 2. Crear y activar entorno virtual
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# 3. Instalar dependencias y levantar el servidor
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Abre en tu navegador: `http://127.0.0.1:8000` (documentación Swagger en `http://127.0.0.1:8000/docs`).

---

## 🐳 Despliegue en Producción (Docker + Nginx)

El servicio se publica enlazado únicamente a `127.0.0.1:8085` dentro del host Linux para exponerlo de forma segura mediante Nginx con HTTPS:

```bash
docker compose up -d --build
```

Verificación rápida del contenedor:

```bash
docker ps --filter "name=urbanflow-app"
curl [http://127.0.0.1:8085/api/health](http://127.0.0.1:8085/api/health)
```

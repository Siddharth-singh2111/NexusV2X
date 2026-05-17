# 🚗 NexusV2X: Real-Time Telemetry & Collision Engine

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Next.js](https://img.shields.io/badge/Next.js-14%2B-black.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)

NexusV2X is a highly scalable, real-time Vehicle-to-Everything (V2X) telemetry and collision detection engine. It ingests simulated vehicle telemetry, smooths noisy sensor data, detects potential collisions in real-time, and visualizes the traffic conditions on a high-performance web dashboard.

---

## ✨ Features

- **SUMO Traffic Simulation:** Simulates realistic vehicular movement, generating raw GPS coordinates.
- **Sensor Noise Injection:** Applies Rayleigh Fading logic to simulate real-world wireless and GPS inaccuracies.
- **Kalman Filtering:** Smooths out noisy GPS  into telemetery data in the backend to calculate precise vehicle trajectories.
- **Real-Time Crash Detection:** Utilizes **Redis Geospatial (GEO)** indexing to detect vehicles coming within a 1.5-meter radius of one another.
- **High-Throughput Streaming:** Uses **Apache Kafka** to handle massive volumes of incoming telemetry data asynchronously.
- **Premium Visualization:** A Next.js 3D web dashboard powered by **Deck.GL**, featuring dynamic heatmaps, vehicle scatterplots, and pulse animations for collision alerts.
- **Fully Dockerized:** Spin up the entire infrastructure (Zookeeper, Kafka, Redis, Backend, Frontend) using a single Docker Compose command.

---

## 🏗️ Architecture Stack

* **Simulator:** SUMO (Simulation of Urban MObility), Python (TraCI)
* **Message Broker:** Apache Kafka & Zookeeper
* **In-Memory Datastore:** Redis
* **Backend:** FastAPI, Python, WebSockets, NumPy (Kalman Filter)
* **Frontend:** Next.js, React, TailwindCSS, Deck.GL, MapLibre

---

## 🚀 Getting Started

### Prerequisites
1. **Docker & Docker Compose** installed.
2. **SUMO** (Simulation of Urban MObility) installed on your host machine to run the simulator.
3. **Python 3.10+** (if running the simulator locally).

### 1. Start the Infrastructure (Docker)
The entire backend and frontend stack is dockerized. Start the services by running:
```bash
docker-compose up -d --build
```
This command spins up:
- **Zookeeper** (Port 2181)
- **Kafka** (Port 9092 for Host, 29092 for internal network)
- **Redis** (Port 6379)
- **FastAPI Backend** (Port 8000)
- **Next.js Dashboard** (Port 3000)

### 2. View the Dashboard
Once the containers are running, navigate to:
👉 **[http://localhost:3000](http://localhost:3000)**

You should see the "V2X Telemetry Engine" HUD, though the active vehicles count will be 0 until the simulator is started.

### 3. Run the Traffic Simulator
On your host machine, install the python requirements for the simulator:
```bash
pip install -r requirements.txt
```
Make sure your `SUMO_HOME` environment variable is set. Then, run the simulator:
```bash
python simulator.py
```
*(As the simulator runs, vehicles will begin populating the dashboard and the heatmap will activate).*

---

## ⚙️ Configuration & Environment Variables

### Deploying to Production / Cloud
When deploying to a remote server, you can customize the environment variables to ensure proper networking.

**Simulator (`simulator.py`)**
- `KAFKA_BROKER`: Set this to your server's IP (e.g., `192.168.1.50:9092`). Defaults to `localhost:9092`.
- `HEADLESS=1`: Run `python simulator.py` with `HEADLESS=1` to run the simulator without the graphical `sumo-gui` interface (perfect for CI/CD or cloud VPS environments).

**Frontend Dashboard**
- `NEXT_PUBLIC_WS_URL`: Change this in your `docker-compose.yml` to point to the server's public IP address (e.g., `ws://your-domain.com:8000/ws/telemetry`) so the client browser knows where to connect.

---

## 🛠️ Testing

A quick consumer script is provided to verify that Kafka is successfully receiving messages from the simulator.
```bash
python test_consumer.py
```

---

## 📝 License
This project is licensed under the MIT License.

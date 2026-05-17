import json
import asyncio
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import os
# pyrefly: ignore [missing-import]
import redis.asyncio as redis
# pyrefly: ignore [missing-import]
from aiokafka import AIOKafkaConsumer
from contextlib import asynccontextmanager


class KalmanFilter2D:
    def __init__(self, dt=0.1):
        self.dt = dt
        # State vector: [lon, lat, v_lon, v_lat]
        self.x = np.zeros((4, 1)) 
        self.P = np.eye(4) # Covariance matrix
        
        # State Transition Matrix
        self.F = np.array([[1, 0, dt, 0],
                           [0, 1, 0, dt],
                           [0, 0, 1, 0],
                           [0, 0, 0, 1]])
        # Measurement Function
        self.H = np.array([[1, 0, 0, 0],
                           [0, 1, 0, 0]])
        
        # Measurement Noise (R) and Process Noise (Q)
        self.R = np.eye(2) * 0.0001 
        self.Q = np.eye(4) * 0.00001

    def process(self, z_lon, z_lat):
        # Predict
        self.x = np.dot(self.F, self.x)
        self.P = np.dot(np.dot(self.F, self.P), self.F.T) + self.Q
        
        # Update
        z = np.array([[z_lon], [z_lat]])
        S = np.dot(self.H, np.dot(self.P, self.H.T)) + self.R
        K = np.dot(np.dot(self.P, self.H.T), np.linalg.inv(S))
        y = z - np.dot(self.H, self.x)
        self.x = self.x + np.dot(K, y)
        self.P = self.P - np.dot(K, np.dot(self.H, self.P))
        
        return self.x[0, 0], self.x[1, 0] # Return smoothed Lon, Lat

# ==========================================
# 2. GLOBAL STATE & CONNECTIONS
# ==========================================
# Dictionary to hold a Kalman filter for EVERY vehicle
vehicle_filters = {}

# Connect to the Dockerized Redis
redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_port = int(os.environ.get('REDIS_PORT', 6379))
redis_client = redis.Redis(host=redis_host, port=redis_port, db=0)
# ==========================================
# 2.5 WEBSOCKET CONNECTION MANAGER
# ==========================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass # Ignore dropped connections

manager = ConnectionManager()


async def consume_kafka():
    kafka_broker = os.environ.get('KAFKA_BROKER', 'localhost:9092')
    consumer = AIOKafkaConsumer(
        'v2x-telemetry',
        bootstrap_servers=kafka_broker,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='latest'
    )
    
    while True:
        try:
            await consumer.start()
            break
        except Exception as e:
            print(f"Waiting for Kafka to be ready... ({e})")
            await asyncio.sleep(5)
    print("DEBUG: FastAPI Backend listening for telemetry and crashes...")
    
    try:
        async for msg in consumer:
            try:
                data = msg.value
                v_id = data['vehicle_id']
                noisy_lon = data['noisy_pos']['lon']
                noisy_lat = data['noisy_pos']['lat']
                
                # 1. Kalman Filter
                if v_id not in vehicle_filters:
                    vehicle_filters[v_id] = KalmanFilter2D(dt=0.1)
                    vehicle_filters[v_id].x[0, 0] = noisy_lon
                    vehicle_filters[v_id].x[1, 0] = noisy_lat
                    
                kf = vehicle_filters[v_id]
                smooth_lon, smooth_lat = kf.process(noisy_lon, noisy_lat)
                
                # 2. Write to Redis
                await redis_client.execute_command(
                    "GEOADD", "vehicle_locations", 
                    float(smooth_lon), float(smooth_lat), str(v_id)
                )
                
                # --- NEW: 3. Instant Crash Detection via Redis ---
                # Find all vehicles within 5 meters of this car
                nearby = await redis_client.geosearch(
                    "vehicle_locations",
                    member=str(v_id),
                    radius=1.5,
                    unit="m"
                )
                
                # Redis returns byte strings, so we decode them
                nearby_ids = [vid.decode('utf-8') for vid in nearby]
                
                # If there is more than 1 vehicle in that 5m radius (itself + another), it's a crash!
                if len(nearby_ids) > 1:
                    for other_vid in nearby_ids:
                        if other_vid != str(v_id):
                            print(f"⚠️ CRASH DETECTED: {v_id} and {other_vid}")
                            crash_payload = json.dumps({
                                "type": "CRASH",
                                "id": f"{v_id}-{other_vid}",
                                "lon": smooth_lon,
                                "lat": smooth_lat
                            })
                            await manager.broadcast(crash_payload)

                # 4. Broadcast Normal Movement Update
                ws_payload = json.dumps({
                    "type": "UPDATE", 
                    "id": v_id, 
                    "lon": smooth_lon, 
                    "lat": smooth_lat
                })
                await manager.broadcast(ws_payload)

            except Exception as e:
                print(f"WORKER ERROR: {e}")

    finally:
        await consumer.stop()
# ==========================================
# 4. FASTAPI APPLICATION SETUP
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the Kafka consumer in the background when the server boots
    task = asyncio.create_task(consume_kafka())
    yield
    task.cancel() # Clean up when the server shuts down

app = FastAPI(lifespan=lifespan, title="V2X Telemetry Engine")
@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection open, waiting for client messages if needed
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
# A quick API endpoint to check Redis data
@app.get("/api/vehicles/count")
async def get_vehicle_count():
    count = await redis_client.zcard("vehicle_locations")
    return {"total_active_vehicles_in_redis": count}
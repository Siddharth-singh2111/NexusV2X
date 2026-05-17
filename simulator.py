import os
import sys
import traci
import json
import time
import numpy as np
from kafka import KafkaProducer

# 1. Environment Setup
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME'")

if os.environ.get('HEADLESS', '0') == '1':
    sumoCmd = ["sumo", "-c", "sumo_config.sumocfg"]
else:
    sumoCmd = ["sumo-gui", "-c", "sumo_config.sumocfg"]

# 2. Wireless Noise Logic (Rayleigh Fading)
def apply_wireless_noise(lon, lat):
    sigma = 0.5 
    x_noise = np.random.normal(0, sigma)
    y_noise = np.random.normal(0, sigma)
    fading_amplitude = np.sqrt(x_noise**2 + y_noise**2)
    
    # Error increases as fading amplitude decreases
    error_scale = 0.0001 / (fading_amplitude + 0.1) 
    
    noisy_lat = lat + np.random.normal(0, error_scale)
    noisy_lon = lon + np.random.normal(0, error_scale)
    
    return noisy_lon, noisy_lat

# 3. Kafka Producer Initialization
kafka_broker = os.environ.get('KAFKA_BROKER', 'localhost:9092')
producer = KafkaProducer(
    bootstrap_servers=[kafka_broker],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# 4. Main Simulation Logic
def run_simulation():
    traci.start(sumoCmd)
    step = 0
    
    print("Simulation started. Sending data to Kafka...")
    
    try:
        while step < 1000:
            traci.simulationStep() 
            vehicle_ids = traci.vehicle.getIDList()
            
            for v_id in vehicle_ids:
                # --- DATA EXTRACTION (This was missing in your 2nd version) ---
                x, y = traci.vehicle.getPosition(v_id)
                speed = traci.vehicle.getSpeed(v_id)
                heading = traci.vehicle.getAngle(v_id)
                
                # Convert grid to Geo
                lon, lat = traci.simulation.convertGeo(x, y)
                
                # Apply noise
                noisy_lon, noisy_lat = apply_wireless_noise(lon, lat)
                
                # Construct Payload
                payload = {
                    "vehicle_id": v_id,
                    "timestamp": time.time(),
                    "true_pos": {"lat": lat, "lon": lon},
                    "noisy_pos": {"lat": noisy_lat, "lon": noisy_lon},
                    "velocity": speed,
                    "heading": heading
                }
                
                # Send to Kafka
                producer.send('v2x-telemetry', payload)
                
            if step % 10 == 0: # Print every 10 steps to keep terminal clean
                print(f"Tick {step}: Sent data for {len(vehicle_ids)} vehicles.")
                
            step += 1
            time.sleep(0.1) 

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Closing connections...")
        traci.close()
        producer.flush() # Ensure all messages are sent
        producer.close()

if __name__ == "__main__":
    run_simulation()
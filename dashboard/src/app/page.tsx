"use client";

import { useState, useEffect } from "react";
import DeckGL from "@deck.gl/react";
import { ScatterplotLayer } from "@deck.gl/layers";
import { HeatmapLayer } from "@deck.gl/aggregation-layers"; // <-- NEW IMPORT
import Map from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";

const INITIAL_VIEW_STATE = {
  longitude: 80.0,
  latitude: 13.52,
  zoom: 13.5,
  pitch: 45,
  bearing: 0,
};

export default function Dashboard() {
  const [vehicles, setVehicles] = useState<{ [id: string]: number[] }>({});
  const [crashes, setCrashes] = useState<{ [id: string]: number[] }>({});

  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/telemetry";
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);
    ws.onerror = () => setIsConnected(false);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === "UPDATE") {
        setVehicles((prev) => ({
          ...prev,
          [data.id]: [data.lon, data.lat],
        }));
      } else if (data.type === "CRASH") {
        setCrashes((prev) => ({
          ...prev,
          [data.id]: [data.lon, data.lat],
        }));
        
        setTimeout(() => {
          setCrashes((prev) => {
            const newCrashes = { ...prev };
            delete newCrashes[data.id];
            return newCrashes;
          });
        }, 3000);
      }
    };

    return () => ws.close();
  }, []);

  const vehicleArray = Object.keys(vehicles).map((id) => ({
    id, position: vehicles[id],
  }));
  
  const crashArray = Object.keys(crashes).map((id) => ({
    id, position: crashes[id],
  }));

  // --- NEW: WE ENHANCED THE LAYERS ARRAY ---
  const layers = [
    // 1. The Heatmap (Rendered on the bottom)
    new HeatmapLayer({
      id: "heatmap-layer",
      data: vehicleArray,
      getPosition: (d: any) => d.position,
      getWeight: () => 1, // Each car has equal weight
      radiusPixels: 60, // How wide the heat spreads
      intensity: 1.5,
      threshold: 0.1,
      colorRange: [
        [0, 0, 0, 0],       // Transparent where there are no cars
        [15, 60, 255, 100], // Cool blue for low traffic
        [255, 255, 0, 150], // Yellow for medium traffic
        [255, 0, 0, 200]    // Deep red for heavy congestion
      ]
    }),

    // 2. Standard Vehicles (Rendered above the heatmap)
    new ScatterplotLayer({
      id: "vehicle-layer",
      data: vehicleArray,
      getPosition: (d: any) => d.position,
      getFillColor: [0, 255, 128],
      getRadius: 10,
      radiusMinPixels: 4,
      radiusMaxPixels: 15,
      transitions: { getPosition: 100 },
    }),

    // 3. Crashes (Rendered on top of everything)
    new ScatterplotLayer({
      id: "crash-layer",
      data: crashArray,
      getPosition: (d: any) => d.position,
      getFillColor: [255, 0, 0, 200],
      getRadius: 50,
      radiusMinPixels: 15,
      radiusMaxPixels: 50,
    }),
  ];

  return (
    <div className="w-screen h-screen bg-black relative font-sans overflow-hidden">
      <div className="absolute top-0 left-0 w-full p-6 z-10 pointer-events-none flex justify-between items-start">
        <div className="bg-black/40 backdrop-blur-md border border-white/10 p-6 rounded-2xl shadow-2xl">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent tracking-widest drop-shadow-sm mb-4">
            V2X TELEMETRY ENGINE
          </h1>
          
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between bg-white/5 rounded-lg px-4 py-3 border border-white/5">
              <span className="text-gray-400 text-sm font-semibold tracking-wide uppercase">Active Vehicles</span>
              <span className="text-emerald-400 font-mono text-xl font-bold ml-6">
                {vehicleArray.length}
              </span>
            </div>
            
            <div className={`flex items-center justify-between rounded-lg px-4 py-3 border transition-colors duration-500 ${crashArray.length > 0 ? 'bg-red-500/20 border-red-500/50 shadow-[0_0_15px_rgba(239,68,68,0.3)] animate-pulse' : 'bg-white/5 border-white/5'}`}>
              <span className="text-gray-400 text-sm font-semibold tracking-wide uppercase">Recent Collisions</span>
              <span className={`font-mono text-xl font-bold ml-6 ${crashArray.length > 0 ? 'text-red-400' : 'text-gray-500'}`}>
                {crashArray.length}
              </span>
            </div>
          </div>
        </div>
        
        <div className="flex flex-col gap-2 items-end">
          <div className="flex items-center gap-2 bg-emerald-900/30 border border-emerald-500/50 text-emerald-400 px-4 py-2.5 rounded-full font-mono text-sm tracking-wider shadow-[0_0_20px_rgba(16,185,129,0.2)] backdrop-blur-md">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></div>
            HEATMAP ONLINE
          </div>
          
          <div className={`flex items-center gap-2 px-3 py-1 rounded-full font-mono text-xs tracking-wider backdrop-blur-md border ${isConnected ? 'bg-green-900/30 border-green-500/50 text-green-400' : 'bg-red-900/30 border-red-500/50 text-red-400'}`}>
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400 animate-pulse'}`}></div>
            {isConnected ? 'BACKEND CONNECTED' : 'DISCONNECTED'}
          </div>
        </div>
      </div>

      <DeckGL initialViewState={INITIAL_VIEW_STATE} controller={true} layers={layers}>
        <Map mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json" />
      </DeckGL>
    </div>
  );
}
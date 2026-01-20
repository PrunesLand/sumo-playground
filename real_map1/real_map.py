import os
import sys
import time

# --- 1. SETUP ENVIRONMENT ---
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME'")

try:
    import libsumo as traci
except ImportError:
    sys.exit("Could not import libsumo.")

# --- 2. CONFIGURATION ---
CONFIG_FILE = "real_map.sumocfg"
SIMULATION_STEPS = 1000

def run_simulation(config_file):
    sumo_args = [
        "sumo",
        "-c", config_file,
        "--no-step-log", "true",
        "--duration-log.disable", "true",
        # REMOVED: "--time-to-teleport", "-1" 
        # We need standard teleporting (defaults to 300s) to measure it.
    ]

    print(f"Starting Simulation...")
    start_time = time.time()
    
    traci.start(sumo_args)

    # --- METRIC ACCUMULATORS ---
    stats = {
        "total_waiting_time": 0.0,
        "total_co2_emissions": 0.0,
        "total_fuel_consumption": 0.0,
        "mean_network_speed": 0.0,
        "total_arrived_vehicles": 0,
        "total_collisions": 0,
        "total_teleported": 0,      # <--- NEW METRIC
        "vehicles_not_arrived": 0,  # <--- NEW METRIC
        "steps_simulated": 0
    }

    step = 0
    
    while step < SIMULATION_STEPS:
        traci.simulationStep()
        
        # 1. Capture Global Counters
        stats["total_arrived_vehicles"] += traci.simulation.getArrivedNumber()
        stats["total_collisions"] += traci.simulation.getCollidingVehiclesNumber()
        
        # Count vehicles that started teleporting in THIS step
        stats["total_teleported"] += traci.simulation.getStartingTeleportNumber()
        
        # 2. Capture Vehicle-Level Metrics
        vehicle_ids = traci.vehicle.getIDList()
        current_step_speed_sum = 0
        vehicle_count = len(vehicle_ids)
        
        if vehicle_count > 0:
            for vid in vehicle_ids:
                stats["total_waiting_time"] += traci.vehicle.getWaitingTime(vid)
                stats["total_co2_emissions"] += traci.vehicle.getCO2Emission(vid)
                stats["total_fuel_consumption"] += traci.vehicle.getFuelConsumption(vid)
                current_step_speed_sum += traci.vehicle.getSpeed(vid)
            
            stats["mean_network_speed"] += (current_step_speed_sum / vehicle_count)

        step += 1
    
    # --- CALCULATE FINAL "NOT ARRIVED" ---
    # getMinExpectedNumber returns: 
    # (Vehicles currently running) + (Vehicles loaded but waiting to insert)
    stats["vehicles_not_arrived"] = traci.simulation.getMinExpectedNumber()

    traci.close()
    
    # Final cleanup calculations
    end_time = time.time()
    stats["simulation_runtime_seconds"] = end_time - start_time
    if step > 0:
        stats["mean_network_speed"] = stats["mean_network_speed"] / step
    
    stats["steps_simulated"] = step
    return stats

if __name__ == "__main__":
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: Config file '{CONFIG_FILE}' not found.")
    else:
        results = run_simulation(CONFIG_FILE)
        
        print("\n" + "="*40)
        print("FULL SIMULATION REPORT")
        print("="*40)
        for key, value in results.items():
            if isinstance(value, float):
                print(f"{key:<30}: {value:,.4f}")
            else:
                print(f"{key:<30}: {value}")
        print("="*40)
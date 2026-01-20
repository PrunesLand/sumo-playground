import os
import sys
import traci

# 1. Setup SUMO_HOME
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME'")

def run_simulation():
    # 2. Define the command to start SUMO-GUI
    # Replace 'your_config.sumocfg' with your actual filename
    sumo_cmd = ["sumo-gui", "-c", "real_map.sumocfg"]
    
    # 3. Start TraCI
    traci.start(sumo_cmd)
    
    step = 0
    while step < 1000:
        # Advance the simulation by one step
        traci.simulationStep()
        
        # Example interaction: Get the IDs of all vehicles currently in the simulation
        vehicle_ids = traci.vehicle.getIDList()
        
        if len(vehicle_ids) > 0:
            print(f"Step {step}: There are {len(vehicle_ids)} vehicles on the network.")
        
        step += 1

    # 4. Close TraCI
    traci.close()
    sys.stdout.flush()

if __name__ == "__main__":
    run_simulation()
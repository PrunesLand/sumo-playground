import os
import sys
import libsumo as traci

# --- SETUP ---
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME'")

CONFIG_FILE = "real_map.sumocfg"

def apply_and_run():
    # Start SUMO
    # We use the dummy "sumo" arg fix
    sumo_args = ["sumo", "-c", CONFIG_FILE, "--no-step-log", "true"]
    print("Starting SUMO...")
    traci.start(sumo_args)

    # 1. Get all Traffic Lights
    tls_ids = traci.trafficlight.getIDList()
    print(f"Found {len(tls_ids)} traffic lights. Applying new timings...\n")

    # 2. Iterate through them with Index (i)
    for i, tls_id in enumerate(tls_ids):
        
        # DETERMINE TARGET DURATION
        # Even index (0, 2, 4...) -> 50 seconds
        # Odd index (1, 3, 5...)  -> 80 seconds
        if i % 2 == 0:
            target_green_time = 50.0
            type_label = "EVEN"
        else:
            target_green_time = 80.0
            type_label = "ODD"

        # 3. GET CURRENT LOGIC
        # We need to pull the full program, modify it, and push it back
        logics = traci.trafficlight.getAllProgramLogics(tls_id)
        current_logic = logics[0] # Get the default program
        
        # 4. MODIFY ONLY GREEN PHASES
        # We assume any phase containing 'G' (Priority Green) or 'g' (Yield Green) is a Green phase.
        # We assume 'y' (Yellow) and pure 'r' (Red) phases should strictly NOT be touched.
        
        changes_made = 0
        for phase in current_logic.phases:
            # Check if this is a Green phase
            if 'G' in phase.state or 'g' in phase.state:
                # Be careful not to modify short "clearing" greens if you have them, 
                # but for standard maps, this is safe.
                phase.duration = target_green_time
                changes_made += 1
        
        # 5. APPLY THE NEW LOGIC
        traci.trafficlight.setProgramLogic(tls_id, current_logic)
        
        print(f"[{type_label}] TLS '{tls_id}' -> Set {changes_made} green phases to {target_green_time}s")

    print("="*50)
    print("Modifications Complete. Running Simulation with new timers...")
    
    # 6. RUN SIMULATION (To verify it works)
    step = 0
    total_waiting = 0
    while step < 1000:
        traci.simulationStep()
        
        # Optional: Collect a metric to see if this helped
        for veh in traci.vehicle.getIDList():
            total_waiting += traci.vehicle.getWaitingTime(veh)
            
        step += 1

    print(f"Simulation Finished. Total Waiting Time: {total_waiting}")
    traci.close()

if __name__ == "__main__":
    apply_and_run()
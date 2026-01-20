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

def inspect_traffic_lights():
    # Start SUMO just to load the network (no simulation steps needed)
    # We add "sumo" as the first arg to fix the libsumo parsing quirk
    sumo_args = ["sumo", "-c", CONFIG_FILE, "--no-step-log", "true"]
    
    print("Loading network geometry...")
    traci.start(sumo_args)

    # 1. Get all Traffic Light IDs
    tls_ids = traci.trafficlight.getIDList()
    print(f"\nTotal Intersections (Traffic Light Systems): {len(tls_ids)}")
    print("=" * 60)

    # 2. Iterate through each intersection to find its parameters
    for tls_id in tls_ids:
        print(f"Intersection ID: {tls_id}")
        
        # Get the logic (the schedule) currently active on this light
        # getAllProgramLogics returns a list of logic objects. We take the first one (default).
        logics = traci.trafficlight.getAllProgramLogics(tls_id)
        current_logic = logics[0]
        
        # Calculate Total Cycle Time (Sum of all phases)
        total_cycle_time = sum(p.duration for p in current_logic.phases)
        
        print(f"  > Current Program ID : {current_logic.programID}")
        print(f"  > Total Cycle Time   : {total_cycle_time} seconds")
        print(f"  > Number of Phases   : {len(current_logic.phases)}")
        print(f"  > Phase Breakdown    :")
        
        # Print details for every phase
        for i, phase in enumerate(current_logic.phases):
            # We explicitly mark phases that are usually NOT modifiable (Yellow lights)
            is_yellow = "y" in phase.state.lower()
            modifiable_marker = "[FIXED]" if is_yellow else "[MODIFIABLE]"
            
            print(f"      Phase {i}: {phase.duration}s  | State: {phase.state} {modifiable_marker}")
            
        print("-" * 60)

    traci.close()

if __name__ == "__main__":
    inspect_traffic_lights()
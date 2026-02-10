import libsumo as traci

CONFIG_FILE = "osm.sumocfg"
sumo_args = ["sumo", "-c", CONFIG_FILE, "--no-step-log", "true", "--no-warnings", "true"]

# Start SUMO
traci.start(sumo_args)

try:
    # Get traffic light IDs
    tls_ids = traci.trafficlight.getIDList()
    print(f"Found {len(tls_ids)} traffic light(s): {tls_ids}")
    
    for tls_id in tls_ids:
        # Get the current program logic
        logic = traci.trafficlight.getAllProgramLogics(tls_id)[0]
        print(f"\nTraffic Light ID: {tls_id}")
        print(f"Program ID: {logic.programID}")
        print(f"Number of phases: {len(logic.phases)}")
        
        for i, phase in enumerate(logic.phases):
            print(f"  Phase {i}: duration={phase.duration}s, state='{phase.state}' (length={len(phase.state)})")
        
finally:
    traci.close()

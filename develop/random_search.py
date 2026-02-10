import numpy as np
import libsumo as traci

CONFIG_FILE = "osm.sumocfg"
SUMO_ARGS = ["sumo", "-c", CONFIG_FILE, "--no-step-log", "true", "--no-warnings", "true"]

# Parameter space: green light 6-82 seconds (red = 90 - green)
PARAM_SPACE = {'green_duration': (6, 82)}

# Objective function penalties
PENALTY_TELEPORT = 100
PENALTY_SLOW = 10
SLOW_THRESHOLD = 5.0  # m/s
SIMULATION_STEPS = 1800


def random_search(objective_func, param_space, n_iterations=100):
    """Random search optimization - minimizes the objective function."""
    best_score = float('inf')
    best_params = None
    history = []
    
    for i in range(n_iterations):
        # Sample random parameters
        params = {name: np.random.randint(low, high + 1) 
                  for name, (low, high) in param_space.items()}
        
        # Evaluate
        score = objective_func(params)
        history.append((params.copy(), score))
        
        # Update best
        if score < best_score:
            best_score = score
            best_params = params.copy()
        
        print(f"Iteration {i+1}/{n_iterations}: Score = {score:.2f}, Best = {best_score:.2f}")
    
    return best_params, best_score, history


def objective_function(params):
    """Calculates: total_delay + (num_teleport × penalty) + (num_slow × penalty)"""
    green_duration = int(params['green_duration'])
    red_duration = 90 - green_duration
    
    traci.start(SUMO_ARGS)
    total_delay = 0.0
    num_teleport = 0
    num_slow = 0
    
    try:
        # Set traffic light timings for all traffic lights
        for tls_id in traci.trafficlight.getIDList():
            existing_logics = traci.trafficlight.getAllProgramLogics(tls_id)
            if not existing_logics or len(existing_logics[0].phases) < 2:
                continue
            
            # Use existing phase states with new durations
            phase_states = [p.state for p in existing_logics[0].phases]
            phases = [
                traci.trafficlight.Phase(green_duration, phase_states[0]),
                traci.trafficlight.Phase(red_duration, phase_states[1])
            ]
            
            logic = traci.trafficlight.Logic("random_search", 0, 0, phases)
            traci.trafficlight.setProgramLogic(tls_id, logic)
            traci.trafficlight.setProgram(tls_id, "random_search")
        
        # Run simulation
        for step in range(SIMULATION_STEPS):
            traci.simulationStep()
            
            for veh_id in traci.vehicle.getIDList():
                total_delay += traci.vehicle.getAccumulatedWaitingTime(veh_id)
                if traci.vehicle.getSpeed(veh_id) < SLOW_THRESHOLD:
                    num_slow += 1
            
            num_teleport += traci.simulation.getStartingTeleportNumber()
    
    finally:
        traci.close()
    
    return total_delay + (num_teleport * PENALTY_TELEPORT) + (num_slow * PENALTY_SLOW)


if __name__ == "__main__":
    print("Starting random search for traffic light optimization...")
    print(f"Parameter space: Green light duration = {PARAM_SPACE['green_duration']}")
    print(f"Total cycle duration = 90 seconds (red = 90 - green)\n")
    
    best_params, best_score, history = random_search(
        objective_function, 
        PARAM_SPACE, 
        n_iterations=5
    )
    
    print(f"\n{'='*60}")
    print(f"Optimization Complete!")
    print(f"{'='*60}")
    print(f"Best green light duration: {best_params['green_duration']} seconds")
    print(f"Best red light duration: {90 - best_params['green_duration']} seconds")
    print(f"Best objective score: {best_score:.2f}")
    print(f"{'='*60}")

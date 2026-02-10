import numpy as np
import libsumo as traci
from multiprocessing import Pool, cpu_count
from functools import partial

CONFIG_FILE = "osm.sumocfg"
SUMO_ARGS = ["sumo", "-c", CONFIG_FILE, "--no-step-log", "true", "--no-warnings", "true"]

# Parameter space: green light 6-82 seconds (red = 90 - green)
PARAM_SPACE = {'green_duration': (6, 82)}

# Objective function penalties
PENALTY_TELEPORT = 100
PENALTY_SLOW = 10
SLOW_THRESHOLD = 5.0  # m/s
SIMULATION_STEPS = 1800


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


def evaluate_single_iteration(iteration_num, param_space):
    """Wrapper function for a single iteration - used by multiprocessing"""
    # Sample random parameters
    params = {name: np.random.randint(low, high + 1) 
              for name, (low, high) in param_space.items()}
    
    # Evaluate
    score = objective_function(params)
    
    print(f"Iteration {iteration_num + 1} completed: Score = {score:.2f}, Params = {params}")
    
    return params, score


def random_search(objective_func, param_space, n_iterations=100, n_processors=None):
    """
    Random search optimization with multiprocessing - minimizes the objective function.
    
    Args:
        objective_func: The function to optimize (not used directly, but kept for API compatibility)
        param_space: Dictionary defining parameter ranges
        n_iterations: Number of random samples to evaluate
        n_processors: Number of processors to use (None = all available, -1 = all but one)
    
    Returns:
        best_params: Best parameters found
        best_score: Best score achieved
        history: List of (params, score) tuples for all iterations
    """
    # Determine number of processors
    if n_processors is None:
        n_proc = cpu_count()
    elif n_processors == -1:
        n_proc = max(1, cpu_count() - 1)
    else:
        n_proc = min(n_processors, cpu_count())
    
    print(f"Using {n_proc} processors (out of {cpu_count()} available)")
    
    best_score = float('inf')
    best_params = None
    history = []
    
    # Create partial function with fixed param_space
    eval_func = partial(evaluate_single_iteration, param_space=param_space)
    
    # Run parallel evaluations
    with Pool(processes=n_proc) as pool:
        results = pool.map(eval_func, range(n_iterations))
    
    # Process results
    for i, (params, score) in enumerate(results):
        history.append((params, score))
        
        # Update best
        if score < best_score:
            best_score = score
            best_params = params.copy()
            print(f"New best found at iteration {i+1}: Score = {best_score:.2f}")
    
    return best_params, best_score, history


if __name__ == "__main__":
    print("Starting random search for traffic light optimization...")
    print(f"Parameter space: Green light duration = {PARAM_SPACE['green_duration']}")
    print(f"Total cycle duration = 90 seconds (red = 90 - green)\n")
    
    # Choose number of processors:
    # None = use all available processors
    # -1 = use all but one processor
    # N = use exactly N processors
    NUM_PROCESSORS = 1  # Adjust this value as needed
    
    best_params, best_score, history = random_search(
        objective_function, 
        PARAM_SPACE, 
        n_iterations=5,
        n_processors=NUM_PROCESSORS
    )
    
    print(f"\n{'='*60}")
    print(f"Optimization Complete!")
    print(f"{'='*60}")
    print(f"Best green light duration: {best_params['green_duration']} seconds")
    print(f"Best red light duration: {90 - best_params['green_duration']} seconds")
    print(f"Best objective score: {best_score:.2f}")
    print(f"{'='*60}")
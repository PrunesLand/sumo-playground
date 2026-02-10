import numpy as np
import libsumo as traci
import multiprocessing as mp
import os

CONFIG_FILE = "osm.sumocfg"

sumo_args = ["sumo", "-c", CONFIG_FILE, "--no-step-log", "true", "--no-warnings", "true"]


def _evaluate_params(args):
    """
    Helper function to evaluate a single parameter set.
    This needs to be a top-level function for multiprocessing to pickle it.
    Calls objective_function directly to avoid pickling libsumo objects.
    """
    params, iteration, penalty_teleport, penalty_slow, slow_threshold = args
    score = objective_function(params, penalty_teleport, penalty_slow, slow_threshold)
    return iteration, params, score


def random_search(param_space, n_iterations=100, minimize=True, n_jobs=None, 
                  penalty_teleport=1000, penalty_slow=10, slow_threshold=5.0):
    """
    Parallel random search optimization algorithm.
    
    Args:
        param_space: Dict mapping parameter names to (min, max) tuples
        n_iterations: Number of random samples to try
        minimize: If True, minimize the objective; if False, maximize
        n_jobs: Number of parallel jobs (None = use all CPU cores)
        penalty_teleport: Penalty for each teleported vehicle
        penalty_slow: Penalty for each slow vehicle
        slow_threshold: Speed threshold for slow vehicles in m/s
    
    Returns:
        best_params: Dictionary of best parameters found
        best_score: Best objective function value
        history: List of (params, score) tuples for all evaluations
    """
    # Determine number of workers
    if n_jobs is None:
        n_jobs = mp.cpu_count()
    
    print(f"Using {n_jobs} parallel workers")
    
    best_score = float('inf') if minimize else float('-inf')
    best_params = None
    history = []
    
    # Pre-generate all random parameters
    all_params = []
    for i in range(n_iterations):
        params = {}
        for param_name, (low, high) in param_space.items():
            # Use randint for integer parameters
            params[param_name] = np.random.randint(low, high + 1)
        all_params.append((params, i, penalty_teleport, penalty_slow, slow_threshold))
    
    # Run evaluations in parallel
    with mp.Pool(processes=n_jobs) as pool:
        results = pool.map(_evaluate_params, all_params)
    
    # Process results
    for iteration, params, score in sorted(results, key=lambda x: x[0]):
        history.append((params.copy(), score))
        
        # Update best if improved
        if minimize:
            if score < best_score:
                best_score = score
                best_params = params.copy()
        else:
            if score > best_score:
                best_score = score
                best_params = params.copy()
        
        print(f"Iteration {iteration+1}/{n_iterations}: Score = {score:.4f}, Best = {best_score:.4f}")
    
    return best_params, best_score, history



# Define parameter space: green light duration from 6 to 82 seconds
def get_param_space():
    """
    Returns the parameter space for random search.
    Green light duration: 6 to 82 seconds (integers)
    Red light duration will be automatically calculated as (90 - green_duration)
    """
    return {
        'green_duration': (6, 82)  # Min: 6, Max: 82
    }


def objective_function(params, penalty_teleport=1000, penalty_slow=10, slow_threshold=5.0):
    """
    Objective function for traffic light optimization.
    
    Args:
        params: Dictionary with 'green_duration' key
        penalty_teleport: Penalty for each teleported vehicle (default: 1000)
        penalty_slow: Penalty for each slow vehicle (default: 10)
        slow_threshold: Speed threshold for slow vehicles in m/s (default: 5.0)
    
    Returns:
        F(x) = total_delay + (num_teleport × penalty_teleport) + (num_slow × penalty_slow)
    """
    green_duration = int(params['green_duration'])
    red_duration = 90 - green_duration  # Total cycle must be 90 seconds
    
    # Start SUMO simulation
    traci.start(sumo_args)
    
    # Initialize metrics
    total_delay = 0.0
    num_teleport = 0
    num_slow = 0
    
    try:
        # Set traffic light timings
        # Get all traffic light IDs
        tls_ids = traci.trafficlight.getIDList()
        
        for tls_id in tls_ids:
            # Get the existing traffic light program to understand the state pattern
            existing_logics = traci.trafficlight.getAllProgramLogics(tls_id)
            if not existing_logics:
                continue
            
            existing_logic = existing_logics[0]
            
            # We'll create a simplified 2-phase program using the existing state patterns
            # Take the first green phase state and first red/yellow phase state as templates
            if len(existing_logic.phases) < 2:
                continue
                
            # Use existing phase states but modify durations
            phase_states = [phase.state for phase in existing_logic.phases]
            
            # Create simplified 2-phase cycle: use first two phase states as templates
            # Adjust durations to match our green/red cycle
            phases = [
                traci.trafficlight.Phase(green_duration, phase_states[0]),
                traci.trafficlight.Phase(red_duration, phase_states[1] if len(phase_states) > 1 else phase_states[0])
            ]
            
            logic = traci.trafficlight.Logic("random_search", 0, 0, phases)
            traci.trafficlight.setProgramLogic(tls_id, logic)
            traci.trafficlight.setProgram(tls_id, "random_search")
        
        # Run simulation for a fixed number of steps (e.g., 3600 steps = 1 hour)
        simulation_steps = 1800
        
        for step in range(simulation_steps):
            traci.simulationStep()
            
            # Get all vehicles in the simulation
            vehicle_ids = traci.vehicle.getIDList()
            
            for veh_id in vehicle_ids:
                # Accumulate waiting time (delay)
                waiting_time = traci.vehicle.getAccumulatedWaitingTime(veh_id)
                total_delay += waiting_time
                
                # Check if vehicle is slow
                speed = traci.vehicle.getSpeed(veh_id)
                if speed < slow_threshold:
                    num_slow += 1
            
            # Count teleports (vehicles that got stuck and were removed)
            num_teleport += traci.simulation.getStartingTeleportNumber()
        
    finally:
        traci.close()
    
    # Calculate objective function
    objective_value = total_delay + (num_teleport * penalty_teleport) + (num_slow * penalty_slow)
    
    return objective_value


if __name__ == "__main__":
    # Get parameter space
    param_space = get_param_space()
    
    # Run random search
    print("Starting random search for traffic light optimization...")
    print(f"Parameter space: Green light duration = {param_space['green_duration']}")
    print(f"Total cycle duration = 90 seconds (red = 90 - green)")
    print()
    
    best_params, best_score, history = random_search(
        param_space, 
        n_iterations=50,  # Adjust based on computational resources
        minimize=True
    )
    
    print(f"\n{'='*60}")
    print(f"Optimization Complete!")
    print(f"{'='*60}")
    print(f"Best green light duration: {best_params['green_duration']} seconds")
    print(f"Best red light duration: {90 - best_params['green_duration']} seconds")
    print(f"Best objective score: {best_score:.2f}")
    print(f"{'='*60}")

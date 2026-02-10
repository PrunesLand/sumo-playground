import numpy as np
import libsumo as traci
from multiprocessing import Pool, cpu_count
from functools import partial
import json
import datetime
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "osm.sumocfg")
SUMO_ARGS = [
    "sumo", 
    "-c", CONFIG_FILE, 
    "--no-step-log", "true", 
    "--no-warnings", "true",
    "--time-to-teleport", "-1",  
]

NUM_PROCESSORS = 1
NUM_ITERATIONS = 5

# Parameter constraints: green light 6-82 seconds (red = 90 - green)
MIN_GREEN = 6
MAX_GREEN = 82
CYCLE_DURATION = 90

# Objective function penalties
PENALTY_TELEPORT = 100
PENALTY_SLOW = 10
SLOW_THRESHOLD = 5.0  # m/s
SIMULATION_STEPS = 3600


def get_traffic_lights():
    """Starts a temp simulation to get all traffic light IDs"""
    traci.start(SUMO_ARGS)
    tls_ids = traci.trafficlight.getIDList()
    traci.close()
    return tls_ids


def objective_function(params, tls_ids):
    """Calculates score and returns detailed statistics"""
    traci.start(SUMO_ARGS)
    
    # Stats collectors
    total_delay = 0.0
    num_teleport = 0
    slow_vehicles = set()
    vehicles_evaluated = set()
    finished_vehicles_count = 0
    
    try:
        # Set traffic light timings
        for tls_id in tls_ids:
            param_key = f"{tls_id}_green"
            if param_key not in params:
                continue
                
            green_duration = int(params[param_key])
            red_duration = CYCLE_DURATION - green_duration
            
            existing_logics = traci.trafficlight.getAllProgramLogics(tls_id)
            if not existing_logics or len(existing_logics[0].phases) < 2:
                continue
            
            phase_states = [p.state for p in existing_logics[0].phases]
            phases = [
                traci.trafficlight.Phase(green_duration, phase_states[0]),
                traci.trafficlight.Phase(red_duration, phase_states[1])
            ]
            
            logic = traci.trafficlight.Logic("random_search", 0, 0, phases)
            traci.trafficlight.setProgramLogic(tls_id, logic)
            traci.trafficlight.setProgram(tls_id, "random_search")
        
        # Run simulation with accumulation
        for step in range(SIMULATION_STEPS):
            traci.simulationStep()
            
            # Helper to get delay for all active vehicles in this step
            for veh_id in traci.vehicle.getIDList():
                vehicles_evaluated.add(veh_id)
                
                # Count waiting time: if speed < 0.1 m/s, add 1 second to total delay
                if traci.vehicle.getSpeed(veh_id) < 0.1:
                    total_delay += 1.0
                
                # Track slow vehicles
                if traci.vehicle.getSpeed(veh_id) < SLOW_THRESHOLD:
                    slow_vehicles.add(veh_id)
            
            # Count finished vehicles
            finished_vehicles_count += len(traci.simulation.getArrivedIDList())
            
            num_teleport += traci.simulation.getStartingTeleportNumber()
        
        # Post-simulation stats
        vehicle_count = len(vehicles_evaluated)
        avg_delay = total_delay / vehicle_count if vehicle_count > 0 else 0
        num_slow = len(slow_vehicles)
        remaining_vehicles_count = len(traci.vehicle.getIDList())
        
    finally:
        traci.close()
    
    # Calculate final score
    score = total_delay + (num_slow * PENALTY_SLOW)
    
    stats = {
        "score": float(score),
        "total_delay": float(total_delay),
        "avg_delay_per_vehicle": float(avg_delay),
        "vehicle_count": int(vehicle_count),
        "finished_vehicles": int(finished_vehicles_count),
        "remaining_vehicles": int(remaining_vehicles_count),
        "teleported_vehicles": int(num_teleport),
        "slow_vehicles": int(num_slow),
        "simulation_steps": SIMULATION_STEPS
    }
    
    return float(score), stats


def evaluate_single_iteration(iteration_num, param_space, tls_ids):
    """Wrapper function for a single iteration"""
    params = {name: np.random.randint(low, high + 1) 
              for name, (low, high) in param_space.items()}
    
    score, stats = objective_function(params, tls_ids)
    
    print(f"Iteration {iteration_num + 1}: Score = {score:.2f}, Finished = {stats['finished_vehicles']}, Remaining = {stats['remaining_vehicles']}")
    return params, score, stats


def random_search(param_space, tls_ids, n_iterations=100, n_processors=None):
    """Random search optimization with multiprocessing"""
    if n_processors is None:
        n_proc = cpu_count()
    elif n_processors == -1:
        n_proc = max(1, cpu_count() - 1)
    else:
        n_proc = min(n_processors, cpu_count())
    
    print(f"Using {n_proc} processors (out of {cpu_count()} available)")
    
    best_score = float('inf')
    best_params = None
    best_stats = None
    history = []
    
    eval_func = partial(evaluate_single_iteration, param_space=param_space, tls_ids=tls_ids)
    
    with Pool(processes=n_proc) as pool:
        results = pool.map(eval_func, range(n_iterations))
    
    for i, (params, score, stats) in enumerate(results):
        history.append({
            "iteration": i + 1,
            "score": score,
            "parameters": params,
            "stats": stats
        })
        
        if score < best_score:
            best_score = score
            best_params = params.copy()
            best_stats = stats.copy()
            # print(f"New best found at iteration {i+1}: Score = {best_score:.2f}")
    
    return best_params, best_score, best_stats, history


if __name__ == "__main__":
    print("Detecting traffic lights...")
    tls_ids = get_traffic_lights()
    
    param_space = {f"{tid}_green": (MIN_GREEN, MAX_GREEN) for tid in tls_ids}
    
    print("Starting optimization...")
    print(f"Total variables: {len(param_space)}")
    
    best_params, best_score, best_stats, history = random_search(
        param_space,
        tls_ids,
        n_iterations=NUM_ITERATIONS,
        n_processors=NUM_PROCESSORS
    )
    
    # Prepare JSON output
    output_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "optimization_config": {
            "iterations": NUM_ITERATIONS,
            "cycle_duration": CYCLE_DURATION,
            "penalties": {
                # "teleport": PENALTY_TELEPORT,
                "slow": PENALTY_SLOW
            }
        },
        "best_solution": {
            "score": best_score,
            "configurations": {},
            "performance_stats": best_stats
        }
    }
    
    # Format best configuration nicely
    for tls_id in tls_ids:
        green = best_params[f"{tls_id}_green"]
        output_data["best_solution"]["configurations"][tls_id] = {
            "green_duration": int(green),
            "red_duration": int(CYCLE_DURATION - green)
        }

    # Save to file
    json_filename = "random_search_results.json"
    with open(json_filename, "w") as f:
        json.dump(output_data, f, indent=4)
    
    print(f"\n{'='*60}")
    print(f"Optimization Complete!")
    print(f"Results saved to: {json_filename}")
    print(f"Best objective score: {best_score:.2f}")
    print(f"Total Vehicles: {best_stats['vehicle_count']}")
    print(f"Finished Vehicles: {best_stats['finished_vehicles']}")
    print(f"Remaining Vehicles: {best_stats['remaining_vehicles']}")
    # print(f"Teleported Vehicles: {best_stats['teleported_vehicles']}")
    print(f"Slow Vehicles: {best_stats['slow_vehicles']}")
    print(f"{'='*60}")
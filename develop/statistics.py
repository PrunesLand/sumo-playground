import os
import sys
import libsumo as traci

CONFIG_FILE = "osm.sumocfg"
IGNORE_THRESHOLD = 1  # Filter out phases shorter than 0.5 seconds

def get_min_max_stats():
    # Start SUMO in headless mode
    sumo_args = ["sumo", "-c", CONFIG_FILE, "--no-step-log", "true", "--no-warnings", "true"]
    
    print(f"Scanning network extrema (Min/Max only)...")
    try:
        traci.start(sumo_args)
    except Exception as e:
        print(f"Error starting SUMO: {e}")
        return

    tls_ids = traci.trafficlight.getIDList()
    
    if not tls_ids:
        print("No traffic lights found.")
        return

    # --- INITIALIZE EXTREMA ---
    # We use infinity for mins and -1 for maxs to ensure the first value overwrites them.
    
    # 1. Complexity (Topology)
    min_lanes = float('inf'); max_lanes = -1
    min_signals = float('inf'); max_signals = -1
    
    # 2. Structure (Phases per Cycle)
    min_phases = float('inf'); max_phases = -1
    
    # 3. Timing (Cycle Durations)
    min_cycle = float('inf'); max_cycle = -1
    
    # 4. Individual Phase Durations
    min_green = float('inf'); max_green = -1
    min_yellow = float('inf'); max_yellow = -1
    min_red = float('inf');   max_red = -1
    
    # 5. Modifiable Counts (Per Intersection)
    min_modifiable = float('inf'); max_modifiable = -1
    
    # Global Totals
    total_modifiable_phases = 0
    total_fixed_phases = 0
    
    # --- Color Specific Counters ---
    total_green = 0
    total_yellow = 0
    total_red = 0
    total_ignored = 0

    # --- SCANNING LOOP ---
    for tls_id in tls_ids:
        
        # --- TOPOLOGY ---
        links = traci.trafficlight.getControlledLinks(tls_id)
        num_signals = len(links)
        
        # Calculate total lanes controlled by this TLS
        num_lanes = sum(len(signal_group) for signal_group in links)
        
        # Update Topology Min/Max
        min_lanes = min(min_lanes, num_lanes)
        max_lanes = max(max_lanes, num_lanes)
        min_signals = min(min_signals, num_signals)
        max_signals = max(max_signals, num_signals)

        # --- LOGIC & PHASES ---
        logics = traci.trafficlight.getAllProgramLogics(tls_id)
        if not logics: continue
        current_logic = logics[0]
        
        phases = current_logic.phases
        num_phases = len(phases)
        
        # Update Structure Min/Max
        min_phases = min(min_phases, num_phases)
        max_phases = max(max_phases, num_phases)
        
        # Cycle Time
        current_cycle_time = sum(p.duration for p in phases)
        min_cycle = min(min_cycle, current_cycle_time)
        max_cycle = max(max_cycle, current_cycle_time)

        # --- INDIVIDUAL PHASE ANALYSIS ---
        local_modifiable = 0
        
        for p in phases:
            dur = p.duration
            
            # --- FILTER: Skip small glitches ---
            if dur < IGNORE_THRESHOLD:
                total_ignored += 1
                continue

            state = p.state.lower()
            
            if 'y' in state or 'u' in state:
                # Yellow / Fixed
                min_yellow = min(min_yellow, dur)
                max_yellow = max(max_yellow, dur)
                total_fixed_phases += 1
                total_yellow += 1
                
            elif 'g' in state:
                # Green / Modifiable
                min_green = min(min_green, dur)
                max_green = max(max_green, dur)
                local_modifiable += 1
                total_modifiable_phases += 1
                total_green += 1
                
            else:
                # All Red (Usually Modifiable/Hold)
                min_red = min(min_red, dur)
                max_red = max(max_red, dur)
                local_modifiable += 1
                total_modifiable_phases += 1
                total_red += 1
        
        # Update Modifiable Count Extremes
        min_modifiable = min(min_modifiable, local_modifiable)
        max_modifiable = max(max_modifiable, local_modifiable)

    traci.close()

    # --- REPORT ---
    print("\n" + "="*50)
    print(f"      NETWORK EXTREMA REPORT ({len(tls_ids)} Intersections)")
    print("="*50)
    
    print("1. INTERSECTION COMPLEXITY (Topology)")
    print(f"   Max Lanes Controlled : {max_lanes}")
    print(f"   Min Lanes Controlled : {min_lanes}")
    print(f"   Max Signals (Heads)  : {max_signals}")
    print(f"   Min Signals (Heads)  : {min_signals}")
    print("-" * 50)
    
    print("2. CYCLE STRUCTURE (Phases)")
    print(f"   Max Phases in a Cycle: {max_phases}")
    print(f"   Min Phases in a Cycle: {min_phases}")
    print(f"   Max Modifiable Phases: {max_modifiable} (in one TLS)")
    print(f"   Min Modifiable Phases: {min_modifiable} (in one TLS)")
    print("-" * 50)
    
    print("3. TIMING (Duration)")
    print(f"   Max Cycle Time       : {max_cycle} s")
    print(f"   Min Cycle Time       : {min_cycle} s")
    print("-" * 50)
    
    if total_green > 0:
        print(f"   Max Green Duration   : {max_green} s")
        print(f"   Min Green Duration   : {min_green} s")
    else:
        print("   Green Duration       : None found")
        
    print("-" * 50)
    
    if total_yellow > 0:
        print(f"   Max Yellow Duration  : {max_yellow} s")
        print(f"   Min Yellow Duration  : {min_yellow} s")
    else:
        print("   Yellow Duration      : None found")
        
    print("-" * 50)
    
    if total_red > 0:
        print(f"   Max Red Duration     : {max_red} s")
        print(f"   Min Red Duration     : {min_red} s")
    else:
        print("   Red Duration         : None found")
        
    print("="*50)
    print("TOTAL COUNTS (Network Wide)")
    print(f"   Total Modifiable Phases: {total_modifiable_phases} (Green + Red)")
    print(f"   Total Fixed Phases     : {total_fixed_phases} (Yellow)")
    print("-" * 50)
    print("   [BREAKDOWN]")
    print(f"   > Green Phases         : {total_green}  (Primary Optimization Target)")
    print(f"   > Red Phases           : {total_red}  (Clearance/Hold)")
    print(f"   > Yellow Phases        : {total_yellow}  (Safety/Fixed)")
    print(f"   > Ignored (<{IGNORE_THRESHOLD}s)    : {total_ignored}")
    print("="*50)

if __name__ == "__main__":
    get_min_max_stats()
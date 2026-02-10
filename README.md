# SUMO Traffic Light Optimization

This project uses Python and SUMO (Simulation of Urban MObility) to optimize traffic light timings for a given road network. 

## 🚀 Setup

### Prerequisites
*   **Python 3.8+**
*   **SUMO 1.x+** with `libsumo` (Python API) installed.
*   **NumPy** (`pip install numpy`)

### Configuration
The main configuration is located in `develop/osm.sumocfg`, which links to the network file (`osm.net.xml.gz`) and route file (`osm.rou.xml`).

---

## 🛠️ Scripts

### 1. `random_search.py` (The Optimizer)
This is the main script that runs the optimization process.

**What it does:**
1.  **Detects Traffic Lights**: Automatically finds all traffic lights in your network.
2.  **Optimizes Independently**: Assigns a unique "Green Duration" variable (6-82s) to *every* traffic light.
3.  **Simulates**: Runs a SUMO simulation for 1 hour (3600 steps) for each random configuration.
4.  **Scores Performance**: Calculates a score based on:
    *   **Total Delay**: Accumulated waiting time (seconds) for all vehicles (1s added per second stopped).
    *   **Penalties**: Extra distinct penalties for "Slow Vehicles" (avg speed < 5 m/s) and "Teleported Vehicles" (jams).

**Usage:**
```bash
cd develop
python3 random_search.py
```

**Output:**
*   Console: Real-time progress of simulations.
*   **`random_search_results.json`**: A detailed report containing:
    *   `best_solution`: The "champion" configuration (Green/Red times for every light).
    *   `performance_stats`: Total delay, vehicle count, finished vs. remaining vehicles.
    *   `history`: (Optional log of all attempts).

---

### 2. `statistics.py` (The Analyzer)
This script analyzes your network *before* you run optimization to understand its complexity.

**What it does:**
*   Scans every intersection.
*   Reports **Min/Max** statistics for:
    *   Number of Lanes / Signals.
    *   Phase counts per cycle.
    *   Cycle durations.
    *   Green/Red/Yellow phase lengths.

**Usage:**
```bash
cd develop
## 📊 Objective Function
The optimizer minimizes the following cost function:
```python
Score = Total_Delay + (Unfinished_Vehicles * 10)
```
*   **Total_Delay**: Sum of every second any vehicle spends stopped (speed < 0.1 m/s).
*   **Unfinished_Vehicles**: Count of vehicles that did not reach their destination by the end of the simulation. 


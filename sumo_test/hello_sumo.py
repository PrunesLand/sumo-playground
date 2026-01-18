import traci
import sys

# "sumo-gui" opens the window, "sumo" runs in background (much faster)
sumoBinary = "sumo-gui" 
sumoCmd = [sumoBinary, "-c", "sim.sumocfg"]

# Start the simulation
traci.start(sumoCmd)

step = 0
while step < 1000:
    traci.simulationStep() # This advances SUMO by one step

    # Example: Get number of vehicles currently waiting
    # ID of an edge in your generated grid, usually "top0to0/0" etc.
    # You can inspect edge IDs in netedit.
    # waiting_time = traci.edge.getWaitingTime("edge_id") 

    step += 1

traci.close()
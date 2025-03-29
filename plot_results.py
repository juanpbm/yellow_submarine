import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

results = []
participant_results = None

# Read and parse results file. 
with open("results.txt", "r") as file:
    for line in file:
        line = line.strip()
        if 'Participant Name' in line:
            participant_results = {
                "name":  line.split(", ")[0].split(": ")[1],
                "haptic": line.split(", ")[1].split(": ")[1] == "True",
                "trials": []
            }
            results.append(participant_results)
        else:
            if "Passed: True" in line:
                time_part, rest = line.split(", Passed: ")
                timestamp = time_part.strip()
                parts = rest.split(", ")
                trial = {
                    "timestamp": timestamp,
                    "passed": parts[0] == "True",
                    "time": float(parts[1].split(": ")[1]),
                    "path_length": float(parts[2].split(": ")[1]),
                    "damage": int(parts[3].split(": ")[1])
                }
                participant_results["trials"].append(trial)

# Define plots for haptics and no haptics
fig_nohap, axes_nohap = plt.subplots(3, 1, figsize=(7, 7))
axes_nohap[0].set_xlabel("Trial#")
axes_nohap[0].set_ylabel("Time")
axes_nohap[0].set_title("Time per Trial (No Haptics)")
axes_nohap[0].xaxis.set_major_locator(MaxNLocator(integer=True))
axes_nohap[1].set_xlabel("Trial#")
axes_nohap[1].set_ylabel("Path Length")
axes_nohap[1].set_title("Path Length per Trial (No Haptics)")
axes_nohap[1].xaxis.set_major_locator(MaxNLocator(integer=True))
axes_nohap[2].set_xlabel("Trial#")
axes_nohap[2].set_ylabel("Damage")
axes_nohap[2].set_title("Damage per Trial (No Haptics)")
axes_nohap[2].xaxis.set_major_locator(MaxNLocator(integer=True))

fig_hap, axes_hap = plt.subplots(3, 1, figsize=(7, 7))
axes_hap[0].set_xlabel("Trial#")
axes_hap[0].set_ylabel("Time")
axes_hap[0].set_title("Time per Trial (Haptics)")
axes_hap[0].xaxis.set_major_locator(MaxNLocator(integer=True))
axes_hap[1].set_xlabel("Trial#")
axes_hap[1].set_ylabel("Path Length")
axes_hap[1].set_title("Path Length per Trial (Haptics)")
axes_hap[1].xaxis.set_major_locator(MaxNLocator(integer=True))
axes_hap[2].set_xlabel("Trial#")
axes_hap[2].set_ylabel("Damage")
axes_hap[2].set_title("Damage per Trial (Haptics)")
axes_hap[2].xaxis.set_major_locator(MaxNLocator(integer=True))

colors = ['b', 'r', 'g', 'c', 'm', 'y', 'k']
hap_times, hap_path_lengths, hap_damages = [], [], []
nohap_times, nohap_path_lengths, nohap_damages = [], [], []
for participant in results:
    time = []
    path_length = []
    damage = []
    color = colors[results.index(participant) % len(colors)]
    for trial in participant["trials"]:
        time.append(trial["time"])
        path_length.append(trial["path_length"])
        damage.append(trial["damage"])
    # print averages per participant. TODO: not sure if needed
    print(f"Participant: {participant['name']}, AVG Time: {np.mean(time)  }")
    print(f"Participant: {participant['name']}, AVG Path Length {np.mean(path_length)}")
    print(f"Participant: {participant['name']}, AVG damge {np.mean(damage)}")
    axes = axes_hap if participant["haptic"] else axes_nohap
    if participant["haptic"]:
        axes = axes_hap
        hap_times.extend(time)
        hap_path_lengths.extend(path_length)
        hap_damages.extend(damage)
    else:
        axes = axes_nohap
        nohap_times.extend(time)
        nohap_path_lengths.extend(path_length)
        nohap_damages.extend(damage)
    
    # Add participant to the plot 
    axes[0].plot(range(len(time)), time, marker='o', color=color, label=participant['name'])
    axes[0].legend()
    axes[0].grid(True)
    axes[1].plot(range(len(path_length)), path_length, marker='o', color=color, label=participant['name'])
    axes[1].legend()
    axes[1].grid(True)
    axes[2].plot(range(len(damage)), damage, marker='o', color=color, label=participant['name'])
    axes[2].legend()
    axes[2].grid(True)

# Show plots
handles, labels = axes_hap[0].get_legend_handles_labels()
fig_hap.legend(handles, labels, loc="upper left", fontsize=10)
for ax in axes_hap:
    ax.legend().remove()
handles, labels = axes_nohap[0].get_legend_handles_labels()
fig_nohap.legend(handles, labels, loc="upper left", fontsize=10)
for ax in axes_nohap:
    ax.legend().remove()
fig_hap.tight_layout()
fig_nohap.tight_layout()
plt.show()

# Calculate and plot averages
print(f"Haptics AVG Time: {np.mean(hap_times)  }")
print(f"Haptics AVG Path Length {np.mean(hap_path_lengths)}")
print(f"Haptics AVG damge {np.mean(hap_damages)}")
print(f"No Haptics AVG Time: {np.mean(nohap_times)  }")
print(f"No Haptics AVG Path Length {np.mean(nohap_path_lengths)}")
print(f"No Haptics AVG damge {np.mean(nohap_damages)}")

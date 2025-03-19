import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

results = []
participant_results = None

with open("results.txt", "r") as file:
    for line in file:
        line = line.strip()
        if 'Participant Name' in line:
            if participant_results is None:
                participant_results = [[element.split(": ")[1] for element in line.split(", ")]]
            else:
                results.append(participant_results)
                participant_results = [[element.split(": ")[1] for element in line.split(", ")]]
        else:
            line = line.split(", ")
            values = [line[0]] + [element.split(": ")[1] for element in line[1:]]
            participant_results.append(values)
    results.append(participant_results)

fig_nohap, axes_nohap = plt.subplots(3, 1, figsize=(7, 7))
axes_nohap[0].set_xlabel("Trial#")
axes_nohap[0].set_ylabel("Time")
axes_nohap[0].set_title("time per trial")
axes_nohap[0].xaxis.set_major_locator(MaxNLocator(integer=True))
axes_nohap[1].set_xlabel("Trial#")
axes_nohap[1].set_ylabel("path length")
axes_nohap[1].set_title("path length per trial")
axes_nohap[1].xaxis.set_major_locator(MaxNLocator(integer=True))
axes_nohap[2].set_xlabel("Trial#")
axes_nohap[2].set_ylabel("Damage")
axes_nohap[2].set_title("Damage per trial")
axes_nohap[2].xaxis.set_major_locator(MaxNLocator(integer=True))

fig_hap, axes_hap = plt.subplots(3, 1, figsize=(7, 7))
axes_hap[0].set_xlabel("Trial#")
axes_hap[0].set_ylabel("Time")
axes_hap[0].set_title("time per trial")
axes_hap[0].xaxis.set_major_locator(MaxNLocator(integer=True))
axes_hap[1].set_xlabel("Trial#")
axes_hap[1].set_ylabel("path length")
axes_hap[1].set_title("path length per trial")
axes_hap[1].xaxis.set_major_locator(MaxNLocator(integer=True))
axes_hap[2].set_xlabel("Trial#")
axes_hap[2].set_ylabel("Damage")
axes_hap[2].set_title("Damage per trial")
axes_hap[2].xaxis.set_major_locator(MaxNLocator(integer=True))

colors = ['b', 'r', 'g', 'c', 'm', 'y', 'k']

for participant in results:
    time = []
    path_length = []
    damage = []
    color = colors[results.index(participant) % len(colors)]
    for trial in participant[1:]: 
        if 'True' in trial[1]:
            time.append(float(trial[2]))
            path_length.append(float(trial[3]))
            damage.append(float(trial[4]))
    print(participant[0], time, path_length, damage)


    if 'True' in participant[0][1]:
        axes = axes_hap
    else:
        axes = axes_nohap

    axes[0].plot(range(len(time)), time, marker='o', color=color, label=participant[0][0])
    axes[0].legend()
    axes[0].grid(True)
    axes[1].plot(range(len(path_length)), path_length, marker='o', color=color, label=participant[0][0])
    axes[1].legend()
    axes[1].grid(True)
    axes[2].plot(range(len(damage)), damage, marker='o', color=color, label=participant[0][0])
    axes[2].legend()
    axes[2].grid(True)


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
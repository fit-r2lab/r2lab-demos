#!/usr/bin/env python3                                                                                                
'''
Plot RSSI values on nodes for one target sender with the R2lab space 

TT 23/3/17
'''

from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.ticker import LinearLocator, FormatStrFormatter
import matplotlib.animation as animation
import numpy as np


target_sender = 1 # refers to the current FIT node sender
xterm_view = False # boolean, True if RSSI values also shown on xterm

# Utilities to retrieve spatial coordinates of FIT nodes in R2lab
pos = [[0,0],[1,5],[1,4],[1,3],[1,2],[1,1],[2,5],[2,4],[2,3],[2,2],[2,1],[3,5],[3,4],[3,3],
       [3,2],[3,1],[4,5],[4,3],[4,2],[5,5],[5,4],[5,3],[5,2],[6,5],[6,3],[6,2],[7,5],[7,4],
       [7,3],[7,2],[7,1],[8,5],[8,4],[8,3],[8,2],[8,1],[9,2],[9,1]]

def fit_node_at_pos(x,y):
    return pos.index([x,y])


# Function used to plot RSSI on figure and also on xterm
def update_fig(framenumber, ax, X, Y, Z, max, rssi_pos, loop, plot):
    global target_sender, xterm_view
    # Retrieve RSSI values (Z) from the RSSI input file

    file_in = open("RSSI.txt", "r")
    for line in file_in:
        # Read RSSI values one line at a time                                                                         
        sender = int(line.split()[0].split('.')[3])
        receiver = int(line.split()[1].split('.')[3])
        if sender == target_sender:
            Z[(pos[receiver][1]-1),(pos[receiver][0]-1)] = float(line.split()[2+rssi_pos].split(',')[0])
    ax.clear()
    # Customize the axis.
    ax.set_zlim(-100.0, 0.0)
    ax.set_ylim(0,6)
    ax.set_xlabel("R2lab room length")
    ax.set_ylabel("R2lab room width")
    ax.set_zlabel("RSSI (dBm)")
    plot.title("RSSI on nodes when sender is fit{:02d} and for antenna {}".format(target_sender,rssi_pos))

    plot = ax.plot_surface(X, Y, Z, cmap=cm.coolwarm, linewidth=1, antialiased=False)
#    plot = ax.plot_wireframe(X, Y, Z, cmap=cm.coolwarm, linewidth=1, antialiased=False)

    if xterm_view:
        ZZ = np.copy(Z)
        for i in range(9):
            ZZ[0][i], ZZ[4][i] = ZZ[4][i], ZZ[0][i]
            ZZ[1][i], ZZ[3][i] = ZZ[3][i], ZZ[1][i]
        print("RSSI on nodes when sender is fit{:02d} and for antenna {}".format(target_sender,rssi_pos))
        print(ZZ)

    if loop:
        target_sender = (target_sender + 1) % (max+1)
        if target_sender == 0:
            target_sender = 1
            xterm_view = False # only write once on xterm
    else:
        xterm_view = False # only write once on xterm
    return plot


def main():
    from argparse import ArgumentParser
    import re
    
    global target_sender, xterm_view

    parser = ArgumentParser()
    parser.add_argument("-m", "--max", default=37, type=int,
                        help="max FIT node number")
    parser.add_argument("-s", "--sender", default=1, type=int,
                        help="target FIT node sender")
    parser.add_argument("-a", "--rssi-pos", default=0,type=int,
                        choices = [0,1,2,3],
                        help="specify the RSSI value to plot according to antennas, default is 0")
    parser.add_argument("-t", "--time", default=1000, type=int,
                        help="delay between each display, default=1000 for 1s")
    parser.add_argument("-l", "--loop", action='store_true', default=False)
    parser.add_argument("-x", "--xterm-view", action='store_true', default=False)

    parser.add_argument("-d", "--debug", action='store_true', default=False)

    args = parser.parse_args()
    
    rssi_pos=args.rssi_pos
    max = args.max
    delay = args.time
    loop = args.loop
    xterm_view = args.xterm_view
    target_sender = args.sender
    
    framenumber = 0

    fig = plt.figure()
    ax = fig.gca(projection='3d')

    # Make X,Y R2lab grid of nodes
    X = np.arange(1, 10, 1)
    Y = np.arange(1, 6, 1)
    X, Y = np.meshgrid(X, Y)

    Z = np.zeros((5,9),dtype=np.float)
    # following coordinates do not have FIT nodes
    Z[0,3] = Z[0,4] = Z[0,5] = -100.0
    Z[3,3] = Z[3,5] = Z[2,8] = Z[3,8] = Z[4,8] = -100.0

    # Retrieve RSSI values (Z) from the RSSI input file
    file_in = open("RSSI.txt", "r")

    update_fig(framenumber, ax, X, Y, Z, max, rssi_pos, loop, plt)

    ani = animation.FuncAnimation(fig, update_fig, 
                                  fargs=(ax, X, Y, Z, max, rssi_pos, loop, plt), 
                                  interval=delay, blit=False)
    plt.show()

    exit(0)

if __name__ == "__main__":main()


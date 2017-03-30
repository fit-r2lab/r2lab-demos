#!/usr/bin/env python3                                                                                                
'''
Plot RSSI values on nodes for one target sender with the R2lab space 
'''

import numpy as np

import plotly.plotly as py
import plotly.tools as tls
import plotly.graph_objs as go

tls.set_credentials_file(username='turletti', api_key='XKYMbfHHpw6qGNd\
pniKW')


pos = [[0,0],[1,5],[1,4],[1,3],[1,2],[1,1],[2,5],[2,4],[2,3],[2,2],[2,1],[3,5],[3,4],[3,3],
       [3,2],[3,1],[4,5],[4,3],[4,2],[5,5],[5,4],[5,3],[5,2],[6,5],[6,3],[6,2],[7,5],[7,4],
       [7,3],[7,2],[7,1],[8,5],[8,4],[8,3],[8,2],[8,1],[9,2],[9,1]]

def fit_node_at_pos(x,y):
    return pos.index([x,y])

def main():
    from argparse import ArgumentParser
    import re

    parser = ArgumentParser()
    parser.add_argument("-s", "--sender", default=1, type=int,
                        help="FIT node sender between 1 and the number of R2lab nodes")
    parser.add_argument("-a", "--rssi-pos", default=0,type=int,choices = [0,1,2,3],
                        help="specify the RSSI value to plot according to antennas, default is 0")

    parser.add_argument("-v", "--verbose", action='store_true', default=False)
    parser.add_argument("-d", "--debug", action='store_true', default=False)

    args = parser.parse_args()
    
    target_sender=args.sender
    rssi_pos=args.rssi_pos

    # Make X,Y R2lab grid of nodes
    X = np.arange(1, 10, 1)
    Y = np.arange(1, 6, 1)
    X, Y = np.meshgrid(X, Y)

    Z = np.zeros((5,9),dtype=np.float)
    Z[0,3] = Z[0,4] = Z[0,5] = -100.0
    Z[3,3] = Z[3,5] = Z[2,8] = Z[3,8] = Z[4,8] = -100.0
    # Retrieve RSSI values (Z) from the RSSI input file
    file_in = open("RSSI.txt", "r")

    for line in file_in:
        # Read RSSI values one line at a time                                                                         
        sender = int(line.split()[0].split('.')[3])
        receiver = int(line.split()[1].split('.')[3])
        if sender == target_sender:
            Z[(pos[receiver][1]-1),(pos[receiver][0]-1)] = float(line.split()[2].split(',')[rssi_pos])
    ZZ = np.copy(Z)
    for i in range(9):
        ZZ[0][i], ZZ[4][i] = ZZ[4][i], ZZ[0][i] 
        ZZ[1][i], ZZ[3][i] = ZZ[3][i], ZZ[1][i] 
    print(ZZ)
    
    # steps for plotly
    data = np.c_[X,Y,Z]
    trace = go.Surface(x=X, y=Y, z=Z)
    data_test = go.Data([trace])
    title = "RSSI (dBm) on R2lab nodes when sender is fit{:02d}".format(target_sender)
    axis = dict(
        showbackground=True, # show axis background
        backgroundcolor="rgb(204, 204, 204)", # set background color to grey
        gridcolor="rgb(255, 255, 255)",       # set grid line color
        zerolinecolor="rgb(255, 255, 255)",   # set zero grid line color
    )
    layout = go.Layout(
        autosize=True,
        title=title,
        scene=go.Scene(  # axes are part of a 'scene' in 3d plots
            xaxis=go.XAxis(axis), # set x-axis style
            yaxis=go.YAxis(axis), # set y-axis style
            zaxis=go.ZAxis(axis)  # set z-axis style
        )
    )
    fig2 = go.Figure(data=data_test, layout=layout)    
    py.plot(fig2, filename='test1')

    exit(0)

if __name__ == "__main__":main()


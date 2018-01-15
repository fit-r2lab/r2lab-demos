"""
Converts a dictionary as output by rssi.py
into data suitable for plotting
"""

import numpy as np

import r2labmap

###  coordinate swaps for
# * numbering that starts at 1
# * y are increasing when paper goes up

def plotx(x):
    return x + 1

def ploty(y):
    return r2lab.height - y

# internal maps
_node_to_position, _position_to_node, _holes \
    = r2labmap.maps(plotx, ploty)

#################### for plotly
def rssi_to_plotly(dict_values):
    """
    converts an input dict into suitable values 
    for plotting in plotly

    Parameters:
        dict_values is expected to be a dict: node_id -> value 

    Returns:
        a tuple X, Y, Z, T(ext) of arrays for plotly
    """
    # input dict may have holes
    X, Y, Z, T = [], [], [], []
    for node_id, value in dict_values.items():
        x, y = _node_to_position[node_id]
        X.append(x)
        Y.append(y)
        Z.append(value)
        T.append("fit{:02d}".format(node_id))
    return X, Y, Z, T


def rssi_to_plotly3D(dict_values):
    """
    converts an input dict into suitable values for plotting in 3D

    Parameters:
        dict_values is expected to be a dict: node_id -> value 

    Returns:
        will return a triple X, Y, Z, T(ext) of numpy arrays for your plotter
    """
    # Make X,Y R2lab grid of nodes                                                                    
    X = np.arange(1, 10, 1, dtype=np.integer)
    Y = np.arange(1, 6, 1, dtype=np.integer)
    X, Y = np.meshgrid(X, Y)

    Z = np.zeros((5,9),dtype=np.float)
    Z[0,3] = Z[0,4] = Z[0,5] = -100 # np.nan
    Z[3,3] = Z[3,5] = Z[2,8] = Z[3,8] = Z[4,8] = -100 # np.nan
    T = [ ["None"]*9 for i in range(6) ]
    for node_id, value in dict_values.items():
        x, y = _node_to_position[node_id]
        Z[y-1,x-1] = value
        T[y-1][x-1]="fit{:02d}".format(node_id)
    return X, Y, Z, T

########################################
if __name__ == '__main__':

    def test1():
        node_ids = range(1, 38)
        assert all(_position_to_node[_node_to_position[id]] == id
                   for id in node_ids)

    test1()

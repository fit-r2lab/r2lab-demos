"""
helper to read a RSSI.txt file
maybe should belong in processmap.py
"""

import numpy as np

from r2lab import R2labMap

def read_rssi(filename, sender, rssi_rank):
    '''
    read a RSSI file and, given a sender node and
    an rssi_rank, returns a dictionary
    receiver_node_number -> value
    '''

    node_number_to_value = {}
    try:
        with open(filename) as in_file:
            for line in in_file:
                try:
                    ip_snd, ip_rcv, *values = line.split()
                    *_, n_snd = ip_snd.split('.')
                    *_, n_rcv = ip_rcv.split('.')
                    n_snd = int(n_snd)
                    n_rcv = int(n_rcv)
                    if n_snd != sender:
                        continue
                    node_number_to_value[n_rcv] = values[rssi_rank]
                except IndexError as e:
                    print("rssi_rank {} not present in values"
                          .format(rssi_rank))
    except IOError as e:
        print("Cannot open file {}: {}" .format(filename, e))

    return node_number_to_value

# convert to plotting

#################### for plotly
def rssi_to_heatmap(rssi_dict):
    """
    converts an input dict into suitable values
    for plotting in plotly

    Parameters:
        rssi_dict is expected to be a dict: node_id -> value

    Returns:
        a tuple X, Y, Z, T(ext) of arrays for plotly
    """
    # input dict may have holes
    r2labmap = R2labMap()
    X, Y, Z, T = [], [], [], []
    for node_id, value in rssi_dict.items():
        x, y = r2labmap.position(node_id)
        X.append(x)
        Y.append(y)
        Z.append(value)
        T.append("fit{:02d}".format(node_id))
    return X, Y, Z, T


def rssi_to_3d(rssi_dict):
    """
    converts an input dict into suitable values for plotting
    in 3D - either for plotly's Surface (needs T)
    or ipyvolume (does not)

    Parameters:
        rssi_dict is expected to be a dict: node_id -> value

    Returns:
        will return a triple X, Y, Z of numpy arrays for ipyvolume
    """
    r2labmap = R2labMap()
    # Make X,Y R2lab grid of nodes
    X = np.arange(1, 10, 1, dtype=np.integer)
    Y = np.arange(1, 6, 1, dtype=np.integer)
    X, Y = np.meshgrid(X, Y)

    Z = np.zeros((5, 9), dtype=np.float)
    Z[0, 3] = Z[0, 4] = Z[0, 5] = -100 # np.nan
    Z[3, 3] = Z[3, 5] = Z[2, 8] = Z[3, 8] = Z[4, 8] = -100 # np.nan
    T = [ ["None"]*9 for i in range(6) ]
    for node_id, value in rssi_dict.items():
        x, y = r2labmap.position(node_id)
        Z[y-1, x-1] = value
        T[y-1][x-1]="fit{:02d}".format(node_id)
    return X, Y, Z, T

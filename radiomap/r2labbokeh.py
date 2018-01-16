"""
Similar to r2labplotly, but slightly different
as we aim at animating

allows to create an empty dataframe that has 
the same shape as the testbed
ad to update it with data coming from the rssi 
storage system
"""

import numpy as np
import pandas as pd


import r2labmap

###  coordinate swaps for
# * numbering that starts at 1
# * y are increasing when paper goes up

def bokx(x):
    return x

def boky(y):
    return r2labmap.height - y

# internal maps
_node_to_position, _position_to_node, _holes \
    = r2labmap.maps(bokx, boky)

########################################
# bokeh - through a dataframe
def init_dataframe():
    """
    returns a dataframe that has the right
    number of lines and columns to depict r2lab nodes
    """
    index = _node_to_position.keys()
    columns = ['x', 'y', 'value']
    df = pd.DataFrame(index = index, columns=columns)
    for node_id, (x, y) in _node_to_position.items():
        df.loc[node_id]['x'] = x
        df.loc[node_id]['y'] = y
        df.loc[node_id]['value'] = 0
    return df
    
def fill_dataframe_from_rssi(df, rssi_dict):
    """
    from a rssi dict that comes out of read_rssi
    replaces values in the input dataframe

    returns df
    """

    for node_id, value in rssi_dict.items():
        df.loc[node_id]['value'] = value
    return df



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
    return y

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
    df = pd.DataFrame(r2labmap.r2labmap)
    def numbers(nam, i):
        return f"{nam}{i:03d}"
    # make column names strings instead of numbers
    columns_map = lambda i: numbers("col", i)
    index_map = lambda i: numbers("col", i)
    df.rename(index = index_map, columns = columns_map, inplace=True)
    # fill with zeros
    for node_id in range(1, 38):
        x, y = _node_to_position[node_id]
        df.iloc[y, x] = 0
    return df
    
def fill_dataframe_from_rssi(df, rssi_dict):
    """
    from a rssi dict that comes out of read_rssi
    replaces values in the input dataframe

    returns df
    """

    for node_id, value in dict_values.items():
        x, y = _node_to_position[node_id]
        df.iloc[y, x] = value
    return df



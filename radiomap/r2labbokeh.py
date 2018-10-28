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
    dataframe = pd.DataFrame(index=index, columns=columns)
    for node_id, (gridx, gridy) in _node_to_position.items():
        dataframe.loc[node_id]['x'] = gridx
        dataframe.loc[node_id]['y'] = gridy
        dataframe.loc[node_id]['value'] = 0
    return dataframe

def fill_dataframe_from_rssi(dataframe, rssi_dict):
    """
    from a rssi dict that comes out of read_rssi
    replaces values in the input dataframe

    returns dataframe
    """

    for node_id, value in rssi_dict.items():
        dataframe.loc[node_id]['value'] = value
    return dataframe

############
# additions / refinements / improvements for batman/olsr
# using more adequate column names, and possibly several
# one in the same dataframe

def init_dataframe_columns(columns):
    """
    returns a dataframe that has the right
    number of lines to depict r2lab nodes
    will then have columns 'x', 'y' + the ones
    mentioned in columns, that is a dict
     column_name : init_value
    """
    index = _node_to_position.keys()
    all_columns = ['x', 'y'] + list(columns.keys())
    dataframe = pd.DataFrame(index=index, columns=all_columns)
    for node_id, (gridx, gridy) in _node_to_position.items():
        dataframe.loc[node_id]['x'] = gridx
        dataframe.loc[node_id]['y'] = gridy
        for column, value in columns.items():
            dataframe.loc[node_id][column] = value
    return dataframe

def fill_dataframe_from_dict(dataframe, data_dict,
                             column_name, default_value):
    """
    from a rssi dict that comes out of read_rssi
    replaces values in the input dataframe

    returns dataframe
    """

    for node_id in range(1, 38):
        dataframe.loc[node_id][column_name] = \
           data_dict.get(node_id, default_value)

    return dataframe

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# the numbers as we display them in livemap
positions = [
    [1,  6, 11, 16,   19,   23,   26, 31, None],
    [2,  7, 12, None, 20,   None, 27, 32, None],
    [3,  8, 13, 17,   21,   24,   28, 33, None],
    [4,  9, 14, 18,   22,   25,   29, 34, 36],
    [5, 10, 15, None, None, None, 30, 35, 37]]

# coordinate swaps
def sx(x):
    return x+1
def sy(y):
    return 5-y

# internal maps
_node_to_position = {
    node_id : (sx(x), sy(y))
    for y, line in enumerate(positions)
    for x, node_id in enumerate(line)
    if node_id
    }

_position_to_node = {
    (sx(x), sy(y)) : node_id
    for y, line in enumerate(positions)
    for x, node_id in enumerate(line)
    if node_id
    }

_holes = {
    (sx(x), sy(y))
    for y, line in enumerate(positions)
    for x, node_id in enumerate(line)
    if not node_id
}

####################
def array_to_xyz(data, fill_holes=False):
    """
    converts an input array into suitable values for plotting in 3d
    
    Parameters:
        data is expected to be an array of size 37 

    Returns:
        will return a triple X, Y, Z of arrays for your plotter
    """
    X, Y, Z = [], [], []
    for node_id, value in enumerate(data):
        x, y = _node_to_position(node_id)
        X.append(x)
        Y.append(y)
        Z.append(value)
    if fill_holes:
        for xhole, yhole in _holes:
            X.append(x)
            Y.append(Y)
            Z.append(None)
    return X, Y, Z


def dict_to_xyz(data, fill_holes=False):
    """
    converts an input dict into suitable values for plotting in 3d
    
    Parameters:
        data is expected to be a dict: node_id -> value 

    Returns:
        will return a triple X, Y, Z of arrays for your plotter
    """
    # input dict may have holes
    X, Y, Z = 37 * [None], 37 * [None], 37 * [None]
    for node_id, value in data.items():
        x, y = _node_to_position[node_id]
        index = node_id - 1
        X[index] = x
        Y[index] = y
        Z[index] = value
    if fill_holes:
        for xhole, yhole in _holes:
            X.append(x)
            Y.append(Y)
            Z.append(None)
    return X, Y, Z



def test1():
    node_ids = range(1, 38)
    assert all(_position_to_node[_node_to_position[id]] == id for id in node_ids)

if __name__ == '__main__':
    test1()


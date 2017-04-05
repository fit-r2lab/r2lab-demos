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
    return x + 1


def sy(y):
    return 5 - y

# internal maps
_node_to_position = {
    node_id: (sx(x), sy(y))
    for y, line in enumerate(positions)
    for x, node_id in enumerate(line)
    if node_id
}

_position_to_node = {
    (sx(x), sy(y)): node_id
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


def array_to_xyzt(array):
    """
    converts an input array into suitable values for plotting in 3d

    Parameters:
        array is expected to be an array of size exactly 37 

    Returns:
        will return a triple X, Y, Z, T(ext) of arrays for your plotter
    """
    X, Y, Z, T = [], [], [], []
    for node_id, value in enumerate(array, 1):
        x, y = _node_to_position(node_id)
        X.append(x)
        Y.append(y)
        Z.append(value)
        T.append("fit{:02d}".format(node_id))
    return X, Y, Z, T


def dict_to_xyzt(dict_values):
    """
    converts an input dict into suitable values for plotting in 3d

    Parameters:
        dict_values is expected to be a dict: node_id -> value 

    Returns:
        will return a triple X, Y, Z, T(ext) of arrays for your plotter
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


def test1():
    node_ids = range(1, 38)
    assert all(_position_to_node[_node_to_position[
               id]] == id for id in node_ids)

if __name__ == '__main__':
    test1()

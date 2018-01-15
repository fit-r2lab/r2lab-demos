"""
basic tool to translate node ids into positions on a grid

depending on the tool, several orientations / numberings
may be needed; this is done through so-called swap function
"""

# the numbers as we display them in livemap
r2labmap = [
    [1,  6, 11, 16,   19,   23,   26, 31, None],
    [2,  7, 12, None, 20,   None, 27, 32, None],
    [3,  8, 13, 17,   21,   24,   28, 33, None],
    [4,  9, 14, 18,   22,   25,   29, 34, 36],
    [5, 10, 15, None, None, None, 30, 35, 37]
]

width = 8
height = 5


# typically swap functions could be something like
# sx = lambda x: x+1 if you want to start numbering at 1
# sy = lambda y: 5-x if you want to have low y's refer
#  to the lower row above

def maps(sx, sy):
    """
    builds and returns as a tuple:

    * node_to_position is a dictionary 
     node_id -> x, y (node_id is between 1 and 37)
    * position_to_node is the reverse dict 
    * holes is a set of tuples (x, y) that correponds 
      to holes in the grid
    """
    
    node_to_position = {
        node_id: (sx(x), sy(y))
        for y, line in enumerate(r2labmap)
        for x, node_id in enumerate(line)
        if node_id
    }

    position_to_node = {
        (sx(x), sy(y)): node_id
        for y, line in enumerate(r2labmap)
        for x, node_id in enumerate(line)
        if node_id
    }

    holes = {
        (sx(x), sy(y))
        for y, line in enumerate(r2labmap)
        for x, node_id in enumerate(line)
        if not node_id
    }

    return node_to_position, position_to_node, holes


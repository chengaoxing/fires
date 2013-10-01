import math
import numpy as np

# Constants to indicate rough bounding box of areas
XMIN = 103.6
XMAX = 100.4
YMIN = 2.25
YMAX = -0.4
UL = [YMAX, XMIN]
LR = [YMIN, XMAX]

def bbox(x, y, d):
    """ Create a bounding box"""
    bb = [[x + d, y + d],
          [x - d, y + d],
          [x - d, y - d],
          [x + d, y - d]]
    return bb

def get_dx(ul, lr):
    """Get horizontal distance from 'ul' to 'lr'."""
    return abs(lr[0] - ul[0])
    
def get_dy(ul, lr):
    """Get vertical distance from 'ul' to 'lr'."""
    return abs(lr[1] - ul[1])

def get_x_tiles(ul, lr, d):
    """Get count of tiles along horizontal axis."""
    return int(math.ceil(get_dx(ul, lr) / (2 * d)))

def get_y_tiles(ul, lr, d):
    """Get count of tiles along vertical axis."""
    return int(math.ceil(get_dy(ul, lr) / (2 * d)))

def calc_d(ul, lr, n, l):
    """Calculate the distance from the tile centroid to tile edge directly
    to the left or right, or directly above or below the centroid.
    
    If 'l' (length of tile side) is supplied, just divide it by two to get 'd'.
    Otherwise, do the math to figure out 'd'."""
    
    if l:
        return l / 2.
        
    else:
        dx = get_dx(ul, lr)
        dy = get_dy(ul, lr)
        
    return math.sqrt(((dx * dy) / (4. * n)))

def get_y(xy, d, yi):
    """Given an xy coordinate, distance d and tile index yi, return the
    x coordinate of the tile centroid."""
    l = d * 2
    return xy[1] - (l * yi) - d

def get_x(xy, d, xi):
    """Given an xy coordinate, distance d and tile index x, return the
    x coordinate of the tile centroid."""
    l = d * 2
    return xy[0] + (l * xi) + d

def mk_tile_bboxes(ul, lr, n=600, l=None):
    """Calculate bounding boxes for all tiles in the region defined by
    the coordinates in 'ul' (upper left) and 'lr' (lower right). Tile
    size and number is determined either by a desired approx. number
    of tiles (default), or a supplied length 'l' of the side of a tile
    in the coordinate system given in 'ul' and 'lr'.
    """
    data = []
    
    d = calc_d(ul, lr, n, l)
    
    for xi in range(get_x_tiles(ul, lr, d)):
        for yi in range(get_y_tiles(ul, lr, d)):
            # calculate x & y of tile centroid
            x = get_x(ul, d, xi)
            y = get_y(ul, d, yi)
            
            # calculate tile bounding box based on centroid
            # coordinates and distance to edge
            bb = bbox(y, x, d)
            
            # store tile coordinates and bounding box as list of lists
            data.append(bb)

    return data

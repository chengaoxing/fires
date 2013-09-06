import datetime
import random
import urllib
import csv
import time
from shapely.geometry import Point
from shapely.prepared import prep
import ee
import os
import ee.mapclient
import requests, zipfile, StringIO
import Image
from matplotlib import rcParams
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import math

def fireQuery():
    # Returns the lat-lon coordinates of all fires in Southeast Asia
    # over the past 24 hours in a list of tuples
    base = "http://firms.modaps.eosdis.nasa.gov"
    params = "active_fire/text/SouthEast_Asia_24h.csv"
    ret = urllib.urlopen("%s/%s" %(base, params))
    l = list(csv.reader(ret))
    x = [i for i in l[1:] if int(i[8]) > 50]
    coord_dict= map(lambda x: Point(float(x[1]), float(x[0])), x)
    return coord_dict

def filterRiau(pts):
    # Returns all fires that are located within a 1.75 degree radius
    # of a point in Riau.  Used to screen out unneccessary fires in
    # Southeast Asia.  
    poly = Point(101.87622, 0.93706).buffer(1.75)
    return filter(prep(poly).contains, pts)

def geeAuth(user_path = os.path.expanduser('~')):
    # Authenticate Earth Engine user.  Ensure that the *.p12 key file
    # is in your ~/.ssh/ directory.
    key_file = '%s/.ssh/ee-privatekey.p12' % user_path
    if os.path.exists(key_file):
        acct = '328542535849@developer.gserviceaccount.com'
        ee.Initialize(ee.ServiceAccountCredentials(acct, key_file))
    else:
        raise Exception('Ensure GEE key file is in ~/.ssh directory')

def graphNDVIdiff(lat, lon, d = 0.01, rapideye = True):
    # Accepts the lat-lon coordinates of a square with dimension `d`
    # and saves an image to disk of the vectorized NDVI difference
    # from RapidEye imagery.

    # Generate the difference between minimum NDVI values for each
    # pixel for the supplied beginning and end year.  The result is a
    # rough approximation of burn scars.

    if rapideye:
        ic = ee.ImageCollection("WRI/RAPIDEYE")
        im_beg = ic.filterDate("1/1/2010", "12/31/2012")
        im_end = ic.filterDate("1/1/2013", "12/31/2013")
        ndvi_begin = im_beg.map_normalizedDifference(["N", "R"]).min()
        ndvi_end   = im_end.map_normalizedDifference(["N", "R"]).min()
        ndvidiff = ndvi_end.subtract(ndvi_begin)
    else:
        print "landsat"
        ic = ee.ImageCollection("L7_L1T")
        im_beg = ic.filterDate("1/1/2010", "12/31/2012")
        im_end = ic.filterDate("1/1/2013", "12/31/2013")
        ndvi_begin = im_beg.map_normalizedDifference(["50", "40"]).min()
        ndvi_end   = im_end.map_normalizedDifference(["50", "40"]).min()
        ndvidiff = ndvi_end.subtract(ndvi_begin)

    # Define the coordinates of the bounding box of the returned image
    bb = [[lon + d, lat + d], 
          [lon - d, lat + d], 
          [lon - d, lat - d], 
          [lon + d, lat - d]]
    
    # Download the NDVI difference image as a zip file
    params = {'scale' : 1, 'crs' : 'EPSG:4326', 'region' : str(bb)}
    path = ndvidiff.getDownloadUrl(params)
    r = requests.get(path)

    # Ensure that the download was successful
    if r.ok:
        print 'Download successful.\nProcessing image...'
    else:
        raise Exception('GEE download failed.')

    # Convert the downloaded tif image to a numpy array
    z = zipfile.ZipFile(StringIO.StringIO(r.content))
    a = filter(lambda x: x.endswith('.tif'), z.namelist())
    p = z.extract(a[0])
    im = Image.open(p)
    arr = np.array(im)

    # Set the extent of the image
    ydim, xdim = arr.shape
    x = np.linspace(lon - d, lon + d, xdim)
    y = np.linspace(lat - d, lat + d, ydim)
    
    # Plot the image, along with the contours to indicate plot extents
    rcParams['contour.negative_linestyle'] = 'solid'
    try:
        plt.contour(x, y, np.flipud(arr), 4, linewidths = 1, colors = 'k')
        plt.imshow(arr, extent = [lon - d, lon + d, lat - d, lat + d])
        plt.savefig('%s-%s-%s.png' %(lat, lon, d))
        plt.clf()
        print "Image saved."
        
    except ValueError as detail:
        print "Not enough variation to contour:", detail

    # remove raw tif file
    print "Cleaning up..."
    os.remove(p)
    print "Done."

def extractImages(n = 10):
    # Extract images from the most recent fires
    geeAuth()
    pts = filterRiau(fireQuery())
    map(lambda p: graphNDVIdiff(p.y, p.x), random.sample(pts, n))

def calcScarArea(bb, cloud_thresh = 0, drop_thresh = -0.15, scale = 5):
    # Calculate the area of burn scars in hectares for the supplied
    # bounding box.

    # Authenticate earth engine credentials
    geeAuth()
    
    # Location of fires after June 1, 2013, stored in fusion tables
    firetable = 'ft:1MH_YS3OsKJwhHLEh9grct2Xz4_dpYfcm_uEgt_0'

    # Calculate NDVI difference for the RapidEye imagery.  Note that
    # you must be added by Thau to the access list in order to access
    # the RapidEye imagery.
    ic = ee.ImageCollection("WRI/RAPIDEYE")
    im_beg = ic.filterDate("1/1/2010", "5/31/2013")
    im_end = ic.filterDate("6/1/2013", "12/31/2013")
    ndvi_begin = im_beg.map_normalizedDifference(["N", "R"]).max()
    ndvi_end   = im_end.map_normalizedDifference(["N", "R"]).max()
    ndvidiff = ndvi_end.subtract(ndvi_begin)

    # Mask out clouds based on NDVI composites
    amask = ndvi_begin.gt(cloud_thresh)
    bmask = ndvi_end.gt(cloud_thresh)
    tmask = amask.add(bmask).gt(1)
    burns = ndvidiff.mask(tmask).lte(drop_thresh)

    # Create polygon to indicate nearby fires.
    polygon = ee.Feature.Polygon(bb)
    fires = ee.FeatureCollection(firetable).filterBounds(polygon)
    fire_extent = fires.map_buffer(2000).union()

    # Caclulate number of pixels identified with a sufficiently large
    # drop in NDVI.  Convert to hectares.
    burn_clip = burns.clip(polygon)
    final_area = burn_clip.clip(fire_extent)
    sum_reducer = ee.call("Reducer.sum")
    summ = final_area.reduceRegion(sum_reducer, polygon, scale).getInfo()
    ha = summ['nd'] * 25 / 10000
    
    return ha

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

def finalScars():
    # Calculate the total area of the scars
    x = map(calcScarArea, mk_tile_bboxes(UL, LR))
    return sum(x)



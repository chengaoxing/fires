import datetime
import random
import urllib
import csv
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

def graphNDVIdiff(lat, lon, d=0.01):
    # Accepts the lat-lon coordinates of a square with dimension `d`
    # and saves an image to disk of the vectorized NDVI difference
    # from RapidEye imagery.

    # Generate the difference between minimum NDVI values for each
    # pixel for the supplied beginning and end year.  The result is a
    # rough approximation of burn scars.
    ic = ee.ImageCollection("WRI/RAPIDEYE")
    im_beg = ic.filterDate("1/1/2010", "12/31/2012")
    im_end = ic.filterDate("1/1/2013", "12/31/2013")
    ndvi_begin = im_beg.map_normalizedDifference(["N", "R"]).min()
    ndvi_end   = im_end.map_normalizedDifference(["N", "R"]).min()
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


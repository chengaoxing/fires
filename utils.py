import urllib
from shapely.geometry import Point
from shapely.prepared import prep

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


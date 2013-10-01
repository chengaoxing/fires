import ee
import bbox
import gee_utils

def generateScars(cloud_thresh = 0, drop_thresh = -0.15):
    # Returns the burnscar image generator

    # Authenticate earth engine credentials
    gee_utils.geeAuth()

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
    fires = ee.FeatureCollection(firetable)
    fire_extent = fires.map_buffer(2000).union()

    # Caclulate number of pixels identified with a sufficiently large
    # drop in NDVI.  Convert to hectares.
    final_area = burns.clip(fire_extent)
    return final_area

def generateURL(img, bbox):
    # Return the download URL for a supplied image, clipped to the
    # suppled bounding box.

    # set the scale in meters, a constant 5 for rapideye imagery
    params = {'scale' : 5, 'crs' : 'EPSG:4326', 'region' : str(bbox)}
    return img.getDownloadUrl(params)

def urlList(n = 20):
    # returns a list of `n` urls for download of burn scar image
    img = generateScars()
    bbox_list = bbox.mk_tile_bboxes(bbox.UL, bbox.LR, n = n)
    return map(lambda x: generateURL(img, x), bbox_list)

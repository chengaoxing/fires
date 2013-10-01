import datetime
import time
import ee
import os

def geeAuth(user_path = os.path.expanduser('~')):
    # Authenticate Earth Engine user.  Ensure that the *.p12 key file
    # is in your ~/.ssh/ directory.
    key_file = '%s/.ssh/ee-privatekey.p12' % user_path
    if os.path.exists(key_file):
        acct = '328542535849@developer.gserviceaccount.com'
        ee.Initialize(ee.ServiceAccountCredentials(acct, key_file))
    else:
        raise Exception('Ensure GEE key file is in ~/.ssh directory')

def ndviDiff(ic, begin, mid, end, rapideye=True):
    dt = time.strptime(mid, "%m/%d/%Y")
    return datetime.datetime(*dt[0:6])
    

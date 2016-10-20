from __future__ import print_function
import json
import rasterio
import numpy as np
import requests
from urlparse import urlparse

def respond(err, res=None):
    return {
        'statusCode': '400' if err else '302',
        'body': { 'location': res },
        'headers': {
            'Content-Type': 'application/json',
            'Location': res
        }
    }

# Sample method that would be created from custom code
# this returns the first array
def custom(arr):
    return arr[0,:,:]
    
def handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))

    if 'queryStringParameters' in event:
        params = event['queryStringParameters'] or {}
    else:
        params = {}

    # GET the right tif based on bbox param or z/x/y params 
    # pass the tiff to the custom function
    # return array as PNG from the
    url = "https://grazntzs5b.execute-api.us-east-1.amazonaws.com/prod/idaho_vrt?format=tif&idaho-id=2c82b22c-a0e1-43d8-a124-d7a00c9ce414&x=9138&y=15563&z=15&label=toa"
    print('Accessing url', url)
    s3_url = urlparse(requests.get(url, allow_redirects=False).text)
    print('got s3 url', s3_url.path)
    #url2 = 's3://idaho-vrt-chelm/toa/2c82b22c-a0e1-43d8-a124-d7a00c9ce414/15/9138/15563.tif'
    with rasterio.open('s3://{}'.format(s3_url.path)) as src:
        arr = np.stack(src.read([5,3,2]))
        print('got array', arr.shape)
        processed = custom( arr )
    # 
    # import matplotlib.pyplot as plt
    # plt.imshow(matrix) #Needs to be in row,col order
    # plt.savefig(filename)
    #
    #
        return respond(None, s3_url)

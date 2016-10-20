from __future__ import print_function
import json
import rasterio
import numpy as np
import requests
from urlparse import urlparse
import tempfile

from boto.s3.connection import S3Connection
from custom import run

def respond(res):
    return res

def handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))

    idaho_id = event['idaho-id']
    z = event['z']
    x = event['x']
    y = event['y']
    cache_key = event['cache_key']
    bucket_name = 'idaho-lambda'


    s3 = S3Connection()
    bucket = s3.get_bucket(bucket_name)

    url = "https://grazntzs5b.execute-api.us-east-1.amazonaws.com/prod/idaho_vrt?format=tif&idaho-id={}&x={}&y={}&z={}&label=toa".format(idaho_id, x, y, z)
    s3_url = urlparse(requests.get(url, allow_redirects=False).text)

    with rasterio.open('s3:/{}'.format(s3_url.path)) as src:
        meta = src.meta
        arr = np.stack(src.read())
        print('got array', arr.shape)
        processed = run( arr )

        meta['driver'] = 'PNG'
        meta['count'] = 3
        meta['dtype'] = 'uint8'
        temp = tempfile.NamedTemporaryFile(suffix=".png")

        with rasterio.open(temp.name, 'w', **meta) as sink:
            sink.write(processed)

        key = bucket.new_key(cache_key)
        key.set_contents_from_filename(temp.name)
        temp.delete

        return respond( cache_key )

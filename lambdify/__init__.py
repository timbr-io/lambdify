import os
import sh
import boto3
import json
from boto.s3.connection import S3Connection
from boto.s3.key import Key
import urllib2
import matplotlib.pyplot as plt
from urlparse import urlparse
import rasterio
import requests
import numpy as np
import sys
import mercantile

_session = boto3.Session(profile_name='dg')
_lambda = _session.client("lambda")
_s3conn = S3Connection(profile_name='dg')
_tilecache = _s3conn.get_bucket('idaho-lambda')

_docker = sh.docker.bake('run')

def process_output(line):
    print(line)

def deploy(name, fn=None, bucket='lambda_methods'):
    print 'Preparing lambda method:', name
    orig_dir = sh.pwd().strip()
    dirname = '{}/{}'.format(orig_dir, name)
    zip_name = '{}/{}.zip'.format(dirname, name) 

    if os.path.exists( dirname ):
        sh.rm('-rf', dirname)

    # cp skeleton project data
    sh.cp('-r', os.path.join(os.path.dirname(__file__), 'project'), dirname)

    base_zip = '{}/dist.zip'.format(dirname)
    if not os.path.exists(base_zip):       
        _docker('--rm', '-v', '{}:/app'.format(dirname), 'quay.io/pypa/manylinux1_x86_64', '/app/scripts/build.sh')
        sh.zip('-9', zip_name, '-j', '{}/README.md'.format(dirname))
        sh.cd(os.path.join(dirname, 'build'))
        sh.zip('-r9', zip_name, sh.glob('*'))
        sh.cd(dirname)
    else:
        sh.mv( base_zip, zip_name )

    if fn is not None:
        with open(os.path.join(dirname, 'src', 'custom.py'), 'w') as fh:
            fh.write(fn)

    sh.cp(os.path.join(dirname, 'src', 'template.py'), os.path.join(dirname, 'src', '{}.py'.format(name)))

    sh.cd(os.path.join(dirname, 'src'))
    sh.zip('-r9', zip_name, sh.glob('*'))
    sh.cd(orig_dir)

    def percent_cb(complete, total):
        sys.stdout.write('.')
        sys.stdout.flush()

    print 'Publishing zip file to S3', 's3://{}/{}.zip'.format(bucket, name)
    b = _s3conn.get_bucket(bucket)
    k = Key(b)
    k.key = '{}.zip'.format(name)
    k.set_contents_from_filename(zip_name, cb=percent_cb, num_cb=10)  
 
    try:
        _lambda.delete_function(FunctionName=name)
    except:
        pass
    
    b = _s3conn.get_bucket('idaho-lambda')
    for key in b.list(prefix=name):
        key.delete()

    print 'Creating function'
    code = {'S3Bucket': bucket, 'S3Key': '{}.zip'.format(name)}
    handler = '{}.handler'.format(name)
    role = 'arn:aws:iam::523345300643:role/lambda_s3_exec_role'
    _lambda.create_function(FunctionName=name, Code=code, Role=role, Handler=handler, Runtime='python2.7', Timeout=60, MemorySize=1024)

     
def preview(fname, idaho_id, z, x, y):
    cache_key = "{fname}/{idaho_id}/{z}/{x}/{y}".format(idaho_id=idaho_id, fname=fname, z=z, x=x, y=y)
    payload = {"idaho_id": idaho_id, "z": z, "x": x, "y": y, "cache_key": cache_key}
    key = _tilecache.get_key(_lambda.invoke(FunctionName=fname, Payload=json.dumps(payload)), validate=False)
    url = "http://s3.amazonaws.com/{bucket}/{cache_key}".format(bucket=key.bucket.name, cache_key=cache_key)
    f = urllib2.urlopen(url)
    img = plt.imread(f)
    plt.imshow(img)
    plt.show() 


def tinker(fn, idaho_id, z=None, x=None, y=None):
    if z is None and x is None and y is None:
        info = requests.get('http://idaho.timbr.io/{}.json'.format(idaho_id)).json()
        center = info['properties']['center']['coordinates'] 
        tile = mercantile.tile(center[0], center[1], 15)
        z, x, y = tile.z, tile.x, tile.y 
          
    payload = {"idaho_id": idaho_id, "z": z, "x": x, "y": y}
    
    url = "https://grazntzs5b.execute-api.us-east-1.amazonaws.com/prod/idaho_vrt?format=tif&idaho-id={}&x={}&y={}&z={}&label=toa".format(idaho_id, x, y, z)
    s3_url = urlparse(requests.get(url, allow_redirects=False).text)
    #print url
    with rasterio.open('s3:/{}'.format(s3_url.path)) as src:
        arr = np.stack(src.read())
        processed = fn( arr )

    plt.imshow(np.rollaxis(processed, 0, 3))
    plt.show()

def get_code(path):
    with open(path, 'r') as ipynb:
        cells = json.loads(ipynb.read())['cells']

    for cell in cells:
        if 'lambda_cell' in cell['metadata']:
            return ''.join(cell['source'])


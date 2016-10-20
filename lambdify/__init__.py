import os
import sh
import boto3
import json
from boto.s3.connection import S3Connection
import urllib2
import matplotlib.pyplot as plt

_session = boto3.Session(profile_name='dg')
_lambda = _session.client("lambda")
_s3conn = S3Connection(profile_name='dg')
_tilecache = _s3conn.get_bucket('idaho-lambda')

_docker = sh.docker.bake('run')

def process_output(line):
    print(line)

def create(name, fn=None, bucket='lambda_methods'):
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

    print 'Publishing zip file to S3', 's3://{}/{}.zip'.format(bucket, name)
    sh.aws('s3', 'cp', zip_name, 's3://{}/{}.zip'.format(bucket, name), '--region', 'us-east-1', '--acl', 'public-read', _out='process_output')
   
    try:
        sh.aws('lambda', 'delete-function', '--region', 'us-east-1', '--function-name', name)
    except:
        pass
    
    sh.aws('s3', 'rm', '--region', 'us-east-1', '--recursive', 's3://idaho-lambda/{}'.format(name))

    print 'Creating function'
    sh.aws('lambda', 'create-function', '--region', 'us-east-1', '--function-name', name, '--code', 'S3Bucket={},S3Key={}.zip'.format(bucket, name), '--role', 'arn:aws:iam::523345300643:role/lambda_s3_exec_role', '--handler', '{}.handler'.format(name), '--runtime', 'python2.7', '--timeout', '60', '--memory-size', '1024')
     
def preview(fname, idaho_id, z, x, y):
    cache_key = "{idaho_id}/{fname}/{z}/{x}/{y}".format(idaho_id=idaho_id, fname=fname, z=z, x=x, y=y)
    payload = {"idaho_id": idaho_id, "z": z, "x": x, "y": y, "cache_key": cache_key}
    key = _tilecache.get_key(_lambda.invoke(FunctionName=fname, Payload=json.dumps(payload)), validate=False)
    url = "http://s3.amazonaws.com/{bucket}/{cache_key}".format(bucket=key.bucket.name, cache_key=cache_key)
    f = urllib2.urlopen(url)
    img = plt.imread(f)
    plt.imshow(img)
    plt.show() 

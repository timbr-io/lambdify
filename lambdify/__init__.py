import os
import sh

docker = sh.docker.bake('run')

def process_output(line):
    print(line)

def create(name, fn='python code string', bucket='lambda_methods'):
    print 'Preparing lambda method:', name
    orig_dir = sh.pwd().strip()
    dirname = '{}/{}'.format(orig_dir, name)
    zip_name = '{}/{}.zip'.format(dirname, name) 

    if not os.path.exists( dirname ):
        # cp skeleton project data
        sh.cp('-r', os.path.join(os.path.dirname(__file__), 'project'), dirname)

    base_zip = '{}/dist.zip'.format(dirname)
    if not os.path.exists(base_zip):       
        docker('--rm', '-v', '{}:/app'.format(dirname), 'quay.io/pypa/manylinux1_x86_64', '/app/scripts/build.sh')
        sh.zip('-9', zip_name, '-j', '{}/README.md'.format(dirname))
        sh.cd(os.path.join(dirname, 'build'))
        sh.zip('-r9', zip_name, sh.glob('*'))
        sh.cd(dirname)
    else:
        sh.cp( base_zip, zip_name )

    ## TODO do the code injection into a template thing
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
    print 'Creating function'
    sh.aws('lambda', 'create-function', '--region', 'us-east-1', '--function-name', name, '--code', 'S3Bucket={},S3Key={}.zip'.format(bucket, name), '--role', 'arn:aws:iam::523345300643:role/lambda_s3_exec_role', '--handler', '{}.handler'.format(name), '--runtime', 'python2.7', '--timeout', '60', '--memory-size', '1024')
      

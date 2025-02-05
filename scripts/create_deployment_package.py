import os
import shutil
import subprocess
import sys
import venv
import boto3
import argparse

# add --recreate_all flag to recreate the deployment package
# python scripts/create_deployment_package.py --recreate_all

# To just send to AWS: 
# python scripts/create_deployment_package.py

os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

def create_deployment_package(recreate_all=True):
    """
    Create a deployment package for AWS Lambda

    
    Args:
        recreate_all: Boolean, if True recreates venv and zip file, if False uses existing ones
    """
    
    venv_dir = 'temp_venv'
    package_dir = 'package'
    zip_file = 'deployment_package.zip'
    
    try:
        if recreate_all:
            print("Creating fresh deployment package...")
            # Create and activate a temporary virtual environment
            if os.path.exists(venv_dir):
                shutil.rmtree(venv_dir)
            venv.create(venv_dir, with_pip=True)
            
            # Get path to pip in the virtual environment
            if sys.platform == 'win32':
                pip_path = os.path.join(venv_dir, 'Scripts', 'pip.exe')
            else:
                pip_path = os.path.join(venv_dir, 'bin', 'pip')
            
            # Create a temporary directory for the package
            if os.path.exists(package_dir):
                shutil.rmtree(package_dir)
            os.makedirs(package_dir)
            
            # Copy all Python files
            shutil.copytree('platforms', f'{package_dir}/platforms')
            shutil.copytree('handlers', f'{package_dir}/handlers')
            shutil.copy('handler.py', f'{package_dir}/handler.py')
            shutil.copy('constants.py', f'{package_dir}/constants.py')
            shutil.copy('auth.py', f'{package_dir}/auth.py')
            
            # Install dependencies to the package directory using the clean virtual environment
            subprocess.check_call([
                pip_path, 'install',
                '--target', package_dir,
                'google-api-python-client',
                'google-auth-httplib2',
                'google-auth-oauthlib',
                'pytz'
            ])
            
            # Create the zip file
            if os.path.exists(zip_file):
                os.remove(zip_file)
            shutil.make_archive('deployment_package', 'zip', package_dir)
            print("Created deployment_package.zip")
        else:
            print("Using existing deployment package...")
            if not os.path.exists(zip_file):
                raise FileNotFoundError(f"Cannot find {zip_file}. Run with --recreate flag to create it.")
        
        # Upload to Lambda using boto3 (it will automatically use credentials from aws configure)
        print("Uploading to Lambda...")
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        
        with open(zip_file, 'rb') as zip_file:
            lambda_client.update_function_code(
                FunctionName='findOpenTimes',
                ZipFile=zip_file.read()
            )
        
        print("Successfully updated Lambda function")
        
    finally:
        if recreate_all:
            # Clean up
            print("Cleaning up temporary files...")
            if os.path.exists(package_dir):
                shutil.rmtree(package_dir)
            if os.path.exists(venv_dir):
                shutil.rmtree(venv_dir)

def main():
    parser = argparse.ArgumentParser(description='Create and deploy Lambda package')
    parser.add_argument('--recreate', action='store_true', 
                      help='Recreate virtual environment and zip file (default: False)')
    args = parser.parse_args()
    
    create_deployment_package(recreate_all=args.recreate)

if __name__ == '__main__':
    main()


# CLI command
# 
# python scripts/create_deployment_package.py
# aws lambda update-function-code --function-name findOpenTimes --zip-file fileb://deployment_package.zip
import os
import shutil
import subprocess
import sys
import venv

def create_deployment_package():
    """Create a deployment package for AWS Lambda"""
    
    venv_dir = 'temp_venv'
    package_dir = 'package'
    zip_file = 'deployment_package.zip'
    
    try:
        print("Creating deployment package...")
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
        shutil.copy('lambda_function.py', f'{package_dir}/lambda_function.py')
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
        
    finally:
        # Clean up
        print("Cleaning up temporary files...")
        if os.path.exists(package_dir):
            shutil.rmtree(package_dir)
        if os.path.exists(venv_dir):
            shutil.rmtree(venv_dir)

if __name__ == '__main__':
    create_deployment_package()


# CLI command
# 
# python scripts/create_deployment_package.py
# aws lambda update-function-code --function-name findOpenTimes --zip-file fileb://deployment_package.zip
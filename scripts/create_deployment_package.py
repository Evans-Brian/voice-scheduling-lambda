import os
import shutil
import subprocess
import sys
import venv
import argparse

# Usage:
# python scripts/create_deployment_package.py             # Uses existing venv if available
# python scripts/create_deployment_package.py --fresh-venv  # Creates new venv from scratch

def create_deployment_package(recreate_venv=False):
    """
    Create a deployment package for AWS Lambda
    
    Args:
        recreate_venv: Boolean, if True recreates virtual environment, if False uses existing one
    """
    # Get the project root directory (parent of scripts directory)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Define paths relative to project root
    venv_dir = os.path.join(root_dir, 'temp_venv')
    package_dir = os.path.join(root_dir, 'package')
    zip_file = os.path.join(root_dir, 'deployment_package.zip')
    
    try:
        print("Creating deployment package...")
        
        # Handle virtual environment
        if recreate_venv:
            print("Creating fresh virtual environment...")
            if os.path.exists(venv_dir):
                shutil.rmtree(venv_dir)
            venv.create(venv_dir, with_pip=True)
        elif not os.path.exists(venv_dir):
            print(f"Virtual environment not found at '{venv_dir}', creating one...")
            venv.create(venv_dir, with_pip=True)
        else:
            print("Using existing virtual environment...")
            
        # Get path to pip in the virtual environment
        if sys.platform == 'win32':
            pip_path = os.path.join(venv_dir, 'Scripts', 'pip.exe')
        else:
            pip_path = os.path.join(venv_dir, 'bin', 'pip')
        
        # Create a temporary directory for the package
        if os.path.exists(package_dir):
            shutil.rmtree(package_dir)
        os.makedirs(package_dir)
        
        # Copy all files
        shutil.copytree('platforms', f'{package_dir}/platforms')
        shutil.copytree('handlers', f'{package_dir}/handlers')
        shutil.copy('lambda_function.py', f'{package_dir}/lambda_function.py')
        shutil.copy('constants.py', f'{package_dir}/constants.py')
        shutil.copy('auth.py', f'{package_dir}/auth.py')
        shutil.copy('token.pickle', os.path.join(package_dir, 'token.pickle'))
        
        # Install dependencies to the package directory using the virtual environment
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
        # Clean up package directory
        print("Cleaning up package directory...")
        if os.path.exists(package_dir):
            shutil.rmtree(package_dir)

def main():
    parser = argparse.ArgumentParser(description='Create Lambda deployment package')
    parser.add_argument('--fresh-venv', action='store_true', 
                      help='Create fresh virtual environment (default: False)')
    args = parser.parse_args()
    
    create_deployment_package(recreate_venv=args.fresh_venv)

if __name__ == '__main__':
    main()


# CLI command
# 
# python scripts/create_deployment_package.py
# aws lambda update-function-code --function-name findOpenTimes --zip-file fileb://deployment_package.zip
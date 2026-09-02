# pip install pynacl requests
import requests
import base64
from nacl import encoding, public
import argparse
import traceback
import os

class GitHubRepoParameterManager:
    """
    Helps to manage Github secrets and variables
    """
    GITHUB_URL = "https://api.github.com/repos/"
    HEADERS = {
        "Accept": "application/vnd.github+json",
        "Authorization":"",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    owner          = ""
    repo           = ""
    access_token   = "" #https://github.com/settings/personal-access-tokens
    secrets_file   = ""
    variables_file = ""
    
    def __init__(self, config):
        self.owner = config.owner if hasattr(config, 'owner') else None
        self.repo = config.repo if hasattr(config, 'repo') else None
        self.access_token = config.access_token if hasattr(config, 'access_token') else None
        self.secrets_file = config.secrets_file if hasattr(config, 'secrets_file') else None
        self.variables_file = config.variables_file if hasattr(config, 'variables_file') else None
        if self.access_token:
            self.HEADERS["Authorization"]= f"Bearer {self.access_token}"

    def modify_secret(self, secret_name, secret_value):
        """Modifies a secret in the repository."""
        pk_url = f"{self.GITHUB_URL}{self.owner}/{self.repo}/actions/secrets/public-key"
        pk_response = requests.get(pk_url, headers=self.HEADERS)
        pk_response=pk_response.json()
        key_id = pk_response["key_id"]
        public_key_base64 = pk_response["key"]
        public_key = public.PublicKey(public_key_base64, encoding.Base64Encoder)
        sealed_box = public.SealedBox(public_key)
        encrypted_bytes = sealed_box.encrypt(secret_value.encode("utf-8"))
        encrypted_string = base64.b64encode(encrypted_bytes).decode("utf-8")
        secret_url = f"{self.GITHUB_URL}{self.owner}/{self.repo}/actions/secrets/{secret_name}"
        payload = {
                "encrypted_value": encrypted_string,
                "key_id": key_id
            }
        response = None
        try:
            response = requests.put(secret_url, headers=self.HEADERS, json=payload)
        except requests.RequestException:
            traceback.print_exc()
        if response.status_code in [201, 204]:
            print(f"Secret '{secret_name}' successfully configured!")
        else:
            print(f"Error {response.status_code}:", response.json())
            
    def delete_secret(self, secret_name):
        """Deletes a secret from the repository."""
        secret_url = f"{self.GITHUB_URL}{self.owner}/{self.repo}/actions/secrets/{secret_name}"
        response= None
        try:
            response = requests.delete(secret_url, headers=self.HEADERS)
        except requests.RequestException:
            traceback.print_exc()

        if response.status_code in [201, 204]:
            print(f"Secret '{secret_name}' successfully deleted!")
        else:
            print(f"Error {response.status_code}:", response.json())

    def modify_variable(self, variable_name, variable_value):
        """
        Modifies a variable in the repository.
        """
        url =  f"{self.GITHUB_URL}{self.owner}/{self.repo}/actions/variables"
        data = {
            "name": f"{variable_name}",
            "value": f"{variable_value}"
        }

        response = requests.post(url, headers=self.HEADERS, json=data)

        if response.status_code == 201:
            print("Variable created successfully!")
        else:
            print(f"Failed: {response.status_code}", response.json())
    def delete_variable(self, variable_name):
        """
        Deletes a variable from the repository.
        """
        variable_url = f"{self.GITHUB_URL}{self.owner}/{self.repo}/actions/variables/{variable_name}"
        response= None
        try:
            response = requests.delete(variable_url, headers=self.HEADERS)
        except requests.RequestException:
            traceback.print_exc()
        if response.status_code in [201, 204]:
            print(f"variable '{variable_name}' successfully deleted!")
        else:
            print(f"Error {response.status_code}:", response.json())

parser = argparse.ArgumentParser( prog='GitHubRepoParameterManager.py', description='''This is a Python script to manage github repository secrets and variables''',epilog=''' ''')
requiredParameter = parser.add_argument_group('Required Parameter')
requiredParameter.add_argument('-o','--owner',    dest='owner',   help='The name of the  S3 bucket where files are downloaded from or  uploaded', required=True)
requiredParameter.add_argument('-r','--repo',  dest='repo',    help='A flag that specifies that a file or group of files should be downloaded from a bucket')
requiredParameter.add_argument('-t','--token',       dest='access_token',     default=None,   help='The key to be used to identify an object in an S3 bucket.')
parser.add_argument('-v','--vars_file',  dest='variables_file',  help='A flag that specifies that a file or  group of files should be uploadd to a bucket')
parser.add_argument('-s','--secrets_file',      dest='secrets_file',    default=None,   help='The path to the file or group of files that should be processed.')

if __name__== '__main__':
    parameters = parser.parse_args()      
    repo_manager = GitHubRepoParameterManager(parameters)
    if parameters.secrets_file:
        if os.path.exists(parameters.secrets_file):
            with open(parameters.secrets_file, 'r') as f:
                for line in f:
                    secret_name, secret_value = line.strip().split('=', 1)
                    repo_manager.modify_secret(secret_name, secret_value)
        else:
            print(f"Secrets file '{parameters.secrets_file}' does not exist.")
    if parameters.variables_file:
        if os.path.exists(parameters.variables_file):
            with open(parameters.variables_file, 'r') as f:
                for line in f:
                    variable_name, variable_value = line.strip().split('=', 1)
                    repo_manager.modify_variable(variable_name, variable_value)
        else:
            print(f"Variables file '{parameters.variables_file}' does not exist.")
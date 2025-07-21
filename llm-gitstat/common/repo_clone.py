import os
import subprocess
import shutil
import urllib.parse

def clone_git_repo(repo_url, local_folder):
  """Clones a Git repository into the specified local folder.

  Args:
    repo_url: The URL of the Git repository to clone.
    local_folder: The local folder where the repository will be cloned.
  """

  # Create the local folder if it doesn't exist
  if not os.path.exists(local_folder):
    os.makedirs(local_folder)

  # Clone the repository
  subprocess.call(['git', 'clone', repo_url, local_folder])

# Example usage
repo_url = "https://github.com/user/repo.git"
local_folder = "my_repo"
clone_git_repo(repo_url, local_folder)



def get_last_part_of_git_url(url):
  # Parse the URL
  parsed_url = urllib.parse.urlparse(url)

  # Extract the path component
  path = parsed_url.path

  # Split the path into parts and get the last part
  last_part = path.split('/')[-1]

  return last_part


def process_repo(git_repo_url):
  name = get_last_part_of_git_url(git_repo_url)
  # Create the temporary directory
  os.makedirs(directory_name, exist_ok=True)

  # Call the function with the directory path
  function_to_call(directory_name)

  # Remove the temporary directory
  shutil.rmtree(directory_name)

# Example usage
def my_function(directory_path):
  # Do something with the directory
  print(f"Working in directory: {directory_path}")

directory_name = "temp_dir"
create_and_remove_directory(directory_name, my_function)
import os
from github import Github
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Retrieve GitHub token from .env file
github_token = os.getenv('GITHUB_TOKEN')
if not github_token:
    raise EnvironmentError("GitHub token not found in the .env file.")

# Initialize GitHub client
g = Github(github_token)

# Function to read and parse Metainfo.txt from GitHub
def parse_metainfo_from_github(file_content):
    """Parses the metainfo file content to extract key-value pairs, handling multi-line fields."""
    metainfo = {}
    current_key = None
    for line in file_content.splitlines():
        stripped_line = line.strip()
        if not stripped_line:
            continue  # Skip empty lines
        if ':' in stripped_line and not stripped_line.startswith('-'):
            # New key-value pair
            key, value = stripped_line.split(':', 1)
            current_key = key.strip()
            metainfo[current_key] = value.strip().strip("'").strip('"')  # Remove quotes if present
        elif current_key and stripped_line.startswith('-'):
            # Continuation of a multi-line value (e.g., keywords list)
            metainfo[current_key] += "\n" + stripped_line.strip().strip("'").strip('"')  # Remove quotes from multi-line
        else:
            current_key = None  # Reset key if format doesn't match
    return metainfo

# Function to generate README content with space lines between entries and centered images
def generate_readme_content(metainfo, images):
    """Generates the README.md content using metainfo and images."""
    readme_content = (
        '<div style="margin: 0; padding: 0; text-align: center; border: none;">\n'
        '<a href="https://quantlet.com" target="_blank" style="text-decoration: none; border: none;">\n'
        '<img src="https://github.com/StefanGam/test-repo/blob/main/quantlet_design.png?raw=true" '
        'alt="Header Image" width="100%" style="margin: 0; padding: 0; display: block; border: none;" />\n'
        '</a>\n'
        '</div>\n\n'
    )

    readme_content += "```\n"  # Start a code block in Markdown

    # Add metadata entries in a clean format with an extra newline for spacing
    for key, value in metainfo.items():
        readme_content += f"{key}: {value}\n\n"

    readme_content += "```\n"  # End the code block in Markdown

    # Images Section (centered using HTML)
    if images:
        for image in images:
            readme_content += f'<div align="center">\n<img src="{image}" alt="Image" />\n</div>\n\n'

    return readme_content

# Function to find image files in a GitHub directory
def find_images_in_github(repo, path):
    """Finds image files in a GitHub repository directory."""
    images = []
    contents = repo.get_contents(path)
    for content in contents:
        if content.type == 'file' and content.name.endswith(('.png', '.jpg', '.jpeg', '.gif')):
            images.append(content.download_url)
    return images

# Function to process a single repository
def process_repository(repo):
    """Processes a single repository to generate README files."""
    print(f"Processing repository: {repo.name}")

    # Process the root directory
    root_contents = repo.get_contents("")  # Start from the root directory

    root_readme_file = next((file for file in root_contents if file.name.lower() == 'readme.md'), None)
    root_metainfo_file = next((file for file in root_contents if file.name.lower() == 'metainfo.txt'), None)
    if not root_readme_file and root_metainfo_file:
        metainfo = parse_metainfo_from_github(root_metainfo_file.decoded_content.decode())
        images = find_images_in_github(repo, "")

        # Generate README content and create the file
        readme_content = generate_readme_content(metainfo, images)
        repo.create_file(
            "README.md",
            "Create README.md at root level",
            readme_content,
            branch=repo.default_branch
        )
        print("README.md created in the root directory")

    # Use a queue to handle directory traversal
    directories_to_check = [root_contents]
    while directories_to_check:
        current_contents = directories_to_check.pop(0)
        for content in current_contents:
            if content.type == 'dir':
                folder_contents = repo.get_contents(content.path)

                readme_file = next((file for file in folder_contents if file.name.lower() == 'readme.md'), None)
                metainfo_file = next((file for file in folder_contents if file.name.lower() == 'metainfo.txt'), None)

                if not readme_file and metainfo_file:
                    metainfo = parse_metainfo_from_github(metainfo_file.decoded_content.decode())
                    images = find_images_in_github(repo, content.path)

                    # Generate README content and create the file
                    readme_content = generate_readme_content(metainfo, images)
                    repo.create_file(
                        f"{content.path}/README.md",
                        "Create README.md in folder",
                        readme_content,
                        branch=repo.default_branch
                    )
                    print(f"README.md created in {content.path}")

                directories_to_check.append(folder_contents)

# Function to process all repositories in an organization
def create_readme_for_all_repos(org_name):
    """Processes all repositories in a given GitHub organization."""
    org = g.get_organization(org_name)
    repos = org.get_repos()

    for repo in repos:
        try:
            process_repository(repo)
        except Exception as e:
            print(f"Error processing repository {repo.name}: {e}")

# Example usage:
create_readme_for_all_repos("QuantLet")

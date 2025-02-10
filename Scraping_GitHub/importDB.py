import re
import os
import logging
from github import Github
import mariadb
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(filename='metadata_extraction.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# MariaDB database connection settings from environment variables
MARIADB_HOST = os.getenv('MARIADB_HOST')
MARIADB_USER = os.getenv('MARIADB_USER')
MARIADB_PORT = int(os.getenv('MARIADB_PORT', default=3306))
MARIADB_PASSWORD = os.getenv('MARIADB_PASSWORD')
MARIADB_DATABASE = os.getenv('MARIADB_DATABASE')

# GitHub authentication token from environment variables
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

# Connect to the MariaDB database
try:
    connection = mariadb.connect(
        host=MARIADB_HOST,
        user=MARIADB_USER,
        port=MARIADB_PORT,
        password=MARIADB_PASSWORD,
        database=MARIADB_DATABASE
    )
    print(f"Conencting to mariadb ...")
except mariadb.Error as e:
    print(f"Error connecting to MariaDB Platform: {e}")
    exit(1)

# Create a cursor object to execute SQL queries
cursor = connection.cursor()

delete_table_query = """
DROP TABLE IF EXISTS metadata;
"""
cursor.execute(delete_table_query)
print("Metadata table cleared successfully.")

# Create metadata table if it doesn't exist
create_table_query = """
CREATE TABLE IF NOT EXISTS metadata (
    id INT AUTO_INCREMENT PRIMARY KEY,
    repo_name VARCHAR(255),
    name_of_quantlet VARCHAR(255),
    published_in TEXT,
    description TEXT,
    keywords TEXT,
    author VARCHAR(255),
    submitted VARCHAR(255),
    url VARCHAR(255),
    parent_folder_url VARCHAR(255),
    language VARCHAR(50),
    image_url VARCHAR(255)
)
"""

# Execute the create table query
cursor.execute(create_table_query)
print("Metadata table created successfully.")

# Function to clean strings
def clean_string(_str):
    if isinstance(_str, list):
        cleaned_strings = [re.sub(r"[\"''']+", "", s.strip()) for s in _str]
        return ', '.join(cleaned_strings)
    elif isinstance(_str, str):
        return re.sub(r"[\"''']+", "", _str.strip())
    else:
        raise ValueError('Input is neither string nor list')

# Function to extract and combine keywords
def extract_keywords(metainfo_content):
    all_keywords = []
    keywords_match = re.search(r'Keywords\s*:\s*(.*)', metainfo_content, re.IGNORECASE)
    if keywords_match:
        all_keywords.extend([re.sub(r"[\"'''-]+", "", kw.strip()) for kw in keywords_match.group(1).split(',')])
    keyword_lines = re.findall(r'^\s*-\s*(.+)$', metainfo_content, re.MULTILINE)
    if keyword_lines:
        cleaned_keywords = [re.sub(r"[\"'''-]+", "", kw.strip()) for kw in keyword_lines]
        all_keywords.extend(cleaned_keywords)
    return ', '.join(all_keywords) if all_keywords else 'nan'

# Function to insert metadata into MariaDB database
def insert_metadata_into_mariadb(repo_name, name, published_in, description, keywords, author, submitted, url, parent_folder_url, language, image_url):
    try:
        insert_query = """
        INSERT INTO metadata (repo_name, name_of_quantlet, published_in, description, keywords, author, submitted, url, parent_folder_url, language, image_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.execute(insert_query, (
            repo_name, name, published_in, description, keywords, author, submitted, url, parent_folder_url, language, image_url
        ))
        connection.commit()
        print("Metadata inserted into MariaDB database successfully.")
    except mariadb.Error as error:
        print("Error inserting metadata into MariaDB database:", error)

# GitHub authentication
github = Github(GITHUB_TOKEN)

# Specify the owner whose repositories to fetch
owner_name = 'QuantLet'

# Get the owner object
owner = github.get_user(owner_name)

# Function to recursively search for Metainfo.txt files in each repository
def search_metainfo_in_repo(repo):
    try:
        contents_stack = [repo.get_contents("")]
        while contents_stack:
            contents = contents_stack.pop()
            for content in contents:
                if content.type == "file" and content.name.lower() in ["metainfo.txt", "Metainfo.txt"]:
                    metainfo_content = content.decoded_content.decode('utf-8')
                    name_match = re.search(r'Name of QuantLet\s*:\s*(.*)', metainfo_content, re.IGNORECASE)
                    published_in_match = re.search(r'Published in\s*:\s*(.*)', metainfo_content, re.IGNORECASE)
                    description_match = re.search(r'Description\s*:\s*(.*)', metainfo_content, re.IGNORECASE)
                    author_match = re.search(r'Author\s*:\s*(.*)', metainfo_content, re.IGNORECASE)
                    submitted_match = re.search(r'Submitted\s*:\s*(.*)', metainfo_content, re.IGNORECASE)
                    name = clean_string([name_match.group(1)]) if name_match else 'nan'
                    published_in = clean_string([published_in_match.group(1)]) if published_in_match else 'nan'
                    description = clean_string([description_match.group(1).lstrip('-').strip()]) if description_match else 'nan'
                    keywords = extract_keywords(metainfo_content)
                    author = clean_string([author_match.group(1)]) if author_match else 'nan'
                    submitted = clean_string([submitted_match.group(1)]) if submitted_match else 'nan'
                    parent_folder_url = os.path.dirname(content.html_url)
                    language = repo.language
                    image_url = 'nan'
                    parent_directory = os.path.dirname(content.path)
                    parent_contents = repo.get_contents(parent_directory)
                    for item in parent_contents:
                        if item.type == "file" and item.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                            image_url = item.download_url
                            break
                    insert_metadata_into_mariadb(repo.full_name, name, published_in, description, keywords, author,
                                                submitted, content.html_url, parent_folder_url, language, image_url)
                elif content.type == "dir":
                    sub_contents = repo.get_contents(content.path)
                    contents_stack.append(sub_contents)
    except Exception as e:
        logging.error(f"Error processing repository {repo.full_name}: {e}")

# Iterate over all repositories of the owner
for repo in owner.get_repos():
    search_metainfo_in_repo(repo)

# Close the cursor and connection
cursor.close()
connection.close()


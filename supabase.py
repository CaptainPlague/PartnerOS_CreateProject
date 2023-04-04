import os
import sys
import subprocess
from supabase import create_client
from dotenv import load_dotenv


def run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        print(f"Error executing command: {command}")
        print(stderr)
        sys.exit(1)

    return stdout.strip()


def create_supabase_project(project_name):
    print(f"Creating a new Supabase project: {project_name}")

    # Create a new directory for the project
    os.makedirs(project_name, exist_ok=True)

    # Change the current directory to the project directory
    os.chdir(project_name)

    # Run `supabase init` to initialize the project
    run_command("supabase init")

    print(f"Supabase project created successfully: {project_name}")


def get_supabase_client():
    # Load environment variables from the .env file
    load_dotenv()

    # Get the Supabase API URL and key from environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    # Create a Supabase client
    supabase = create_client(supabase_url, supabase_key)

    return supabase


def fetch_data_from_table(table_name):
    supabase = get_supabase_client()

    # Fetch all rows from the specified table
    response = supabase.from_(table_name).select()

    if response.error:
        print(f"Error fetching data from {table_name}: {response.error}")
    else:
        print(f"Data from {table_name}:")
        for row in response.data:
            print(row)


if __name__ == "__main__":
    project_name = "my_supabase_project"
    create_supabase_project(project_name)

    # Example usage: fetch data from a table called "users"
    fetch_data_from_table("users")
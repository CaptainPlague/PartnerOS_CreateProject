import subprocess
import os
import sys


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


if __name__ == "__main__":
    project_name = "my_supabase_project"
    create_supabase_project(project_name)
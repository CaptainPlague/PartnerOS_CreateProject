import requests
import json


def authenticate(email, password):
    auth_url = "https://auth.supabase.co/auth/v1/token?grant_type=password"
    headers = {
        "apikey": "public-anon-xxxxxxxxxxxxxx",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "email": email,
        "password": password,
    }
    response = requests.post(auth_url, headers=headers, data=data)
    access_token = response.json()["access_token"]
    return access_token


def create_project(access_token, project_name, org_id):
    create_project_url = "https://api.supabase.io/projects"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    data = {
        "name": project_name,
        "org_id": org_id,
    }
    response = requests.post(create_project_url, headers=headers, json=data)
    project_id = response.json()["id"]
    return project_id


def get_api_key_and_url(access_token, project_id):
    api_key_url = f"https://api.supabase.io/projects/{project_id}/api_keys"
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    response = requests.get(api_key_url, headers=headers)
    api_key_data = response.json()

    supabase_url = f"https://{project_id}.supabase.co"
    supabase_key = [key["key"] for key in api_key_data if key["name"] == "public"][0]

    return supabase_url, supabase_key


def main():
    # Replace these values with your actual Supabase credentials
    email = "chinezulpechinez@gmail.com"
    password = "Password123."
    org_id = "ilhdskyhpsqkahomgklh"
    project_name = "PythonCreatedProject"

    access_token = authenticate(email, password)
    project_id = create_project(access_token, project_name, org_id)
    supabase_url, supabase_key = get_api_key_and_url(access_token, project_id)

    print(f"Supabase URL: {supabase_url}")
    print(f"Supabase Key: {supabase_key}")


if __name__ == "__main__":
    main()

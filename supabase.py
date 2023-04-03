import httpx
import json

# Replace these with your own Supabase project URL and API key
supabase_url = "https://xnnhyzgihyreuentwged.supabase.co"
supabase_api_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhubmh5emdpaHlyZXVlbnR3Z2VkIiwicm9sZSI6ImFub24iLCJpYXQiOjE2NzYyODczMTIsImV4cCI6MTk5MTg2MzMxMn0.Xg9q0HXmWXzouYYPohaKAsyIA6lUQTRlX2CkuLJS47U"
headers = {
    "apikey": supabase_api_key,
    "Content-Type": "application/json"
}

def create_project(project_name):
    endpoint = f"{supabase_url}/v1/projects"
    data = {
        "name": "Test Project",
        "organization_id": "combined-fuchsia-lion",
        "db_pass": "redacted",
        "region": "eu-west-1",
        "plan": "free",
        "kps_enabled": ""
    }
    print('JSON DUMP', json.dumps(data))
    response = httpx.post(endpoint, headers=headers,  data=json.dumps(data))

    if response.status_code == 201:
        print("Task created successfully")
        print(response.json())
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    project_name = "Test Project Creation"
    create_project(project_name)
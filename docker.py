import docker
import os

# Set up the Docker client
client = docker.from_env()

# Define the necessary services and their images
services = {
    "postgres": "supabase/postgres:latest",
    "gotrue": "supabase/gotrue:latest",
    "realtime": "supabase/realtime:latest",
}

# Create a network for the services to communicate with each other
network = client.networks.create("supabase")

# Set the environment variables for each service
postgres_env = [
    "POSTGRES_DB=postgres",
    "POSTGRES_USER=postgres",
    "POSTGRES_PASSWORD=postgres",
]

gotrue_env = [
    "GOTRUE_API_HOST=0.0.0.0",
    "GOTRUE_API_PORT=9999",
    "GOTRUE_JWT_SECRET=mysecret",
    "GOTRUE_API_DATABASE_URL=postgres://postgres:postgres@postgres:5432/postgres?sslmode=disable",
]

realtime_env = [
    "REALTIME_API_HOST=0.0.0.0",
    "REALTIME_API_PORT=8888",
    "REALTIME_JWT_SECRET=mysecret",
    "REALTIME_DATABASE_URL=postgres://postgres:postgres@postgres:5432/postgres?sslmode=disable",
]

# Create and run the services
postgres_container = client.containers.run(
    services["postgres"],
    name="postgres",
    environment=postgres_env,
    network="supabase",
    detach=True,
)

gotrue_container = client.containers.run(
    services["gotrue"],
    name="gotrue",
    environment=gotrue_env,
    network="supabase",
    detach=True,
)

realtime_container = client.containers.run(
    services["realtime"],
    name="realtime",
    environment=realtime_env,
    network="supabase",
    detach=True,
)

print("Local Supabase project created.")
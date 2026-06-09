import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load variables from .env
load_dotenv()

# Get the Neo4j credentials
URI = os.getenv('NEO4J_URI')
USERNAME = os.getenv('NEO4J_USERNAME')
PASSWORD = os.getenv('NEO4J_PASSWORD')

print(f"Attempting to connect to Neo4j AuraDB at: {URI}")

try:
    # Attempt to create a connection
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print("\n✅ SUCCESS! EduGen is connected to the Graph Database.")
    driver.close()
    
except Exception as e:
    print(f"\n❌ CONNECTION FAILED. Error details:\n{e}")
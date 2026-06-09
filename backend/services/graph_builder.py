import os
from pathlib import Path
from dotenv import load_dotenv

# LangChain and AI Imports
from langchain_ollama import ChatOllama  # <-- NEW: Using local Ollama instead of Gemini
from langchain_neo4j import Neo4jGraph 
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_core.documents import Document

# 1. Load the Vault (.env file)
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# 2. Connect to Neo4j
print("Connecting to Neo4j Database...")
graph = Neo4jGraph(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD"),
    database=os.getenv("NEO4J_DATABASE")
)

# 3. Initialize the Local OLLAMA Brain (Gemma 2)
print("Waking up local Gemma model for Knowledge Extraction...")
llm = ChatOllama(
    model="gemma2:2b", # Points to the exact local model running on your machine
    temperature=0 
)

# 4. Set up the LangChain Graph Transformer
llm_transformer = LLMGraphTransformer(llm=llm)

def check_database_knowledge():
    """
    Queries the Neo4j database to show what Gemma actually saved.
    """
    print("\n--- Fetching Knowledge from Neo4j ---")
    
    # Cypher query to get 15 relationships
    query = """
    MATCH (n)-[r]->(m) 
    RETURN n.id AS source, type(r) AS relationship, m.id AS target 
    LIMIT 15
    """
    
    results = graph.query(query)
    
    if not results:
        print("The database is currently empty.")
    else:
        for row in results:
            print(f"🧠 {row['source']} --[{row['relationship']}]--> {row['target']}")

def build_graph_from_text(text):
    """
    Takes plain text, uses local Gemma AI to extract entities and relationships, 
    and saves them directly into the Neo4j database.
    """
    print("\nReading text and extracting knowledge graph (This might take a minute locally)...")
    
    doc = Document(page_content=text)
    
    graph_documents = llm_transformer.convert_to_graph_documents([doc])
    
    graph.add_graph_documents(graph_documents)
    
    nodes_found = len(graph_documents[0].nodes)
    rels_found = len(graph_documents[0].relationships)
    print(f"✅ SUCCESS! Added {nodes_found} Nodes and {rels_found} Relationships to EduGen's brain.")


# --- TEST RUN ---
if __name__ == "__main__":
    sample_edugen_data = """
    EduGen is an AI-powered career guidance system designed for university students. 
    
    A Software Engineer is a technology career that requires skills like Python programming, Database Management, and Problem Solving. Python is a programming language used in backend development. MySQL is a Database Management system.
    
    A Data Scientist is a data-focused career. The skills required for a Data Scientist include Machine Learning, Statistics, Python programming, and Data Visualization. 
    
    A UI/UX Designer is a creative technology career. The skills required to be a UI/UX Designer include Wireframing, Figma, User Research, and Empathy. Figma is a design tool.
    
    A Cybersecurity Analyst is a security career. The skills required for a Cybersecurity Analyst include Network Security, Ethical Hacking, Risk Assessment, and Linux.
    """
    
    print("--- Starting EduGen Knowledge Extraction ---")
    build_graph_from_text(sample_edugen_data)

    # Add this line to see the results!
    check_database_knowledge()
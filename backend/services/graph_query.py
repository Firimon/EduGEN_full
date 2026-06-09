import os
from pathlib import Path
from dotenv import load_dotenv

# LangChain and AI Imports
from langchain_ollama import ChatOllama  
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_core.prompts.prompt import PromptTemplate

# 1. Load the Vault (.env file)
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# 2. Connect to Neo4j
graph = Neo4jGraph(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD"),
    database=os.getenv("NEO4J_DATABASE")
)

# 3. Dynamic Host Resolution
# When deployed on Render, this reads your configured server URL.
# When running locally on your laptop, it defaults back to localhost.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# 4. Initialize BOTH Brains (Cloud & Local)
print(f"☁️ Connecting to primary Cloud Gemma 4 model via: {OLLAMA_BASE_URL}")
cloud_llm = ChatOllama(
    model="gemma4:31b-cloud", 
    base_url=OLLAMA_BASE_URL,
    temperature=0 
)

print(f"💻 Connecting to offline Local Gemma model via: {OLLAMA_BASE_URL}")
local_llm = ChatOllama(
    model="gemma4", 
    base_url=OLLAMA_BASE_URL,
    temperature=0 
)

# 5. Give AE-GEN a Persona!
qa_template = """You are AE-GEN, an expert AI career assistant for EduGEN.

Database Context:
{context}

User Question: {question}

Instructions:
1. If the user only says "hello", "hi", or "hey", reply normally and ask how you can help with their career.
2. If the Database Context contains information related to the user's question, use it to answer!
3. IMPORTANT: If the Database Context is empty or unhelpful, DO NOT say "I don't know". Instead, use your own general knowledge as a career advisor to answer the user's question.
4. Keep answers professional, encouraging, and use bullet points for readability.

Helpful Answer:"""

QA_PROMPT = PromptTemplate(
    input_variables=["context", "question"], 
    template=qa_template
)

# 6. Create the GraphRAG Engine
chain = GraphCypherQAChain.from_llm(
    graph=graph,
    cypher_llm=cloud_llm,
    qa_llm=cloud_llm,
    verbose=True, 
    qa_prompt=QA_PROMPT,
    allow_dangerous_requests=True,
    return_direct=False 
)

def ask_edugen(question):
    """
    Triple-Tier Hybrid Brain: 
    1. Tries Neo4j Graph + Cloud LLM.
    2. Falls back to General Cloud LLM.
    3. Emergency Fallback to Offline Local LLM if Wi-Fi drops.
    """
    print(f"\n🤔 User asked: '{question}'")
    
    # Define the fallback prompt early so both Attempt 2 and 3 can use it
    fallback_prompt = f"""
    You are AE-GEN, an expert AI career assistant for EduGEN. 
    The user asked: "{question}"
    Provide highly actionable, professional, and encouraging career advice. 
    Use bullet points for readability. Do not mention that a database failed.
    """

    try:
        # ATTEMPT 1: Try to pull specific data from the Graph Database
        response = chain.invoke({"query": question})
        answer = response['result']
        
        if "I don't know" in answer or not answer.strip():
            raise ValueError("Graph query returned empty context. Triggering fallback.")
            
        print(f"\n🤖 EduGen Graph AI says: {answer}")
        return answer

    except Exception as e:
        print(f"\n⚠️ Graph query skipped/failed ({e}). Trying General Cloud AI...")
        
        try:
            # ATTEMPT 2: Fallback to General Career Advice via Cloud LLM
            fallback_response = cloud_llm.invoke(fallback_prompt)
            answer = fallback_response.content
            
            print(f"\n🤖 EduGen Cloud AI says: {answer}")
            return answer
            
        except Exception as wifi_error:
            # ATTEMPT 3: Wi-Fi or Cloud connection down. Route to backup local target.
            print(f"\n🚨 Connection Lost! ({wifi_error}). Switching to OFFLINE LOCAL AI...")
            
            offline_response = local_llm.invoke(fallback_prompt)
            answer = offline_response.content
            
            print(f"\n🤖 EduGen Local AI (Offline Mode) says: {answer}")
            return answer
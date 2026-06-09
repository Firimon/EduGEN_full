import os
from langchain_ollama import ChatOllama
from langchain_core.prompts.prompt import PromptTemplate

# Initialize the local Gemma model
llm = ChatOllama(model="gemma2:2b", temperature=0.2) # Slight temperature for better writing

def optimize_resume(resume_text):
    print("📝 Running Resume Optimizer...")
    template = """You are an expert HR Recruiter and Resume Writer.
    Read the following resume text or bullet points provided by a student.
    
    Your task:
    1. Identify weak verbs (like 'helped', 'did', 'made') and replace them with strong action verbs (like 'orchestrated', 'developed', 'engineered').
    2. Provide a short, bulleted list of suggested improvements for their resume.
    3. Be encouraging and professional.
    
    Resume Text: {text}
    
    Feedback:"""
    
    prompt = PromptTemplate(input_variables=["text"], template=template)
    chain = prompt | llm
    
    try:
        response = chain.invoke({"text": resume_text})
        return response.content
    except Exception as e:
        print(f"Error: {e}")
        return "Sorry, I couldn't process this resume right now."

def analyze_skills(user_input):
    print("📊 Running Skill Gap Analyzer...")
    template = """You are an expert Career Strategist.
    A student has provided their target job and their current skills.
    
    Your task:
    1. Identify the industry-standard skills required for their target job in 2025.
    2. Compare those against the skills they currently have.
    3. Clearly list the "Skill Gap" (the missing skills they need to learn).
    4. Provide 2-3 actionable steps on how they can learn those missing skills.
    
    Student Input: {text}
    
    Analysis:"""
    
    prompt = PromptTemplate(input_variables=["text"], template=template)
    chain = prompt | llm
    
    try:
        response = chain.invoke({"text": user_input})
        return response.content
    except Exception as e:
        print(f"Error: {e}")
        return "Sorry, I couldn't analyze these skills right now."
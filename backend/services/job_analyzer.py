import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool  
from langchain_community.tools import DuckDuckGoSearchRun

# 🚀 Load keys securely
load_dotenv()



# BLAZING FAST OLLAMA CLOUD SETUP (Hardcoded Test)
cloud_llm = LLM(
    model="ollama/gemma4:31b-cloud",       
    base_url="http://localhost:11434",  
    api_key="c92bcd4ae2a24e69a8a1a9cd6fb4bcf0.1_KoSaClRZyf8IuCXBEr8enE",  # <-- Put your real sk-... key inside the quotes
    temperature=0.7
)

# ==========================================
# CUSTOM NATIVE CREWAI SEARCH TOOL (Fixes the Pydantic Error)
# ==========================================
class WebSearchTool(BaseTool):
    name: str = "Live Web Search"
    description: str = "Search the internet for current job market data, salaries, and hiring trends."

    def _run(self, query: str) -> str:
        search = DuckDuckGoSearchRun()
        return search.run(query)

# Initialize our custom tool!
search_tool = WebSearchTool()


def generate_fit_analysis(job_title, user_skills, academic_level):
    """
    Spawns a CrewAI panel to analyze a user's fit for a specific job.
    """
    
    # ==========================================
    # 1. DEFINE THE AGENTS
    # ==========================================
    ats_agent = Agent(
        role='ATS System Decoder',
        goal=f'Identify the top 5 mandatory skills and technologies required for a {job_title} role.',
        backstory='You are an advanced Applicant Tracking System used by top tech companies. You know exactly what recruiters are looking for.',
        verbose=True,
        allow_delegation=False,
        llm=cloud_llm  # <-- UPDATED TO CLOUD
    )

    auditor_agent = Agent(
        role='Career Profile Auditor',
        goal=f'Compare the candidate\'s current skills ({user_skills}) and education ({academic_level}) against the ATS requirements.',
        backstory='You are a brutally honest but supportive career coach. Your job is to tell the student exactly what they are missing to get hired.',
        verbose=True,
        allow_delegation=False,
        llm=cloud_llm  # <-- UPDATED TO CLOUD
    )

    # ==========================================
    # 2. DEFINE THE TASKS
    # ==========================================
    ats_task = Task(
        description=f'List the definitive technical and soft skills required to be hired as a {job_title}.',
        expected_output='A concise list of required skills.',
        agent=ats_agent
    )

    audit_task = Task(
        description=f'Read the ATS requirements. Read the user skills: {user_skills}. Provide a "Match Report" with three sections: 1. Match Percentage (estimate). 2. What they already have. 3. What they are missing (Skill Gaps). Keep it brief and encouraging.',
        expected_output='A formatted Fit Analysis report with a Match Percentage and Skill Gaps.',
        agent=auditor_agent
    )

    # ==========================================
    # 3. FORM THE CREW
    # ==========================================
    analysis_crew = Crew(
        agents=[ats_agent, auditor_agent],
        tasks=[ats_task, audit_task],
        process=Process.sequential 
    )

    print(f"🚀 Analyzing Fit for: {job_title}...")
    result = analysis_crew.kickoff()
    
    return str(result)


def generate_deep_web_research(job_title):
    """
    Spawns a single CrewAI agent equipped with a search tool to browse the 
    live internet autonomously using Gemma 4's native function calling.
    """
    
    # ==========================================
    # 1. DEFINE THE RESEARCH AGENT (WITH SEARCH TOOL)
    # ==========================================
    web_researcher = Agent(
        role='Senior Market Research Analyst',
        goal=f'Scour the live internet for the most up-to-date information on the {job_title} role.',
        backstory='You are a top-tier industry analyst. You use the internet to find real, current data about salaries, hiring companies, and market demands.',
        tools=[search_tool],  
        llm=cloud_llm,  # <-- UPDATED TO CLOUD
        verbose=True,
        allow_delegation=False
    )

    # ==========================================
    # 2. DEFINE THE RESEARCH TASK
    # ==========================================
    research_task = Task(
        description=f"""
        Use your search tool to browse the internet and find the following for a {job_title} role in the current year:
        1. Current average salary range (specify the country or globally).
        2. Top 3 companies actively hiring for this role right now.
        3. The most demanded new skill for this role right now.
        Synthesize your findings into a clean, highly professional summary.
        """,
        expected_output="A 3-paragraph market research summary containing live salary data, hiring trends, and key skills.",
        agent=web_researcher
    )

    # ==========================================
    # 3. FORM THE CREW
    # ==========================================
    crew = Crew(
        agents=[web_researcher],
        tasks=[research_task],
        verbose=True
    )

    print(f"🌐 Gemma 4 Cloud is autonomously browsing the web for: {job_title}...")
    result = crew.kickoff()
    
    return str(result)
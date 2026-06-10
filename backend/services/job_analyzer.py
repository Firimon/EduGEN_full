import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from langchain_community.chat_models import ChatOllama  # NATIVE CHATOLLAMA IMPORT
from crewai.tools import BaseTool  
from langchain_community.tools import DuckDuckGoSearchRun

# 🚀 Load keys securely
load_dotenv()

# Dynamic Host Resolution for Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "a906e8ce381d42ec86e63a62be531214.dMe0FP2x6bhDa3OonqxODZr8")

# BLAZING FAST OLLAMA CLOUD SETUP (Bypassing LiteLLM)
cloud_llm = ChatOllama(
    model="gemma4:31b-cloud",  # Removed 'ollama/' prefix. ChatOllama passes this raw.
    base_url=OLLAMA_BASE_URL,
    temperature=0.7,
    # Explicitly inject the API key into the request header for cloud auth
    headers={"Authorization": f"Bearer {OLLAMA_API_KEY}"} 
)

# ==========================================
# CUSTOM NATIVE CREWAI SEARCH TOOL 
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
    ats_agent = Agent(
        role='ATS System Decoder',
        goal=f'Identify the top 5 mandatory skills and technologies required for a {job_title} role.',
        backstory='You are an advanced Applicant Tracking System used by top tech companies. You know exactly what recruiters are looking for.',
        verbose=True,
        allow_delegation=False,
        llm=cloud_llm  
    )

    auditor_agent = Agent(
        role='Career Profile Auditor',
        goal=f'Compare the candidate\'s current skills ({user_skills}) and education ({academic_level}) against the ATS requirements.',
        backstory='You are a brutally honest but supportive career coach. Your job is to tell the student exactly what they are missing to get hired.',
        verbose=True,
        allow_delegation=False,
        llm=cloud_llm  
    )

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
    Spawns a single CrewAI agent equipped with a search tool to browse the live internet autonomously.
    """
    web_researcher = Agent(
        role='Senior Market Research Analyst',
        goal=f'Scour the live internet for the most up-to-date information on the {job_title} role.',
        backstory='You are a top-tier industry analyst. You use the internet to find real, current data about salaries, hiring companies, and market demands.',
        tools=[search_tool],  
        llm=cloud_llm,  
        verbose=True,   
        allow_delegation=False
    )

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

    crew = Crew(
        agents=[web_researcher],
        tasks=[research_task],
        verbose=True
    )

    print(f"🌐 Gemma 4 Cloud is autonomously browsing the web for: {job_title}...")
    result = crew.kickoff()
    
    return str(result)


def generate_assessment_options_crew(scenario):
    """
    Spawns a specialized CrewAI agent to dynamically create contextual answer options for assessment.html.
    """
    psychometric_agent = Agent(
        role='Psychometric Assessment Designer',
        goal='Create highly relevant, structured behavioral choices based on a student scenario context.',
        backstory='You are an expert psychometrician and talent development strategist. You design options that map out clean career indicators.',
        verbose=False,
        allow_delegation=False,
        llm=cloud_llm
    )

    assessment_task = Task(
        description=f"""
        An assessment scenario has been loaded: "{scenario}"

        Generate exactly 4 unique answer options contextualized perfectly around this situation. 
        Each option must align to one distinct professional mindset trait:
        - logic: Focused on algorithms, structured backend logic, database operations, or optimization.
        - design: Focused on user empathy, front-end visual elements, styling consistency, or interface layout.
        - business: Focused on project milestones, scope tracking, marketplace deployment, or financial impact.
        - social: Focused on documentation updates, team code review harmony, or stakeholder feedback alignment.

        Formatting constraints:
        - Keep option text brief (under 12 words).
        - Provide ONLY a clean, valid raw JSON array block. No extra conversation text.
        """,
        expected_output='A raw JSON array containing 4 objects with keys: "trait" and "text".',
        agent=psychometric_agent
    )

    assessment_crew = Crew(
        agents=[psychometric_agent],
        tasks=[assessment_task],
        verbose=False
    )

    print(f"📝 CrewAI is preparing assessment options for scenario text...")
    result = assessment_crew.kickoff()
    
    return str(result)


def generate_admin_question_crew(trait):
    """
    Spawns a specialized CrewAI agent to dynamically create a new assessment question for the admin panel database.
    """
    trait_mapping = {
        "logic": "Logical, analytical, backend programming, and data analysis.",
        "design": "Creative, UI/UX design, frontend development, and visual aesthetics.",
        "business": "Business strategy, project management, leadership, and product planning.",
        "software_engineer": "Software Engineering, covering writing clean code, data structures, debugging code, and system architecture structures.",
        "data_analyst": "Data Analytics, focusing on data manipulation, database querying, statistical calculations, and graph interpretation.",
        "ui_ux_designer": "UI/UX Design, including wireframing, component accessibility, interface aesthetics, and user research empathy.",
        "cybersecurity_analyst": "Cybersecurity, focusing on network vulnerability analysis, threat mitigation, and evaluating script execution risks."
    }
    
    target_trait = trait_mapping.get(trait, "General technology")

    admin_agent = Agent(
        role='Assessment Database Engineer',
        goal='Generate a single, high-quality assessment statement testing a specific technical trait.',
        backstory='You design psychometric questions for an educational platform to evaluate student career aptitudes.',
        verbose=False,
        allow_delegation=False,
        llm=cloud_llm
    )

    admin_task = Task(
        description=f"""
        Write ONE single, high-quality assessment statement designed to test if a student has a strong situational aptitude or preference for: {target_trait}
        
        Rules:
        - Write it in the first person (e.g., "I enjoy...", "When presented with...").
        - Make the text represent a realistic technical challenge, scenario, or preference matching that specialization.
        - It must be a statement that a user can strongly agree or disagree with.
        - Keep it under 2 sentences.
        - Do not include quotes, prefixes, or any extra conversational text. Output ONLY the raw statement text.
        """,
        expected_output='A single sentence containing the assessment statement.',
        agent=admin_agent
    )

    admin_crew = Crew(
        agents=[admin_agent],
        tasks=[admin_task],
        verbose=False
    )

    print(f"📝 CrewAI is generating an admin assessment question for: {trait}")
    result = admin_crew.kickoff()
    
    return str(result)
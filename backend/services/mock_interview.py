from crewai import Agent, Task, Crew, Process, LLM

# 1. Initialize your local AI model natively through CrewAI
local_llm = LLM(
    model="ollama/gemma4",
    base_url="http://localhost:11434"
)

def generate_interview_panel(user_message, user_skills):
    """
    Spawns a single CrewAI Hiring Manager to conduct a strict, back-and-forth mock interview.
    """
    
    # ==========================================
    # 2. DEFINE THE STRICT INTERVIEWER AGENT
    # ==========================================
    interviewer_agent = Agent(
        role='Senior Technical Hiring Manager',
        goal='Conduct a rigorous, realistic, one-on-one job interview.',
        # NOTICE: We removed the word "CV" from the backstory so it stops hallucinating one!
        backstory='You are a highly experienced Hiring Manager at a top tech firm. You conduct strict, professional, back-and-forth interviews. You ask tough behavioral and technical questions one at a time.',
        verbose=True,
        allow_delegation=False,
        llm=local_llm
    )

    # ==========================================
    # 3. DEFINE THE STRICT TASK (The Rule of One)
    # ==========================================
    interview_task = Task(
        description=f'''
        The candidate has just spoken to you. 
        Candidate's message: "{user_message}"
        Candidate's Known Background/Skills: "{user_skills}"
        
        CRITICAL INTERVIEW RULES:
        1. Act EXACTLY like a human interviewer. Be professional, slightly tough, but fair.
        2. IF the candidate's message is just a greeting (e.g., "hello", "hi"): Greet them back, welcome them, and ask what role they are interviewing for today. DO NOT mention their background, skills, or CV yet. Just ask for the role.
        3. IF the candidate's message is a job title (e.g., "Data Analyst", "Software Engineer"): Acknowledge the role, look at their Known Background/Skills, and ask your VERY FIRST interview question.
        4. IF the candidate is answering a previous question: Evaluate their answer briefly, then ASK THE NEXT QUESTION.
        5. NEVER give the candidate the answers. 
        6. YOU MUST ONLY ASK ONE QUESTION AT A TIME. Stop generating text immediately after you ask your question.
        ''',
        expected_output='A professional response from an interviewer, ending with exactly ONE question.',
        agent=interviewer_agent
    )

    # ==========================================
    # 4. FORM THE CREW & EXECUTE
    # ==========================================
    interview_crew = Crew(
        agents=[interviewer_agent],
        tasks=[interview_task],
        verbose=True
    )

    print(f"🚀 Kicking off Mock Interviewer...")
    result = interview_crew.kickoff()
    
    return str(result)
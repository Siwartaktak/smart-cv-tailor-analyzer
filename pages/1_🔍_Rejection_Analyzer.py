# ============================================================================
# SMART REJECTION ANALYZER - COMPLETE VERSION WITH ALL TABS
# ============================================================================

import sys
from pathlib import Path

# Add parent directory to path (useful if importing from shared modules)
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

import streamlit as st
import requests
import json
import re
from datetime import datetime
import PyPDF2
import docx

# Page config
st.set_page_config(
    page_title="Smart Rejection Analyzer",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(120deg, #1f77b4, #ff6b6b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.3rem;
        color: #555;
        text-align: center;
        margin-bottom: 2rem;
    }
    .gap-critical {
        background: #ffebee;
        padding: 15px;
        border-left: 5px solid #f44336;
        border-radius: 5px;
        margin: 10px 0;
        color: #000000 !important;
    }
    .gap-critical *, .gap-critical h2, .gap-critical p, .gap-critical strong, .gap-critical li {
        color: #000000 !important;
    }
    .gap-important {
        background: #fff3e0;
        padding: 15px;
        border-left: 5px solid #ff9800;
        border-radius: 5px;
        margin: 10px 0;
        color: #000000 !important;
    }
    .gap-important *, .gap-important strong, .gap-important li {
        color: #000000 !important;
    }
    .recommendation-box {
        background: #e8f5e9;
        padding: 20px;
        border-left: 5px solid #4caf50;
        border-radius: 5px;
        margin: 15px 0;
        color: #000000 !important;
    }
    .recommendation-box *, .recommendation-box strong, .recommendation-box li {
        color: #000000 !important;
    }
    .evidence-box {
        background: #e3f2fd;
        padding: 15px;
        border-left: 5px solid #2196f3;
        border-radius: 5px;
        margin: 10px 0;
        color: #000000 !important;
    }
    .evidence-box *, .evidence-box strong, .evidence-box li {
        color: #000000 !important;
    }
    .improvement-box {
        background: #f3e5f5;
        padding: 20px;
        border-left: 5px solid #9c27b0;
        border-radius: 5px;
        margin: 15px 0;
        color: #000000 !important;
    }
    .improvement-box *, .improvement-box strong, .improvement-box h4, .improvement-box ul, .improvement-box li {
        color: #000000 !important;
    }
    .metric-card {
        background: black;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        text-align: center;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# JSON PARSING
# ============================================================================

def safe_parse_json(response: str) -> dict:
    """Enhanced JSON parsing with better error handling"""
    if not response:
        return None
    
    # Strategy 1: Direct parse
    try:
        return json.loads(response)
    except:
        pass
    
    # Strategy 2: Extract from markdown
    try:
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
    except:
        pass
    
    # Strategy 3: Find JSON object
    try:
        cleaned = re.sub(r'\s+', ' ', response)
        start = cleaned.find('{')
        if start == -1:
            return None
        
        brace_count = 0
        for i in range(start, len(cleaned)):
            if cleaned[i] == '{':
                brace_count += 1
            elif cleaned[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_str = cleaned[start:i+1]
                    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)  # Remove trailing commas
                    return json.loads(json_str)
    except Exception as e:
        st.warning(f"JSON parsing attempt failed: {str(e)[:100]}")
    
    return None

def extract_from_failed_response(response: str) -> dict:
    """Extract whatever we can from a failed JSON response"""
    return {
        "primary_rejection_reason": "AI analysis completed but response format was invalid. Please try again or check the raw response below.",
        "technical_skills_gap": {
            "critical_missing": ["Unable to parse - check raw response"],
            "important_missing": [],
            "weak_skills": []
        },
        "experience_gap": {
            "required_years": "Unknown",
            "candidate_years": "Unknown",
            "gap": "Unknown",
            "seniority_mismatch": "false"
        },
        "education_gap": {
            "required": "Unknown",
            "candidate_has": "Unknown",
            "gap_exists": "false"
        },
        "domain_experience_gap": {
            "required_domain": "Unknown",
            "candidate_domain": "Unknown",
            "gap_description": "Unable to parse response"
        },
        "project_relevance_score": "0",
        "detailed_analysis": "The AI generated a response, but it was not in the correct format. This usually means the response was too long or complex. Try with a shorter CV/Job Description, or check the raw response below.",
        "specific_evidence": {
            "from_job_description": [],
            "from_cv": [],
            "the_gap": "Unable to parse"
        },
        "actionable_recommendations": [
            "Try running the analysis again",
            "Ensure your CV and job description are not too long (keep under 2000 characters each)",
            "Check the raw AI response in the expandable section below"
        ],
        "estimated_time_to_qualify": "Unknown",
        "confidence": "low",
        "parse_error": True,
        "raw_response": response[:1000]
    }

# ============================================================================
# OLLAMA & ANALYZER
# ============================================================================

class OllamaLLM:
    def __init__(self, model_name="llama3:8b", base_url="http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
    
    def test_connection(self):
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def generate(self, prompt: str, temperature: float = 0.3) -> str:
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature, 
                "num_predict": 2000,
                "top_p": 0.9,
                "top_k": 40
            }
        }
        try:
            response = requests.post(self.api_url, json=payload, timeout=240)
            if response.status_code == 200:
                return response.json()['response']
            return None
        except Exception as e:
            st.error(f"API Error: {str(e)}")
            return None

class SmartRejectionAnalyzer:
    def __init__(self, llm):
        self.llm = llm
    
    def create_comparison_prompt(self, cv_text: str, job_description: str, rejection_email: str) -> str:
        """Enhanced prompt with better rejection reason generation"""
        # Truncate to avoid overwhelming the model
        cv_text = cv_text[:1800]
        job_description = job_description[:1800]
        rejection_email = (rejection_email[:400] if rejection_email else "No specific rejection email provided - generic rejection assumed")
        
        return f"""You are an expert career analyst. Your task is to determine the REAL reason why a candidate was rejected by comparing their CV against the job requirements.

===========================================
CRITICAL ANALYSIS RULES:
===========================================
1. Base your analysis on ACTUAL EVIDENCE from the three documents below
2. The rejection reason must be specific and data-driven
3. Only mention skills/requirements that appear in the job description
4. Look for the BIGGEST gap that likely caused the rejection
5. Consider the rejection email for clues, but validate against CV and job description

=== REJECTION EMAIL (READ THIS FIRST FOR CLUES) ===
{rejection_email}

=== JOB DESCRIPTION (THESE ARE THE REQUIREMENTS) ===
{job_description}

=== CANDIDATE'S CV (WHAT THEY HAVE) ===
{cv_text}

===========================================
YOUR ANALYSIS PROCESS:
===========================================

STEP 1: Analyze the rejection email
- Does it mention specific reasons? (e.g., "more experienced candidates", "technical skills mismatch")
- Does it hint at what was missing?
- Is it generic or specific?

STEP 2: Extract job requirements
- Required technical skills (list them)
- Required years of experience
- Required education/certifications
- Required domain/industry experience
- Required project types

STEP 3: Check what candidate has
- Go through CV and find matching skills
- Note what's missing
- Note what's weak or insufficient

STEP 4: Identify the PRIMARY gap
- What is the BIGGEST mismatch?
- Is it skills? Experience? Education? Domain knowledge?
- What gap would most likely cause rejection?

STEP 5: Formulate rejection reason
- Write ONE clear sentence explaining the main reason
- Base it on concrete evidence
- Be specific (not vague like "lack of qualifications")

===========================================
GOOD vs BAD REJECTION REASONS:
===========================================

BAD (vague): "Candidate lacks required qualifications"
GOOD: "Lacks 3+ years of Python development and data pipeline experience required for senior role"

BAD (invented): "Missing AWS and Kubernetes skills"
GOOD: "Job requires Java and Spring Boot (5+ years) but candidate has only 2 years"

BAD (generic): "Not a good fit"
GOOD: "Position needs financial domain experience but candidate background is in e-commerce"

===========================================
OUTPUT FORMAT (JSON ONLY):
===========================================

Return ONLY this JSON structure (no other text before or after):

{{
    "primary_rejection_reason": "ONE specific sentence: What is the main reason based on evidence? Be concrete and specific. Example: 'Lacks required 5+ years Python experience and machine learning expertise explicitly required in job description'",
    
    "rejection_email_analysis": {{
        "email_type": "specific/generic/mixed",
        "hints_from_email": ["Any clues from rejection email about why rejected"],
        "key_phrases": ["Important phrases from rejection email"]
    }},
    
    "technical_skills_gap": {{
        "critical_missing": ["Skills from job description that candidate completely lacks - be specific"],
        "important_missing": ["Nice-to-have skills from job description that are missing"],
        "weak_skills": ["Skills candidate claims but seems insufficient/weak"]
    }},
    
    "experience_gap": {{
        "required_years": "X years or 'Not specified'",
        "candidate_years": "Y years (estimate from CV)",
        "gap": "Z years short" or "No gap",
        "seniority_mismatch": "true/false - is there a level mismatch (junior vs senior)?"
    }},
    
    "education_gap": {{
        "required": "From job description",
        "candidate_has": "From CV",
        "gap_exists": "true/false"
    }},
    
    "domain_experience_gap": {{
        "required_domain": "Industry/domain from job (e.g., fintech, healthcare)",
        "candidate_domain": "Industry from CV",
        "gap_description": "Explain mismatch if exists"
    }},
    
    "project_relevance_score": "0-10 (how relevant are candidate's projects to job requirements?)",
    
    "detailed_analysis": "2-3 sentences explaining the rejection. Connect the dots: 'The job requires X and Y, but the candidate only has Z. This mismatch in [specific area] is likely the primary reason for rejection.'",
    
    "specific_evidence": {{
        "from_job_description": ["Quote 2-3 key requirements from job description"],
        "from_cv": ["Quote 2-3 relevant parts from CV"],
        "the_gap": "Clear explanation: Job needs X, Y, Z but candidate only has X. Missing Y and Z (with specifics)."
    }},
    
    "actionable_recommendations": [
        "Based on gaps found - provide 3-5 specific, actionable steps with timelines",
        "Example: 'Complete Python advanced course focusing on data pipelines (2-3 months)'",
        "Example: 'Build 2-3 portfolio projects demonstrating machine learning skills (3-4 months)'"
    ],
    
    "estimated_time_to_qualify": "6-12 months (or specific estimate)",
    
    "confidence": "high/medium/low - how confident are you in this analysis?"
}}

===========================================
REMEMBER:
===========================================
- Be SPECIFIC in the primary_rejection_reason
- Use EVIDENCE from the three documents
- Don't invent requirements not in job description
- The rejection reason should be the #1 dealbreaker
- If multiple gaps exist, identify which one is most critical

NOW ANALYZE AND RETURN ONLY THE JSON:"""

    def validate_analysis(self, result: dict, job_description: str) -> dict:
        """Validate that analysis doesn't mention skills not in job description"""
        job_lower = job_description.lower()
        
        common_hallucinations = ['aws', 'docker', 'kubernetes', 'k8s', 'azure', 'gcp', 
                                 'jenkins', 'terraform', 'ansible', 'redis', 'kafka']
        
        tech_gap = result.get('technical_skills_gap', {})
        for category in ['critical_missing', 'important_missing', 'weak_skills']:
            skills = tech_gap.get(category, [])
            validated_skills = []
            
            for skill in skills:
                skill_lower = skill.lower()
                is_common_tech = any(term in skill_lower for term in common_hallucinations)
                
                if is_common_tech:
                    if any(term in job_lower for term in skill_lower.split()):
                        validated_skills.append(skill)
                    else:
                        st.warning(f"Removed hallucinated requirement: '{skill}' (not in job description)")
                else:
                    validated_skills.append(skill)
            
            tech_gap[category] = validated_skills
        
        result['technical_skills_gap'] = tech_gap
        
        primary = result.get('primary_rejection_reason', '')
        for tech in common_hallucinations:
            if tech in primary.lower() and tech not in job_lower:
                st.warning(f"Primary reason mentioned '{tech.upper()}' which is not in job description. AI may be hallucinating.")
                primary = re.sub(rf'\b{tech}\b', '', primary, flags=re.IGNORECASE)
                primary = re.sub(r'\s+', ' ', primary).strip()
                result['primary_rejection_reason'] = primary
        
        return result
    
    def analyze(self, cv_text: str, job_description: str, rejection_email: str) -> dict:
        if not cv_text or len(cv_text) < 50:
            return {"error": "CV is too short or empty"}
        if not job_description or len(job_description) < 50:
            return {"error": "Job description is too short or empty"}
        
        prompt = self.create_comparison_prompt(cv_text, job_description, rejection_email)
        response = self.llm.generate(prompt, temperature=0.2)
        
        if not response:
            return {"error": "No response from AI. Check if Ollama is running with: ollama serve"}
        
        result = safe_parse_json(response)
        
        if result:
            primary = result.get('primary_rejection_reason', '')
            if len(primary) < 10 or 'State the most likely reason' in primary:
                return extract_from_failed_response(response)
            
            result = self.validate_analysis(result, job_description)
            return result
        else:
            return extract_from_failed_response(response)

# ============================================================================
# SESSION STATE
# ============================================================================

if 'llm' not in st.session_state:
    st.session_state.llm = OllamaLLM()
if 'analyzer' not in st.session_state:
    st.session_state.analyzer = SmartRejectionAnalyzer(st.session_state.llm)
if 'history' not in st.session_state:
    st.session_state.history = []

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=80)
    st.title("Smart Analyzer")
    st.markdown("---")
    
    st.subheader("System Status")
    if st.session_state.llm.test_connection():
        st.success("AI Connected")
    else:
        st.error("AI Disconnected")
        st.info("Run: `ollama serve`")
    
    st.markdown("---")
    page = st.radio("Navigate", ["Home", "Analyze Rejection", "History", "How It Works"])
    st.markdown("---")
    st.caption("Made with ❤️ by Siwar")

# ============================================================================
# PAGES
# ============================================================================

if page == "Home":
    st.markdown('<p class="main-header">Smart Rejection Analyzer</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI compares YOUR CV vs JOB REQUIREMENTS to find REAL rejection reasons</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="metric-card"><h2></h2><h3>Your CV</h3><p>Upload or paste</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-card"><h2></h2><h3>Job Description</h3><p>Paste requirements</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="metric-card"><h2></h2><h3>Rejection Email</h3><p>Optional</p></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.success("Ready? Click **'Analyze Rejection'** in the sidebar!")

elif page == "Analyze Rejection":
    st.title("Smart Rejection Analysis")
    
    st.subheader("Your CV / Resume")
    cv_file = st.file_uploader("Upload your CV (PDF or DOCX)", type=["pdf", "docx"])
    
    cv_text = ""
    if cv_file:
        try:
            if cv_file.name.lower().endswith(".pdf"):
                reader = PyPDF2.PdfReader(cv_file)
                cv_text = "\n".join(page.extract_text() or "" for page in reader.pages)
            elif cv_file.name.lower().endswith(".docx"):
                document = docx.Document(cv_file)
                cv_text = "\n".join(p.text for p in document.paragraphs)
            st.success("CV uploaded!")
        except Exception as e:
            st.error(f"Failed to read CV: {e}")
    
    cv_text_manual = st.text_area("Or paste your CV text", height=200, placeholder="Paste CV here")
    if cv_text_manual.strip():
        cv_text = cv_text_manual
    
    st.subheader("Job Description")
    job_desc = st.text_area("Paste the job description", height=300, placeholder="Paste full job description")
    
    rejection_email = st.text_area("Rejection Email (optional)", height=150, placeholder="Paste rejection email if available")
    
    if st.button("Analyze My Rejection", type="primary", use_container_width=True):
        if not cv_text:
            st.error("Please provide your CV!")
        elif not job_desc:
            st.error("Please provide the job description!")
        elif not st.session_state.llm.test_connection():
            st.error("AI is not connected. Start Ollama: `ollama serve`")
        else:
            with st.spinner("AI analyzing (30-60 seconds)..."):
                result = st.session_state.analyzer.analyze(cv_text, job_desc, rejection_email)
                st.session_state.history.append({
                    'timestamp': datetime.now(),
                    'cv_snippet': cv_text[:100] + "...",
                    'job_snippet': job_desc[:100] + "...",
                    'result': result
                })
            
            if "error" in result:
                st.error(f"{result['error']}")
                if 'raw_response' in result:
                    with st.expander("See raw AI response for debugging"):
                        st.text(result['raw_response'])
            else:
                if result.get('parse_error'):
                    st.warning("AI response could not be parsed properly. Showing partial results.")
                    with st.expander("See raw AI response"):
                        st.text(result.get('raw_response', 'No response available'))
                else:
                    st.success("Analysis Complete!")
                
                conf = result.get('confidence', 'medium').lower()
                conf_emoji = {"high": "High", "medium": "Medium", "low": "Low"}.get(conf, "")
                st.markdown(f"**Confidence:** {conf_emoji} **{conf.upper()}**")
                
                st.markdown("---")
                st.markdown("## PRIMARY REJECTION REASON")
                st.markdown(f"<div class='gap-critical'><h2>{result.get('primary_rejection_reason', 'Not determined')}</h2></div>", unsafe_allow_html=True)
                st.markdown("---")
                
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["Gap Analysis", "Evidence", "How to Improve", "Action Plan", "Full Report"])
                
                with tab1:
                    st.subheader("Gap Breakdown")
                    tech_gap = result.get('technical_skills_gap', {})
                    if tech_gap.get('critical_missing'):
                        st.markdown("**CRITICAL Missing:**")
                        for skill in tech_gap['critical_missing']:
                            st.markdown(f"<div class='gap-critical'>• {skill}</div>", unsafe_allow_html=True)
                    if tech_gap.get('important_missing'):
                        st.markdown("**IMPORTANT Missing:**")
                        for skill in tech_gap['important_missing']:
                            st.markdown(f"<div class='gap-important'>• {skill}</div>", unsafe_allow_html=True)
                    
                    exp_gap = result.get('experience_gap', {})
                    if exp_gap:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Required", exp_gap.get('required_years', 'N/A'))
                        with col2:
                            st.metric("You Have", exp_gap.get('candidate_years', 'N/A'))
                        with col3:
                            st.metric("Gap", exp_gap.get('gap', 'N/A'))
                
                with tab2:
                    evidence = result.get('specific_evidence', {})
                    st.markdown("**From Job Description:**")
                    for quote in evidence.get('from_job_description', []):
                        st.markdown(f"<div class='evidence-box'> \"{quote}\"</div>", unsafe_allow_html=True)
                    st.markdown("**From Your CV:**")
                    for quote in evidence.get('from_cv', []):
                        st.markdown(f"<div class='evidence-box'> \"{quote}\"</div>", unsafe_allow_html=True)
                    st.markdown("**The Gap:**")
                    st.error(evidence.get('the_gap', 'Not specified'))
                    st.markdown("### Detailed Analysis")
                    st.write(result.get('detailed_analysis', 'No analysis available'))
                
                with tab3:
                    st.subheader("How to Improve & Get the Job")
                    st.markdown(f"<div class='improvement-box'><strong>Rejection Reason:</strong><br>{result.get('primary_rejection_reason')}</div>", unsafe_allow_html=True)
                    
                    critical = result.get('technical_skills_gap', {}).get('critical_missing', [])
                    if critical:
                        st.markdown("#### PRIORITY 1: Master Critical Skills (0-3 months)")
                        for i, skill in enumerate(critical, 1):
                            st.markdown(f"""
                            <div class='improvement-box'>
                                <strong>{i}. {skill}</strong><br>
                                <strong>How to learn:</strong>
                                <ul>
                                    <li>Take online course (Coursera, Udemy, freeCodeCamp)</li>
                                    <li>Complete 2-3 hands-on projects</li>
                                    <li>Add to CV with specific achievements</li>
                                </ul>
                                <strong>Timeline:</strong> 4-8 weeks<br>
                                <strong>Proof:</strong> GitHub projects or portfolio
                            </div>
                            """, unsafe_allow_html=True)
                    
                    if result.get('experience_gap', {}).get('gap', '0') != '0':
                        st.markdown("#### PRIORITY 2: Gain Experience (3-6 months)")
                        st.markdown("""
                        <div class='improvement-box'>
                            <strong>How to bridge the experience gap:</strong>
                            <ul>
                                <li><strong>Freelance:</strong> 2-3 projects on Upwork/Fiverr</li>
                                <li><strong>Open Source:</strong> Contribute to relevant projects</li>
                                <li><strong>Personal Projects:</strong> Build 3-5 portfolio pieces</li>
                            </ul>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("### Your Improvement Timeline")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown("<div class='improvement-box'><h4>Month 1-3</h4><strong>Focus: Skills</strong><br>Complete courses<br>Build projects<br>Update CV</div>", unsafe_allow_html=True)
                    with col2:
                        st.markdown("<div class='improvement-box'><h4>Month 3-6</h4><strong>Focus: Experience</strong><br>Freelance/Contribute<br>Build portfolio</div>", unsafe_allow_html=True)
                    with col3:
                        st.markdown("<div class='improvement-box'><h4>Month 6+</h4><strong>Focus: Apply</strong><br>Polish CV<br>Interview prep<br>Apply again</div>", unsafe_allow_html=True)
                    
                    st.success("Follow this plan to become qualified in 6-9 months!")
                
                with tab4:
                    st.subheader("Your Action Plan")
                    for i, rec in enumerate(result.get('actionable_recommendations', []), 1):
                        st.markdown(f"<div class='recommendation-box'><strong>{i}.</strong> {rec}</div>", unsafe_allow_html=True)
                    st.metric("Estimated Time to Qualify", result.get('estimated_time_to_qualify', 'Not specified'))
                
                with tab5:
                    st.subheader("Complete Report")
                    report = f"""ANALYSIS REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

PRIMARY REASON: {result.get('primary_rejection_reason', 'N/A')}

CRITICAL SKILLS MISSING: {', '.join(result.get('technical_skills_gap', {}).get('critical_missing', []))}

RECOMMENDATIONS:
""" + "\n".join([f"{i}. {rec}" for i, rec in enumerate(result.get('actionable_recommendations', []), 1)])
                    
                    st.text_area("Copy Report", report, height=400)
                    st.download_button("Download Report", report, f"rejection_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.txt", mime="text/plain")

elif page == "History":
    st.title("Analysis History")
    if not st.session_state.history:
        st.info("No analyses yet!")
    else:
        for i, item in enumerate(reversed(st.session_state.history), 1):
            with st.expander(f"Analysis {i} - {item['timestamp'].strftime('%Y-%m-%d %H:%M')}"):
                st.text(item['cv_snippet'])
                result = item['result']
                if 'error' not in result:
                    st.markdown(f"**Primary Reason:** {result.get('primary_rejection_reason', 'N/A')}")

elif page == "How It Works":
    st.title("How It Works")
    st.markdown("""
    ## The Process
    
    1. Upload CV + Job Description
    2. AI analyzes skill gaps, experience gaps
    3. Get evidence-based results
    4. Receive action plan with timeline
    
    ### Privacy
    - Runs locally
    - Uses Ollama (local AI)
    - No external data transmission
    """)

st.markdown("---")
st.markdown('<div style="text-align: center; color: #666;"><p><strong>Smart Rejection Analyzer</strong> | Powered by Llama 3</p></div>', unsafe_allow_html=True)
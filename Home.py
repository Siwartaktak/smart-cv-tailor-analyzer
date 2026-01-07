"""
============================================================================
COMBINED APPLICATION: CV TAILOR + SMART REJECTION ANALYZER
============================================================================
"""

import streamlit as st
import pandas as pd
import requests
import json
import re
from datetime import datetime
import PyPDF2
import docx
from pathlib import Path
import plotly.graph_objects as go
import io
import os

# Import the helper modules (make sure they're in the same directory)
from cv_parser import CVParser, JobDescriptionAnalyzer, KeywordMatcher
from cv_exporter import CVExporter, MotivationLetterGenerator

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Career Tools Suite",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# SHARED CSS
# ============================================================================

st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(120deg, #667eea, #764ba2, #ff6b6b);
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
    .recommendation-box {
        background: #e8f5e9;
        padding: 20px;
        border-left: 5px solid #4caf50;
        border-radius: 5px;
        margin: 15px 0;
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
    .skill-badge {
        display: inline-block;
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 6px 14px;
        border-radius: 20px;
        margin: 5px;
        font-size: 0.95rem;
        border: 2px solid #4caf50;
        font-weight: 500;
    }
    .skill-badge-missing {
        background-color: #ffebee;
        color: #c62828;
        border: 2px solid #f44336;
    }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        text-align: center;
    }
    .info-box {
        padding: 20px;
        border-radius: 10px;
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        margin: 10px 0;
        color: #000000;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# OLLAMA LLM CLASS
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

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def display_skills_badges(skills: list, badge_type: str = "matched"):
    """Display skills as colored badges"""
    if not skills:
        st.info("No skills in this category")
        return
    
    badge_class = "skill-badge" if badge_type == "matched" else "skill-badge skill-badge-missing"
    
    html = '<div style="margin: 10px 0;">'
    for skill in sorted(skills):
        html += f'<span class="{badge_class}">{skill.title()}</span>'
    html += '</div>'
    
    st.markdown(html, unsafe_allow_html=True)

def create_match_gauge(score: float):
    """Create a gauge chart for match score"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Match Score", 'font': {'size': 24}},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': "#667eea"},
            'steps': [
                {'range': [0, 40], 'color': '#ffcdd2'},
                {'range': [40, 70], 'color': '#fff9c4'},
                {'range': [70, 100], 'color': '#c8e6c9'}
            ],
        }
    ))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=60, b=20))
    return fig

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def init_session_state():
    """Initialize all session state variables"""
    if 'app_mode' not in st.session_state:
        st.session_state.app_mode = 'home'
    
    # Rejection Analyzer states
    if 'llm' not in st.session_state:
        st.session_state.llm = OllamaLLM()
    if 'rejection_history' not in st.session_state:
        st.session_state.rejection_history = []
    
    # CV Tailor states
    if 'cv_data' not in st.session_state:
        st.session_state.cv_data = None
    if 'job_req' not in st.session_state:
        st.session_state.job_req = None
    if 'match_results' not in st.session_state:
        st.session_state.match_results = None
    if 'uploaded_file_path' not in st.session_state:
        st.session_state.uploaded_file_path = None

init_session_state()

# ============================================================================
# SIDEBAR NAVIGATION
# ============================================================================

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=80)
    st.title("🎯 Career Tools Suite")
    st.markdown("---")
    
    # Main app selector
    app_choice = st.radio(
        "Choose Your Tool",
        ["🏠 Home", "🔍 Rejection Analyzer", "📄 CV Tailor", "ℹ️ About"],
        key="app_selector"
    )
    
    st.markdown("---")
    
    # Show relevant status based on selected app
    if app_choice == "🔍 Rejection Analyzer":
        st.subheader("🔌 AI Status")
        if st.session_state.llm.test_connection():
            st.success("✅ AI Connected")
        else:
            st.error("❌ AI Disconnected")
            st.info("Run: `ollama serve`")
    
    elif app_choice == "📄 CV Tailor":
        st.subheader("📊 Progress")
        steps = [
            ("📤", "Upload CV", st.session_state.cv_data is not None),
            ("💼", "Job Description", st.session_state.job_req is not None),
            ("🎯", "Analysis", st.session_state.match_results is not None),
        ]
        for icon, label, completed in steps:
            if completed:
                st.markdown(f"✅ {icon} **{label}**")
            else:
                st.markdown(f"⚪ {icon} {label}")
    
    st.markdown("---")
    st.caption("Made with ❤️ by Siwar")

# ============================================================================
# HOME PAGE
# ============================================================================

if app_choice == "🏠 Home":
    st.markdown('<p class="main-header">🎯 Career Tools Suite</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Your AI-powered career advancement toolkit</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 30px; border-radius: 15px; color: white; height: 300px;">
            <h2>🔍 Smart Rejection Analyzer</h2>
            <p style="font-size: 1.1rem; margin-top: 20px;">
                Understand why you were rejected by comparing your CV against 
                job requirements with AI-powered analysis.
            </p>
            <ul style="margin-top: 20px;">
                <li>Deep CV vs Job Description comparison</li>
                <li>Identifies skill gaps</li>
                <li>Actionable improvement plan</li>
                <li>Timeline to qualification</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                    padding: 30px; border-radius: 15px; color: white; height: 300px;">
            <h2>📄 CV Tailor</h2>
            <p style="font-size: 1.1rem; margin-top: 20px;">
                Automatically customize your CV for any job posting by 
                intelligently adding missing skills.
            </p>
            <ul style="margin-top: 20px;">
                <li>Preserves your original format</li>
                <li>Adds missing required skills</li>
                <li>Generates cover letters</li>
                <li>Increases match score</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🎯 Tools Available", "2")
    with col2:
        st.metric("🤖 AI-Powered", "Yes")
    with col3:
        st.metric("📊 Success Rate", "95%+")
    
    st.markdown("---")
    st.info("👈 Select a tool from the sidebar to get started!")

# ============================================================================
# REJECTION ANALYZER APP (Placeholder - use pages/1_🔍_Rejection_Analyzer.py)
# ============================================================================

elif app_choice == "🔍 Rejection Analyzer":
    st.title("🔍 Smart Rejection Analysis")
    st.info("💡 This feature is available in the sidebar under **Rejection Analyzer** page.")
    st.markdown("Please use the dedicated page for full functionality.")

# ============================================================================
# CV TAILOR APP - WITH REAL ANALYSIS
# ============================================================================

elif app_choice == "📄 CV Tailor":
    st.title("📄 CV Tailor - Smart Resume Customization")
    
    tab1, tab2, tab3 = st.tabs(["📤 Upload & Analyze", "🎯 Results", "📥 Download"])
    
    # ========================================================================
    # TAB 1: UPLOAD & ANALYZE
    # ========================================================================
    with tab1:
        st.markdown("## Step 1: Upload Your CV")
        
        uploaded_cv = st.file_uploader(
            "Choose your CV file", 
            type=['pdf', 'docx'], 
            key="tailor_cv",
            help="Only DOCX files can be edited. PDF files can only be analyzed."
        )
        
        if uploaded_cv:
            with st.spinner("📖 Reading your CV..."):
                try:
                    # Save uploaded file
                    temp_path = f"uploaded_cv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{uploaded_cv.name.split('.')[-1]}"
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_cv.getbuffer())
                    
                    st.session_state.uploaded_file_path = temp_path
                    
                    # Parse CV using real parser
                    parser = CVParser()
                    st.session_state.cv_data = parser.parse_cv(temp_path)
                    st.session_state.cv_data.original_file_path = temp_path
                    
                    st.success("✅ CV uploaded and parsed successfully!")
                    
                    # Display CV summary
                    st.markdown("### 📊 Your CV Summary")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        name = st.session_state.cv_data.personal_info.name or "Not detected"
                        st.metric("👤 Name", name[:25])
                    with col2:
                        email = st.session_state.cv_data.personal_info.email
                        st.metric("📧 Email", "✓ Found" if email else "✗ Not found")
                    with col3:
                        skills_count = sum(len(v) for v in st.session_state.cv_data.skills.values() if isinstance(v, list))
                        st.metric("🛠️ Skills Found", skills_count)
                    
                    # Show detected skills
                    with st.expander("🔍 View Detected Skills", expanded=False):
                        if st.session_state.cv_data.skills.get('technical'):
                            display_skills_badges(st.session_state.cv_data.skills['technical'][:30])
                        else:
                            st.info("No technical skills detected")
                    
                except Exception as e:
                    st.error(f"❌ Error reading CV: {str(e)}")
                    st.info("Make sure the file is a valid PDF or DOCX")
        
        st.markdown("---")
        st.markdown("## Step 2: Paste Job Description")
        
        job_desc_tailor = st.text_area(
            "Paste the complete job description here",
            height=300,
            key="tailor_job",
            placeholder="Paste the full job posting including: job title, company, required skills, responsibilities..."
        )
        
        if st.button("🔍 Analyze Match", type="primary", use_container_width=True):
            if not st.session_state.cv_data:
                st.error("❌ Please upload your CV first!")
            elif not job_desc_tailor or len(job_desc_tailor) < 50:
                st.error("❌ Please provide a complete job description!")
            else:
                with st.spinner("🔍 Analyzing job description and comparing with your CV..."):
                    try:
                        # Analyze job description
                        analyzer = JobDescriptionAnalyzer()
                        st.session_state.job_req = analyzer.analyze(job_desc_tailor)
                        
                        # Calculate match score
                        matcher = KeywordMatcher()
                        st.session_state.match_results = matcher.calculate_match_score(
                            st.session_state.cv_data,
                            st.session_state.job_req
                        )
                        
                        st.success("✅ Analysis complete! Check the **Results** tab.")
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"❌ Error during analysis: {str(e)}")
    
    # ========================================================================
    # TAB 2: RESULTS - WITH REAL DATA
    # ========================================================================
    with tab2:
        st.markdown("## 🎯 Match Analysis Results")
        
        if not st.session_state.match_results:
            st.warning("⚠️ Please complete the upload and analysis in the first tab.")
        else:
            results = st.session_state.match_results
            score = results['overall_score']
            
            # Score interpretation
            if score >= 80:
                st.success(f"🎉 Excellent Match! {score}%")
            elif score >= 60:
                st.info(f"👍 Good Match: {score}%")
            else:
                st.warning(f"⚠️ Fair Match: {score}% - We'll add missing skills to improve!")
            
            st.divider()
            
            # Display gauge and stats
            col1, col2 = st.columns([1, 1])
            with col1:
                fig = create_match_gauge(score)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("### 📊 Quick Stats")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("✅ Matched Skills", len(results['matched_preferred']))
                with col_b:
                    st.metric("➕ Skills to Add", len(results['missing_preferred']))
                
                st.markdown("---")
                st.metric("🎯 Skills Match Score", f"{results['preferred_score']}%")
            
            st.divider()
            
            # Display matched and missing skills
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### ✅ Skills You Already Have")
                with st.expander(f"View Matched Skills ({len(results['matched_preferred'])})", expanded=True):
                    if results['matched_preferred']:
                        display_skills_badges(results['matched_preferred'])
                    else:
                        st.info("No matching skills found")
            
            with col2:
                st.markdown("### ➕ Skills We'll Add to Your CV")
                with st.expander(f"View Missing Skills ({len(results['missing_preferred'])})", expanded=True):
                    if results['missing_preferred']:
                        display_skills_badges(results['missing_preferred'], "missing")
                        st.info("💡 These skills will be added to your tailored CV!")
                    else:
                        st.success("✅ You already have all required skills!")
    
    # ========================================================================
    # TAB 3: DOWNLOAD - WITH REAL CV GENERATION
    # ========================================================================
    with tab3:
        st.markdown("## 📥 Download Your Tailored CV")
        
        if not st.session_state.match_results:
            st.warning("⚠️ Please complete the analysis first.")
        else:
            existing_skills = st.session_state.match_results['matched_preferred']
            missing_skills = st.session_state.match_results['missing_preferred']
            all_skills = existing_skills + missing_skills
            
            st.markdown(f"""
            <div class="info-box">
            <h3>✨ What You'll Get:</h3>
            <ul>
                <li><strong>{len(all_skills)} total skills</strong> ({len(existing_skills)} existing + {len(missing_skills)} new)</li>
                <li>Your original CV format <strong>preserved perfectly</strong></li>
                <li>Only the <strong>Skills section updated</strong></li>
                <li>Professional <strong>categorized skills layout</strong></li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()
            
            st.markdown("### 🛠️ Skills in Your New CV")
            display_skills_badges(sorted(all_skills)[:30])
            if len(all_skills) > 30:
                st.info(f"+ {len(all_skills) - 30} more skills...")
            
            st.divider()
            
            # Check if original file exists and is DOCX
            original_path = st.session_state.uploaded_file_path
            
            if not original_path or not Path(original_path).exists():
                st.error("❌ Original file not found. Please re-upload your CV.")
            elif not original_path.endswith('.docx'):
                st.error("❌ CV editing only works with DOCX files. Please upload a .docx file.")
            else:
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    if st.button("🚀 Generate Tailored CV", type="primary", use_container_width=True):
                        with st.spinner("📝 Creating your tailored CV..."):
                            try:
                                # Use real CV exporter
                                cv_bytes = CVExporter.export_docx(original_path, all_skills)
                                
                                st.session_state['cv_bytes'] = cv_bytes
                                st.session_state['cv_filename'] = f"tailored_cv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
                                
                                st.success("✅ CV ready for download!")
                                st.info("💡 Your original format has been preserved")
                                st.info("💡 Skills section has been updated with all required skills")
                                
                            except Exception as e:
                                st.error(f"❌ Error generating CV: {str(e)}")
                                st.info("Make sure python-docx is installed: `pip install python-docx`")
                
                with col2:
                    if 'cv_bytes' in st.session_state:
                        st.download_button(
                            label="⬇️ Download Tailored CV (DOCX)",
                            data=st.session_state['cv_bytes'],
                            file_name=st.session_state['cv_filename'],
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            type="primary",
                            use_container_width=True
                        )
                        
                        st.success("✅ Click above to download!")

# ============================================================================
# ABOUT PAGE
# ============================================================================

elif app_choice == "ℹ️ About":
    st.title("ℹ️ About Career Tools Suite")
    
    st.markdown("""
    ## 🎯 Mission
    
    Help job seekers understand rejections and optimize their applications using AI.
    
    ## 🛠️ Tools
    
    ### 1. Smart Rejection Analyzer
    - Compares your CV against job requirements
    - Identifies real skill gaps
    - Provides actionable improvement plans
    - Uses local AI (Ollama) for privacy
    
    ### 2. CV Tailor
    - Automatically customizes CVs for specific jobs
    - Preserves original formatting
    - Adds missing required skills
    - Generates cover letters
    
    ## 🔒 Privacy
    - Runs locally with Ollama
    - No data sent to external servers
    - Your documents stay on your machine
    
    ## 📚 Requirements
    - Python 3.8+
    - Ollama (for AI features)
    - See requirements.txt for packages
    
    ## 🚀 How to Use
    
    1. **CV Tailor**: Upload CV (DOCX) → Paste job description → Get tailored CV
    2. **Rejection Analyzer**: Upload CV → Paste job description → Get gap analysis
    
    **Note:** CV editing only works with DOCX files. PDF files can be analyzed but not edited.
    """)

st.markdown("---")
st.markdown('<div style="text-align: center; color: #666;"><p>🎯 Career Tools Suite | Powered by AI</p></div>', 
           unsafe_allow_html=True)
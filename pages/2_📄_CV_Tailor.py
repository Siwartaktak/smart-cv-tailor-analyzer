# ============================================================================
# CV TAILOR - STREAMLIT APP (UPDATED - PREFERRED SKILLS ONLY)
# ============================================================================
# ADD THIS AT THE VERY TOP - BEFORE OTHER IMPORTS
import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))
import streamlit as st
from datetime import datetime
from pathlib import Path
import plotly.graph_objects as go
import json

from cv_parser import CVParser, JobDescriptionAnalyzer, KeywordMatcher
from cv_exporter import CVExporter, MotivationLetterGenerator

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="CV Tailor - Smart Resume Customization",
    page_icon="📄",
    layout="wide"
)

# ============================================================================
# SESSION STATE
# ============================================================================

def init_session_state():
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
# CSS
# ============================================================================

st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 20px 0;
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
    .info-box {
        padding: 20px;
        border-radius: 10px;
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        margin: 10px 0;
        color: #000000;
    }
    .info-box h3, .info-box h4 {
        color: #000000;
    }
    .info-box ul, .info-box p, .info-box li {
        color: #000000;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_match_gauge(score: float):
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

def display_skills_badges(skills: list, badge_type: str = "matched"):
    if not skills:
        st.info("No skills in this category")
        return
    
    badge_class = "skill-badge" if badge_type == "matched" else "skill-badge skill-badge-missing"
    
    html = '<div style="margin: 10px 0;">'
    for skill in sorted(skills):
        html += f'<span class="{badge_class}">{skill.title()}</span>'
    html += '</div>'
    
    st.markdown(html, unsafe_allow_html=True)

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    st.markdown('<h1 class="main-header">📄 CV Tailor</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.title("📊 Progress")
        
        steps = [
            ("📤", "Upload CV", st.session_state.cv_data is not None),
            ("💼", "Job Description", st.session_state.job_req is not None),
            ("🎯", "Analysis", st.session_state.match_results is not None),
            ("📥", "Download", False)
        ]
        
        for icon, label, completed in steps:
            if completed:
                st.markdown(f"✅ {icon} **{label}**")
            else:
                st.markdown(f"⚪ {icon} {label}")
        
        st.divider()
        
        if st.session_state.match_results:
            score = st.session_state.match_results['overall_score']
            st.metric("🎯 Match Score", f"{score}%")
        
        st.divider()
        
        if st.button("🔄 Start Over", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            init_session_state()
            st.rerun()
    
    # Main Content Tabs
    tab1, tab2, tab3 = st.tabs([
        "📤 Upload & Analyze", 
        "🎯 Results", 
        "📥 Download Tailored CV"
    ])
    
    # ========================================================================
    # TAB 1: UPLOAD & ANALYZE
    # ========================================================================
    with tab1:
        st.markdown("## Step 1: Upload Your CV")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            uploaded_cv = st.file_uploader(
                "Choose your CV file",
                type=['pdf', 'docx'],
                help="Your CV format will be preserved - only skills section will be updated"
            )
            
            if uploaded_cv:
                with st.spinner("📖 Reading your CV..."):
                    try:
                        temp_path = f"uploaded_cv.{uploaded_cv.name.split('.')[-1]}"
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_cv.getbuffer())
                        
                        st.session_state.uploaded_file_path = temp_path
                        
                        parser = CVParser()
                        st.session_state.cv_data = parser.parse_cv(temp_path)
                        st.session_state.cv_data.original_file_path = temp_path
                        
                        st.success("✅ CV uploaded successfully!")
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        
        with col2:
            st.markdown("""
            <div class="info-box">
            <h4>📋 Supported Formats</h4>
            <ul>
                <li>Word (.docx)</li>
            </ul>
            <p><strong>Note:</strong> Your original formatting will be preserved!</p>
            </div>
            """, unsafe_allow_html=True)
        
        if st.session_state.cv_data:
            st.divider()
            st.markdown("### 📊 Your CV Summary")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                name = st.session_state.cv_data.personal_info.name or "Not found"
                st.metric("👤 Name", name[:25])
            with col2:
                email = st.session_state.cv_data.personal_info.email
                st.metric("📧 Email", "✓ Found" if email else "✗ Not found")
            with col3:
                skills_count = sum(len(v) for v in st.session_state.cv_data.skills.values() if isinstance(v, list))
                st.metric("🛠️ Skills Found", skills_count)
            
            with st.expander("🔍 View Your Skills", expanded=True):
                if st.session_state.cv_data.skills.get('technical'):
                    display_skills_badges(st.session_state.cv_data.skills['technical'][:20])
        
        st.divider()
        st.markdown("## Step 2: Paste Job Description")
        
        job_description = st.text_area(
            "Paste the complete job description here",
            height=300,
            placeholder="Include: job title, company, required skills, responsibilities..."
        )
        
        if st.button("🔍 Analyze Job & Compare", type="primary", disabled=not job_description):
            if not st.session_state.cv_data:
                st.error("⚠️ Please upload your CV first!")
            else:
                with st.spinner("🔍 Analyzing job description and comparing with your CV..."):
                    try:
                        analyzer = JobDescriptionAnalyzer()
                        st.session_state.job_req = analyzer.analyze(job_description)
                        
                        matcher = KeywordMatcher()
                        st.session_state.match_results = matcher.calculate_match_score(
                            st.session_state.cv_data,
                            st.session_state.job_req
                        )
                        
                        st.success("✅ Analysis complete! Check the Results tab.")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    
    # ========================================================================
    # TAB 2: RESULTS
    # ========================================================================
    with tab2:
        st.markdown("## 🎯 Match Analysis Results")
        
        if not st.session_state.match_results:
            st.warning("⚠️ Please complete the upload and analysis first.")
        else:
            results = st.session_state.match_results
            score = results['overall_score']
            
            if score >= 80:
                st.success(f"🎉 Excellent Match! {score}%")
            elif score >= 60:
                st.info(f"👍 Good Match: {score}%")
            else:
                st.warning(f"⚠️ Fair Match: {score}% - Don't worry, we'll add the missing skills!")
            
            st.divider()
            
            col1, col2 = st.columns([1, 1])
            with col1:
                fig = create_match_gauge(score)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.markdown("### 📊 Quick Stats")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("✅ Skills You Have", len(results['matched_preferred']))
                with col_b:
                    st.metric("➕ Skills to Add", len(results['missing_preferred']))
                
                st.markdown("---")
                st.metric("Skills Match", f"{results['preferred_score']}%")
            
            st.divider()
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### ✅ Skills You Already Have")
                with st.expander(f"Matched Skills ({len(results['matched_preferred'])})", expanded=True):
                    if results['matched_preferred']:
                        display_skills_badges(results['matched_preferred'])
                    else:
                        st.info("No skills matched")
                        
            with col2:
                st.markdown("### ➕ Skills We'll Add to Your CV")
                with st.expander(f"Missing Skills ({len(results['missing_preferred'])})", expanded=True):
                    if results['missing_preferred']:
                        display_skills_badges(results['missing_preferred'], "missing")
                        st.info("💡 We'll add these to boost your match!")
                    else:
                        st.success("✅ All skills matched!")
    
    # ========================================================================
    # TAB 3: DOWNLOAD TAILORED CV
    # ========================================================================
    with tab3:
        st.markdown("## 📥 Download Your Tailored CV & Cover Letter")
        
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
                <li>Only the <strong>SKILLS section updated</strong></li>
                <li>Professional <strong>categorized skills layout</strong></li>
                <li>Ready-to-send <strong>motivation letter</strong></li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()
            
            st.markdown("### 🛠️ Skills in Your New CV")
            display_skills_badges(sorted(all_skills)[:30])
            if len(all_skills) > 30:
                st.info(f"+ {len(all_skills) - 30} more skills...")
            
            st.divider()
            
            st.markdown("### 📄 Download Updated CV")
            
            original_path = st.session_state.uploaded_file_path
            
            if not original_path or not Path(original_path).exists():
                st.error("❌ Original file not found. Please re-upload your CV.")
            else:
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    if st.button("🚀 Generate Tailored CV", type="primary", use_container_width=True):
                        with st.spinner("📝 Creating your tailored CV (preserving original format)..."):
                            try:
                                # Export using the existing method that preserves format
                                cv_bytes = CVExporter.export_docx(original_path, all_skills)
                                
                                st.session_state['cv_bytes'] = cv_bytes
                                st.session_state['cv_filename'] = f"tailored_cv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
                                
                                st.success("✅ CV ready for download!")
                                st.info("💡 Format: DOCX (editable)")
                                st.info("💡 Your original layout and design are preserved")
                                st.info("💡 Only the Skills section has been updated")
                                
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
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
                        
                        st.success("✅ Ready to download!")
                        st.info("📝 You can convert to PDF using Word or Google Docs")
            
            st.divider()
            
            st.markdown("### 📧 Download Motivation Letter")
            
            # Pre-fill from CV
            candidate_name = st.session_state.cv_data.personal_info.name or "Your Name"
            candidate_email = st.session_state.cv_data.personal_info.email or "your.email@example.com"
            candidate_phone = st.session_state.cv_data.personal_info.phone or ""
            job_title = st.session_state.job_req.job_title or "the position"
            company = st.session_state.job_req.company or "your company"
            
            st.markdown("#### 📝 Personalize Your Cover Letter")
            
            col1, col2 = st.columns(2)
            with col1:
                company_input = st.text_input("Company Name", value=company, key="company_cl")
                candidate_address = st.text_input("Your Address (Optional)", placeholder="Street, City, Country", key="address_cl")
                education_input = st.text_area(
                    "Education/Background (Optional)",
                    placeholder="e.g., I am currently pursuing a Master's degree in Data Science at XYZ University",
                    height=80,
                    key="education_cl"
                )
            
            with col2:
                job_title_input = st.text_input("Job Title", value=job_title, key="jobtitle_cl")
                portfolio_input = st.text_input("Portfolio URL (Optional)", placeholder="https://yourportfolio.com", key="portfolio_cl")
                github_input = st.text_input("GitHub URL (Optional)", placeholder="https://github.com/yourusername", key="github_cl")
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚀 Generate Professional Cover Letter", type="primary", use_container_width=True):
                    with st.spinner("✍️ Writing your personalized cover letter..."):
                        try:
                            generator = MotivationLetterGenerator()
                            letter = generator.generate(
                                candidate_name=candidate_name,
                                candidate_email=candidate_email,
                                candidate_phone=candidate_phone,
                                candidate_address=candidate_address,
                                job_title=job_title_input,
                                company_name=company_input,
                                matched_skills=existing_skills,
                                responsibilities=st.session_state.job_req.responsibilities,
                                candidate_education=education_input,
                                portfolio_url=portfolio_input,
                                github_url=github_input
                            )
                            st.session_state['motivation_letter'] = letter
                            st.success("✅ Professional cover letter ready!")
                            st.info("💡 Review and customize before sending")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
            
            with col2:
                if 'motivation_letter' in st.session_state:
                    st.download_button(
                        label="⬇️ Download Cover Letter (.txt)",
                        data=st.session_state['motivation_letter'],
                        file_name=f"cover_letter_{company_input.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
            
            if 'motivation_letter' in st.session_state:
                with st.expander("📄 Preview Cover Letter", expanded=True):
                    st.text_area(
                        "Your Cover Letter",
                        value=st.session_state['motivation_letter'],
                        height=400,
                        key="preview_cl",
                        help="You can copy and edit this text before using it"
                    )
            
            st.divider()
            
            st.info("""
            **💡 Tips for Using Your Tailored CV:**
            
            1. **Review Before Sending**: Always review the generated content
            2. **Original Format Preserved**: Your layout, fonts, and design remain intact
            3. **Skills Updated**: Only the Skills section has been enhanced
            4. **Customize Further**: Feel free to edit the downloaded DOCX file
            5. **Convert to PDF**: Use Word or Google Docs for final PDF conversion
            6. **Track Applications**: Keep both original and tailored versions
            """)

if __name__ == "__main__":
    main()
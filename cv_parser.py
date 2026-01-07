# ============================================================================
# CV TAILOR - CV PARSER (FINAL VERSION)
# ============================================================================

import re
from typing import Dict, List, Set
from dataclasses import dataclass
import PyPDF2
from docx import Document

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class PersonalInfo:
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""

@dataclass
class CVData:
    personal_info: PersonalInfo
    skills: Dict[str, List[str]] = None
    raw_text: str = ""
    original_file_path: str = ""
    
    def __post_init__(self):
        if self.skills is None:
            self.skills = {}

@dataclass
class JobRequirements:
    job_title: str = ""
    company: str = ""
    required_skills: List[str] = None
    preferred_skills: List[str] = None
    all_skills: List[str] = None
    responsibilities: List[str] = None
    
    def __post_init__(self):
        if self.required_skills is None:
            self.required_skills = []
        if self.preferred_skills is None:
            self.preferred_skills = []
        if self.all_skills is None:
            self.all_skills = []
        if self.responsibilities is None:
            self.responsibilities = []
        
        if not self.all_skills and (self.required_skills or self.preferred_skills):
            self.all_skills = list(set(self.required_skills + self.preferred_skills))

# ============================================================================
# KEYWORD EXTRACTOR
# ============================================================================

class KeywordExtractor:
    def __init__(self):
        self.technical_skills = {
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'go', 
            'php', 'swift', 'kotlin', 'scala', 'rust', 'r', 'matlab',
            'html', 'css', 'react', 'angular', 'vue', 'node.js', 'nodejs',
            'django', 'flask', 'fastapi', 'express', 'spring boot', 'asp.net',
            'next.js', 'svelte', 'jquery', 'bootstrap', 'tailwind',
            'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'oracle', 'nosql',
            'dynamodb', 'cassandra', 'elasticsearch', 'sqlite',
            'aws', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes', 'k8s',
            'terraform', 'ansible', 'jenkins', 'gitlab', 'github actions', 'ci/cd',
            'machine learning', 'deep learning', 'data science', 'artificial intelligence',
            'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'pandas', 'numpy',
            'matplotlib', 'nlp', 'computer vision', 'opencv',
            'spark', 'hadoop', 'kafka', 'airflow', 'databricks',
            'git', 'jira', 'agile', 'scrum', 'devops',
            'rest api', 'graphql', 'microservices', 'linux', 'bash',
            'api', 'etl', 'tableau', 'power bi', 'excel'
        }
    
    def extract_skills_from_text(self, text: str) -> Set[str]:
        text_lower = text.lower()
        found_skills = set()
        
        for skill in self.technical_skills:
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text_lower):
                found_skills.add(skill)
        
        # Handle common abbreviations
        if re.search(r'\bml\b', text_lower):
            found_skills.add('machine learning')
        if re.search(r'\bai\b', text_lower):
            found_skills.add('artificial intelligence')
        if re.search(r'\bjs\b', text_lower):
            found_skills.add('javascript')
        
        return found_skills

# ============================================================================
# CV PARSER
# ============================================================================

class CVParser:
    def __init__(self):
        self.keyword_extractor = KeywordExtractor()
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        self.phone_pattern = r'(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        self.linkedin_pattern = r'linkedin\.com/in/[\w-]+'
        self.github_pattern = r'github\.com/[\w-]+'
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            print(f"Error reading PDF: {e}")
        return text
    
    def extract_text_from_docx(self, file_path: str) -> str:
        text = ""
        try:
            doc = Document(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            print(f"Error reading DOCX: {e}")
        return text
    
    def extract_text(self, file_path: str) -> str:
        if file_path.endswith('.pdf'):
            return self.extract_text_from_pdf(file_path)
        elif file_path.endswith('.docx'):
            return self.extract_text_from_docx(file_path)
        else:
            raise ValueError("Unsupported file format")
    
    def extract_personal_info(self, text: str) -> PersonalInfo:
        personal = PersonalInfo()
        
        email_match = re.search(self.email_pattern, text)
        if email_match:
            personal.email = email_match.group(0)
        
        phone_match = re.search(self.phone_pattern, text)
        if phone_match:
            personal.phone = phone_match.group(0)
        
        linkedin_match = re.search(self.linkedin_pattern, text, re.IGNORECASE)
        if linkedin_match:
            personal.linkedin = linkedin_match.group(0)
        
        github_match = re.search(self.github_pattern, text, re.IGNORECASE)
        if github_match:
            personal.github = github_match.group(0)
        
        lines = text.split('\n')
        for line in lines[:5]:
            line = line.strip()
            if line and 3 < len(line) < 50 and not re.search(r'[@\d]', line):
                personal.name = line
                break
        
        return personal
    
    def parse_cv(self, file_path: str) -> CVData:
        raw_text = self.extract_text(file_path)
        personal_info = self.extract_personal_info(raw_text)
        all_cv_skills = self.keyword_extractor.extract_skills_from_text(raw_text)
        
        skills_dict = {'technical': sorted(list(all_cv_skills))}
        
        cv_data = CVData(
            personal_info=personal_info,
            skills=skills_dict,
            raw_text=raw_text,
            original_file_path=file_path
        )
        
        return cv_data

# ============================================================================
# JOB DESCRIPTION ANALYZER
# ============================================================================

class JobDescriptionAnalyzer:
    def __init__(self):
        self.keyword_extractor = KeywordExtractor()
    
    def extract_skills_from_job(self, text: str) -> Dict[str, List[str]]:
        all_skills = self.keyword_extractor.extract_skills_from_text(text)
        text_lower = text.lower()
        
        required_skills = []
        preferred_skills = []
        
        # Look for required section
        required_patterns = [
            r'required(?:\s+(?:skills|qualifications))?[:\s]+(.*?)(?=preferred|nice|bonus|responsibilities|$)',
            r'must\s+have[:\s]+(.*?)(?=preferred|nice|$)',
        ]
        
        required_text = ""
        for pattern in required_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL)
            if match:
                required_text = match.group(1)
                break
        
        # Categorize skills
        for skill in all_skills:
            if required_text and skill in required_text:
                required_skills.append(skill)
            else:
                preferred_skills.append(skill)
        
        required_skills = list(set(required_skills))
        preferred_skills = list(set(preferred_skills))
        
        # If no separation, split 70/30
        if not preferred_skills and len(required_skills) > 3:
            split_point = int(len(required_skills) * 0.7)
            preferred_skills = required_skills[split_point:]
            required_skills = required_skills[:split_point]
        
        return {
            'required': sorted(required_skills),
            'preferred': sorted(preferred_skills),
            'all': sorted(list(all_skills))
        }
    
    def extract_responsibilities(self, text: str) -> List[str]:
        """Extract key responsibilities"""
        responsibilities = []
        
        patterns = [
            r'(?:responsibilities|duties)[:\s]+(.*?)(?=requirements|qualifications|skills|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                section_text = match.group(1)
                items = re.findall(r'[•\-\*]\s*([^\n•\-\*]+)', section_text)
                if items:
                    responsibilities = [item.strip() for item in items if len(item.strip()) > 20]
                break
        
        return responsibilities[:5]
    
    def analyze(self, job_description: str) -> JobRequirements:
        lines = job_description.split('\n')
        job_title = ""
        company = ""
        
        for line in lines[:10]:
            line = line.strip()
            if line and 5 < len(line) < 100 and not line.startswith(('http', 'www')):
                if not job_title:
                    job_title = line
                elif not company and line != job_title:
                    company = line
                    break
        
        skills_dict = self.extract_skills_from_job(job_description)
        responsibilities = self.extract_responsibilities(job_description)
        
        job_req = JobRequirements(
            job_title=job_title,
            company=company,
            required_skills=skills_dict['required'],
            preferred_skills=skills_dict['preferred'],
            all_skills=skills_dict['all'],
            responsibilities=responsibilities
        )
        
        return job_req

# ============================================================================
# KEYWORD MATCHER
# ============================================================================

class KeywordMatcher:
    def calculate_match_score(self, cv_data: CVData, job_req: JobRequirements) -> Dict:
        cv_skills = set()
        for skill_category in cv_data.skills.values():
            if isinstance(skill_category, list):
                cv_skills.update([s.lower() for s in skill_category])
        
        job_required = set([s.lower() for s in job_req.required_skills])
        job_preferred = set([s.lower() for s in job_req.preferred_skills])
        
        matched_required = cv_skills.intersection(job_required)
        missing_required = job_required - cv_skills
        
        matched_preferred = cv_skills.intersection(job_preferred)
        missing_preferred = job_preferred - cv_skills
        
        required_score = (len(matched_required) / len(job_required) * 100) if job_required else 100
        preferred_score = (len(matched_preferred) / len(job_preferred) * 100) if job_preferred else 100
        overall_score = (required_score * 0.7 + preferred_score * 0.3)
        
        results = {
            'overall_score': round(overall_score, 1),
            'required_score': round(required_score, 1),
            'preferred_score': round(preferred_score, 1),
            'matched_required': sorted(list(matched_required)),
            'missing_required': sorted(list(missing_required)),
            'matched_preferred': sorted(list(matched_preferred)),
            'missing_preferred': sorted(list(missing_preferred)),
        }
        
        return results
import streamlit as st
import spacy
import fitz  # PyMuPDF
from docx import Document
import re
import json
import pandas as pd
import io
from datetime import datetime
import zipfile
from typing import Dict, List, Any, Optional
import tempfile
import os

# Configure Streamlit page
st.set_page_config(
    page_title="Smart Resume Parser",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

class ResumeParser:
    def __init__(self):
        """Initialize the resume parser with spaCy model."""
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except IOError:
            st.error("spaCy English model not found. Please install it using: python -m spacy download en_core_web_sm")
            st.stop()
        
        # Skills patterns (expandable)
        self.skills_patterns = [
            r'\b(?:python|java|javascript|c\+\+|c#|php|ruby|swift|kotlin|go|rust|scala)\b',
            r'\b(?:react|angular|vue|django|flask|spring|express|node\.?js)\b',
            r'\b(?:sql|mysql|postgresql|mongodb|redis|elasticsearch|sqlite)\b',
            r'\b(?:aws|azure|gcp|docker|kubernetes|jenkins|git|linux|windows)\b',
            r'\b(?:html|css|bootstrap|tailwind|sass|less)\b',
            r'\b(?:machine learning|ai|nlp|deep learning|tensorflow|pytorch|scikit-learn)\b',
            r'\b(?:project management|agile|scrum|jira|confluence)\b',
            r'\b(?:photoshop|illustrator|figma|sketch|adobe|canva)\b'
        ]
        
        # Section headers patterns
        self.section_patterns = {
            'experience': r'(?i)(?:work\s+)?(?:experience|employment|professional\s+experience|career|work\s+history)',
            'education': r'(?i)(?:education|academic|qualifications|degrees?|university|college)',
            'skills': r'(?i)(?:skills|technical\s+skills|competencies|technologies|expertise)',
            'projects': r'(?i)(?:projects?|portfolio|work\s+samples)',
            'contact': r'(?i)(?:contact|personal\s+info|details)',
            'summary': r'(?i)(?:summary|objective|profile|about|overview)'
        }
        
        # Email and phone patterns
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        self.phone_pattern = r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'

    def extract_text_from_pdf(self, pdf_file) -> str:
        """Extract text from PDF using PyMuPDF."""
        try:
            pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
            text = ""
            for page_num in range(pdf_document.page_count):
                page = pdf_document.load_page(page_num)
                text += page.get_text()
            pdf_document.close()
            return text
        except Exception as e:
            st.error(f"Error extracting PDF text: {str(e)}")
            return ""

    def extract_text_from_docx(self, docx_file) -> str:
        """Extract text from DOCX using python-docx."""
        try:
            doc = Document(docx_file)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            st.error(f"Error extracting DOCX text: {str(e)}")
            return ""

    def clean_text(self, text: str) -> str:
        """Clean and preprocess text."""
        # Remove extra whitespaces and normalize
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text

    def extract_contact_info(self, text: str) -> Dict[str, Optional[str]]:
        """Extract contact information."""
        contact_info = {
            'email': None,
            'phone': None
        }
        
        # Extract email
        email_match = re.search(self.email_pattern, text)
        if email_match:
            contact_info['email'] = email_match.group()
        
        # Extract phone
        phone_match = re.search(self.phone_pattern, text)
        if phone_match:
            contact_info['phone'] = phone_match.group()
        
        return contact_info

    def extract_name(self, text: str) -> Optional[str]:
        """Extract candidate name using spaCy NER."""
        doc = self.nlp(text[:500])  # Check first 500 characters
        names = []
        
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                names.append(ent.text)
        
        # Return first name found (usually the candidate's name)
        return names[0] if names else None

    def extract_skills(self, text: str) -> List[str]:
        """Extract skills using regex patterns."""
        skills = set()
        text_lower = text.lower()
        
        for pattern in self.skills_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            skills.update(matches)
        
        return list(skills)

    def extract_sections(self, text: str) -> Dict[str, str]:
        """Extract different sections from resume."""
        sections = {}
        
        for section_name, pattern in self.section_patterns.items():
            # Find section header
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                start_pos = match.end()
                
                # Find the end of this section (next section header or end of text)
                end_pos = len(text)
                for other_pattern in self.section_patterns.values():
                    if other_pattern != pattern:
                        next_match = re.search(other_pattern, text[start_pos:], re.IGNORECASE | re.MULTILINE)
                        if next_match:
                            potential_end = start_pos + next_match.start()
                            if potential_end < end_pos:
                                end_pos = potential_end
                
                section_content = text[start_pos:end_pos].strip()
                sections[section_name] = section_content[:500]  # Limit content length
        
        return sections

    def extract_education(self, text: str) -> List[Dict[str, str]]:
        """Extract education information."""
        education_info = []
        
        # Common degree patterns
        degree_patterns = [
            r'(?i)\b(?:bachelor|master|phd|doctorate|diploma|certificate)\s+(?:of\s+)?(?:science|arts|engineering|business|computer)\b',
            r'(?i)\b(?:b\.?s\.?|m\.?s\.?|b\.?a\.?|m\.?a\.?|ph\.?d\.?|mba)\b',
            r'(?i)\b(?:undergraduate|graduate|postgraduate)\b'
        ]
        
        # University/Institution patterns
        institution_patterns = [
            r'(?i)\b(?:university|college|institute|school)\s+of\s+\w+\b',
            r'(?i)\b\w+\s+(?:university|college|institute)\b'
        ]
        
        degrees = []
        for pattern in degree_patterns:
            degrees.extend(re.findall(pattern, text))
        
        institutions = []
        for pattern in institution_patterns:
            institutions.extend(re.findall(pattern, text))
        
        # Combine degrees and institutions
        for i, degree in enumerate(degrees[:3]):  # Limit to 3 entries
            education_entry = {
                'degree': degree.strip(),
                'institution': institutions[i].strip() if i < len(institutions) else 'N/A'
            }
            education_info.append(education_entry)
        
        return education_info

    def extract_experience_years(self, text: str) -> Optional[str]:
        """Extract total years of experience."""
        experience_patterns = [
            r'(?i)(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)',
            r'(?i)(?:experience|exp).*?(\d+)\+?\s*(?:years?|yrs?)',
        ]
        
        for pattern in experience_patterns:
            match = re.search(pattern, text)
            if match:
                return f"{match.group(1)} years"
        
        return None

    def parse_resume(self, file, filename: str) -> Dict[str, Any]:
        """Parse a single resume and extract structured information."""
        # Extract text based on file type
        if filename.lower().endswith('.pdf'):
            text = self.extract_text_from_pdf(file)
        elif filename.lower().endswith(('.docx', '.doc')):
            text = self.extract_text_from_docx(file)
        else:
            return {'error': 'Unsupported file format'}
        
        if not text:
            return {'error': 'Could not extract text from file'}
        
        # Clean text
        clean_text = self.clean_text(text)
        
        # Extract information
        parsed_data = {
            'filename': filename,
            'name': self.extract_name(clean_text),
            'contact_info': self.extract_contact_info(clean_text),
            'skills': self.extract_skills(clean_text),
            'education': self.extract_education(clean_text),
            'experience_years': self.extract_experience_years(clean_text),
            'sections': self.extract_sections(clean_text),
            'parsed_at': datetime.now().isoformat()
        }
        
        return parsed_data

def main():
    st.title("Smart Resume Parser")
    st.markdown("Upload multiple resumes to extract structured information automatically!")
    
    # Initialize parser
    if 'parser' not in st.session_state:
        st.session_state.parser = ResumeParser()
    
    # Sidebar
    st.sidebar.title("📊 Parser Settings")
    max_files = st.sidebar.slider("Maximum files to process", 5, 50, 10)
    export_format = st.sidebar.selectbox("Export Format", ["JSON", "CSV", "Both"])
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose resume files",
        type=['pdf', 'docx', 'doc'],
        accept_multiple_files=True,
        help=f"Upload up to {max_files} PDF or DOCX files"
    )
    
    if uploaded_files:
        if len(uploaded_files) > max_files:
            st.warning(f"Too many files! Please upload maximum {max_files} files.")
            uploaded_files = uploaded_files[:max_files]
        
        st.info(f"Processing {len(uploaded_files)} resume(s)...")
        
        # Process files
        parsed_results = []
        progress_bar = st.progress(0)
        
        for i, file in enumerate(uploaded_files):
            with st.spinner(f"Processing {file.name}..."):
                result = st.session_state.parser.parse_resume(file, file.name)
                parsed_results.append(result)
            progress_bar.progress((i + 1) / len(uploaded_files))
        
        # Store results in session state
        st.session_state.parsed_results = parsed_results
        
        # Display results
        st.success(f"Successfully processed {len(parsed_results)} resumes!")
        
        # Create tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Summary", "👤 Individual Results", "📊 Skills Analysis", "💾 Export"])
        
        with tab1:
            display_summary(parsed_results)
        
        with tab2:
            display_individual_results(parsed_results)
        
        with tab3:
            display_skills_analysis(parsed_results)
        
        with tab4:
            display_export_options(parsed_results, export_format)

def display_summary(results: List[Dict]):
    """Display summary statistics."""
    st.subheader("📈 Processing Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    successful = sum(1 for r in results if 'error' not in r)
    failed = len(results) - successful
    
    with col1:
        st.metric("Total Files", len(results))
    with col2:
        st.metric("Successfully Parsed", successful, delta=successful-failed)
    with col3:
        st.metric("Failed", failed, delta=failed-successful if failed > 0 else None)
    with col4:
        total_skills = sum(len(r.get('skills', [])) for r in results if 'error' not in r)
        st.metric("Total Skills Found", total_skills)
    
    # Create summary table
    if successful > 0:
        summary_data = []
        for result in results:
            if 'error' not in result:
                summary_data.append({
                    'Filename': result['filename'],
                    'Name': result.get('name', 'N/A'),
                    'Email': result.get('contact_info', {}).get('email', 'N/A'),
                    'Phone': result.get('contact_info', {}).get('phone', 'N/A'),
                    'Skills Count': len(result.get('skills', [])),
                    'Education Count': len(result.get('education', [])),
                    'Experience': result.get('experience_years', 'N/A')
                })
        
        if summary_data:
            df = pd.DataFrame(summary_data)
            st.dataframe(df, use_container_width=True)

def display_individual_results(results: List[Dict]):
    """Display individual resume results."""
    st.subheader("👤 Individual Resume Details")
    
    for i, result in enumerate(results):
        with st.expander(f"📄 {result['filename']}", expanded=i==0):
            if 'error' in result:
                st.error(f"Error processing file: {result['error']}")
                continue
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Personal Information:**")
                st.write(f"• Name: {result.get('name', 'N/A')}")
                st.write(f"• Email: {result.get('contact_info', {}).get('email', 'N/A')}")
                st.write(f"• Phone: {result.get('contact_info', {}).get('phone', 'N/A')}")
                st.write(f"• Experience: {result.get('experience_years', 'N/A')}")
            
            with col2:
                st.write("**Skills:**")
                skills = result.get('skills', [])
                if skills:
                    for skill in skills[:10]:  # Show first 10 skills
                        st.write(f"• {skill}")
                    if len(skills) > 10:
                        st.write(f"... and {len(skills) - 10} more")
                else:
                    st.write("No skills detected")
            
            # Education
            education = result.get('education', [])
            if education:
                st.write("**Education:**")
                for edu in education:
                    st.write(f"• {edu['degree']} - {edu['institution']}")
            
            # Sections
            sections = result.get('sections', {})
            if sections:
                st.write("**Sections Found:**")
                for section_name, content in sections.items():
                    if content:
                        st.write(f"• {section_name.title()}: {content[:100]}...")

def display_skills_analysis(results: List[Dict]):
    """Display skills analysis and statistics."""
    st.subheader("📊 Skills Analysis")
    
    # Collect all skills
    all_skills = []
    for result in results:
        if 'error' not in result:
            all_skills.extend(result.get('skills', []))
    
    if not all_skills:
        st.warning("No skills found in the processed resumes.")
        return
    
    # Count skills frequency
    from collections import Counter
    skill_counts = Counter(all_skills)
    
    # Most common skills
    st.write("**Top 15 Most Common Skills:**")
    top_skills = skill_counts.most_common(15)
    
    col1, col2 = st.columns(2)
    
    with col1:
        for skill, count in top_skills[:8]:
            st.write(f"• {skill}: {count} resume(s)")
    
    with col2:
        for skill, count in top_skills[8:]:
            st.write(f"• {skill}: {count} resume(s)")
    
    # Skills distribution chart
    if len(top_skills) > 0:
        chart_data = pd.DataFrame(top_skills, columns=['Skill', 'Count'])
        st.bar_chart(chart_data.set_index('Skill'))

def display_export_options(results: List[Dict], format_choice: str):
    """Display export options and generate downloadable files."""
    st.subheader("💾 Export Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Generate Export Files", type="primary"):
            # Prepare data for export
            export_data = []
            for result in results:
                if 'error' not in result:
                    export_data.append({
                        'filename': result['filename'],
                        'name': result.get('name', ''),
                        'email': result.get('contact_info', {}).get('email', ''),
                        'phone': result.get('contact_info', {}).get('phone', ''),
                        'skills': ', '.join(result.get('skills', [])),
                        'education': ', '.join([f"{e['degree']} - {e['institution']}" for e in result.get('education', [])]),
                        'experience_years': result.get('experience_years', ''),
                        'parsed_at': result.get('parsed_at', '')
                    })
            
            if export_data:
                # Create download buttons
                if format_choice in ["JSON", "Both"]:
                    json_data = json.dumps(results, indent=2, default=str)
                    st.download_button(
                        label="📥 Download JSON",
                        data=json_data,
                        file_name=f"parsed_resumes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                
                if format_choice in ["CSV", "Both"]:
                    df = pd.DataFrame(export_data)
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_data,
                        file_name=f"parsed_resumes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                
                st.success("Export files generated successfully!")
            else:
                st.error("No data to export.")
    
    with col2:
        st.info("**Export Information:**\n"
                "• JSON format includes complete parsed data\n"
                "• CSV format includes summarized data\n"
                "• Files are timestamped for easy identification")

if __name__ == "__main__":
    main()
import streamlit as st
import fitz  # PyMuPDF
from docx import Document
import re
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import Counter

# Configure Streamlit page
st.set_page_config(
    page_title="Smart Resume Parser",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

class ResumeParser:
    def __init__(self):
        """Initialize the resume parser without spaCy (Streamlit Cloud compatible)."""
        
        # Skills patterns (comprehensive list)
        self.skills_patterns = [
            # Programming Languages
            r'\b(?:python|java|javascript|typescript|c\+\+|c#|php|ruby|swift|kotlin|go|rust|scala|r|matlab)\b',
            
            # Web Technologies
            r'\b(?:react|angular|vue|django|flask|spring|express|node\.?js|next\.?js|nuxt)\b',
            r'\b(?:html5?|css3?|bootstrap|tailwind|sass|less|jquery)\b',
            
            # Databases
            r'\b(?:sql|mysql|postgresql|mongodb|redis|elasticsearch|sqlite|oracle|cassandra)\b',
            
            # Cloud & DevOps
            r'\b(?:aws|azure|gcp|google cloud|docker|kubernetes|jenkins|git|github|gitlab|linux|windows|ubuntu)\b',
            r'\b(?:terraform|ansible|puppet|chef|vagrant|ci/cd|devops)\b',
            
            # Data Science & AI
            r'\b(?:machine learning|ai|nlp|deep learning|tensorflow|pytorch|scikit-learn|pandas|numpy|matplotlib|seaborn)\b',
            r'\b(?:data science|data analysis|statistics|big data|hadoop|spark|kafka)\b',
            
            # Business & Soft Skills
            r'\b(?:project management|agile|scrum|jira|confluence|leadership|communication)\b',
            
            # Design Tools
            r'\b(?:photoshop|illustrator|figma|sketch|adobe|canva|after effects|premiere)\b',
            
            # Mobile Development
            r'\b(?:android|ios|react native|flutter|xamarin|swift|objective-c)\b'
        ]
        
        # Section headers patterns
        self.section_patterns = {
            'experience': r'(?i)(?:work\s+)?(?:experience|employment|professional\s+experience|career|work\s+history|employment\s+history)',
            'education': r'(?i)(?:education|academic|qualifications|degrees?|university|college|academic\s+background)',
            'skills': r'(?i)(?:skills|technical\s+skills|competencies|technologies|expertise|core\s+competencies)',
            'projects': r'(?i)(?:projects?|portfolio|work\s+samples|personal\s+projects)',
            'contact': r'(?i)(?:contact|personal\s+info|details|contact\s+information)',
            'summary': r'(?i)(?:summary|objective|profile|about|overview|professional\s+summary)',
            'certifications': r'(?i)(?:certifications?|certificates?|licenses?|achievements?)'
        }
        
        # Contact patterns
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        self.phone_pattern = r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        
        # Name patterns (without spaCy)
        self.name_indicators = [
            r'^([A-Z][a-z]+\s+[A-Z][a-z]+)',  # First line with proper case
            r'([A-Z][a-z]+\s+[A-Z]\.?\s+[A-Z][a-z]+)',  # Name with middle initial
            r'([A-Z][A-Z\s]+[A-Z])',  # All caps names
        ]

    def extract_text_from_pdf(self, pdf_file) -> str:
        """Extract text from PDF using PyMuPDF."""
        try:
            pdf_bytes = pdf_file.read()
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
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
        """Extract candidate name using pattern matching (spaCy-free version)."""
        # Get first few lines where name usually appears
        lines = text.split('\n')[:5]
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines or lines with emails/phones
            if not line or '@' in line or re.search(r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', line):
                continue
            
            # Try different name patterns
            for pattern in self.name_indicators:
                match = re.search(pattern, line)
                if match:
                    candidate_name = match.group(1).strip()
                    
                    # Basic validation - ensure it looks like a name
                    if (len(candidate_name.split()) >= 2 and 
                        len(candidate_name) > 3 and 
                        not any(keyword in candidate_name.lower() for keyword in ['resume', 'cv', 'curriculum'])):
                        return candidate_name
        
        return None

    def extract_skills(self, text: str) -> List[str]:
        """Extract skills using regex patterns."""
        skills = set()
        text_lower = text.lower()
        
        for pattern in self.skills_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            skills.update(matches)
        
        # Remove common false positives
        false_positives = {'as', 'in', 'on', 'to', 'or', 'and', 'the', 'a', 'an'}
        skills = {skill for skill in skills if skill not in false_positives and len(skill) > 1}
        
        return sorted(list(skills))

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
                sections[section_name] = section_content[:800]  # Increased limit
        
        return sections

    def extract_education(self, text: str) -> List[Dict[str, str]]:
        """Extract education information."""
        education_info = []
        
        # Enhanced degree patterns
        degree_patterns = [
            r'(?i)\b(?:bachelor|master|phd|doctorate|diploma|certificate)\s+(?:of\s+)?(?:science|arts|engineering|business|computer|technology)\b',
            r'(?i)\b(?:b\.?s\.?|m\.?s\.?|b\.?a\.?|m\.?a\.?|ph\.?d\.?|mba|m\.?tech|b\.?tech)\b',
            r'(?i)\b(?:undergraduate|graduate|postgraduate|doctoral)\b'
        ]
        
        # Enhanced institution patterns
        institution_patterns = [
            r'(?i)\b(?:university|college|institute|school)\s+of\s+[\w\s]+\b',
            r'(?i)\b[\w\s]+\s+(?:university|college|institute|polytechnic)\b',
            r'(?i)\b(?:iit|mit|stanford|harvard|cambridge|oxford)[\w\s]*\b'
        ]
        
        degrees = []
        for pattern in degree_patterns:
            matches = re.findall(pattern, text)
            degrees.extend([match.strip() for match in matches])
        
        institutions = []
        for pattern in institution_patterns:
            matches = re.findall(pattern, text)
            institutions.extend([match.strip() for match in matches])
        
        # Combine degrees and institutions
        max_entries = min(len(degrees), 3)  # Limit to 3 entries
        for i in range(max_entries):
            education_entry = {
                'degree': degrees[i],
                'institution': institutions[i] if i < len(institutions) else 'Institution not specified'
            }
            education_info.append(education_entry)
        
        return education_info

    def extract_experience_years(self, text: str) -> Optional[str]:
        """Extract total years of experience."""
        experience_patterns = [
            r'(?i)(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)',
            r'(?i)(?:experience|exp).*?(\d+)\+?\s*(?:years?|yrs?)',
            r'(?i)(\d+)\+?\s*(?:years?|yrs?).*?(?:experience|exp)',
        ]
        
        for pattern in experience_patterns:
            match = re.search(pattern, text)
            if match:
                years = match.group(1)
                return f"{years}+ years"
        
        return None

    def parse_resume(self, file, filename: str) -> Dict[str, Any]:
        """Parse a single resume and extract structured information."""
        try:
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
            
        except Exception as e:
            return {'error': f'Processing error: {str(e)}'}

def main():
    st.title("Smart Resume Parser")
    st.markdown("**AI-Powered Resume Processing Tool** - Upload multiple resumes to extract structured information automatically!")
    
    # Add info about the cloud version
    st.info(" **Streamlit Cloud Version** - Optimized for fast deployment without heavy ML dependencies")
    
    # Initialize parser
    if 'parser' not in st.session_state:
        st.session_state.parser = ResumeParser()
    
    # Sidebar
    st.sidebar.title("📊 Parser Settings")
    st.sidebar.markdown("### Processing Options")
    max_files = st.sidebar.slider("Maximum files to process", 5, 25, 10)
    export_format = st.sidebar.selectbox("Export Format", ["JSON", "CSV", "Both"])
    
    # Add information panel
    with st.sidebar.expander("About This Tool"):
        st.markdown("""
        **Features:**
        - 📄 PDF & DOCX support
        - 👤 Contact info extraction
        - 🛠️ Skills identification
        - 🎓 Education parsing
        - 📊 Batch processing
        - 💾 Multiple export formats
        
        **Technology Stack:**
        - Python, PyMuPDF, Streamlit
        - Advanced regex patterns
        - Text processing algorithms
        """)
    
    # File uploader
    st.markdown("### Upload Resume Files")
    uploaded_files = st.file_uploader(
        "Choose resume files (PDF or DOCX)",
        type=['pdf', 'docx', 'doc'],
        accept_multiple_files=True,
        help=f"Upload up to {max_files} resume files for batch processing"
    )
    
    if uploaded_files:
        if len(uploaded_files) > max_files:
            st.warning(f" Too many files! Processing first {max_files} files only.")
            uploaded_files = uploaded_files[:max_files]
        
        st.success(f"✅ {len(uploaded_files)} file(s) uploaded successfully!")
        
        # Process button
        if st.button(" Start Processing", type="primary", use_container_width=True):
            process_resumes(uploaded_files, max_files, export_format)

def process_resumes(uploaded_files, max_files, export_format):
    """Process uploaded resume files."""
    st.markdown("###  Processing Results")
    
    # Process files
    parsed_results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, file in enumerate(uploaded_files):
        status_text.text(f"Processing {file.name}... ({i+1}/{len(uploaded_files)})")
        
        with st.spinner(f"Analyzing {file.name}..."):
            result = st.session_state.parser.parse_resume(file, file.name)
            parsed_results.append(result)
        
        progress_bar.progress((i + 1) / len(uploaded_files))
    
    status_text.text(" Processing completed!")
    
    # Store results in session state
    st.session_state.parsed_results = parsed_results
    
    # Display results
    successful = sum(1 for r in parsed_results if 'error' not in r)
    st.success(f" Successfully processed {successful}/{len(parsed_results)} resumes!")
    
    if successful == 0:
        st.error(" No resumes were processed successfully. Please check file formats and try again.")
        return
    
    # Create tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Summary", "👤 Individual Results", "📈 Skills Analysis", "💾 Export Data"])
    
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
    st.markdown("#### 📈 Processing Overview")
    
    # Calculate metrics
    successful = sum(1 for r in results if 'error' not in r)
    failed = len(results) - successful
    total_skills = sum(len(r.get('skills', [])) for r in results if 'error' not in r)
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(" Total Files", len(results))
    with col2:
        st.metric(" Successfully Parsed", successful, delta=successful-failed)
    with col3:
        st.metric(" Failed", failed)
    with col4:
        st.metric(" Skills Identified", total_skills)
    
    # Create summary table
    if successful > 0:
        st.markdown("#### 📋 Summary Table")
        summary_data = []
        for result in results:
            if 'error' not in result:
                summary_data.append({
                    'Filename': result['filename'][:30] + '...' if len(result['filename']) > 30 else result['filename'],
                    'Name': result.get('name', 'Not detected'),
                    'Email': result.get('contact_info', {}).get('email', 'Not found'),
                    'Phone': result.get('contact_info', {}).get('phone', 'Not found'),
                    'Skills Count': len(result.get('skills', [])),
                    'Education Entries': len(result.get('education', [])),
                    'Experience': result.get('experience_years', 'Not specified')
                })
        
        if summary_data:
            df = pd.DataFrame(summary_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

def display_individual_results(results: List[Dict]):
    """Display individual resume results."""
    st.markdown("#### 👤 Detailed Resume Analysis")
    
    successful_results = [r for r in results if 'error' not in r]
    
    if not successful_results:
        st.warning("No successful results to display.")
        return
    
    # Resume selector
    selected_idx = st.selectbox(
        "Select a resume to view details:",
        range(len(successful_results)),
        format_func=lambda x: f"{successful_results[x]['filename']} - {successful_results[x].get('name', 'Unknown')}"
    )
    
    result = successful_results[selected_idx]
    
    # Display selected resume details
    st.markdown(f"### 📄 {result['filename']}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**👤 Personal Information**")
        st.write(f"**Name:** {result.get('name', 'Not detected')}")
        st.write(f"**Email:** {result.get('contact_info', {}).get('email', 'Not found')}")
        st.write(f"**Phone:** {result.get('contact_info', {}).get('phone', 'Not found')}")
        st.write(f"**Experience:** {result.get('experience_years', 'Not specified')}")
        
        # Education
        education = result.get('education', [])
        if education:
            st.markdown("**🎓 Education**")
            for edu in education:
                st.write(f"• **{edu['degree']}** - {edu['institution']}")
        else:
            st.markdown("**🎓 Education:** Not detected")
    
    with col2:
        st.markdown("** Skills Detected**")
        skills = result.get('skills', [])
        if skills:
            # Group skills by category for better display
            tech_skills = [s for s in skills if any(tech in s.lower() for tech in ['python', 'java', 'javascript', 'sql', 'react', 'angular'])]
            other_skills = [s for s in skills if s not in tech_skills]
            
            if tech_skills:
                st.markdown("*Technical Skills:*")
                for skill in tech_skills[:8]:
                    st.write(f"• {skill.title()}")
            
            if other_skills:
                st.markdown("*Other Skills:*")
                for skill in other_skills[:8]:
                    st.write(f"• {skill.title()}")
            
            if len(skills) > 16:
                st.write(f"... and {len(skills) - 16} more skills")
        else:
            st.write("No skills detected")
    
    # Sections preview
    sections = result.get('sections', {})
    if sections:
        st.markdown("**📑 Document Sections Found**")
        for section_name, content in sections.items():
            if content:
                with st.expander(f"📖 {section_name.title()} Section"):
                    st.write(content[:300] + "..." if len(content) > 300 else content)

def display_skills_analysis(results: List[Dict]):
    """Display skills analysis and statistics."""
    st.markdown("#### 📈 Skills Market Analysis")
    
    # Collect all skills
    all_skills = []
    for result in results:
        if 'error' not in result:
            all_skills.extend(result.get('skills', []))
    
    if not all_skills:
        st.warning(" No skills found in the processed resumes.")
        return
    
    # Count skills frequency
    skill_counts = Counter(all_skills)
    total_unique_skills = len(skill_counts)
    
    # Display metrics
    col1, col2 = st.columns(2)
    with col1:
        st.metric("🔧 Unique Skills Found", total_unique_skills)
    with col2:
        st.metric("📊 Total Skill Mentions", len(all_skills))
    
    # Most common skills
    st.markdown("**🏆 Top Skills Across All Resumes**")
    top_skills = skill_counts.most_common(15)
    
    if top_skills:
        # Create two columns for skills display
        col1, col2 = st.columns(2)
        
        mid_point = len(top_skills) // 2
        
        with col1:
            for skill, count in top_skills[:mid_point]:
                percentage = (count / len([r for r in results if 'error' not in r])) * 100
                st.write(f"**{skill.title()}:** {count} resumes ({percentage:.1f}%)")
        
        with col2:
            for skill, count in top_skills[mid_point:]:
                percentage = (count / len([r for r in results if 'error' not in r])) * 100
                st.write(f"**{skill.title()}:** {count} resumes ({percentage:.1f}%)")
        
        # Skills distribution chart
        st.markdown("**📊 Skills Distribution Chart**")
        chart_data = pd.DataFrame(top_skills, columns=['Skill', 'Frequency'])
        chart_data['Skill'] = chart_data['Skill'].str.title()
        st.bar_chart(chart_data.set_index('Skill'))

def display_export_options(results: List[Dict], format_choice: str):
    """Display export options and generate downloadable files."""
    st.markdown("#### 💾 Export Processed Data")
    
    successful_results = [r for r in results if 'error' not in r]
    
    if not successful_results:
        st.error(" No data available for export.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📋 Export Options**")
        st.write(f"• **{len(successful_results)} resumes** ready for export")
        st.write(f"• **Format:** {format_choice}")
        st.write(f"• **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        # Preview data structure
        if st.checkbox(" Preview Export Structure"):
            sample_data = {
                'filename': successful_results[0]['filename'],
                'name': successful_results[0].get('name', ''),
                'skills_count': len(successful_results[0].get('skills', [])),
                'education_count': len(successful_results[0].get('education', []))
            }
            st.json(sample_data)
    
    with col2:
        st.markdown("** Download Files**")
        
        # Prepare data for export
        if format_choice in ["JSON", "Both"]:
            json_data = json.dumps(successful_results, indent=2, default=str)
            st.download_button(
                label=" Download Complete JSON Data",
                data=json_data,
                file_name=f"resume_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                help="Complete structured data with all extracted information"
            )
        
        if format_choice in ["CSV", "Both"]:
            # Create flattened data for CSV
            export_data = []
            for result in successful_results:
                export_data.append({
                    'filename': result['filename'],
                    'name': result.get('name', ''),
                    'email': result.get('contact_info', {}).get('email', ''),
                    'phone': result.get('contact_info', {}).get('phone', ''),
                    'skills': ' | '.join(result.get('skills', [])),
                    'skills_count': len(result.get('skills', [])),
                    'education': ' | '.join([f"{e['degree']} from {e['institution']}" for e in result.get('education', [])]),
                    'experience_years': result.get('experience_years', ''),
                    'processed_date': result.get('parsed_at', '')
                })
            
            df = pd.DataFrame(export_data)
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="📊 Download CSV Report",
                data=csv_data,
                file_name=f"resume_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                help="Simplified tabular data for spreadsheet analysis"
            )
        
        st.success(" Export files ready for download!")

# Error handling for failed results
def show_error_summary(results):
    """Show summary of any processing errors."""
    errors = [r for r in results if 'error' in r]
    if errors:
        st.markdown("#### Processing Warnings")
        for error in errors:
            st.warning(f"**{error.get('filename', 'Unknown file')}:** {error['error']}")

if __name__ == "__main__":
    main()
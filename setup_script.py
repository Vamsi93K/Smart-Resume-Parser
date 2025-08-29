#!/usr/bin/env python3
"""
Smart Resume Parser - Setup Script
This script installs all required dependencies and downloads the spaCy model.
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during {description}:")
        print(f"Command: {command}")
        print(f"Error: {e.stderr}")
        return False

def main():
    print("🚀 Smart Resume Parser - Setup Script")
    print("=" * 50)
    
    # Check if we're in a virtual environment
    if sys.prefix == sys.base_prefix:
        print("⚠️  Warning: You're not in a virtual environment!")
        print("It's recommended to create and activate a virtual environment first:")
        print("   python -m venv resume_parser_env")
        print("   source resume_parser_env/bin/activate  # On Windows: resume_parser_env\\Scripts\\activate")
        response = input("\nContinue anyway? (y/N): ").strip().lower()
        if response != 'y':
            print("Setup cancelled.")
            return
    else:
        print("✅ Virtual environment detected!")
    
    # Install requirements
    if not run_command("pip install -r requirements.txt", "Installing Python packages"):
        print("❌ Failed to install requirements. Please check the error messages above.")
        return
    
    # Download spaCy model
    if not run_command("python -m spacy download en_core_web_sm", "Downloading spaCy English model"):
        print("❌ Failed to download spaCy model. Please run manually:")
        print("   python -m spacy download en_core_web_sm")
        return
    
    print("\n🎉 Setup completed successfully!")
    print("\n📝 To run the application:")
    print("   streamlit run resume_parser.py")
    print("\n📁 Project Structure:")
    print("   ├── resume_parser.py      # Main application")
    print("   ├── requirements.txt      # Dependencies")
    print("   └── setup.py              # This setup script")
    print("\n💡 Tips:")
    print("   • Place your resume files in a folder for easy access")
    print("   • Supported formats: PDF, DOCX, DOC")
    print("   • You can process 5-50 resumes at once")

if __name__ == "__main__":
    main()
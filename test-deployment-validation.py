#!/usr/bin/env python3
"""
Test script to demonstrate deployment validation features
"""
import sys
import os
sys.path.insert(0, '/Users/rakesh/CascadeProjects/ai-pipeline-v2/lambdas/story-execution/github-orchestrator')

from lambda_function import generate_workflow_yaml

def show_validation_steps():
    """Show the validation steps that will be added to GitHub Actions workflow."""
    
    tech_stack = 'react_fullstack'
    workflow = generate_workflow_yaml(tech_stack, "CI/CD Pipeline", "18", ["npm install", "npm run build", "npm test"])
    
    # Extract and display just the validation steps
    lines = workflow.split('\n')
    in_validation = False
    validation_sections = []
    current_section = []
    
    for line in lines:
        if 'Pre-deployment Validation' in line or 'Validate Deployment' in line:
            in_validation = True
            if current_section:
                validation_sections.append('\n'.join(current_section))
            current_section = [line]
        elif in_validation:
            if line.strip().startswith('- name:') and 'Validation' not in line and 'Validate' not in line:
                in_validation = False
                if current_section:
                    validation_sections.append('\n'.join(current_section))
                current_section = []
            else:
                current_section.append(line)
    
    if current_section:
        validation_sections.append('\n'.join(current_section))
    
    print("=" * 70)
    print("DEPLOYMENT VALIDATION STEPS ADDED TO GITHUB ACTIONS")
    print("=" * 70)
    print()
    
    print("📋 PRE-DEPLOYMENT VALIDATION:")
    print("-" * 40)
    print("This step runs BEFORE attempting to deploy to Netlify:")
    print()
    print("✓ Checks if publish directory exists")
    print("✓ Counts files in build output")
    print("✓ Verifies index.html is present")
    print("✓ Shows directory structure")
    print("✓ Searches for build output if missing")
    print()
    
    print("📋 POST-DEPLOYMENT VALIDATION:")
    print("-" * 40)
    print("This step runs AFTER Netlify deployment:")
    print()
    print("✓ Tests if deployment URL is accessible (HTTP status)")
    print("✓ Verifies build artifacts were created")
    print("✓ Checks for index.html in build output")
    print("✓ Counts files in deployment")
    print("✓ Measures deployed content size")
    print("✓ Provides validation summary with pass/warning status")
    print()
    
    print("📊 VALIDATION OUTPUT EXAMPLE:")
    print("-" * 40)
    print("""
🔍 Pre-deployment validation...
✅ Publish directory exists: ./client/dist
✅ Found 42 files to deploy
✅ index.html present
📁 Build output structure:
  total 168
  -rw-r--r--  1 runner  docker   12345 Aug 27 10:30 index.html
  drwxr-xr-x  5 runner  docker     160 Aug 27 10:30 assets
  ...

🔍 Validating deployment...
Checking if deployment is accessible...
✅ Deployment is accessible (HTTP 200)

📦 Verifying build artifacts...
✅ Build output directory exists: ./client/dist
   Found 42 files in build output
✅ index.html found in build output
   Sample files:
     - ./client/dist/index.html
     - ./client/dist/assets/main.js
     - ./client/dist/assets/style.css
     - ./client/dist/favicon.ico

🌐 Checking deployed content...
✅ Deployed site has content (125432 bytes)

📊 Validation Summary:
✅ Deployment validation PASSED
   - Site is accessible
   - Build artifacts exist
   - Content is present
""")
    
    print("=" * 70)
    print("BENEFITS:")
    print("-" * 40)
    print("1. Early detection of build failures")
    print("2. Verification that deployment contains actual content")
    print("3. Clear diagnostics when deployments fail")
    print("4. Confidence that 'successful' deployments are actually working")
    print("5. Detailed logs for debugging deployment issues")
    print()

if __name__ == "__main__":
    show_validation_steps()
#!/usr/bin/env python3
"""
Test script to validate workflow generation for different tech stacks
"""
import sys
import os
sys.path.insert(0, '/Users/rakesh/CascadeProjects/ai-pipeline-v2/lambdas/story-execution/github-orchestrator')

# Import the functions we need to test
from lambda_function import generate_workflow_yaml, generate_netlify_config, get_build_commands

def test_workflow_generation():
    """Test workflow generation for different tech stacks"""
    
    tech_stacks = ['react_spa', 'react_fullstack', 'vue_spa']
    
    for tech_stack in tech_stacks:
        print(f"\n{'='*60}")
        print(f"Testing {tech_stack}")
        print('='*60)
        
        # Get build commands
        build_commands = get_build_commands(tech_stack)
        print(f"Build commands: {build_commands}")
        
        # Generate workflow
        workflow = generate_workflow_yaml(tech_stack, f"{tech_stack} CI/CD", "18", build_commands)
        
        # Check for publish-dir
        if 'publish-dir:' in workflow:
            for line in workflow.split('\n'):
                if 'publish-dir:' in line:
                    print(f"✅ Publish directory: {line.strip()}")
                    break
        
        # Generate Netlify config
        netlify_config = generate_netlify_config(tech_stack)
        
        # Check base directory for react_fullstack
        if tech_stack == 'react_fullstack':
            if 'base = "client"' in netlify_config:
                print("✅ Netlify base directory set to 'client' for react_fullstack")
            else:
                print("❌ Missing base = 'client' for react_fullstack")
        
        # Check publish directory in Netlify config
        for line in netlify_config.split('\n'):
            if 'publish = ' in line:
                print(f"✅ Netlify publish: {line.strip()}")
                break
        
        # Verify the workflow has the build verification step
        if 'Verify and prepare build outputs' in workflow:
            print("✅ Build verification step present")
        else:
            print("⚠️  Missing build verification step")
        
        # Check for new validation steps
        if 'Pre-deployment Validation' in workflow:
            print("✅ Pre-deployment validation step present")
        else:
            print("⚠️  Missing pre-deployment validation")
            
        if 'Validate Deployment' in workflow:
            print("✅ Post-deployment validation step present")
        else:
            print("⚠️  Missing post-deployment validation")

if __name__ == "__main__":
    test_workflow_generation()
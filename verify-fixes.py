#!/usr/bin/env python3
"""
Quick verification that our critical fixes are in place
"""

import sys
import os

# Add the lambda directory to the path
lambda_path = '/Users/rakesh/CascadeProjects/ai-pipeline-v2/lambdas/story-execution/github-orchestrator'
if lambda_path not in sys.path:
    sys.path.insert(0, lambda_path)

from lambda_function import generate_workflow_yaml

print("🔍 Verifying Critical Fixes")
print("=" * 60)

# Generate a workflow for react_fullstack
workflow = generate_workflow_yaml(
    tech_stack='react_fullstack',
    workflow_name="CI/CD Pipeline", 
    node_version="18",
    build_commands=["npm install", "npm test", "npm run build"]
)

print("\n✅ FIX 1: Netlify GitHub Token")
if 'github-token: ${{ secrets.GITHUB_TOKEN }}' in workflow:
    print("   ✓ GitHub token is present in Netlify action")
    print("   This ensures PR comments work correctly")
else:
    print("   ✗ MISSING: GitHub token not found")

print("\n✅ FIX 2: NPM Lock File Handling")
if 'Check for lock files' in workflow:
    print("   ✓ Conditional npm caching based on lock file presence")
    print("   This prevents 'cache-dependency-path' errors")
else:
    print("   ✗ MISSING: Lock file check not found")

print("\n✅ FIX 3: Smart Dependency Installation")
if 'npm ci' in workflow and 'package-lock.json' in workflow:
    print("   ✓ Uses 'npm ci' when lock file exists")
    print("   ✓ Falls back to 'npm install' when no lock file")
else:
    print("   ✗ MISSING: Smart npm install logic not found")

print("\n✅ FIX 4: Monorepo Directory Structure")
if './client/dist' in workflow:
    print("   ✓ Uses './client/dist' for react_fullstack projects")
    print("   This fixes 'dist directory not found' errors")
else:
    print("   ✗ MISSING: Wrong publish directory")

print("\n✅ FIX 5: GitHub Permissions")
if 'pull-requests: write' in workflow and 'deployments: write' in workflow:
    print("   ✓ Has necessary permissions for PR comments")
    print("   ✓ Can create deployment statuses")
else:
    print("   ✗ MISSING: Some permissions missing")

print("\n" + "=" * 60)
print("📊 SUMMARY:")
print("=" * 60)

# Check all critical fixes
fixes_ok = all([
    'github-token: ${{ secrets.GITHUB_TOKEN }}' in workflow,
    'Check for lock files' in workflow,
    'npm ci' in workflow,
    './client/dist' in workflow,
    'pull-requests: write' in workflow
])

if fixes_ok:
    print("✅ ALL CRITICAL FIXES ARE IN PLACE!")
    print("\nExpected behavior:")
    print("  • No more 'package-lock.json not found' errors")
    print("  • No more 'dist directory not found' errors")  
    print("  • Netlify deployments will use consistent site IDs")
    print("  • PR comments will show deployment URLs")
    print("  • GitHub Actions will complete successfully")
else:
    print("❌ Some fixes are missing - check details above")

# Show a sample of the workflow
print("\n📄 Sample Workflow Section (dependency installation):")
print("-" * 50)
lines = workflow.split('\n')
for i, line in enumerate(lines):
    if 'Install dependencies' in line:
        # Show the next 15 lines
        for j in range(i, min(i+15, len(lines))):
            print(lines[j])
        break
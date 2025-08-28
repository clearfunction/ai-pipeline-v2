#!/usr/bin/env python3
"""
Test that the GitHub workflow failures are fixed
Specifically testing the issues that were causing:
1. "Failed checks: test-and-deploy, test-and-deploy"
2. Missing package-lock.json causing npm cache failures
"""

import sys
import os

# Add the lambda directory to the path
lambda_path = '/Users/rakesh/CascadeProjects/ai-pipeline-v2/lambdas/story-execution/github-orchestrator'
if lambda_path not in sys.path:
    sys.path.insert(0, lambda_path)

from lambda_function import generate_workflow_yaml

print("🧪 Testing GitHub Workflow Failure Fixes")
print("=" * 60)
print("\nSimulating a project WITHOUT package-lock.json")
print("(This was causing the failures)")
print("-" * 40)

# Generate workflow
workflow = generate_workflow_yaml(
    tech_stack='react_spa',
    workflow_name="CI/CD Pipeline", 
    node_version="18",
    build_commands=["npm install", "npm test", "npm run build"]
)

print("\n📋 Checking the problematic Setup Node.js step:")
print("-" * 40)

# Find the Setup Node.js section
lines = workflow.split('\n')
setup_node_section = []
in_setup = False

for i, line in enumerate(lines):
    if 'Check for lock files' in line:
        # Found the lock file check - show it and the next setup steps
        for j in range(i, min(i+35, len(lines))):
            if 'Install dependencies' in lines[j]:
                break
            print(lines[j])

print("\n✅ ANALYSIS OF FIXES:")
print("-" * 40)

# OLD problematic code that would fail:
print("\n❌ OLD (would fail without package-lock.json):")
print("""
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
        cache: 'npm'  # FAILS if no package-lock.json!
        cache-dependency-path: package-lock.json  # FAILS!
""")

# NEW fixed code:
print("\n✅ NEW (works with or without package-lock.json):")
print("""
    - name: Check for lock files
      id: check-locks
      run: |
        if [ -f "package-lock.json" ]; then
          echo "has_npm_lock=true" >> $GITHUB_OUTPUT
        fi
    
    - name: Setup Node.js (with cache)
      if: steps.check-locks.outputs.has_npm_lock == 'true'
      uses: actions/setup-node@v4
      with:
        cache: 'npm'  # Only if lock file exists!
    
    - name: Setup Node.js (no cache)
      if: steps.check-locks.outputs.has_npm_lock != 'true'
      uses: actions/setup-node@v4
      with:
        node-version: '18'  # No cache parameter!
""")

print("\n📋 Checking dependency installation fix:")
print("-" * 40)

# Check install dependencies section
for i, line in enumerate(lines):
    if 'Install dependencies' in line:
        for j in range(i, min(i+15, len(lines))):
            print(lines[j])
        break

print("\n✅ EXPECTED BEHAVIOR:")
print("-" * 40)
print("1. If package-lock.json EXISTS:")
print("   • Uses npm cache for faster builds")
print("   • Runs 'npm ci' for reproducible installs")
print("   • GitHub Actions runs successfully")
print("")
print("2. If package-lock.json MISSING:")
print("   • Skips npm cache (no failure)")
print("   • Runs 'npm install' instead")
print("   • GitHub Actions still runs successfully")
print("")
print("3. Result:")
print("   • No more 'cache-dependency-path' errors")
print("   • No more 'Failed checks: test-and-deploy'")
print("   • Workflow completes even without lock file")

# Final verification
has_conditional_cache = 'Check for lock files' in workflow
has_npm_ci_fallback = 'npm ci' in workflow and 'npm install' in workflow
has_conditional_setup = 'has_npm_lock' in workflow

print("\n" + "=" * 60)
print("📊 TEST RESULTS:")
print("=" * 60)

if has_conditional_cache and has_npm_ci_fallback and has_conditional_setup:
    print("✅ GitHub workflow failures should be FIXED!")
    print("   The workflow now handles missing package-lock.json gracefully")
else:
    print("❌ Some fixes may be missing:")
    if not has_conditional_cache:
        print("   - Missing lock file check")
    if not has_npm_ci_fallback:
        print("   - Missing npm ci/install fallback")
    if not has_conditional_setup:
        print("   - Missing conditional Node.js setup")
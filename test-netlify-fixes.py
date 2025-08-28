#!/usr/bin/env python3
"""
Test script to verify Netlify deployment and GitHub workflow fixes
"""

import sys
import os

# Add the lambda directory to the path
lambda_path = '/Users/rakesh/CascadeProjects/ai-pipeline-v2/lambdas/story-execution/github-orchestrator'
if lambda_path not in sys.path:
    sys.path.insert(0, lambda_path)

# Import the functions directly from the lambda
from lambda_function import GitHubService, generate_workflow_yaml

def test_workflow_generation():
    """Test that the workflow generation includes all our fixes"""
    
    print("🧪 Testing GitHub Actions Workflow Generation")
    print("=" * 60)
    
    # Test for react_fullstack (monorepo) project
    tech_stack = 'react_fullstack'
    
    # Generate workflow using the standalone function
    workflow_yaml = generate_workflow_yaml(
        tech_stack=tech_stack,
        workflow_name="CI/CD Pipeline",
        node_version="18",
        build_commands=["npm install", "npm test", "npm run build"]
    )
    
    print("\n📋 Checking Critical Fixes:\n")
    
    # Test 1: Check for github-token in Netlify deployment
    has_github_token = 'github-token: ${{ secrets.GITHUB_TOKEN }}' in workflow_yaml
    print(f"✅ GitHub token in Netlify action: {has_github_token}")
    if not has_github_token:
        print("  ❌ FAILED: Missing github-token in Netlify deployment")
    
    # Test 2: Check for PR comments enabled
    has_pr_comments = 'enable-pull-request-comment: true' in workflow_yaml
    print(f"✅ Pull request comments enabled: {has_pr_comments}")
    if not has_pr_comments:
        print("  ❌ FAILED: PR comments not enabled")
    
    # Test 3: Check for proper permissions
    has_permissions = 'pull-requests: write' in workflow_yaml
    print(f"✅ Pull request write permissions: {has_permissions}")
    if not has_permissions:
        print("  ❌ FAILED: Missing pull-requests write permission")
    
    # Test 4: Check for conditional npm caching (lock file handling)
    has_lock_check = 'Check for lock files' in workflow_yaml
    print(f"✅ Lock file checking: {has_lock_check}")
    if not has_lock_check:
        print("  ❌ FAILED: Missing lock file check")
    
    # Test 5: Check for npm ci vs npm install logic
    has_npm_ci_logic = 'npm ci' in workflow_yaml and 'package-lock.json' in workflow_yaml
    print(f"✅ Smart npm install logic: {has_npm_ci_logic}")
    if not has_npm_ci_logic:
        print("  ❌ FAILED: Missing npm ci conditional logic")
    
    # Test 6: Check for correct publish directory for monorepo
    has_client_dist = './client/dist' in workflow_yaml or 'client/dist' in workflow_yaml
    print(f"✅ Correct publish dir for monorepo: {has_client_dist}")
    if not has_client_dist:
        print("  ❌ FAILED: Wrong publish directory for react_fullstack")
    
    # Test 7: Check for timeout on Netlify deployment
    has_timeout = 'timeout-minutes:' in workflow_yaml
    print(f"✅ Netlify timeout configured: {has_timeout}")
    if not has_timeout:
        print("  ❌ FAILED: Missing timeout configuration")
    
    # Test 8: Check for deployment permissions
    has_deployment_perms = 'deployments: write' in workflow_yaml
    print(f"✅ Deployment permissions: {has_deployment_perms}")
    if not has_deployment_perms:
        print("  ❌ FAILED: Missing deployments write permission")
    
    # Test 9: Check that old problematic patterns are gone
    has_simple_npm_cache = 'cache: \'npm\'' in workflow_yaml and 'Check for lock files' not in workflow_yaml
    print(f"✅ Removed unconditional npm cache: {not has_simple_npm_cache}")
    if has_simple_npm_cache:
        print("  ❌ FAILED: Still has unconditional npm cache that will fail")
    
    print("\n📄 Sample of Generated Workflow (Netlify section):")
    print("-" * 50)
    
    # Find and print the Netlify deployment section
    lines = workflow_yaml.split('\n')
    in_netlify_section = False
    netlify_lines = []
    
    for i, line in enumerate(lines):
        if 'Deploy to Netlify' in line:
            in_netlify_section = True
        if in_netlify_section:
            netlify_lines.append(line)
            if i < len(lines) - 1 and lines[i + 1].strip() and not lines[i + 1].startswith(' '):
                break
    
    if netlify_lines:
        print('\n'.join(netlify_lines[:30]))  # Show first 30 lines of Netlify section
    
    print("\n" + "=" * 60)
    
    # Summary
    all_passed = all([
        has_github_token,
        has_pr_comments,
        has_permissions,
        has_lock_check,
        has_npm_ci_logic,
        has_client_dist,
        has_timeout,
        has_deployment_perms,
        not has_simple_npm_cache
    ])
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! The workflow should now:")
        print("  ✅ Handle missing package-lock.json gracefully")
        print("  ✅ Deploy to Netlify with proper authentication")
        print("  ✅ Create PR comments with deployment URLs")
        print("  ✅ Use correct directory structure for monorepos")
        print("  ✅ Have all necessary GitHub permissions")
    else:
        print("\n❌ SOME TESTS FAILED - Review the issues above")
    
    return all_passed

def test_netlify_site_consistency():
    """Test that Netlify site ID handling is correct"""
    
    print("\n🧪 Testing Netlify Site ID Handling")
    print("=" * 60)
    
    # Simulate the workflow checking for NETLIFY_SITE_ID
    workflow_yaml = generate_workflow_yaml(
        tech_stack='react_spa',
        workflow_name="CI/CD Pipeline",
        node_version="18",
        build_commands=["npm install", "npm test", "npm run build"]
    )
    
    # Check that NETLIFY_SITE_ID is referenced
    uses_site_id = 'NETLIFY_SITE_ID' in workflow_yaml
    print(f"✅ Workflow uses NETLIFY_SITE_ID secret: {uses_site_id}")
    
    # Check that NETLIFY_AUTH_TOKEN is referenced
    uses_auth_token = 'NETLIFY_AUTH_TOKEN' in workflow_yaml
    print(f"✅ Workflow uses NETLIFY_AUTH_TOKEN secret: {uses_auth_token}")
    
    # Check that the action won't fail if site ID is missing
    has_github_token_fallback = 'github-token:' in workflow_yaml
    print(f"✅ Has github-token for fallback: {has_github_token_fallback}")
    
    print("\n📝 Note: With github-token, Netlify action will:")
    print("  • Use existing site if NETLIFY_SITE_ID is set")
    print("  • Create new site if NETLIFY_SITE_ID is missing")
    print("  • Post deployment URL as PR comment either way")
    
    return uses_site_id and uses_auth_token and has_github_token_fallback

def test_monorepo_handling():
    """Test that monorepo projects are handled correctly"""
    
    print("\n🧪 Testing Monorepo Directory Structure")
    print("=" * 60)
    
    # Test different tech stacks
    test_cases = [
        ('react_spa', './dist', 'Standard React SPA'),
        ('react_fullstack', './client/dist', 'React Fullstack Monorepo'),
        ('vue_spa', './dist', 'Vue SPA'),
        ('node_api', None, 'Node API (no frontend)')
    ]
    
    all_correct = True
    
    for tech_stack, expected_dir, description in test_cases:
        workflow_yaml = generate_workflow_yaml(
            tech_stack=tech_stack,
            workflow_name="CI/CD Pipeline",
            node_version="18",
            build_commands=["npm install", "npm test", "npm run build"]
        )
        
        if expected_dir:
            has_correct_dir = f'publish-dir: {expected_dir}' in workflow_yaml or f'publish-dir: \'{expected_dir}\'' in workflow_yaml
            print(f"✅ {description}: {'✓' if has_correct_dir else '✗'} (expects {expected_dir})")
            if not has_correct_dir:
                # Try to find what directory it's actually using
                for line in workflow_yaml.split('\n'):
                    if 'publish-dir:' in line:
                        print(f"  Found: {line.strip()}")
                all_correct = False
        else:
            has_netlify = 'Deploy to Netlify' in workflow_yaml
            print(f"✅ {description}: {'✗ (has Netlify)' if has_netlify else '✓ (no Netlify)'}")
            if has_netlify:
                all_correct = False
    
    return all_correct

if __name__ == "__main__":
    print("🚀 Testing Netlify Deployment and GitHub Workflow Fixes")
    print("=" * 60)
    
    # Run all tests
    workflow_ok = test_workflow_generation()
    netlify_ok = test_netlify_site_consistency()
    monorepo_ok = test_monorepo_handling()
    
    print("\n" + "=" * 60)
    print("📊 FINAL TEST RESULTS:")
    print("=" * 60)
    
    if workflow_ok and netlify_ok and monorepo_ok:
        print("✅ ALL TESTS PASSED!")
        print("\nThe Lambda should now:")
        print("  1. Handle projects without package-lock.json")
        print("  2. Deploy to consistent Netlify sites")
        print("  3. Create visible PR comments")
        print("  4. Use correct directories for monorepos")
        print("  5. Have all necessary GitHub permissions")
    else:
        print("❌ Some tests failed. Review the output above.")
        sys.exit(1)
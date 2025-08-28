#!/usr/bin/env python3
"""
Test what dependency versions the story executor generates
"""

import sys
import os
import json

# Add paths
sys.path.insert(0, '/Users/rakesh/CascadeProjects/ai-pipeline-v2')
sys.path.insert(0, '/Users/rakesh/CascadeProjects/ai-pipeline-v2/lambdas/core/story-executor')

from templates.react_fullstack_generator import ReactFullstackTemplateGenerator
from templates.react_spa_generator import ReactSPATemplateGenerator

print("🔍 Testing Dependency Version Generation")
print("=" * 60)

print("\n1. Testing React Fullstack Generator:")
print("-" * 40)

# Generate package.json for fullstack
fullstack_gen = ReactFullstackTemplateGenerator()
fullstack_files = fullstack_gen.generate_project_scaffold('test-project', {})

# Find the client package.json
for file in fullstack_files:
    if file.file_path == 'client/package.json':
        package_data = json.loads(file.content)
        deps = package_data.get('dependencies', {})
        dev_deps = package_data.get('devDependencies', {})
        
        print(f"React version: {deps.get('react', 'NOT FOUND')}")
        print(f"React DOM version: {deps.get('react-dom', 'NOT FOUND')}")
        print(f"@testing-library/react: {dev_deps.get('@testing-library/react', 'NOT FOUND')}")
        print(f"@testing-library/user-event: {dev_deps.get('@testing-library/user-event', 'NOT FOUND')}")
        
        # Check for compatibility
        react_version = deps.get('react', '')
        testing_lib_version = dev_deps.get('@testing-library/react', '')
        
        if '^18' in react_version and '^16' in testing_lib_version:
            print("\n❌ INCOMPATIBLE VERSIONS DETECTED!")
            print("   React 18 with Testing Library 16 will cause npm install failures")
        elif '^18' in react_version and '^14' in testing_lib_version:
            print("\n✅ Compatible versions")
        break

print("\n2. Testing React SPA Generator:")
print("-" * 40)

# Generate package.json for SPA
spa_gen = ReactSPATemplateGenerator()
spa_files = spa_gen.generate_project_scaffold('test-project', {})

# Find the package.json
for file in spa_files:
    if file.file_path == 'package.json':
        package_data = json.loads(file.content)
        deps = package_data.get('dependencies', {})
        dev_deps = package_data.get('devDependencies', {})
        
        print(f"React version: {deps.get('react', 'NOT FOUND')}")
        print(f"React DOM version: {deps.get('react-dom', 'NOT FOUND')}")
        print(f"@testing-library/react: {dev_deps.get('@testing-library/react', 'NOT FOUND')}")
        print(f"@testing-library/user-event: {dev_deps.get('@testing-library/user-event', 'NOT FOUND')}")
        
        # Check for compatibility
        react_version = deps.get('react', '')
        testing_lib_version = dev_deps.get('@testing-library/react', '')
        
        if '^18' in react_version and '^16' in testing_lib_version:
            print("\n❌ INCOMPATIBLE VERSIONS DETECTED!")
            print("   React 18 with Testing Library 16 will cause npm install failures")
        elif '^18' in react_version and '^14' in testing_lib_version:
            print("\n✅ Compatible versions")
        break

print("\n" + "=" * 60)
print("📊 COMPATIBILITY MATRIX:")
print("=" * 60)
print("✅ CORRECT (Compatible):")
print("   React ^18.2.0 + @testing-library/react ^14.2.1")
print("")
print("❌ WRONG (Incompatible):")
print("   React ^18.x.x + @testing-library/react ^16.x.x")
print("")
print("The story executor must use Testing Library v14 with React 18!")
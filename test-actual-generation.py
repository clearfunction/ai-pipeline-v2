#!/usr/bin/env python3
"""
Test what the Lambda actually generates and simulate npm install
"""

import sys
import os
import json
import tempfile
import subprocess

# Add paths
sys.path.insert(0, '/Users/rakesh/CascadeProjects/ai-pipeline-v2')
sys.path.insert(0, '/Users/rakesh/CascadeProjects/ai-pipeline-v2/lambdas/core/story-executor')

from templates.react_fullstack_generator import ReactFullstackTemplateGenerator

print("🔬 Testing Actual Package Generation and NPM Install")
print("=" * 70)

# Generate the files
print("\n1. Generating React Fullstack project files...")
generator = ReactFullstackTemplateGenerator()
files = generator.generate_project_scaffold('test-project', {})

# Find the client package.json
client_package = None
for file in files:
    if file.file_path == 'client/package.json':
        client_package = file
        break

if not client_package:
    print("❌ No client/package.json found!")
    sys.exit(1)

print("✅ Found client/package.json")

# Parse and display the versions
package_data = json.loads(client_package.content)
deps = package_data.get('dependencies', {})
dev_deps = package_data.get('devDependencies', {})

print("\n2. Checking generated versions:")
print("-" * 40)
print(f"React: {deps.get('react', 'NOT FOUND')}")
print(f"React DOM: {deps.get('react-dom', 'NOT FOUND')}")
print(f"@testing-library/react: {dev_deps.get('@testing-library/react', 'NOT FOUND')}")
print(f"@testing-library/user-event: {dev_deps.get('@testing-library/user-event', 'NOT FOUND')}")
print(f"@testing-library/jest-dom: {dev_deps.get('@testing-library/jest-dom', 'NOT FOUND')}")

# Check if versions have carets
testing_react = dev_deps.get('@testing-library/react', '')
if '^' in testing_react:
    print("\n⚠️  WARNING: Still using caret (^) in version!")
    print(f"   Found: {testing_react}")
    print("   This will cause npm to resolve to v16!")
else:
    print(f"\n✅ Using exact version: {testing_react}")

# Create a temp directory and test npm install
print("\n3. Testing npm install behavior...")
print("-" * 40)

with tempfile.TemporaryDirectory() as tmpdir:
    client_dir = os.path.join(tmpdir, 'client')
    os.makedirs(client_dir)
    
    # Write the package.json
    package_path = os.path.join(client_dir, 'package.json')
    with open(package_path, 'w') as f:
        f.write(client_package.content)
    
    print(f"📁 Created test directory: {client_dir}")
    print("📦 Running npm install --dry-run to see what would be installed...")
    
    # Run npm install with dry-run to see what versions would be resolved
    try:
        result = subprocess.run(
            ['npm', 'install', '--dry-run', '--json'],
            cwd=client_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print("❌ npm install --dry-run failed!")
            print("STDERR:", result.stderr[:1000])
            
            # Try to parse error
            if '@testing-library/react@16' in result.stderr:
                print("\n🚨 PROBLEM IDENTIFIED:")
                print("   npm is still trying to install @testing-library/react@16!")
                print("   This means the package.json still has incompatible version specs")
        else:
            print("✅ npm install --dry-run succeeded")
            
            # Try to parse the output
            try:
                output_data = json.loads(result.stdout)
                print("\n📋 Would install these versions:")
                # This might not work as expected with --dry-run --json
            except:
                # Fall back to text parsing
                if '@testing-library/react@16' in result.stdout:
                    print("⚠️  Would install @testing-library/react@16 (incompatible!)")
                elif '@testing-library/react@14' in result.stdout:
                    print("✅ Would install @testing-library/react@14 (compatible)")
    
    except subprocess.TimeoutExpired:
        print("⏰ npm install timed out")
    except Exception as e:
        print(f"❌ Error running npm install: {e}")

    # Also test with actual npm install (without dry-run) to see the real error
    print("\n4. Running actual npm install to replicate GitHub Actions...")
    print("-" * 40)
    
    try:
        result = subprocess.run(
            ['npm', 'install'],
            cwd=client_dir,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print("❌ npm install FAILED (same as GitHub Actions!)")
            print("\nError output:")
            print(result.stderr[:2000] if result.stderr else result.stdout[:2000])
            
            # Check for the specific error
            if 'Could not resolve dependency' in result.stderr:
                print("\n🎯 EXACT ERROR REPRODUCED LOCALLY!")
                
                # Extract the problematic versions
                if '@testing-library/react@16' in result.stderr:
                    print("   Problem: npm is resolving to @testing-library/react@16")
                    print("   Solution: The package.json MUST specify exact version 14.2.1")
        else:
            print("✅ npm install succeeded")
            
            # Check what was actually installed
            package_lock_path = os.path.join(client_dir, 'package-lock.json')
            if os.path.exists(package_lock_path):
                with open(package_lock_path, 'r') as f:
                    lock_data = json.load(f)
                    
                # Check testing library version
                testing_lib_path = 'node_modules/@testing-library/react'
                if testing_lib_path in lock_data.get('packages', {}):
                    installed_version = lock_data['packages'][testing_lib_path].get('version', 'unknown')
                    print(f"\n📦 Actually installed @testing-library/react version: {installed_version}")
                    
                    if installed_version.startswith('16'):
                        print("   ❌ Installed v16 - INCOMPATIBLE!")
                    elif installed_version.startswith('14'):
                        print("   ✅ Installed v14 - Compatible")
    
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n" + "=" * 70)
print("📊 ANALYSIS COMPLETE")
print("=" * 70)
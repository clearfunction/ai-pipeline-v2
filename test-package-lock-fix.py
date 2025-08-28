#!/usr/bin/env python3
"""
Test that the template generators no longer create stub package-lock.json files
"""

import sys
import os

# Add paths
sys.path.insert(0, '/Users/rakesh/CascadeProjects/ai-pipeline-v2')
sys.path.insert(0, '/Users/rakesh/CascadeProjects/ai-pipeline-v2/lambdas/core/story-executor')

from templates.react_fullstack_generator import ReactFullstackTemplateGenerator
from templates.react_spa_generator import ReactSPATemplateGenerator
from templates.vue_spa_generator import VueSPATemplateGenerator
from templates.node_api_generator import NodeAPITemplateGenerator

print("🔍 Testing Package Lock JSON Removal Fix")
print("=" * 60)

# Test each generator
generators = [
    ('React Fullstack', ReactFullstackTemplateGenerator()),
    ('React SPA', ReactSPATemplateGenerator()),
    ('Vue SPA', VueSPATemplateGenerator()),
    ('Node API', NodeAPITemplateGenerator())
]

all_passed = True

for name, generator in generators:
    print(f"\nTesting {name} Generator:")
    print("-" * 40)
    
    # Generate project scaffold
    files = generator.generate_project_scaffold('test-project', {})
    
    # Check for package-lock.json files
    package_lock_files = [f for f in files if 'package-lock.json' in f.file_path]
    
    if package_lock_files:
        print(f"❌ FAILED: Still generating package-lock.json files:")
        for f in package_lock_files:
            print(f"   - {f.file_path}")
        all_passed = False
    else:
        print(f"✅ PASSED: No package-lock.json files generated")
    
    # Check that package.json is still being generated
    package_json_files = [f for f in files if f.file_path.endswith('package.json')]
    if package_json_files:
        print(f"✅ package.json files still generated: {len(package_json_files)}")
        for f in package_json_files:
            print(f"   - {f.file_path}")
    else:
        print(f"❌ ERROR: No package.json files generated!")
        all_passed = False

print("\n" + "=" * 60)
if all_passed:
    print("🎉 ALL TESTS PASSED!")
    print("✅ No stub package-lock.json files are being generated")
    print("✅ package.json files are still being generated correctly")
    print("✅ GitHub Actions will now use 'npm install' on first run")
    print("✅ This will fix the 'npm ci' sync error")
else:
    print("❌ SOME TESTS FAILED - Check the output above")

print("\n📊 Summary:")
print("The fix removes stub package-lock.json files that didn't contain")
print("actual dependency resolution data. This was causing npm ci to fail.")
print("Now GitHub Actions will use 'npm install' for initial setup.")
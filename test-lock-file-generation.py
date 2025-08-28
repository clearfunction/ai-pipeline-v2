#!/usr/bin/env python3
"""
Test that lock file generation works correctly for all templates.
"""

import sys
import os

# Add project paths
sys.path.insert(0, '/Users/rakesh/CascadeProjects/ai-pipeline-v2')
sys.path.insert(0, '/Users/rakesh/CascadeProjects/ai-pipeline-v2/lambdas/core/story-executor')

from templates.react_spa_generator import ReactSPATemplateGenerator
from templates.react_fullstack_generator import ReactFullstackTemplateGenerator
from templates.vue_spa_generator import VueSPATemplateGenerator
from templates.node_api_generator import NodeAPITemplateGenerator

def test_lock_file_generation():
    """Test that all template generators create package-lock.json files."""
    
    print("🧪 Testing Lock File Generation in Template Generators")
    print("=" * 60)
    
    generators = [
        ('React SPA', ReactSPATemplateGenerator()),
        ('React Fullstack', ReactFullstackTemplateGenerator()),
        ('Vue SPA', VueSPATemplateGenerator()),
        ('Node API', NodeAPITemplateGenerator())
    ]
    
    all_passed = True
    
    for name, generator in generators:
        print(f"\n📦 Testing {name} Generator:")
        
        try:
            # Generate project scaffold
            files = generator.generate_project_scaffold(f'test-{name.lower().replace(" ", "-")}', None)
            
            # Check for package.json and package-lock.json
            file_paths = [f.file_path for f in files]
            
            has_package_json = False
            has_package_lock = False
            lock_files = []
            
            for path in file_paths:
                if path.endswith('package.json'):
                    has_package_json = True
                if path.endswith('package-lock.json'):
                    has_package_lock = True
                    lock_files.append(path)
            
            print(f"   Files generated: {len(files)}")
            print(f"   Has package.json: {'✅' if has_package_json else '❌'}")
            print(f"   Has package-lock.json: {'✅' if has_package_lock else '❌'}")
            
            if lock_files:
                print(f"   Lock files found:")
                for lock_file in lock_files:
                    print(f"      • {lock_file}")
                    
                    # Check the content of lock file
                    lock_content = next((f.content for f in files if f.file_path == lock_file), None)
                    if lock_content:
                        # Check for required fields
                        if '"lockfileVersion": 3' in lock_content:
                            print(f"      ✅ Valid lockfileVersion 3 format")
                        else:
                            print(f"      ❌ Invalid lock file format")
                            all_passed = False
            
            if not has_package_lock:
                print(f"   ❌ FAILED: No package-lock.json generated")
                all_passed = False
            else:
                print(f"   ✅ PASSED: Lock file generation working")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 SUCCESS: All generators produce package-lock.json files!")
        print("✅ Validation should now pass for lock file requirements")
        print("✅ The files use minimal valid lockfileVersion 3 format")
        print("✅ Ready to deploy the fix")
    else:
        print("❌ FAILURE: Some generators are not producing lock files")
    
    return all_passed

if __name__ == "__main__":
    success = test_lock_file_generation()
    sys.exit(0 if success else 1)
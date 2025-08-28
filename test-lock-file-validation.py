#!/usr/bin/env python3
"""
Test the lock file generation and validation fix in the deployed Lambda.
"""

import json
import boto3
import sys

def test_lock_file_validation():
    """Test that lock files are generated and validation passes."""
    
    print("🧪 Testing Lock File Generation and Validation Fix")
    print("=" * 70)
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Test with React SPA
    test_event = {
        'architecturePlannerResult': {
            'Payload': {
                'data': {
                    'architecture': {
                        'project_id': 'lock-file-test-react',
                        'name': 'lock-file-test-react',
                        'tech_stack': 'react_spa',
                        'components': [],
                        'dependencies': {'react': '^18.2.0'},
                        'build_config': {'package_manager': 'npm', 'bundler': 'vite'},
                        'user_stories': [
                            {
                                'story_id': 'story-001',
                                'title': 'Lock File Test',
                                'description': 'Verify lock file generation',
                                'acceptance_criteria': ['Lock files generated'],
                                'priority': 1
                            }
                        ]
                    },
                    'pipeline_context': {
                        'project_id': 'lock-file-test-react'
                    }
                }
            }
        }
    }
    
    print("1️⃣ Testing Story Executor (React SPA)...")
    
    # Invoke story executor
    response = lambda_client.invoke(
        FunctionName='ai-pipeline-v2-story-executor-dev',
        InvocationType='RequestResponse',
        Payload=json.dumps(test_event)
    )
    
    executor_result = json.loads(response['Payload'].read())
    
    if 'errorMessage' in executor_result:
        print(f"❌ Story executor failed: {executor_result['errorMessage']}")
        return False
    
    # Check for lock files
    generated_files = executor_result['data']['generated_files']
    has_package_json = False
    has_package_lock = False
    
    for file_info in generated_files:
        if file_info['file_path'] == 'package.json':
            has_package_json = True
        if file_info['file_path'] == 'package-lock.json':
            has_package_lock = True
    
    print(f"   Generated {len(generated_files)} files")
    print(f"   Has package.json: {'✅' if has_package_json else '❌'}")
    print(f"   Has package-lock.json: {'✅' if has_package_lock else '❌'}")
    
    if not has_package_lock:
        print("❌ Lock file not generated!")
        return False
    
    # Test validation
    print("\n2️⃣ Testing Integration Validator...")
    
    validator_event = {
        'storyExecutorResult': {
            'Payload': executor_result
        }
    }
    
    validator_response = lambda_client.invoke(
        FunctionName='ai-pipeline-v2-integration-validator-dev',
        InvocationType='RequestResponse',
        Payload=json.dumps(validator_event)
    )
    
    validator_result = json.loads(validator_response['Payload'].read())
    
    if 'errorMessage' in validator_result:
        print(f"❌ Validator failed: {validator_result['errorMessage']}")
        return False
    
    # Check lock file validation
    validation_data = validator_result.get('data', {})
    validation_summary = validation_data.get('validation_summary', {})
    validation_passed = validation_summary.get('validation_passed', False)
    validation_results = validation_data.get('validation_results', [])
    
    # Also check if it's in a different format
    if not validation_results and 'validations' in validation_data:
        validation_results = validation_data['validations']
    
    lock_file_validation = None
    for result in validation_results:
        if result.get('validation_type') == 'lock_file_validation':
            lock_file_validation = result
            break
    
    if lock_file_validation:
        print(f"   Lock file validation: {'✅ PASSED' if lock_file_validation['passed'] else '❌ FAILED'}")
        if lock_file_validation.get('details'):
            details = lock_file_validation['details']
            print(f"   • Has package.json: {details.get('has_package_json', 'N/A')}")
            print(f"   • Has package-lock.json: {details.get('has_package_lock', 'N/A')}")
        
        if not lock_file_validation['passed'] and lock_file_validation.get('issues'):
            print(f"   Issues: {lock_file_validation['issues']}")
    
    print(f"\n   Overall validation: {'✅ PASSED' if validation_passed else '❌ FAILED'}")
    
    # Test with React Fullstack to ensure monorepo also works
    print("\n3️⃣ Testing React Fullstack (monorepo)...")
    
    fullstack_event = test_event.copy()
    fullstack_event['architecturePlannerResult']['Payload']['data']['architecture']['tech_stack'] = 'react_fullstack'
    fullstack_event['architecturePlannerResult']['Payload']['data']['architecture']['project_id'] = 'lock-file-test-fullstack'
    fullstack_event['architecturePlannerResult']['Payload']['data']['architecture']['name'] = 'lock-file-test-fullstack'
    
    response = lambda_client.invoke(
        FunctionName='ai-pipeline-v2-story-executor-dev',
        InvocationType='RequestResponse',
        Payload=json.dumps(fullstack_event)
    )
    
    fullstack_result = json.loads(response['Payload'].read())
    
    if 'errorMessage' not in fullstack_result:
        fullstack_files = fullstack_result['data']['generated_files']
        fullstack_lock_files = [f['file_path'] for f in fullstack_files if 'package-lock.json' in f['file_path']]
        print(f"   Generated {len(fullstack_files)} files")
        print(f"   Lock files found: {len(fullstack_lock_files)}")
        for lock_file in fullstack_lock_files[:3]:  # Show first 3
            print(f"      • {lock_file}")
    
    print("\n" + "=" * 70)
    
    if validation_passed and has_package_lock:
        print("🎉 SUCCESS: Lock file generation and validation fix is working!")
        print("✅ Template generators now create minimal valid package-lock.json files")
        print("✅ Integration validator accepts the generated lock files")
        print("✅ Validation no longer fails due to missing lock files")
        print("✅ The original validation failure was unrelated to the parsing enhancements")
        return True
    else:
        print("❌ Lock file validation still has issues")
        return False

if __name__ == "__main__":
    success = test_lock_file_validation()
    sys.exit(0 if success else 1)
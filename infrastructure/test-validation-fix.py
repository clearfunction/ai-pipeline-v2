#!/usr/bin/env python3
"""
Test the deployed validation fix for lock files.
"""

import json
import boto3
import time

def test_validation_fix():
    """Test that validation now passes with lock file generation."""
    
    print("🧪 Testing Validation Fix for Lock Files")
    print("=" * 70)
    
    # Create test event
    test_event = {
        'architecturePlannerResult': {
            'Payload': {
                'data': {
                    'architecture': {
                        'project_id': 'lock-file-validation-test',
                        'name': 'lock-file-validation-test',
                        'tech_stack': 'react_spa',
                        'components': [],
                        'dependencies': {'react': '^18.2.0'},
                        'build_config': {'package_manager': 'npm', 'bundler': 'vite'},
                        'user_stories': [
                            {
                                'story_id': 'story-001',
                                'title': 'Lock File Validation Test',
                                'description': 'Test that lock files are now generated correctly',
                                'acceptance_criteria': [
                                    'package-lock.json should be generated',
                                    'Validation should pass for lock files'
                                ],
                                'priority': 1
                            }
                        ]
                    },
                    'pipeline_context': {
                        'project_id': 'lock-file-validation-test'
                    }
                }
            }
        }
    }
    
    try:
        # Create Lambda client
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        
        # Test story-executor
        print("📡 Invoking story-executor Lambda...")
        function_name = 'ai-pipeline-v2-story-executor-dev'
        
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )
        
        response_payload = json.loads(response['Payload'].read())
        
        if 'errorMessage' in response_payload:
            print(f"❌ Story executor failed: {response_payload['errorMessage']}")
            return False
        
        print(f"✅ Story executor succeeded")
        print(f"   Generated files: {len(response_payload['data']['generated_files'])}")
        
        # Check for package-lock.json
        generated_files = response_payload['data']['generated_files']
        lock_files_found = []
        
        for file_info in generated_files:
            if 'package-lock.json' in file_info['file_path']:
                lock_files_found.append(file_info['file_path'])
        
        if lock_files_found:
            print(f"✅ Lock files generated: {lock_files_found}")
        else:
            print(f"❌ No lock files generated!")
            return False
        
        # Now test integration-validator
        print("\n📡 Invoking integration-validator Lambda...")
        validator_event = {
            'storyExecutorResult': {
                'Payload': response_payload
            }
        }
        
        validator_function = 'ai-pipeline-v2-integration-validator-dev'
        
        validator_response = lambda_client.invoke(
            FunctionName=validator_function,
            InvocationType='RequestResponse',
            Payload=json.dumps(validator_event)
        )
        
        validator_payload = json.loads(validator_response['Payload'].read())
        
        if 'errorMessage' in validator_payload:
            print(f"❌ Validator failed: {validator_payload['errorMessage']}")
            return False
        
        # Check validation results
        validation_passed = validator_payload['data']['validation_summary']['validation_passed']
        validation_results = validator_payload['data']['validation_results']
        
        print(f"\n📋 Validation Results:")
        print(f"   Overall: {'✅ PASSED' if validation_passed else '❌ FAILED'}")
        
        for result in validation_results:
            if result['validation_type'] == 'lock_file_validation':
                print(f"\n   Lock File Validation:")
                print(f"      Passed: {'✅' if result['passed'] else '❌'}")
                if 'details' in result:
                    details = result['details']
                    print(f"      Has package.json: {details.get('has_package_json', 'N/A')}")
                    print(f"      Has package-lock.json: {details.get('has_package_lock', 'N/A')}")
                if not result['passed']:
                    print(f"      Issues: {result.get('issues', [])}")
        
        if validation_passed:
            print(f"\n🎉 SUCCESS: Validation now passes with lock file generation fix!")
            print(f"✅ Lock files are being generated correctly")
            print(f"✅ Integration validator accepts the lock files")
            print(f"✅ The parsing enhancements did not cause the validation failure")
            print(f"✅ Fix has been successfully deployed")
            return True
        else:
            print(f"\n❌ Validation still failing")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_validation_fix()
    exit(0 if success else 1)
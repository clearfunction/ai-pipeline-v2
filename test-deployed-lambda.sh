#!/bin/bash

# Test the deployed Lambda to see what it generates

echo "🔍 Testing Deployed Story Executor Lambda"
echo "=========================================="

# Create a test payload
cat > /tmp/test-story-executor.json << 'EOF'
{
  "architecturePlannerResult": {
    "Payload": {
      "data": {
        "architecture": {
          "project_id": "dependency-test",
          "name": "dependency-test",
          "tech_stack": "react_fullstack",
          "components": [],
          "dependencies": {"react": "^18.2.0"},
          "build_config": {"package_manager": "npm", "bundler": "vite"},
          "user_stories": [{
            "story_id": "story_001",
            "title": "Test Story",
            "description": "Test dependency versions",
            "acceptance_criteria": ["Should have correct versions"],
            "priority": 1
          }]
        },
        "pipeline_context": {
          "project_id": "dependency-test"
        }
      }
    }
  }
}
EOF

echo "📦 Invoking Lambda..."
aws lambda invoke \
  --function-name ai-pipeline-v2-story-executor-dev \
  --payload file:///tmp/test-story-executor.json \
  --cli-binary-format raw-in-base64-out \
  /tmp/story-executor-response.json \
  --region us-east-1

echo ""
echo "📋 Checking response..."

# Check if the Lambda succeeded
if [ -f /tmp/story-executor-response.json ]; then
  # Extract and check the generated files
  python3 -c "
import json
import sys

with open('/tmp/story-executor-response.json', 'r') as f:
    response = json.load(f)

if response.get('status') != 'success':
    print('❌ Lambda execution failed:', response.get('message'))
    sys.exit(1)

print('✅ Lambda executed successfully')

# Find client package.json in generated files
for file_info in response.get('data', {}).get('generated_files', []):
    if file_info.get('file_path') == 'client/package.json':
        print('\\n📦 Found client/package.json')
        
        # The content might be in S3, not in the response
        if 's3_key' in file_info:
            print(f\"   File is in S3: {file_info['s3_key']}\")
            print('   Would need to download from S3 to check versions')
        elif 'content' in file_info:
            # Parse the package.json content
            import json
            pkg = json.loads(file_info['content'])
            dev_deps = pkg.get('devDependencies', {})
            
            testing_react = dev_deps.get('@testing-library/react', 'NOT FOUND')
            testing_user = dev_deps.get('@testing-library/user-event', 'NOT FOUND')
            
            print(f\"\\n   @testing-library/react: {testing_react}\")
            print(f\"   @testing-library/user-event: {testing_user}\")
            
            if '^' in testing_react:
                print('\\n   ❌ PROBLEM: Still using caret (^) versions!')
                print('   The Lambda is not using the updated code!')
            else:
                print('\\n   ✅ Using exact versions (no caret)')
        break
else:
    print('❌ No client/package.json found in generated files')
"
else
  echo "❌ No response file created"
fi

echo ""
echo "=========================================="
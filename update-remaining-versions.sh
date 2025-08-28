#!/bin/bash

echo "📦 Updating remaining test package versions to exact..."

# Update vitest in all generators
echo "Updating vitest to exact version 1.4.0..."
find /Users/rakesh/CascadeProjects/ai-pipeline-v2/lambdas/core/story-executor/templates -name "*_generator.py" -exec \
  sed -i '' 's/"vitest": "\^1\.4\.0"/"vitest": "1.4.0"/g' {} \;

# Update jest in node_api_generator
echo "Updating jest to exact version 29.7.0..."
sed -i '' 's/"jest": "\^29\.7\.0"/"jest": "29.7.0"/g' \
  /Users/rakesh/CascadeProjects/ai-pipeline-v2/lambdas/core/story-executor/templates/node_api_generator.py

# Update ts-jest
echo "Updating ts-jest to exact version 29.1.2..."
sed -i '' 's/"ts-jest": "\^29\.1\.2"/"ts-jest": "29.1.2"/g' \
  /Users/rakesh/CascadeProjects/ai-pipeline-v2/lambdas/core/story-executor/templates/node_api_generator.py

echo "✅ Done! Checking results..."

# Verify the changes
echo ""
echo "=== Verification ==="
echo "React SPA vitest:"
grep '"vitest":' /Users/rakesh/CascadeProjects/ai-pipeline-v2/lambdas/core/story-executor/templates/react_spa_generator.py | head -1

echo "React Fullstack vitest:"
grep '"vitest":' /Users/rakesh/CascadeProjects/ai-pipeline-v2/lambdas/core/story-executor/templates/react_fullstack_generator.py | head -1

echo "Node API jest:"
grep '"jest":' /Users/rakesh/CascadeProjects/ai-pipeline-v2/lambdas/core/story-executor/templates/node_api_generator.py | head -1
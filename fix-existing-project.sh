#!/bin/bash

echo "🔧 Fixing Existing Project Dependencies"
echo "========================================"
echo ""
echo "This script will fix the dependency versions in the existing project"
echo "that was generated before our fix."
echo ""

# Clone the repository
REPO_NAME="coach-connect-app-functional-scope-document-20250826234138"
REPO_URL="https://github.com/rakeshatcf/${REPO_NAME}.git"

echo "📦 Cloning repository..."
cd /tmp
rm -rf $REPO_NAME
git clone $REPO_URL

if [ ! -d "$REPO_NAME" ]; then
  echo "❌ Failed to clone repository"
  exit 1
fi

cd $REPO_NAME

echo "📋 Current package.json versions:"
python3 -c "
import json
with open('package.json', 'r') as f:
    pkg = json.load(f)
    dev_deps = pkg.get('devDependencies', {})
    print(f'  @testing-library/react: {dev_deps.get(\"@testing-library/react\", \"NOT FOUND\")}')
    print(f'  @testing-library/user-event: {dev_deps.get(\"@testing-library/user-event\", \"NOT FOUND\")}')
"

echo ""
echo "🔧 Fixing versions to exact (removing carets)..."

# Fix the versions using sed (macOS compatible)
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS
  sed -i '' 's/"@testing-library\/react": ".*"/"@testing-library\/react": "14.2.1"/' package.json
  sed -i '' 's/"@testing-library\/user-event": ".*"/"@testing-library\/user-event": "14.5.2"/' package.json
  sed -i '' 's/"@testing-library\/jest-dom": ".*"/"@testing-library\/jest-dom": "6.4.2"/' package.json
else
  # Linux
  sed -i 's/"@testing-library\/react": ".*"/"@testing-library\/react": "14.2.1"/' package.json
  sed -i 's/"@testing-library\/user-event": ".*"/"@testing-library\/user-event": "14.5.2"/' package.json
  sed -i 's/"@testing-library\/jest-dom": ".*"/"@testing-library\/jest-dom": "6.4.2"/' package.json
fi

echo "📋 Updated package.json versions:"
python3 -c "
import json
with open('package.json', 'r') as f:
    pkg = json.load(f)
    dev_deps = pkg.get('devDependencies', {})
    print(f'  @testing-library/react: {dev_deps.get(\"@testing-library/react\", \"NOT FOUND\")}')
    print(f'  @testing-library/user-event: {dev_deps.get(\"@testing-library/user-event\", \"NOT FOUND\")}')
    print(f'  @testing-library/jest-dom: {dev_deps.get(\"@testing-library/jest-dom\", \"NOT FOUND\")}')
"

echo ""
echo "🧪 Testing npm install locally..."
npm install > /tmp/npm-install.log 2>&1

if [ $? -eq 0 ]; then
  echo "✅ npm install succeeded!"
  echo ""
  echo "📦 Creating package-lock.json for reproducible builds..."
  
  # The npm install already created package-lock.json
  if [ -f "package-lock.json" ]; then
    echo "✅ package-lock.json created"
  fi
  
  echo ""
  echo "📤 Committing and pushing fixes..."
  
  git config user.name "AI Pipeline Fix"
  git config user.email "ai-pipeline@example.com"
  git add package.json package-lock.json
  git commit -m "Fix: Use exact versions for React testing libraries

- Remove caret (^) from @testing-library packages
- Use exact version 14.2.1 for @testing-library/react (compatible with React 18)
- Add package-lock.json for reproducible builds
- Fixes npm dependency resolution conflicts"
  
  git push
  
  if [ $? -eq 0 ]; then
    echo "✅ Successfully pushed fixes to GitHub!"
    echo ""
    echo "🎉 The GitHub Actions should now work!"
    echo "   The next workflow run will use these fixed versions."
  else
    echo "❌ Failed to push (might need authentication)"
    echo ""
    echo "📝 Manual fix instructions:"
    echo "   1. Go to: https://github.com/rakeshatcf/${REPO_NAME}"
    echo "   2. Edit package.json"
    echo "   3. Change these lines:"
    echo '      "@testing-library/react": "14.2.1",'
    echo '      "@testing-library/user-event": "14.5.2",'
    echo '      "@testing-library/jest-dom": "6.4.2",'
    echo "   4. Commit the changes"
  fi
else
  echo "❌ npm install failed!"
  echo "Error log:"
  tail -20 /tmp/npm-install.log
fi

echo ""
echo "========================================"
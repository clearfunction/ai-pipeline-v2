#!/bin/bash

# Test deployed applications from AI Pipeline
# Usage: ./scripts/test-deployment.sh <project-name> [environment]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME=$1
ENVIRONMENT=${2:-dev}

if [ -z "$PROJECT_NAME" ]; then
    echo -e "${RED}Error: Project name is required${NC}"
    echo "Usage: $0 <project-name> [environment]"
    exit 1
fi

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}   AI Pipeline - Deployment Testing  ${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo -e "${YELLOW}Project: $PROJECT_NAME${NC}"
echo -e "${YELLOW}Environment: $ENVIRONMENT${NC}"
echo ""

# Test URLs (these would be dynamically retrieved in production)
FRONTEND_URL="https://${PROJECT_NAME}-${ENVIRONMENT}.netlify.app"
BACKEND_URL="https://${PROJECT_NAME}-api-${ENVIRONMENT}.example.com"
GITHUB_REPO="https://github.com/${GITHUB_USERNAME:-rakeshatcf}/${PROJECT_NAME}"

# Function to test URL accessibility
test_url() {
    local url=$1
    local name=$2
    local expected_status=${3:-200}
    
    echo -n "Testing ${name}... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null || echo "000")
    
    if [ "$response" -eq "$expected_status" ]; then
        echo -e "${GREEN}✓ OK (HTTP $response)${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED (HTTP $response)${NC}"
        return 1
    fi
}

# Function to test API endpoint
test_api_endpoint() {
    local url=$1
    local name=$2
    
    echo -n "Testing ${name}... "
    
    response=$(curl -s --max-time 10 "$url" 2>/dev/null || echo "ERROR")
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null || echo "000")
    
    if [ "$http_code" -eq 200 ] && [ "$response" != "ERROR" ]; then
        echo -e "${GREEN}✓ OK${NC}"
        echo "    Response: ${response:0:100}..."
        return 0
    else
        echo -e "${RED}✗ FAILED (HTTP $http_code)${NC}"
        return 1
    fi
}

# Initialize test counters
TESTS_PASSED=0
TESTS_TOTAL=0

echo -e "${BLUE}Frontend Testing${NC}"
echo "----------------------------------------"

# Test frontend deployment
((TESTS_TOTAL++))
if test_url "$FRONTEND_URL" "Frontend Application"; then
    ((TESTS_PASSED++))
    
    # Additional frontend tests
    echo -n "Checking HTML content... "
    content=$(curl -s --max-time 10 "$FRONTEND_URL" 2>/dev/null || echo "")
    
    if echo "$content" | grep -q "<!DOCTYPE html>" && echo "$content" | grep -q "<title>"; then
        echo -e "${GREEN}✓ Valid HTML${NC}"
    else
        echo -e "${YELLOW}⚠ Unexpected content${NC}"
    fi
fi

echo ""
echo -e "${BLUE}Backend API Testing${NC}"
echo "----------------------------------------"

# Test backend health endpoint
((TESTS_TOTAL++))
if test_api_endpoint "${BACKEND_URL}/health" "Health Endpoint"; then
    ((TESTS_PASSED++))
fi

# Test backend root endpoint
((TESTS_TOTAL++))
if test_api_endpoint "$BACKEND_URL" "API Root"; then
    ((TESTS_PASSED++))
fi

# Test backend API docs (if available)
((TESTS_TOTAL++))
if test_url "${BACKEND_URL}/docs" "API Documentation" 200; then
    ((TESTS_PASSED++))
else
    # Try alternative doc paths
    if test_url "${BACKEND_URL}/api/docs" "API Documentation (alt path)" 200; then
        ((TESTS_PASSED++))
    fi
fi

echo ""
echo -e "${BLUE}GitHub Repository Testing${NC}"
echo "----------------------------------------"

# Test GitHub repository
((TESTS_TOTAL++))
if test_url "$GITHUB_REPO" "GitHub Repository"; then
    ((TESTS_PASSED++))
    
    # Check if repository has recent commits
    echo -n "Checking repository activity... "
    if command -v gh >/dev/null 2>&1; then
        recent_commits=$(gh api repos/${GITHUB_USERNAME:-rakeshatcf}/${PROJECT_NAME}/commits --jq '. | length' 2>/dev/null || echo "0")
        if [ "$recent_commits" -gt 0 ]; then
            echo -e "${GREEN}✓ $recent_commits commits found${NC}"
        else
            echo -e "${YELLOW}⚠ No recent commits${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ gh CLI not available${NC}"
    fi
fi

echo ""
echo -e "${BLUE}Performance Testing${NC}"
echo "----------------------------------------"

# Basic performance tests
if command -v curl >/dev/null 2>&1; then
    echo -n "Frontend response time... "
    frontend_time=$(curl -o /dev/null -s -w "%{time_total}" --max-time 10 "$FRONTEND_URL" 2>/dev/null || echo "999")
    
    if (( $(echo "$frontend_time < 3.0" | bc -l 2>/dev/null || echo "0") )); then
        echo -e "${GREEN}✓ ${frontend_time}s (good)${NC}"
    elif (( $(echo "$frontend_time < 5.0" | bc -l 2>/dev/null || echo "0") )); then
        echo -e "${YELLOW}⚠ ${frontend_time}s (acceptable)${NC}"
    else
        echo -e "${RED}✗ ${frontend_time}s (slow)${NC}"
    fi
    
    echo -n "Backend response time... "
    backend_time=$(curl -o /dev/null -s -w "%{time_total}" --max-time 10 "${BACKEND_URL}/health" 2>/dev/null || echo "999")
    
    if (( $(echo "$backend_time < 1.0" | bc -l 2>/dev/null || echo "0") )); then
        echo -e "${GREEN}✓ ${backend_time}s (excellent)${NC}"
    elif (( $(echo "$backend_time < 2.0" | bc -l 2>/dev/null || echo "0") )); then
        echo -e "${YELLOW}⚠ ${backend_time}s (acceptable)${NC}"
    else
        echo -e "${RED}✗ ${backend_time}s (slow)${NC}"
    fi
fi

echo ""
echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}         Testing Summary              ${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo -e "${YELLOW}Project: $PROJECT_NAME${NC}"
echo -e "${YELLOW}Tests Passed: ${GREEN}$TESTS_PASSED${NC}${YELLOW}/${TESTS_TOTAL}${NC}"

if [ $TESTS_PASSED -eq $TESTS_TOTAL ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    
    echo ""
    echo -e "${YELLOW}Access URLs:${NC}"
    echo "Frontend: $FRONTEND_URL"
    echo "Backend:  $BACKEND_URL"
    echo "GitHub:   $GITHUB_REPO"
    
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "1. Perform manual testing using the checklist in docs/TESTING_SETUP.md"
    echo "2. Review and test user story acceptance criteria"
    echo "3. Report any issues in the GitHub PR"
    
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo "1. Check deployment logs: aws logs tail /aws/lambda/ai-pipeline-v2-github-orchestrator-${ENVIRONMENT} --follow"
    echo "2. Verify secrets configuration: ./scripts/test-secrets.sh ${ENVIRONMENT}"
    echo "3. Check GitHub Actions status: gh run list --repo ${GITHUB_USERNAME:-rakeshatcf}/${PROJECT_NAME}"
    
    exit 1
fi
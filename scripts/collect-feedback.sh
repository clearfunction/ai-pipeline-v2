#!/bin/bash

# Collect feedback from manual testing and integration results
# Usage: ./scripts/collect-feedback.sh <project-name> [environment]

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
FEEDBACK_FILE="feedback-${PROJECT_NAME}-${ENVIRONMENT}-$(date '+%Y%m%d-%H%M').json"

if [ -z "$PROJECT_NAME" ]; then
    echo -e "${RED}Error: Project name is required${NC}"
    echo "Usage: $0 <project-name> [environment]"
    exit 1
fi

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}   AI Pipeline - Feedback Collection ${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo -e "${YELLOW}Project: $PROJECT_NAME${NC}"
echo -e "${YELLOW}Environment: $ENVIRONMENT${NC}"
echo ""

# Function to prompt for user input
prompt_input() {
    local prompt="$1"
    local var_name="$2"
    local default_value="$3"
    
    if [ -n "$default_value" ]; then
        read -p "$prompt [$default_value]: " input
        if [ -z "$input" ]; then
            input="$default_value"
        fi
    else
        read -p "$prompt: " input
    fi
    
    eval "$var_name='$input'"
}

# Function to prompt for rating (1-10)
prompt_rating() {
    local prompt="$1"
    local var_name="$2"
    local rating
    
    while true; do
        read -p "$prompt (1-10): " rating
        if [[ "$rating" =~ ^[1-9]$|^10$ ]]; then
            break
        else
            echo "Please enter a number between 1 and 10."
        fi
    done
    
    eval "$var_name='$rating'"
}

# Function to prompt for yes/no
prompt_yes_no() {
    local prompt="$1"
    local var_name="$2"
    local response
    
    while true; do
        read -p "$prompt (y/n): " response
        case $response in
            [Yy]* ) eval "$var_name='yes'"; break;;
            [Nn]* ) eval "$var_name='no'"; break;;
            * ) echo "Please answer yes (y) or no (n).";;
        esac
    done
}

echo -e "${BLUE}Testing Information${NC}"
echo "----------------------------------------"

# Get tester information
prompt_input "Tester name" TESTER_NAME
prompt_input "Testing duration (minutes)" TESTING_TIME "30"

# Get URLs
FRONTEND_URL="https://${PROJECT_NAME}-${ENVIRONMENT}.netlify.app"
BACKEND_URL="https://${PROJECT_NAME}-api-${ENVIRONMENT}.example.com"
GITHUB_REPO="https://github.com/${GITHUB_USERNAME:-rakeshatcf}/${PROJECT_NAME}"

echo ""
echo -e "${BLUE}Deployment Status${NC}"
echo "----------------------------------------"

# Check deployment status automatically
prompt_yes_no "Was the frontend accessible" FRONTEND_ACCESSIBLE
if [ "$FRONTEND_ACCESSIBLE" = "yes" ]; then
    prompt_rating "Frontend performance rating" FRONTEND_PERFORMANCE
    prompt_rating "Frontend user experience rating" FRONTEND_UX
else
    FRONTEND_PERFORMANCE=0
    FRONTEND_UX=0
fi

prompt_yes_no "Was the backend accessible" BACKEND_ACCESSIBLE
if [ "$BACKEND_ACCESSIBLE" = "yes" ]; then
    prompt_rating "Backend performance rating" BACKEND_PERFORMANCE
    prompt_rating "Backend reliability rating" BACKEND_RELIABILITY
else
    BACKEND_PERFORMANCE=0
    BACKEND_RELIABILITY=0
fi

echo ""
echo -e "${BLUE}User Story Validation${NC}"
echo "----------------------------------------"

prompt_input "Number of user stories tested" STORIES_TESTED "0"
prompt_input "Number of user stories passed" STORIES_PASSED "0"
prompt_input "Number of acceptance criteria tested" CRITERIA_TESTED "0"
prompt_input "Number of acceptance criteria passed" CRITERIA_PASSED "0"

echo ""
echo -e "${BLUE}Quality Assessment${NC}"
echo "----------------------------------------"

prompt_rating "Overall code quality" OVERALL_QUALITY
prompt_rating "User experience quality" UX_QUALITY
prompt_rating "Performance" PERFORMANCE_RATING
prompt_rating "Reliability" RELIABILITY_RATING

# Calculate overall score
OVERALL_SCORE=$(( (OVERALL_QUALITY + UX_QUALITY + PERFORMANCE_RATING + RELIABILITY_RATING) / 4 ))

echo ""
echo -e "${BLUE}Issues and Feedback${NC}"
echo "----------------------------------------"

prompt_input "Critical issues found" CRITICAL_ISSUES "0"
prompt_input "Major issues found" MAJOR_ISSUES "0"
prompt_input "Minor issues found" MINOR_ISSUES "0"

echo ""
echo "Please describe any issues found (press Enter on empty line to finish):"
ISSUES_DESCRIPTION=""
while IFS= read -r line; do
    if [ -z "$line" ]; then
        break
    fi
    ISSUES_DESCRIPTION="$ISSUES_DESCRIPTION$line\n"
done

echo ""
echo "Additional feedback or suggestions (press Enter on empty line to finish):"
ADDITIONAL_FEEDBACK=""
while IFS= read -r line; do
    if [ -z "$line" ]; then
        break
    fi
    ADDITIONAL_FEEDBACK="$ADDITIONAL_FEEDBACK$line\n"
done

echo ""
echo -e "${BLUE}Recommendation${NC}"
echo "----------------------------------------"

echo "Based on your testing, what is your recommendation?"
echo "1. Approve for production"
echo "2. Approve with minor issues"
echo "3. Needs major fixes before approval"
echo "4. Reject - significant issues"

while true; do
    read -p "Enter choice (1-4): " RECOMMENDATION_NUM
    case $RECOMMENDATION_NUM in
        1) RECOMMENDATION="approve"; RECOMMENDATION_TEXT="Approve for production"; break;;
        2) RECOMMENDATION="approve_with_issues"; RECOMMENDATION_TEXT="Approve with minor issues"; break;;
        3) RECOMMENDATION="needs_fixes"; RECOMMENDATION_TEXT="Needs major fixes before approval"; break;;
        4) RECOMMENDATION="reject"; RECOMMENDATION_TEXT="Reject - significant issues"; break;;
        *) echo "Please enter 1, 2, 3, or 4.";;
    esac
done

# Calculate success metrics
if [ "$STORIES_TESTED" -gt 0 ]; then
    STORY_SUCCESS_RATE=$(( STORIES_PASSED * 100 / STORIES_TESTED ))
else
    STORY_SUCCESS_RATE=0
fi

if [ "$CRITERIA_TESTED" -gt 0 ]; then
    CRITERIA_SUCCESS_RATE=$(( CRITERIA_PASSED * 100 / CRITERIA_TESTED ))
else
    CRITERIA_SUCCESS_RATE=0
fi

TOTAL_ISSUES=$(( CRITICAL_ISSUES + MAJOR_ISSUES + MINOR_ISSUES ))

# Generate feedback JSON
cat > "$FEEDBACK_FILE" << EOF
{
  "project_info": {
    "project_name": "$PROJECT_NAME",
    "environment": "$ENVIRONMENT",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "tester": "$TESTER_NAME",
    "testing_time_minutes": $TESTING_TIME
  },
  "deployment_urls": {
    "frontend": "$FRONTEND_URL",
    "backend": "$BACKEND_URL",
    "github_repo": "$GITHUB_REPO"
  },
  "deployment_status": {
    "frontend_accessible": "$FRONTEND_ACCESSIBLE",
    "backend_accessible": "$BACKEND_ACCESSIBLE"
  },
  "user_story_validation": {
    "stories_tested": $STORIES_TESTED,
    "stories_passed": $STORIES_PASSED,
    "story_success_rate": $STORY_SUCCESS_RATE,
    "criteria_tested": $CRITERIA_TESTED,
    "criteria_passed": $CRITERIA_PASSED,
    "criteria_success_rate": $CRITERIA_SUCCESS_RATE
  },
  "quality_ratings": {
    "overall_quality": $OVERALL_QUALITY,
    "ux_quality": $UX_QUALITY,
    "performance": $PERFORMANCE_RATING,
    "reliability": $RELIABILITY_RATING,
    "frontend_performance": $FRONTEND_PERFORMANCE,
    "frontend_ux": $FRONTEND_UX,
    "backend_performance": $BACKEND_PERFORMANCE,
    "backend_reliability": $BACKEND_RELIABILITY,
    "overall_score": $OVERALL_SCORE
  },
  "issues": {
    "critical_issues": $CRITICAL_ISSUES,
    "major_issues": $MAJOR_ISSUES,
    "minor_issues": $MINOR_ISSUES,
    "total_issues": $TOTAL_ISSUES,
    "issues_description": "$(echo -e "$ISSUES_DESCRIPTION" | tr '\n' ' ')"
  },
  "feedback": {
    "additional_feedback": "$(echo -e "$ADDITIONAL_FEEDBACK" | tr '\n' ' ')",
    "recommendation": "$RECOMMENDATION",
    "recommendation_text": "$RECOMMENDATION_TEXT"
  },
  "testing_summary": {
    "passed": $([ "$RECOMMENDATION" = "approve" ] || [ "$RECOMMENDATION" = "approve_with_issues" ]; echo $?),
    "needs_work": $([ "$RECOMMENDATION" = "needs_fixes" ] || [ "$RECOMMENDATION" = "reject" ]; echo $?),
    "success_indicators": {
      "deployment_successful": $([ "$FRONTEND_ACCESSIBLE" = "yes" ] || [ "$BACKEND_ACCESSIBLE" = "yes" ]; echo $?),
      "high_quality": $([ $OVERALL_SCORE -ge 7 ]; echo $?),
      "low_issues": $([ $TOTAL_ISSUES -le 2 ]; echo $?)
    }
  }
}
EOF

echo ""
echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}         Feedback Summary             ${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo -e "${YELLOW}Project: $PROJECT_NAME${NC}"
echo -e "${YELLOW}Overall Score: $OVERALL_SCORE/10${NC}"
echo -e "${YELLOW}Story Success Rate: $STORY_SUCCESS_RATE%${NC}"
echo -e "${YELLOW}Total Issues: $TOTAL_ISSUES${NC}"
echo -e "${YELLOW}Recommendation: $RECOMMENDATION_TEXT${NC}"
echo ""

# Provide feedback file info
echo -e "${GREEN}Feedback saved to: $FEEDBACK_FILE${NC}"
echo ""

# Provide next steps based on recommendation
case $RECOMMENDATION in
    "approve")
        echo -e "${GREEN}✅ Ready for production deployment!${NC}"
        echo ""
        echo -e "${YELLOW}Next steps:${NC}"
        echo "1. Add approval comment to GitHub PR"
        echo "2. Merge the pull request"
        echo "3. Monitor production deployment"
        ;;
    "approve_with_issues")
        echo -e "${YELLOW}⚠️  Approved with minor issues noted${NC}"
        echo ""
        echo -e "${YELLOW}Next steps:${NC}"
        echo "1. Create GitHub issues for minor problems"
        echo "2. Add conditional approval to PR"
        echo "3. Proceed with deployment"
        echo "4. Address issues in follow-up iterations"
        ;;
    "needs_fixes")
        echo -e "${RED}❌ Major fixes required before approval${NC}"
        echo ""
        echo -e "${YELLOW}Next steps:${NC}"
        echo "1. Create detailed GitHub issues with screenshots"
        echo "2. Comment on PR with required fixes"
        echo "3. Re-run pipeline after fixes are made"
        echo "4. Retest when ready"
        ;;
    "reject")
        echo -e "${RED}❌ Significant issues - deployment not recommended${NC}"
        echo ""
        echo -e "${YELLOW}Next steps:${NC}"
        echo "1. Document all issues in GitHub"
        echo "2. Review generated code quality"
        echo "3. Consider architecture or story adjustments"
        echo "4. Re-run pipeline with improvements"
        ;;
esac

echo ""
echo -e "${YELLOW}Feedback file location:${NC} $FEEDBACK_FILE"

# Optionally upload feedback to S3 for aggregation
if command -v aws >/dev/null 2>&1; then
    echo ""
    read -p "Upload feedback to S3 for analysis? (y/n): " UPLOAD_FEEDBACK
    if [[ "$UPLOAD_FEEDBACK" =~ ^[Yy]$ ]]; then
        FEEDBACK_BUCKET="ai-pipeline-v2-processed-$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo 'unknown')-${AWS_DEFAULT_REGION:-us-east-1}"
        
        if aws s3 cp "$FEEDBACK_FILE" "s3://$FEEDBACK_BUCKET/feedback/" 2>/dev/null; then
            echo -e "${GREEN}✓ Feedback uploaded to S3 for analysis${NC}"
        else
            echo -e "${YELLOW}⚠ Could not upload to S3 (continuing locally)${NC}"
        fi
    fi
fi

echo ""
echo -e "${BLUE}======================================${NC}"
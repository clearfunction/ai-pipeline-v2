#!/bin/bash

# Monitor AI Pipeline deployments and provide status feedback
# Usage: ./scripts/monitor-deployments.sh [environment] [--watch]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-dev}
WATCH_MODE=false

if [ "$2" = "--watch" ]; then
    WATCH_MODE=true
fi

AWS_REGION=${AWS_DEFAULT_REGION:-us-east-1}

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}   AI Pipeline - Deployment Monitor  ${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo -e "${YELLOW}Environment: $ENVIRONMENT${NC}"
echo -e "${YELLOW}Watch Mode: $WATCH_MODE${NC}"
echo ""

# Function to check Lambda function health
check_lambda_health() {
    local function_name=$1
    local display_name=$2
    
    echo -n "Checking ${display_name}... "
    
    # Get function configuration
    config=$(aws lambda get-function --function-name "$function_name" --region "$AWS_REGION" 2>/dev/null || echo "ERROR")
    
    if [ "$config" = "ERROR" ]; then
        echo -e "${RED}✗ Not Found${NC}"
        return 1
    fi
    
    # Check last update status
    status=$(echo "$config" | jq -r '.Configuration.LastUpdateStatus // "Unknown"')
    state=$(echo "$config" | jq -r '.Configuration.State // "Unknown"')
    
    if [ "$status" = "Successful" ] && [ "$state" = "Active" ]; then
        echo -e "${GREEN}✓ Healthy${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Status: $status, State: $state${NC}"
        return 1
    fi
}

# Function to check recent executions
check_recent_executions() {
    local function_name=$1
    local hours=${2:-24}
    
    echo -n "  Recent executions (${hours}h): "
    
    # Get CloudWatch metrics for invocations
    end_time=$(date -u +%Y-%m-%dT%H:%M:%S)
    start_time=$(date -u -d "${hours} hours ago" +%Y-%m-%dT%H:%M:%S)
    
    metrics=$(aws cloudwatch get-metric-statistics \
        --namespace AWS/Lambda \
        --metric-name Invocations \
        --dimensions Name=FunctionName,Value="$function_name" \
        --start-time "$start_time" \
        --end-time "$end_time" \
        --period 3600 \
        --statistics Sum \
        --region "$AWS_REGION" \
        --query 'Datapoints[].Sum' \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$metrics" ] && [ "$metrics" != "None" ]; then
        total=$(echo "$metrics" | awk '{sum += $1} END {print sum}')
        echo -e "${GREEN}$total invocations${NC}"
    else
        echo -e "${YELLOW}No data${NC}"
    fi
}

# Function to check error rates
check_error_rate() {
    local function_name=$1
    local hours=${2:-24}
    
    echo -n "  Error rate (${hours}h): "
    
    end_time=$(date -u +%Y-%m-%dT%H:%M:%S)
    start_time=$(date -u -d "${hours} hours ago" +%Y-%m-%dT%H:%M:%S)
    
    errors=$(aws cloudwatch get-metric-statistics \
        --namespace AWS/Lambda \
        --metric-name Errors \
        --dimensions Name=FunctionName,Value="$function_name" \
        --start-time "$start_time" \
        --end-time "$end_time" \
        --period 3600 \
        --statistics Sum \
        --region "$AWS_REGION" \
        --query 'Datapoints[].Sum' \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$errors" ] && [ "$errors" != "None" ]; then
        total_errors=$(echo "$errors" | awk '{sum += $1} END {print sum}')
        if [ "$total_errors" -eq 0 ]; then
            echo -e "${GREEN}0 errors${NC}"
        else
            echo -e "${RED}$total_errors errors${NC}"
        fi
    else
        echo -e "${GREEN}No errors${NC}"
    fi
}

# Function to monitor single iteration
monitor_iteration() {
    echo -e "${BLUE}Lambda Function Health${NC}"
    echo "----------------------------------------"
    
    # Core pipeline functions
    CORE_FUNCTIONS=(
        "ai-pipeline-v2-document-processor-${ENVIRONMENT}:Document Processor"
        "ai-pipeline-v2-requirements-synthesizer-${ENVIRONMENT}:Requirements Synthesizer"
        "ai-pipeline-v2-architecture-planner-${ENVIRONMENT}:Architecture Planner"
        "ai-pipeline-v2-story-executor-${ENVIRONMENT}:Story Executor"
    )
    
    # Story execution functions
    STORY_FUNCTIONS=(
        "ai-pipeline-v2-integration-validator-${ENVIRONMENT}:Integration Validator"
        "ai-pipeline-v2-github-orchestrator-${ENVIRONMENT}:GitHub Orchestrator"
    )
    
    # Review functions
    REVIEW_FUNCTIONS=(
        "ai-pipeline-v2-review-coordinator-${ENVIRONMENT}:Review Coordinator"
    )
    
    healthy_functions=0
    total_functions=0
    
    echo -e "${YELLOW}Core Pipeline:${NC}"
    for func_info in "${CORE_FUNCTIONS[@]}"; do
        IFS=':' read -r func_name display_name <<< "$func_info"
        ((total_functions++))
        if check_lambda_health "$func_name" "$display_name"; then
            ((healthy_functions++))
            check_recent_executions "$func_name" 24
            check_error_rate "$func_name" 24
        fi
        echo
    done
    
    echo -e "${YELLOW}Story Execution:${NC}"
    for func_info in "${STORY_FUNCTIONS[@]}"; do
        IFS=':' read -r func_name display_name <<< "$func_info"
        ((total_functions++))
        if check_lambda_health "$func_name" "$display_name"; then
            ((healthy_functions++))
            check_recent_executions "$func_name" 24
            check_error_rate "$func_name" 24
        fi
        echo
    done
    
    echo -e "${YELLOW}Review Workflow:${NC}"
    for func_info in "${REVIEW_FUNCTIONS[@]}"; do
        IFS=':' read -r func_name display_name <<< "$func_info"
        ((total_functions++))
        if check_lambda_health "$func_name" "$display_name"; then
            ((healthy_functions++))
            check_recent_executions "$func_name" 24
            check_error_rate "$func_name" 24
        fi
        echo
    done
    
    echo -e "${BLUE}Infrastructure Health${NC}"
    echo "----------------------------------------"
    
    # Check S3 buckets
    echo -n "S3 Raw Bucket... "
    raw_bucket="ai-pipeline-v2-raw-$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo 'unknown')-${AWS_REGION}"
    if aws s3 ls "s3://$raw_bucket" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Accessible${NC}"
    else
        echo -e "${RED}✗ Not Accessible${NC}"
    fi
    
    echo -n "S3 Code Artifacts Bucket... "
    code_bucket="ai-pipeline-v2-code-artifacts-$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo 'unknown')-${AWS_REGION}"
    if aws s3 ls "s3://$code_bucket" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Accessible${NC}"
    else
        echo -e "${RED}✗ Not Accessible${NC}"
    fi
    
    # Check DynamoDB tables
    echo -n "DynamoDB User Stories Table... "
    if aws dynamodb describe-table --table-name "ai-pipeline-v2-user-stories-${ENVIRONMENT}" --region "$AWS_REGION" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Available${NC}"
    else
        echo -e "${RED}✗ Not Available${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}Recent Activity${NC}"
    echo "----------------------------------------"
    
    # Check recent CloudWatch log activity
    echo -n "Recent pipeline executions... "
    recent_logs=$(aws logs describe-log-streams \
        --log-group-name "/aws/lambda/ai-pipeline-v2-story-executor-${ENVIRONMENT}" \
        --order-by LastEventTime \
        --descending \
        --max-items 5 \
        --region "$AWS_REGION" \
        --query 'logStreams[].lastEventTime' \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$recent_logs" ] && [ "$recent_logs" != "None" ]; then
        echo -e "${GREEN}✓ Active${NC}"
        echo "  Last execution: $(date -d @$(($(echo "$recent_logs" | cut -d' ' -f1) / 1000)) 2>/dev/null || echo 'Unknown')"
    else
        echo -e "${YELLOW}⚠ No recent activity${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}System Summary${NC}"
    echo "----------------------------------------"
    echo -e "Healthy Functions: ${GREEN}$healthy_functions${NC}/$total_functions"
    
    if [ $healthy_functions -eq $total_functions ]; then
        echo -e "System Status: ${GREEN}✓ All Systems Operational${NC}"
    else
        unhealthy=$((total_functions - healthy_functions))
        echo -e "System Status: ${YELLOW}⚠ $unhealthy Functions Need Attention${NC}"
    fi
    
    echo -e "Last Updated: ${YELLOW}$(date)${NC}"
}

# Function to generate simple status report
generate_status_report() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local report_file="monitoring-report-${ENVIRONMENT}-$(date '+%Y%m%d-%H%M').txt"
    
    echo "AI Pipeline Deployment Status Report" > "$report_file"
    echo "Generated: $timestamp" >> "$report_file"
    echo "Environment: $ENVIRONMENT" >> "$report_file"
    echo "===========================================" >> "$report_file"
    echo "" >> "$report_file"
    
    # Capture current status (without colors)
    monitor_iteration 2>&1 | sed 's/\x1B\[[0-9;]*[JKmsu]//g' >> "$report_file"
    
    echo ""
    echo -e "${YELLOW}Status report saved to: $report_file${NC}"
}

# Main execution
if [ "$WATCH_MODE" = true ]; then
    echo -e "${YELLOW}Monitoring in watch mode (Ctrl+C to stop)${NC}"
    echo ""
    
    while true; do
        clear
        echo -e "${BLUE}======================================${NC}"
        echo -e "${BLUE}   AI Pipeline - Live Monitoring     ${NC}"
        echo -e "${BLUE}======================================${NC}"
        echo ""
        
        monitor_iteration
        
        echo ""
        echo -e "${YELLOW}Refreshing in 30 seconds...${NC}"
        sleep 30
    done
else
    monitor_iteration
    
    echo ""
    echo -e "${YELLOW}Options:${NC}"
    echo "  --watch    Monitor continuously"
    echo "  --report   Generate status report"
    
    if [ "$2" = "--report" ]; then
        generate_status_report
    fi
fi

echo ""
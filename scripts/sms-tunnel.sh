#!/usr/bin/env bash
#
# sms-tunnel.sh — Open an SSM port-forward to the SMS API internal ALB.
#
# When sms-api is deployed into a private VPC (GovCloud `smscdk`, the test
# stack `smsvpctest`, etc.) the Application Load Balancer is internal-only
# and has no public DNS. This script uses AWS Systems Manager Session Manager
# to tunnel from your laptop, through the Batch submit-node EC2, to the
# internal ALB — so local tools (atlantis CLI, browsers) can reach the API
# without a VPN.
#
# Public deployments (e.g. sms.cam.uchc.edu) do NOT need this — hit the URL
# directly.
#
# Usage:
#   AWS_PROFILE=<sso-profile> AWS_DEFAULT_REGION=<region> \
#       ./sms-tunnel.sh -s <stack-prefix> [-p <local-port>]
#
# Required:
#   -s, --stack PREFIX     CloudFormation stack prefix (e.g. smscdk, smsvpctest)
#
# Options:
#   -p, --port PORT        Local port to bind (default: 8080)
#   -h, --help             Show this help message
#
# Environment:
#   AWS_DEFAULT_REGION     Required. AWS region of the deployment.
#   AWS_PROFILE            Required. AWS profile (SSO or otherwise).
#
# Prerequisites:
#   - AWS CLI v2
#   - Session Manager plugin
#     (https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html)
#   - Valid SSO login: `aws sso login --profile $AWS_PROFILE`
#
# Once the tunnel is up, point clients at http://localhost:$LOCAL_PORT:
#   /docs          — SMS API (Swagger UI)
#   /              — Pathway Tools web UI (served from the same ALB)
#   /sms/sms.html  — PTools SMS simulation UI
#

set -euo pipefail

AWS_PROFILE="${AWS_PROFILE:-}"
AWS_REGION="${AWS_DEFAULT_REGION:-${AWS_REGION:-}}"

ALB_PORT="80"
LOCAL_PORT="${LOCAL_PORT:-8080}"
STACK_PREFIX=""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

show_help() {
    cat << EOF
${BOLD}sms-tunnel.sh${NC} — SSM port-forward to the SMS API internal ALB

${BOLD}USAGE:${NC}
    AWS_PROFILE=<sso-profile> AWS_DEFAULT_REGION=<region> \\
        ./sms-tunnel.sh -s <stack-prefix> [OPTIONS]

${BOLD}REQUIRED:${NC}
    -s, --stack PREFIX     CloudFormation stack prefix (e.g. smscdk, smsvpctest)

${BOLD}OPTIONS:${NC}
    -p, --port PORT        Local port to bind (default: 8080)
    -h, --help             Show this help message

${BOLD}ENVIRONMENT:${NC}
    AWS_DEFAULT_REGION     Required. AWS region of the deployment.
    AWS_PROFILE            Required. AWS profile (SSO or otherwise).

${BOLD}EXAMPLES:${NC}
    # GovCloud test stack
    AWS_PROFILE=stanford-sso AWS_DEFAULT_REGION=us-gov-west-1 \\
        ./sms-tunnel.sh -s smsvpctest

    # GovCloud main stack on a custom local port
    AWS_PROFILE=stanford-sso AWS_DEFAULT_REGION=us-gov-west-1 \\
        ./sms-tunnel.sh -s smscdk -p 9000

EOF
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--stack)
            STACK_PREFIX="$2"
            shift 2
            ;;
        -p|--port)
            LOCAL_PORT="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

if [ -z "$AWS_PROFILE" ]; then
    echo -e "${RED}ERROR: AWS_PROFILE environment variable must be set${NC}"
    echo ""
    show_help
    exit 1
fi

if [ -z "$AWS_REGION" ]; then
    echo -e "${RED}ERROR: AWS_DEFAULT_REGION environment variable must be set${NC}"
    echo ""
    show_help
    exit 1
fi

if [ -z "$STACK_PREFIX" ]; then
    echo -e "${RED}ERROR: Stack prefix is required (-s <stack-prefix>)${NC}"
    echo ""
    show_help
    exit 1
fi

get_stack_output() {
    local stack_name="$1"
    local output_key="$2"
    AWS_PROFILE=$AWS_PROFILE aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --region "$AWS_REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='$output_key'].OutputValue" \
        --output text 2>/dev/null
}

echo -e "${YELLOW}Looking up deployment resources...${NC}"
echo -e "  Stack prefix: ${BOLD}$STACK_PREFIX${NC}"
echo -e "  Region: ${BOLD}$AWS_REGION${NC}"
echo ""

TUNNEL_INSTANCE_ID=$(get_stack_output "${STACK_PREFIX}-batch" "SubmitNodeInstanceId")
if [ -z "$TUNNEL_INSTANCE_ID" ] || [ "$TUNNEL_INSTANCE_ID" = "None" ]; then
    echo -e "${RED}ERROR: Could not find submit node instance ID${NC}"
    echo "  Stack: ${STACK_PREFIX}-batch"
    echo "  Output: SubmitNodeInstanceId"
    echo ""
    echo "Make sure the batch stack is deployed and you have access."
    exit 1
fi

ALB_DNS=$(get_stack_output "${STACK_PREFIX}-internal-alb" "AlbDnsName")
if [ -z "$ALB_DNS" ] || [ "$ALB_DNS" = "None" ]; then
    echo -e "${RED}ERROR: Could not find ALB DNS name${NC}"
    echo "  Stack: ${STACK_PREFIX}-internal-alb"
    echo "  Output: AlbDnsName"
    echo ""
    echo "Make sure the internal-alb stack is deployed."
    exit 1
fi

echo -e "${GREEN}✓ Found tunnel instance: $TUNNEL_INSTANCE_ID${NC}"
echo -e "${GREEN}✓ Found ALB: $ALB_DNS${NC}"
echo ""

check_prerequisites() {
    local missing=0

    if ! command -v aws &> /dev/null; then
        echo -e "${RED}✗ AWS CLI not found${NC}"
        echo "  Install: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
        missing=1
    else
        echo -e "${GREEN}✓ AWS CLI installed${NC}"
    fi

    if ! command -v session-manager-plugin &> /dev/null; then
        echo -e "${RED}✗ Session Manager plugin not found${NC}"
        echo "  Install: https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html"
        missing=1
    else
        echo -e "${GREEN}✓ Session Manager plugin installed${NC}"
    fi

    if ! AWS_PROFILE=$AWS_PROFILE aws sts get-caller-identity --region $AWS_REGION &> /dev/null; then
        echo -e "${RED}✗ AWS credentials not valid${NC}"
        echo -e "  Check your AWS_PROFILE ($AWS_PROFILE) or run: ${CYAN}aws sso login --profile $AWS_PROFILE${NC}"
        missing=1
    else
        echo -e "${GREEN}✓ AWS credentials valid${NC}"
    fi

    if [[ $missing -eq 1 ]]; then
        echo ""
        echo -e "${RED}Please fix the above issues and try again.${NC}"
        exit 1
    fi
}

check_port() {
    if lsof -Pi :$LOCAL_PORT -sTCP:LISTEN -t &> /dev/null; then
        echo -e "${RED}Error: Port $LOCAL_PORT is already in use${NC}"
        echo "Try a different port: ./sms-tunnel.sh -s $STACK_PREFIX -p 9000"
        exit 1
    fi
}

main() {
    echo ""
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  SMS API Tunnel${NC}"
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    echo -e "${YELLOW}Checking prerequisites...${NC}"
    echo ""
    check_prerequisites
    echo ""

    check_port

    echo -e "${YELLOW}Starting secure tunnel...${NC}"
    echo ""
    echo -e "  ${BLUE}Stack:${NC}       $STACK_PREFIX"
    echo -e "  ${BLUE}Profile:${NC}     $AWS_PROFILE"
    echo -e "  ${BLUE}Region:${NC}      $AWS_REGION"
    echo -e "  ${BLUE}Tunnel via:${NC}  $TUNNEL_INSTANCE_ID"
    echo -e "  ${BLUE}Target:${NC}      $ALB_DNS:$ALB_PORT"
    echo -e "  ${BLUE}Local Port:${NC}  $LOCAL_PORT"
    echo ""
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${GREEN}${BOLD}  Point clients at:  http://localhost:$LOCAL_PORT/${NC}"
    echo ""
    echo -e "  For atlantis:  ${CYAN}export API_BASE_URL=http://localhost:$LOCAL_PORT${NC}"
    echo ""
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${CYAN}Endpoints available through this tunnel:${NC}"
    echo -e "    • http://localhost:$LOCAL_PORT/docs          ${BLUE}(SMS API / Swagger UI)${NC}"
    echo -e "    • http://localhost:$LOCAL_PORT/              ${BLUE}(Pathway Tools UI)${NC}"
    echo -e "    • http://localhost:$LOCAL_PORT/sms/sms.html  ${BLUE}(PTools SMS simulation UI)${NC}"
    echo ""
    echo -e "${YELLOW}Press Ctrl+C to disconnect${NC}"
    echo ""

    AWS_PROFILE=$AWS_PROFILE aws ssm start-session \
        --target "$TUNNEL_INSTANCE_ID" \
        --document-name AWS-StartPortForwardingSessionToRemoteHost \
        --parameters "{\"host\":[\"$ALB_DNS\"],\"portNumber\":[\"$ALB_PORT\"],\"localPortNumber\":[\"$LOCAL_PORT\"]}" \
        --region "$AWS_REGION"
}

main

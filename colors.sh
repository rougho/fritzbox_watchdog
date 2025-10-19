#!/bin/bash
# ASCII Color Codes for Terminal Output
# Source this file with: source colors.sh

# Text Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;37m'

# Background Colors
BG_RED='\033[41m'
BG_GREEN='\033[42m'
BG_YELLOW='\033[43m'
BG_BLUE='\033[44m'
BG_PURPLE='\033[45m'
BG_CYAN='\033[46m'

# Text Styles
BOLD='\033[1m'
DIM='\033[2m'
UNDERLINE='\033[4m'
BLINK='\033[5m'
REVERSE='\033[7m'

# Reset
NC='\033[0m' # No Color / Reset

# Status Labels with Colors
ERROR="${RED}[ERROR]${NC}"
SUCCESS="${GREEN}[SUCCESS]${NC}"
WARNING="${YELLOW}[WARNING]${NC}"
INFO="${CYAN}[INFO]${NC}"
DEBUG="${GRAY}[DEBUG]${NC}"
CONFIG="${BLUE}[CONFIG]${NC}"
PACKAGE="${PURPLE}[PACKAGE]${NC}"
START="${GREEN}[START]${NC}"
STOP="${RED}[STOP]${NC}"
TEST="${YELLOW}[TEST]${NC}"
PASS="${GREEN}[PASS]${NC}"
FAIL="${RED}[FAIL]${NC}"

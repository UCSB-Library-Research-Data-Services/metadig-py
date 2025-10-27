#!/bin/bash

# validate_dataverse_dataset.sh
# Quick validation script for Dataverse datasets using MetaDIG quality checks
# Usage: ./scripts/validate_dataverse_dataset.sh doi:10.5072/FK2/XXXXX

set -e  # Exit on error

# Configuration
DATAVERSE_URL="https://dataverse.grit.ucsb.edu"
SUITE_PATH="suites/metadata-suite.xml"
CHECK_FOLDER="suites/checks/"
HASHSTORE_PATH="./hashstore"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if DOI is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: No DOI provided${NC}"
    echo "Usage: $0 <doi>"
    echo "Example: $0 doi:10.5072/FK2/AM1BXB"
    exit 1
fi

# create tmp directory if it doesn't exist
mkdir -p tmp

DOI="$1"
SAFE_FILENAME=$(echo "$DOI" | sed 's/[\/:]/_/g')
EML_FILE="tmp/${SAFE_FILENAME}.xml"
SYSMETA_FILE="tmp/${SAFE_FILENAME}_sysmeta.xml"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}MetaDIG Quality Check - Dataverse${NC}"
echo -e "${BLUE}========================================${NC}"
echo "Dataset: $DOI"
echo ""

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo -e "Activating virtual environment..."
    source .venv/bin/activate
fi

# Step 1: Convert Dataverse JSON to EML
echo -e "Fetching metadata and converting to EML..."
python scripts/json_to_eml.py \
    --base-url "$DATAVERSE_URL" \
    --persistent-id "$DOI" \
    --output "$EML_FILE" \
    --insecure

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to fetch metadata${NC}"
    exit 1
fi

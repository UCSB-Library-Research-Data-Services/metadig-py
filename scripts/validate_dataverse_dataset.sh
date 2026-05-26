#!/bin/bash

# validate_dataverse_dataset.sh
# Quick validation script for Dataverse datasets using MetaDIG quality checks
# Usage: ./scripts/validate_dataverse_dataset.sh doi:10.5072/FK2/XXXXX

set -e  # Exit on error

# Configuration
DATAVERSE_URL="https://dataverse.grit.ucsb.edu"
SUITE_PATH="metadig-checks/src/suites/FAIR-suite-0.5.0.xml"
CHECK_FOLDER="metadig-checks/src/checks"
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

DOI="$1"
SAFE_FILENAME=$(echo "$DOI" | sed 's/[\/:]/_/g')
EML_FILE="${SAFE_FILENAME}.xml"
SYSMETA_FILE="${SAFE_FILENAME}_sysmeta.xml"

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

# Step 2: Generate system metadata stub
echo -e "Generating system metadata stub..."
python -c "
import sys
sys.path.insert(0, 'scripts')
from dataverse_to_metadig import write_sysmeta_stub

write_sysmeta_stub(
    identifier='$DOI',
    authoritative_member_node='urn:node:DATAVERSE',
    rights_holder='public',
    file_name='$EML_FILE',
    out_path='$SYSMETA_FILE',
    format_id='https://eml.ecoinformatics.org/eml-2.2.0'
)
"

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to generate system metadata${NC}"
    exit 1
fi

# Step 3: Run MetaDIG quality checks
echo -e "Running quality checks..."
echo ""

python -m metadig.metadigclient \
    -runsuite \
    -suitepath "$SUITE_PATH" \
    -mdoc "$EML_FILE" \
    -sysmeta "$SYSMETA_FILE" \
    -checkfolder "$CHECK_FOLDER" \
    -sp "$HASHSTORE_PATH" 2>/dev/null

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}Validation complete!${NC}"
    echo ""
    echo "Generated files:"
    echo "  - $EML_FILE (metadata)"
    echo "  - $SYSMETA_FILE (system metadata)"
else
    echo -e "${RED}Validation failed${NC}"
    exit 1
fi

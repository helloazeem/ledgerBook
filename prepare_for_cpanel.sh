#!/bin/bash

# Exit on error
set -e

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Preparing LedgerBook for cPanel deployment...${NC}"

# Create a temporary directory for the deployment files
TEMP_DIR="ledgerbook_cpanel_deploy"
mkdir -p $TEMP_DIR

# Copy necessary files
echo -e "${GREEN}Copying application files...${NC}"
cp -r app.py models.py requirements.txt templates static $TEMP_DIR/
cp passenger_wsgi.py .htaccess setup_cpanel.sh check_app.py DEPLOY_TO_CPANEL.md $TEMP_DIR/

# Create instance directory
echo -e "${GREEN}Creating instance directory...${NC}"
mkdir -p $TEMP_DIR/instance

# Create a README specifically for cPanel deployment
echo -e "${GREEN}Creating README for deployment...${NC}"
cat > $TEMP_DIR/README.md << 'EOF'
# LedgerBook cPanel Deployment

This package contains all files needed to deploy LedgerBook to cPanel.

## Quick Start

1. Upload all files to your chosen directory on your cPanel account
2. Run setup_cpanel.sh to set up the environment
3. Update the .htaccess file with your actual path
4. Configure the Python application in cPanel
5. Visit your site to start using LedgerBook

For detailed instructions, see DEPLOY_TO_CPANEL.md

## Testing

Run `python check_app.py` to verify the setup is working correctly.
EOF

# Create a zip file for easy upload
echo -e "${GREEN}Creating deployment zip file...${NC}"
ZIPFILE="ledgerbook_cpanel_deploy.zip"
zip -r $ZIPFILE $TEMP_DIR

# Clean up temp directory
echo -e "${GREEN}Cleaning up...${NC}"
rm -rf $TEMP_DIR

echo -e "${YELLOW}Deployment package created: $ZIPFILE${NC}"
echo -e "${YELLOW}Upload this file to your cPanel account and follow the instructions in DEPLOY_TO_CPANEL.md${NC}" 
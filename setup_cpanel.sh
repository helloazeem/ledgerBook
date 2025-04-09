#!/bin/bash

# Exit on error
set -e

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting LedgerBook setup on cPanel...${NC}"

# Create and activate virtual environment
echo -e "${GREEN}Creating Python virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo -e "${GREEN}Upgrading pip...${NC}"
pip install --upgrade pip

# Install required packages
echo -e "${GREEN}Installing required packages...${NC}"
pip install -r requirements.txt

# Create instance directory
echo -e "${GREEN}Creating instance directory...${NC}"
mkdir -p instance

# Initialize the database
echo -e "${GREEN}Initializing the database...${NC}"
python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database tables created successfully')
"

# Set permissions
echo -e "${GREEN}Setting proper permissions...${NC}"
chmod -R 755 .
chmod -R 777 instance
chmod 755 passenger_wsgi.py

echo -e "${YELLOW}Setup complete! Please update your .htaccess file with the correct path to your application.${NC}"
echo -e "${YELLOW}Path should be: $(pwd)/static/ in the Alias directive.${NC}" 
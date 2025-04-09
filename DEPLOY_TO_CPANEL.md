# Deploying LedgerBook to cPanel

This guide provides step-by-step instructions for deploying the LedgerBook application to a cPanel hosting account.

## Prerequisites

- A cPanel hosting account with Python support
- Python 3.7 or later installed on your cPanel server
- SSH access to your cPanel account (recommended but not required)
- Access to cPanel File Manager

## Deployment Steps

### 1. Prepare the Files for Upload

Make sure you have the following files ready for upload:
- All application files (.py, templates, static assets)
- passenger_wsgi.py (for WSGI configuration)
- .htaccess (for web server configuration)
- requirements.txt (for Python dependencies)
- setup_cpanel.sh (for environment setup)

### 2. Upload Files to cPanel

#### Option A: Using File Manager

1. Log into your cPanel account
2. Navigate to the "File Manager"
3. Navigate to your desired directory, typically `public_html` or a subdirectory
4. Click "Upload" and upload all the files and directories from your local project

#### Option B: Using SFTP

1. Connect to your server using an SFTP client (like FileZilla)
2. Navigate to your desired directory
3. Upload all project files and directories

### 3. Set Up the Python Environment

#### Option A: Using SSH

If you have SSH access to your cPanel account:

1. Connect to your server via SSH
2. Navigate to your application directory
3. Make the setup script executable:
   ```
   chmod +x setup_cpanel.sh
   ```
4. Run the setup script:
   ```
   ./setup_cpanel.sh
   ```

#### Option B: Using cPanel Terminal

If SSH access is not available, but cPanel Terminal is:

1. Access your cPanel account
2. Navigate to "Terminal" in cPanel
3. Navigate to your application directory
4. Run the commands from setup_cpanel.sh manually

### 4. Update the .htaccess File

After deployment, you need to update the path in the .htaccess file to match your actual directory path:

1. Find the line with `Alias /static/ /home/username/myapp/static/`
2. Replace `/home/username/myapp/static/` with the actual path to your static directory 
   (The setup script will output this path when it runs)

### 5. Configure Python Application in cPanel

1. In cPanel, navigate to "Setup Python App"
2. Click "Create Application"
3. Configure the application:
   - Select the application path where you uploaded the files
   - Set the application URL (e.g., `/ledgerbook` or your domain)
   - Select Python version (3.7+)
   - Set "Application startup file" to `passenger_wsgi.py`
   - Set "Application Entry point" to `application`
   - Set "WSGI application group" to `%{GLOBAL}`

4. Click "Create" to save the configuration

### 6. Test the Application

1. Visit your application URL (e.g., `https://yourdomain.com/ledgerbook`)
2. You should see the LedgerBook login page
3. Log in using your credentials

### Troubleshooting

If you encounter issues:

1. Check the error logs in cPanel (under "Errors" or "Logs")
2. Verify permissions (files should be 644, directories 755, instance directory 777)
3. Ensure the virtual environment is properly configured
4. Check that all requirements are installed correctly
5. Verify the database file is writeable

## Security Considerations

- Make sure your SECRET_KEY is set securely in a way that's not exposed in your code
- Consider using cPanel's environment variables for sensitive information
- Ensure that your instance directory (containing the database) has proper permissions

## Maintenance

To update your application in the future:

1. Upload the new files to your application directory
2. If there are database schema changes, run migrations
3. Restart the application in cPanel if necessary 
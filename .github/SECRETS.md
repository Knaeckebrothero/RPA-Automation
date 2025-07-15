# GitHub Secrets Configuration

This document explains how to set up GitHub secrets for enhanced testing with real email data.

## Required Secrets (Optional)

The GitHub Actions workflow can optionally use real email credentials to download example emails for testing. If these secrets are not provided, the tests will use mock data.

### Setting up GitHub Secrets

1. Go to your repository on GitHub
2. Navigate to **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret**
4. Add the following secrets:

### Email Configuration Secrets

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `IMAP_HOST` | Your email server host | `imap.gmail.com` |
| `IMAP_PORT` | Email server port (usually 993 for SSL) | `993` |
| `IMAP_USER` | Your email username | `your.email@gmail.com` |
| `IMAP_PASSWORD` | Your email password or app password | `your_app_password` |
| `INBOX` | Your inbox name | `INBOX` |

### Gmail Setup

For Gmail accounts:
1. Enable 2-factor authentication
2. Generate an App Password:
   - Go to [Google Account settings](https://myaccount.google.com/)
   - Security > 2-Step Verification > App passwords
   - Generate a new app password
   - Use this app password as `IMAP_PASSWORD`

### Testing the Setup

Once secrets are configured:
1. Push to `main` or `develop` branch
2. Check the Actions tab in your repository
3. The workflow will show "Downloading example emails..." if credentials are working
4. Tests will run with real email data if available, otherwise with mock data

## Security Notes

- Never commit email credentials to the repository
- Use app passwords instead of main passwords when possible
- GitHub secrets are encrypted and only accessible to repository maintainers
- The workflow uses `continue-on-error: true` for email download, so tests will still run if email access fails
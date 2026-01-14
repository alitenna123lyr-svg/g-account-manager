# 2FA Code Generator

A simple desktop application to manage and generate TOTP 2FA codes for multiple accounts.

## Features

- Import accounts from file (format: `email----password----secondary_email----2fa_key`)
- Auto-detect file separators
- Auto-refresh 2FA codes every 30 seconds
- Click any cell to copy content
- Duplicate account detection
- One-click remove all duplicates
- Toast notifications for copy actions
- Delete confirmation to prevent accidents

## Requirements

- Python 3.x
- PyQt6
- pyotp

## Installation

```bash
pip install PyQt6 pyotp
```

## Usage

```bash
python 2fa_generator.py
```

## File Format

Create a text file with your accounts in this format:
```
email@example.com----password----backup@email.com----2FA_SECRET_KEY
another@example.com----pass2----backup2@email.com----ANOTHER_SECRET
```

## Screenshot

The application displays:
- Email, Password, Secondary Email, 2FA Key, 2FA Code columns
- Auto-refreshing countdown timer
- Click any cell to copy its content

## Security Note

- Your account data files are excluded from git (see .gitignore)
- Never commit sensitive account information to public repositories

# SecureBank AI — Banking Security Monitoring Desktop Application

SecureBank AI is a **PySide6 desktop prototype** for monitoring banking-style sign-in events, file-access activity, suspicious behaviour, and security alerts.

It demonstrates security monitoring, role-based access, machine-learning-assisted risk detection, and automated email notifications.

**Important:** This is an educational and presentation prototype. It is not connected to a bank's live systems and must not be used as a production banking security system.

## Project Security and Privacy

This source package excludes local `.env` credentials and the local SQLite database.

- Application data is stored outside the project directory.
- Environment variables are used for private credentials.
- Local databases and virtual environments are excluded from Git.
- Never upload real customer records, passwords, API keys, or confidential banking information.
- Use only authorised datasets and data you have permission to redistribute.

## Features

### 1. Security Monitoring Dashboard

- Web-style overview with a clean page header and security posture indicator.
- Six aligned KPI cards.
- Full-width activity charts.
- Latest security alerts.
- Top risky accounts.
- Existing monitoring metrics and charts retained.

### 2. Security Alert Management

- Readable alert feed with automatic text wrapping.
- Suspicious sign-in monitoring.
- Risk-based alert classification.
- Security event history and notification delivery status.

### 3. Role-Based User Interfaces

Separate dashboards and functionality for:

- Customers
- Security Staff
- Administrators

Profile management includes Username, Full name, E-mail, and Role, with separate Save Profile and Update Password actions.

### 4. Secure Login Interface

- Bank-and-shield background.
- Customer, Staff, and Admin portal selectors.
- Login and registration interface.
- Security footer and contact information.
- Maximized application windows with consistent sizing.

### 5. Automated Email Notifications

The application supports email notifications for:

- Successful sign-ins.
- Failed login attempts.
- Account registration.
- Profile and password changes.
- Sign-outs and account lockouts.
- Manual file activity.
- Report exports.
- Account administration.
- Suspicious activity reports.
- Alert resolution.

Notification routing depends on risk levels, account preferences, and administrator/security settings.

CSV imports generate summary notifications rather than sending individual emails for historical records.

Synthetic simulator activity does not send emails to simulated users.

### 6. Machine Learning and Risk Detection

The application includes machine-learning-assisted risk monitoring and suspicious activity detection.

Default ML metrics use synthetic bootstrap data for demonstration purposes. They are not validated banking accuracy measurements.

## Dataset Information and Attribution

This project uses research datasets for educational and security-monitoring demonstrations.

### RBA Dataset

- File: `rba-dataset.zip`
- Source: https://zenodo.org/records/6782156
- Dataset authors: Stephan Wiefling, Paul René Jørgensen, Sigurd Thunem, and Luigi Lo Iacono.
- Licence: Creative Commons Attribution 4.0 International (CC BY 4.0).
- Licence details: https://creativecommons.org/licenses/by/4.0/

Research paper:

Stephan Wiefling, Paul René Jørgensen, Sigurd Thunem, and Luigi Lo Iacono, "Pump Up Password Security! Evaluating and Enhancing Risk-Based Authentication on a Real-World Large-Scale Online Service." ACM Transactions on Privacy and Security (2022). DOI: 10.1145/3546069.

### SPEDIA Dataset

- Original source: https://zenodo.org/records/15495572
- Conversion script: `convert_spedia_for_leakguard.py`
- The converted file `spedia_leakguard_compatible.csv` is generated locally and is excluded from this public repository until its redistribution permissions are confirmed.
- Check the original dataset record's licence and conditions before sharing the original or converted data.

### Dataset Usage Notice

These datasets are used for educational and demonstration purposes only. Dataset ownership and applicable licence conditions remain with their respective rights holders. Any adaptations must be identified appropriately and must comply with the original dataset licence.

## 1. Installation and Running (Windows)

### Requirements

- Windows 10 or Windows 11.
- Python 3.14, subject to dependency compatibility.
- Git (optional, for cloning the repository).

### Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd SecureBankAI
```

Alternatively, download and extract the source ZIP.

### Create a virtual environment

```bat
py -3.14 -m venv .venv
.venv\Scripts\activate
```

If Python 3.14 is not recognised, check installed Python versions:

```bat
py -0p
```

Use a supported Python version compatible with the dependencies listed in `requirements.txt`.

### Install dependencies

```bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Start the application

```bat
python main.py
```

The application uses a local SQLite database stored outside the GitHub project directory.

For a fresh installation, the application should initialise its database through its database initialisation process.

For the prepared presentation build, use the supplied demo database only if it is separately provided and authorised for distribution.

**Do not replace an existing database containing important records without making a backup.**

## 2. Environment Variables and SMTP Configuration

Private credentials must never be committed to GitHub.

Create your private `.env` file using `.env.example` as a reference.

The current source configuration loads `.env` from the parent directory of the project folder.

For example:

```text
E:\final git demo\
    .env
    SecureBankAI_Final_Updated\
        main.py
        config.py
        requirements.txt
```

Create and edit the environment file:

```bat
copy .env.example .env
notepad ..\.env
```

Example configuration:

```env
SB_STAFF_CODE=your-private-staff-code
SB_ADMIN_CODE=your-private-admin-code

SB_SMTP_USER=your-sender@gmail.com
SB_SMTP_APP_PASSWORD=your-google-app-password

SB_SECURITY_EMAIL=your-security-team@example.com
```

### Gmail SMTP Setup

1. Enable Google 2-Step Verification.
2. Generate a Google App Password.
3. Use the App Password instead of your normal Gmail password.
4. Enter your credentials in the private `.env` file.
5. Restart the application after changing environment variables.

The current SMTP implementation uses Gmail over SSL.

A bank's own SMTP relay would require adapting the sender configuration.

**Never upload `.env` to GitHub.**

For the packaged EXE, the current configuration resolves `.env` from the parent directory of the executable's containing directory. Keep the file private and verify its location for your actual EXE folder structure.

## 3. Account Notification Configuration

To enable account notifications:

1. Log in as a customer, staff member, or administrator.
2. Open My Profile and verify the account email address.
3. Open My Alerts / Notifications.
4. Enable Send account activity and security notices to my e-mail.
5. Save the notification preferences.
6. Set the suspicious-login threshold to MEDIUM and HIGH if both severities should be received.

### SMTP Verification

Navigate to:

**Admin → System & Notifications**

Use:

**Send test e-mail to me + security team**

Verify the email configuration and review:

**My Alerts → Notification History & Delivery Status**

Test successful login, failed login, profile updates, manual file activity, and report exports.

Suspicious bulk-file activity is deliberately routed to administrators/security rather than the potentially involved account.

Live events can generate multiple emails because there is no notification cooldown.

## 4. Testing and Validation

Run these commands from the project directory with the virtual environment activated.

### Python compilation check

```bash
python -m compileall -q .
```

### Application smoke test

```bash
python smoke_test.py
```

These checks help identify Python compilation errors and application-level issues.

A successful smoke test does not replace full manual testing of the application's security and database behaviour.

### Suggested Presentation Demonstration

Demonstrate:

1. Login interface.
2. Customer dashboard.
3. Staff dashboard.
4. Administrator dashboard.
5. Security overview and KPI cards.
6. Notification preferences.
7. Normal login event.
8. Suspicious login event.
9. Low-risk manual file event.
10. High-volume file activity scenario.
11. Notification history and delivery status.

Use only synthetic or otherwise authorised demonstration records.

## 5. Optional Windows EXE Build

The project includes `build_exe.bat` for creating a Windows executable.

With the virtual environment activated, run:

```bat
build_exe.bat
```

The packaged application uses the application data directory:

```text
%LOCALAPPDATA%\SecureBankAI
```

The configured database location is:

```text
%LOCALAPPDATA%\SecureBankAI\securebank.db
```

When a packaged database is included in the EXE distribution, the application copies it to the local application data directory on first launch if no database already exists.

Do not bundle private `.env` files or real customer databases.

## 6. Project Security Guidelines

Before publishing or distributing the project:

- Keep `.env` private.
- Never commit API keys, SMTP passwords, or authentication secrets.
- Do not upload real banking customer information.
- Keep local database files out of the public repository.
- Verify dataset redistribution licences.
- Use synthetic data for presentations and testing.
- Back up important databases before updates.
- Review staged Git files before committing.

## 7. Disclaimer

SecureBank AI is an educational and demonstration-oriented desktop prototype.

It is designed to demonstrate banking-style security monitoring, suspicious activity detection, risk classification, and automated notifications.

It has not been independently validated, certified, or approved for deployment in real banking infrastructure.

All metrics and machine-learning results should be interpreted as demonstration outputs rather than guarantees of real-world fraud detection accuracy.

---

**Project:** SecureBank AI  
**Platform:** Windows Desktop  
**Technology:** Python, PySide6, SQLite, SQLAlchemy, Machine Learning  
**Purpose:** Banking Security Monitoring Demonstration
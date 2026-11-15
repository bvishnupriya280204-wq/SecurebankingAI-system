"""Optional, manually-run demo account manager for isolated testing.

Usage: python demo_users.py --create | --list | --remove
This module is never imported by main.py and never runs automatically.
Use only with a disposable/test database, never a live banking database.
"""
import argparse
import secrets
import string
import database as db

DEMO_ACCOUNTS = (
    ("demo_customer", "customer", "Demo Customer"),
    ("demo_staff", "staff", "Demo Security Staff"),
    ("demo_admin", "admin", "Demo Administrator"),
)

def make_password():
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "Demo-" + "".join(secrets.choice(alphabet) for _ in range(14)) + "A7"

def create():
    db.init_db()
    print("\nCreating optional demo accounts in the configured database:")
    for username, role, full_name in DEMO_ACCOUNTS:
        if db.get_user(username):
            print(f"SKIPPED: {username} already exists (password unchanged).")
            continue
        password = make_password()
        ok, message = db.create_user(username, password, role, full_name,
                                      f"{username}@example.invalid", "demo-test-device")
        if ok:
            print(f"\nRole: {role.title()}\nUsername: {username}\nPassword: {password}")
        else:
            print(f"FAILED: {username}: {message}")
    print("\nStore these credentials securely. They are for local testing only.")

def list_accounts():
    db.init_db()
    for username, role, _ in DEMO_ACCOUNTS:
        print(f"{username}: {role if db.get_user(username) else 'not created'}")

def remove():
    db.init_db()
    for username, _, _ in DEMO_ACCOUNTS:
        if db.get_user(username):
            db.delete_user(username)
            print(f"Removed account: {username}")
        else:
            print(f"Not present: {username}")
    print("Historical activity is retained for audit review.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optional SecureBank AI demo account utility")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--create", action="store_true", help="Create missing demo accounts")
    group.add_argument("--list", action="store_true", help="List dedicated demo accounts")
    group.add_argument("--remove", action="store_true", help="Remove dedicated demo accounts")
    args = parser.parse_args()
    if args.create: create()
    elif args.list: list_accounts()
    elif args.remove: remove()

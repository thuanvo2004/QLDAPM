#!/usr/bin/env python3
"""
Utility script for managing migrations without Flask CLI issues
"""

import sys
from flask import Flask
from flask_migrate import Migrate

def get_app():
    """Create Flask app for migration operations"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Duyngo123%40@localhost:3306/job?charset=utf8mb4'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    from app.extensions import db
    from app import models  # Import models
    
    db.init_app(app)
    migrate = Migrate(app, db)
    return app

def show_current():
    """Show current migration"""
    app = get_app()
    with app.app_context():
        from flask_migrate import current
        current()

def create_migration(message="Auto migration"):
    """Create new migration"""
    app = get_app()
    with app.app_context():
        from flask_migrate import migrate
        migrate(message=message)

def apply_migrations():
    """Apply all pending migrations"""
    app = get_app()
    with app.app_context():
        from flask_migrate import upgrade
        upgrade()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python migration_utils.py current    # Show current migration")
        print("  python migration_utils.py migrate 'message'  # Create new migration")
        print("  python migration_utils.py upgrade    # Apply migrations")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'current':
        show_current()
    elif command == 'migrate':
        message = sys.argv[2] if len(sys.argv) > 2 else "Auto migration"
        create_migration(message)
    elif command == 'upgrade':
        apply_migrations()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


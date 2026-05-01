"""
main.py — Application entry point.
Initialises the database, shows the login window, then launches the main window.
"""

import sys
import os

# Ensure the project root is on the Python path regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import initialise_database
from app.ui.styles import apply_theme
from app.ui.login_window import LoginWindow
from app.ui.main_window import MainWindow
import app.auth as auth


def main():
    initialise_database()

    # Show login until the user authenticates or closes the window
    while True:
        login = LoginWindow()
        login.mainloop()
        session = auth.get_session()
        if session is None:
            # User closed the login window without logging in
            sys.exit(0)
        # Launch main application
        app_window = MainWindow(session)
        apply_theme(app_window)
        app_window.mainloop()
        # If we return here the user logged out — loop back to login
        if auth.get_session() is None:
            continue
        break


if __name__ == "__main__":
    main()

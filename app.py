#!/usr/bin/env python3
"""
Azure Web App startup entry point.
This ensures the bot starts correctly on Azure App Service.
"""

import os
import sys
import subprocess

# Set environment for Azure
os.environ.setdefault("PYTHONUNBUFFERED", "1")

if __name__ == "__main__":
    # Start the bot
    try:
        from bot import main
        main()
    except KeyboardInterrupt:
        print("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting bot: {e}")
        sys.exit(1)

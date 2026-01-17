#!/usr/bin/env python3
"""
Azure App Service entry point for ArpadBot.
Azure looks for main.py or app.py by default.
This file ensures the bot starts correctly.
"""

import os
import sys

# Ensure unbuffered output for Azure logging
os.environ.setdefault("PYTHONUNBUFFERED", "1")

if __name__ == "__main__":
    try:
        # Import and start the bot
        from bot import main
        main()
    except KeyboardInterrupt:
        print("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting bot: {e}", file=sys.stderr)
        sys.exit(1)

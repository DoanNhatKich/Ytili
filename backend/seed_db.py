#!/usr/bin/env python3
"""
Database seeding script for Ytili platform
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.dirname(__file__))

from app.core.database import AsyncSessionLocal
from app.core.seed_data import seed_database


async def main():
    """Main seeding function"""
    async with AsyncSessionLocal() as db:
        try:
            await seed_database(db)
        except Exception as e:
            print(f"Error seeding database: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())

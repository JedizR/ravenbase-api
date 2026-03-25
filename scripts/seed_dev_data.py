"""Seed script placeholder. Populated in STORY-002+."""
import asyncio

import structlog


async def main() -> None:
    structlog.get_logger().info("seed.skipped", message="No seed data yet — implement in STORY-002+")


if __name__ == "__main__":
    asyncio.run(main())

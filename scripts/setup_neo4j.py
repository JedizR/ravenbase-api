"""Idempotent Neo4j constraints and indexes setup. Safe to run multiple times."""

import asyncio

from neo4j import AsyncGraphDatabase

from src.core.config import settings

CONSTRAINTS = [
    "CREATE CONSTRAINT user_unique IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
    "CREATE CONSTRAINT profile_unique IF NOT EXISTS FOR (p:SystemProfile) REQUIRE p.profile_id IS UNIQUE",
    "CREATE CONSTRAINT memory_unique IF NOT EXISTS FOR (m:Memory) REQUIRE m.memory_id IS UNIQUE",
    "CREATE CONSTRAINT concept_unique IF NOT EXISTS FOR (c:Concept) REQUIRE (c.tenant_id, c.name) IS UNIQUE",
    "CREATE INDEX concept_name_idx IF NOT EXISTS FOR (c:Concept) ON (c.name)",
]


async def setup_neo4j() -> None:
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )
    try:
        async with driver.session() as session:
            for statement in CONSTRAINTS:
                await session.run(statement)
                name = statement.split("IF NOT EXISTS")[0].strip().split()[-1]
                print(f"Applied: {name}")  # noqa: T201
        print("Neo4j setup complete.")  # noqa: T201
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(setup_neo4j())

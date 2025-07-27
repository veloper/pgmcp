# Scrapy Models: Synchronous psycopg2 Architecture

## Overview
This module provides SQLAlchemy models for Scrapy pipelines. Only synchronous psycopg2 is supported, as Scrapy uses Twisted, which is incompatible with asyncio. Synchronous database drivers are required for safe operation in Scrapy.

## Why Synchronous Only?
- The Twisted reactor manages Scrapy's event loop and does not allow asyncio to run.
- Using async SQLAlchemy or asyncpg will cause runtime errors, deadlocks, or unpredictable behavior.
- psycopg2 is synchronous and does not interact with event loops, making it reliable in this context.

## Model Mirroring
- Models in this module mirror the async models from the main application.
- These models are not managed by Alembic migrations and are not the source of truth.
- Any changes to async models must be manually reflected here to prevent schema drift and runtime errors.

## Risks & Constraints
- Schema drift can occur if async model changes are not manually synced.
- Alembic will not catch mismatches; only runtime errors will reveal problems.
- Model duplication is necessary for stability and compatibility; this is a Python ecosystem limitation, not a workaround.

## Takeaways

This is a necessary evil of wanting to use Scrapy within an Async application.

Two choices: 
  - Struggle, beg, barrow, and steal a way to make Scrapy be callable from within an `asyncio.run(main())`
  - Accept that Scrapy is synchronous, do what we've done here -- minor duplication of models, isolated risk.



# Architecture

AstroMatch is split into processing, similarity engine, global discovery, terrain3d, backend, frontend, shared contracts, and validation. Domain modules communicate through JSON schemas and do not import each other's internals. Current fixtures are explicitly synthetic; NASA ingestion and scientific calibration remain future work.

Ownership: processing (Developer 1), engine (Developer 2), discovery (Developer 3), terrain3d and validation (Developer 4). Frontend and backend are shared integration modules.

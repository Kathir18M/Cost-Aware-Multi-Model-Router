# Infrastructure & Deployment Configuration

This directory contains infrastructure setup, database configurations, container definitions, and deployment scripts for the Cost-Aware Multi-Model Router platform.

## Directory Structure

```
infrastructure/
├── mongodb/
│   └── docker-compose.yml   # Sample local MongoDB 7.0 container config
└── README.md                # Infrastructure documentation
```

## Local MongoDB Setup (Docker)

To run a local MongoDB instance using Docker Compose:

```bash
cd infrastructure/mongodb
docker compose up -d
```

This starts a MongoDB instance accessible at `mongodb://localhost:27017` with database `cost_aware_router`.

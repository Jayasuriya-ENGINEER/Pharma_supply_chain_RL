# Pharma Supply Chain Disruption Environment (PSCE)

## Digital Twin Concept
This environment simulates real-world pharmaceutical logistics including:
- batch-level expiry decay
- cold-chain failures
- multi-warehouse distribution
- transport cost optimization

## Features
- deterministic simulation
- structured RL environment
- multi-region prioritization (ICU vs normal)
- cost vs safety trade-offs

## Tasks
- EASY: stable system
- MEDIUM: supplier delay
- HARD: cold chain + supplier failure


## Advanced Features

- Dynamic inventory rebalancing across warehouses
- Emergency sourcing under supplier failure
- Cold-chain-aware routing decisions
- Expiry-aware batch prioritization

## Key Insight

The system demonstrates how proactive redistribution and adaptive logistics
strategies improve resilience under disruptions in pharma supply chains.


## Intelligent Decision Policy

The agent uses:
- proactive inventory redistribution
- expiry-aware prioritization
- cost-aware warehouse selection
- dynamic demand allocation

This mimics real-world pharmaceutical logistics decision-making under uncertainty.


## Run
uvicorn api.main:app --port 7860

## Baseline
python inference.py
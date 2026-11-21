# Core Prime trajectory and preference dataset v1

Experimental synthetic draft—not validated or approved training data. No real user conversations are included.

## Trajectory format
JSONL records include unique id, domain, scenario, ordered role/text turns, traits and split. Entries contain multi-turn context; held-out records must not be included in training.

## Contrastive preference format
JSONL records include a prompt, preferred and rejected response, preference label, short observable behavioral reason and split. Reasons describe visible behavior, not private chain-of-thought.

## Intended use
- Train character as conversation trajectory, not phrase or adjective imitation.
- Contrast natural character with forced wit, bland compliance, verbosity, contrarianism and caricature.
- Keep holdout entries separate and report leakage checks.
- Treat synthetic authored examples as experimental; measure quality before training.

## Validation
Parse JSONL line by line; IDs unique; roles alternate; trajectory length >=4; pair candidates present; preference label consistent; holdout isolated.
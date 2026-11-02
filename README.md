# Cor Trading AI: ledger witness (public, metadata only)

This repository holds ONE file, `heads.jsonl`: an append-only log with one line per trading session of the simulated Daily AI portfolio. A line contains only: record number, session date, run label,
the ledger's row count, the ledger's head hash, a consistency link to the previous record (`prev_rows`, `prev_head_now`, `prev`) and a timestamp. It contains no holdings, values, decisions, orders,
parameters, logs, credentials or account data. All trading is simulated; no real money and no broker are involved.

Purpose: a copy of the ledger's integrity fingerprint that does not live on the trading server, so a deleted, truncated or rewritten history cannot go unnoticed. The GitHub Action in
`.github/workflows/verify.yml` checks the whole git history of the file on every push and every night (chain, append-only growth, freshness). To verify by hand: clone, then `python3 verify_witness.py`.

A caveat stated plainly: the log attests what the trading server reported; it cannot by itself catch a server that reports false but self-consistent records.

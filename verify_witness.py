import hashlib
import json
import re
from datetime import datetime

GENESIS = "0" * 64
FIELDS = ("v", "seq", "session", "label", "ledger_rows", "ledger_head", "prev_rows", "prev_head_now", "prev", "at")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FILE = "heads.jsonl"
SEEN_FILE = "witness_seen.json"


class WitnessError(Exception):
    pass


class WitnessNetworkError(WitnessError):
    pass


def canon(rec: dict) -> str:
    return json.dumps(rec, sort_keys=True, separators=(",", ":"))


def line_hash(line: str) -> str:
    return hashlib.sha256(line.encode()).hexdigest()


def parse(text: str) -> tuple[list[dict], list[str]]:
    """(records, lines). Raises WitnessError on anything that is not a clean sequence of canonical JSON lines."""
    if text == "":
        return [], []
    if not text.endswith("\n"):
        raise WitnessError("the log does not end with a newline")
    lines = text[:-1].split("\n")
    recs = []
    for i, ln in enumerate(lines, 1):
        try:
            rec = json.loads(ln)
        except ValueError:
            raise WitnessError(f"line {i} is not JSON") from None
        if not isinstance(rec, dict) or canon(rec) != ln:
            raise WitnessError(f"line {i} is not a canonical JSON object")
        recs.append(rec)
    return recs, lines


def verify_chain(text: str) -> list[str]:
    """[] when the whole log is a valid, internally consistent chain; otherwise one sentence per problem (first problems only)."""
    try:
        recs, lines = parse(text)
    except WitnessError as exc:
        return [str(exc)]
    out: list[str] = []
    prev = None
    for i, r in enumerate(recs):
        n = i + 1
        if tuple(sorted(r)) != tuple(sorted(FIELDS)):
            out.append(f"record {n}: wrong set of fields")
            break
        ok_types = (r["v"] == 1 and isinstance(r["seq"], int) and isinstance(r["ledger_rows"], int) and isinstance(r["prev_rows"], int) and isinstance(r["session"], str) and DATE.match(r["session"])
                    and all(isinstance(r[k], str) and HEX64.match(r[k]) for k in ("ledger_head", "prev_head_now", "prev")) and isinstance(r["label"], str) and isinstance(r["at"], str))
        if not ok_types:
            out.append(f"record {n}: invalid field types or values")
            break
        try:
            datetime.fromisoformat(r["at"])
        except ValueError:
            out.append(f"record {n}: bad timestamp")
            break
        if r["seq"] != n:
            out.append(f"record {n}: record number is {r['seq']}")
        exp_prev = GENESIS if prev is None else line_hash(lines[i - 1])
        if r["prev"] != exp_prev:
            out.append(f"record {n}: link to the previous record is broken (an earlier record was edited, removed or reordered)")
        if r["ledger_rows"] < 1:
            out.append(f"record {n}: row count below 1")
        if prev is not None:
            if r["ledger_rows"] <= prev["ledger_rows"]:
                out.append(f"record {n}: ledger rows did not grow ({prev['ledger_rows']} -> {r['ledger_rows']}): history was truncated or replayed")
            if r["session"] <= prev["session"]:
                out.append(f"record {n}: session {r['session']} is not after {prev['session']}")
            if r["prev_rows"] != prev["ledger_rows"] or r["prev_head_now"] != prev["ledger_head"]:
                out.append(f"record {n}: the ledger no longer holds the head witnessed in record {n - 1} at row {prev['ledger_rows']} (history was rewritten)")
        else:
            if r["prev_rows"] != 0 or r["prev_head_now"] != GENESIS:
                out.append("record 1: must start from nothing")
        if len(out) >= 5:
            break
        prev = r
    return out

import os, subprocess, sys
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

LAUNCH = "2026-11-04"
SESSIONS = ['2026-10-05', '2026-10-06', '2026-10-07', '2026-10-08', '2026-10-09', '2026-10-12', '2026-10-13', '2026-10-14', '2026-10-15', '2026-10-16', '2026-10-19', '2026-10-20', '2026-10-21', '2026-10-22', '2026-10-23', '2026-10-26', '2026-10-27', '2026-10-28', '2026-10-29', '2026-10-30', '2026-11-02', '2026-11-03', '2026-11-04', '2026-11-05', '2026-11-06', '2026-11-09', '2026-11-10', '2026-11-11', '2026-11-12', '2026-11-13', '2026-11-16', '2026-11-17', '2026-11-18', '2026-11-19', '2026-11-20', '2026-11-23', '2026-11-24', '2026-11-25', '2026-11-27', '2026-11-30', '2026-12-01', '2026-12-02', '2026-12-03', '2026-12-04', '2026-12-07', '2026-12-08', '2026-12-09', '2026-12-10', '2026-12-11', '2026-12-14', '2026-12-15', '2026-12-16', '2026-12-17', '2026-12-18', '2026-12-21', '2026-12-22', '2026-12-23', '2026-12-24', '2026-12-28', '2026-12-29', '2026-12-30', '2026-12-31', '2027-01-04', '2027-01-05', '2027-01-06', '2027-01-07', '2027-01-08', '2027-01-11', '2027-01-12', '2027-01-13', '2027-01-14', '2027-01-15', '2027-01-19', '2027-01-20', '2027-01-21', '2027-01-22', '2027-01-25', '2027-01-26', '2027-01-27', '2027-01-28', '2027-01-29', '2027-02-01', '2027-02-02', '2027-02-03', '2027-02-04', '2027-02-05', '2027-02-08', '2027-02-09', '2027-02-10', '2027-02-11', '2027-02-12', '2027-02-16', '2027-02-17', '2027-02-18', '2027-02-19', '2027-02-22', '2027-02-23', '2027-02-24', '2027-02-25', '2027-02-26', '2027-03-01', '2027-03-02', '2027-03-03', '2027-03-04', '2027-03-05', '2027-03-08', '2027-03-09', '2027-03-10', '2027-03-11', '2027-03-12', '2027-03-15', '2027-03-16', '2027-03-17', '2027-03-18', '2027-03-19', '2027-03-22', '2027-03-23', '2027-03-24', '2027-03-25', '2027-03-29', '2027-03-30', '2027-03-31', '2027-04-01', '2027-04-02', '2027-04-05', '2027-04-06', '2027-04-07', '2027-04-08', '2027-04-09', '2027-04-12', '2027-04-13', '2027-04-14', '2027-04-15', '2027-04-16', '2027-04-19', '2027-04-20', '2027-04-21', '2027-04-22', '2027-04-23', '2027-04-26', '2027-04-27', '2027-04-28', '2027-04-29', '2027-04-30', '2027-05-03', '2027-05-04', '2027-05-05', '2027-05-06', '2027-05-07', '2027-05-10', '2027-05-11', '2027-05-12', '2027-05-13', '2027-05-14', '2027-05-17', '2027-05-18', '2027-05-19', '2027-05-20', '2027-05-21', '2027-05-24', '2027-05-25', '2027-05-26', '2027-05-27', '2027-05-28', '2027-06-01', '2027-06-02', '2027-06-03', '2027-06-04', '2027-06-07', '2027-06-08', '2027-06-09', '2027-06-10', '2027-06-11', '2027-06-14', '2027-06-15', '2027-06-16', '2027-06-17', '2027-06-21', '2027-06-22', '2027-06-23', '2027-06-24', '2027-06-25', '2027-06-28', '2027-06-29', '2027-06-30', '2027-07-01', '2027-07-02', '2027-07-06', '2027-07-07', '2027-07-08', '2027-07-09', '2027-07-12', '2027-07-13', '2027-07-14', '2027-07-15', '2027-07-16', '2027-07-19', '2027-07-20', '2027-07-21', '2027-07-22', '2027-07-23', '2027-07-26', '2027-07-27', '2027-07-28', '2027-07-29', '2027-07-30', '2027-08-02', '2027-08-03', '2027-08-04', '2027-08-05', '2027-08-06', '2027-08-09', '2027-08-10', '2027-08-11', '2027-08-12', '2027-08-13', '2027-08-16', '2027-08-17', '2027-08-18', '2027-08-19', '2027-08-20', '2027-08-23', '2027-08-24', '2027-08-25', '2027-08-26', '2027-08-27', '2027-08-30', '2027-08-31', '2027-09-01', '2027-09-02', '2027-09-03', '2027-09-07', '2027-09-08', '2027-09-09', '2027-09-10', '2027-09-13', '2027-09-14', '2027-09-15', '2027-09-16', '2027-09-17', '2027-09-20', '2027-09-21', '2027-09-22', '2027-09-23', '2027-09-24', '2027-09-27', '2027-09-28', '2027-09-29', '2027-09-30', '2027-10-01', '2027-10-04', '2027-10-05', '2027-10-06', '2027-10-07', '2027-10-08', '2027-10-11', '2027-10-12', '2027-10-13', '2027-10-14', '2027-10-15', '2027-10-18', '2027-10-19', '2027-10-20', '2027-10-21', '2027-10-22', '2027-10-25', '2027-10-26', '2027-10-27', '2027-10-28', '2027-10-29', '2027-11-01', '2027-11-02', '2027-11-03', '2027-11-04', '2027-11-05', '2027-11-08', '2027-11-09', '2027-11-10', '2027-11-11', '2027-11-12', '2027-11-15', '2027-11-16', '2027-11-17', '2027-11-18', '2027-11-19', '2027-11-22', '2027-11-23', '2027-11-24', '2027-11-26', '2027-11-29', '2027-11-30', '2027-12-01', '2027-12-02', '2027-12-03', '2027-12-06', '2027-12-07', '2027-12-08', '2027-12-09', '2027-12-10', '2027-12-13', '2027-12-14', '2027-12-15', '2027-12-16', '2027-12-17', '2027-12-20', '2027-12-21', '2027-12-22', '2027-12-23', '2027-12-27', '2027-12-28', '2027-12-29', '2027-12-30', '2027-12-31', '2028-01-03', '2028-01-04', '2028-01-05', '2028-01-06', '2028-01-07', '2028-01-10', '2028-01-11', '2028-01-12', '2028-01-13', '2028-01-14', '2028-01-18', '2028-01-19', '2028-01-20', '2028-01-21', '2028-01-24', '2028-01-25', '2028-01-26', '2028-01-27', '2028-01-28', '2028-01-31', '2028-02-01', '2028-02-02', '2028-02-03', '2028-02-04', '2028-02-07', '2028-02-08', '2028-02-09', '2028-02-10', '2028-02-11', '2028-02-14', '2028-02-15', '2028-02-16', '2028-02-17', '2028-02-18', '2028-02-22', '2028-02-23', '2028-02-24', '2028-02-25', '2028-02-28', '2028-02-29', '2028-03-01', '2028-03-02', '2028-03-03', '2028-03-06', '2028-03-07', '2028-03-08', '2028-03-09', '2028-03-10', '2028-03-13', '2028-03-14', '2028-03-15', '2028-03-16', '2028-03-17', '2028-03-20', '2028-03-21', '2028-03-22', '2028-03-23', '2028-03-24', '2028-03-27', '2028-03-28', '2028-03-29', '2028-03-30', '2028-03-31', '2028-04-03', '2028-04-04', '2028-04-05', '2028-04-06', '2028-04-07', '2028-04-10', '2028-04-11', '2028-04-12', '2028-04-13', '2028-04-17', '2028-04-18', '2028-04-19', '2028-04-20', '2028-04-21', '2028-04-24', '2028-04-25', '2028-04-26', '2028-04-27', '2028-04-28', '2028-05-01', '2028-05-02', '2028-05-03', '2028-05-04', '2028-05-05', '2028-05-08', '2028-05-09', '2028-05-10', '2028-05-11', '2028-05-12', '2028-05-15', '2028-05-16', '2028-05-17', '2028-05-18', '2028-05-19', '2028-05-22', '2028-05-23', '2028-05-24', '2028-05-25', '2028-05-26', '2028-05-30', '2028-05-31', '2028-06-01', '2028-06-02', '2028-06-05', '2028-06-06', '2028-06-07', '2028-06-08', '2028-06-09', '2028-06-12', '2028-06-13', '2028-06-14', '2028-06-15', '2028-06-16', '2028-06-20', '2028-06-21', '2028-06-22', '2028-06-23', '2028-06-26', '2028-06-27', '2028-06-28', '2028-06-29', '2028-06-30', '2028-07-03', '2028-07-05', '2028-07-06', '2028-07-07', '2028-07-10', '2028-07-11', '2028-07-12', '2028-07-13', '2028-07-14', '2028-07-17', '2028-07-18', '2028-07-19', '2028-07-20', '2028-07-21', '2028-07-24', '2028-07-25', '2028-07-26', '2028-07-27', '2028-07-28', '2028-07-31', '2028-08-01', '2028-08-02', '2028-08-03', '2028-08-04', '2028-08-07', '2028-08-08', '2028-08-09', '2028-08-10', '2028-08-11', '2028-08-14', '2028-08-15', '2028-08-16', '2028-08-17', '2028-08-18', '2028-08-21', '2028-08-22', '2028-08-23', '2028-08-24', '2028-08-25', '2028-08-28', '2028-08-29', '2028-08-30', '2028-08-31', '2028-09-01', '2028-09-05', '2028-09-06', '2028-09-07', '2028-09-08', '2028-09-11', '2028-09-12', '2028-09-13', '2028-09-14', '2028-09-15', '2028-09-18', '2028-09-19', '2028-09-20', '2028-09-21', '2028-09-22', '2028-09-25', '2028-09-26', '2028-09-27', '2028-09-28', '2028-09-29', '2028-10-02', '2028-10-03', '2028-10-04', '2028-10-05', '2028-10-06', '2028-10-09', '2028-10-10', '2028-10-11', '2028-10-12', '2028-10-13', '2028-10-16', '2028-10-17', '2028-10-18', '2028-10-19', '2028-10-20', '2028-10-23', '2028-10-24', '2028-10-25', '2028-10-26', '2028-10-27', '2028-10-30', '2028-10-31', '2028-11-01', '2028-11-02', '2028-11-03', '2028-11-06', '2028-11-07', '2028-11-08', '2028-11-09', '2028-11-10', '2028-11-13', '2028-11-14', '2028-11-15', '2028-11-16', '2028-11-17', '2028-11-20', '2028-11-21', '2028-11-22', '2028-11-24', '2028-11-27', '2028-11-28', '2028-11-29', '2028-11-30', '2028-12-01', '2028-12-04', '2028-12-05', '2028-12-06', '2028-12-07', '2028-12-08', '2028-12-11', '2028-12-12', '2028-12-13', '2028-12-14', '2028-12-15', '2028-12-18', '2028-12-19', '2028-12-20', '2028-12-21', '2028-12-22', '2028-12-26', '2028-12-27', '2028-12-28', '2028-12-29']
NY = ZoneInfo("America/New_York")
EVENING_END = (22, 45)
NOW = datetime.fromisoformat(os.environ["WITNESS_TEST_NOW"]) if os.environ.get("WITNESS_TEST_NOW") else datetime.now(timezone.utc)      # the override exists for tests only; GitHub runners never set it


def git(*a):
    r = subprocess.run(["git", *a], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("git " + " ".join(a) + ": " + r.stderr.strip()[:200])
    return r.stdout


def expected_session(now):
    """The latest NYSE session whose evening window (22:45 ET that day) has ended at `now`."""
    ny = now.astimezone(NY)
    best = None
    for s in SESSIONS:
        d = date.fromisoformat(s)
        if ny >= datetime(d.year, d.month, d.day, EVENING_END[0], EVENING_END[1], tzinfo=NY):
            best = s
    return best


def main():
    problems = []
    commits = [c for c in git("log", "--format=%H", "--reverse", "--", FILE).split() if c]
    versions = []
    for c in commits:
        try:
            versions.append((c, git("show", f"{c}:{FILE}")))
        except RuntimeError:
            problems.append(f"{FILE} is missing in commit {c[:10]} (deleted?)")
    prev_text = ""
    for c, text in versions:
        for p in verify_chain(text):
            problems.append(f"commit {c[:10]}: {p}")
        if not text.startswith(prev_text) or len(text) < len(prev_text):
            problems.append(f"commit {c[:10]}: the log is not an append-only extension of the previous version (a record was edited, removed or truncated)")
        prev_text = text
    head_text = ""
    try:
        head_text = open(FILE).read()
    except FileNotFoundError:
        if commits:
            problems.append(f"{FILE} is missing from the current tree")
    if commits and head_text != prev_text:
        problems.append("the current file differs from its latest committed version")
    recs, _ = parse(head_text) if not verify_chain(head_text) else ([], [])
    if recs:
        if len({r["label"] for r in recs}) != 1:
            problems.append("the run label changed inside the log")
        ats = [datetime.fromisoformat(r["at"]) for r in recs]
        if any(b < a for a, b in zip(ats, ats[1:])) or ats[-1] > NOW + timedelta(hours=1):
            problems.append("record timestamps go backwards or lie in the future")
    exp = expected_session(NOW)
    last = recs[-1]["session"] if recs else None
    if exp and exp >= LAUNCH and (last is None or last < exp):
        problems.append(f"STALE: the latest NYSE session is {exp} and the witness log is at {last or 'nothing'} (the agent did not witness it by 22:45 ET)")
    print(f"records={len(recs)} commits={len(commits)} last_session={last} expected_session={exp}")
    if problems:
        print("WITNESS VERIFICATION FAILED:")
        for p in problems:
            print(" -", p)
        sys.exit(1)
    print("witness verification OK")


main()

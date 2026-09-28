"""Hard budget guard for every call that spends Make.com operations (DhammaLab rollback / legacy only).

Policy (Nat, 28 Sep 2026)
- DhammaLab Make budget = 0 operations per day by default. Normal production never calls Make.
- No automatic fallback to Make anywhere.
- A rollback needs ALL of: an open rollback session (reason + numeric max operations + expiry, created by hand)
  AND env DHAMMALAB_MAKE_ROLLBACK=1 in the process that calls Make.
- Every call is counted in a local ledger; a call that would exceed the session cap is refused before it is sent.

CLI
  python3 make_guard.py open --reason "why" --max-ops 30 [--hours 4] [--approved-by Nat]
  python3 make_guard.py status
  python3 make_guard.py close
"""
import os, sys, json, time, fcntl, datetime, argparse

DIR = os.path.expanduser('~/.config/dhammalab')
SESSION = os.path.join(DIR, 'make_session.json')
LEDGER = os.path.join(DIR, 'make_calls.jsonl')
# Make operations consumed per webhook call of scenario 4942061 (webhook + module(s) + response), conservative
OPS_PER_CALL = {'tts': 3, 'tts rollback': 3, 'image': 3, 'video': 3, 'video_get': 4, 'transcribe': 5, 'transcribe (rollback)': 5}
DEFAULT_OPS = 5

class MakeGateClosed(RuntimeError):
    pass

def _now():
    return datetime.datetime.utcnow()

def _load():
    if not os.path.exists(SESSION): return None
    s = json.load(open(SESSION))
    if _now().isoformat() > s['expires_utc']: return None
    return s

def make_endpoint(purpose=''):
    """Return (hook, key) for exactly one Make call, or raise MakeGateClosed. Counts the call before returning."""
    if os.environ.get('DHAMMALAB_MAKE_ROLLBACK') != '1':
        raise MakeGateClosed(f'Make call blocked ({purpose}): DhammaLab Make budget is 0 ops/day. '
                             'Rollback needs an open session (make_guard.py open ...) and DHAMMALAB_MAKE_ROLLBACK=1.')
    ops = OPS_PER_CALL.get(purpose, DEFAULT_OPS)
    os.makedirs(DIR, exist_ok=True)
    with open(SESSION + '.lock', 'w') as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        s = _load()
        if not s:
            raise MakeGateClosed(f'Make call blocked ({purpose}): no open, unexpired rollback session.')
        if s['used_ops'] + ops > s['max_ops']:
            raise MakeGateClosed(f'Make call blocked ({purpose}): would use {s["used_ops"] + ops} of {s["max_ops"]} ops allowed '
                                 f'for rollback session {s["id"]} ({s["reason"]}).')
        s['used_ops'] += ops; s['calls'] += 1
        json.dump(s, open(SESSION, 'w'), ensure_ascii=False, indent=1)
    with open(LEDGER, 'a') as f:
        f.write(json.dumps({'t': _now().isoformat() + 'Z', 'session': s['id'], 'purpose': purpose, 'ops': ops,
                            'used_ops': s['used_ops'], 'max_ops': s['max_ops']}, ensure_ascii=False) + '\n')
    hook = open('/home/claude/lab/.tts_hook').read().strip()
    key = open('/home/claude/lab/.tts_key').read().strip()
    return hook, key

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=['open', 'status', 'close'])
    ap.add_argument('--reason'); ap.add_argument('--max-ops', type=int); ap.add_argument('--hours', type=float, default=4)
    ap.add_argument('--approved-by', default='')
    a = ap.parse_args()
    os.makedirs(DIR, exist_ok=True)
    if a.cmd == 'open':
        if not a.reason or not a.max_ops or a.max_ops <= 0:
            sys.exit('open needs --reason and a positive --max-ops')
        s = {'id': _now().strftime('rb%Y%m%d%H%M%S'), 'reason': a.reason, 'approved_by': a.approved_by,
             'max_ops': a.max_ops, 'used_ops': 0, 'calls': 0, 'opened_utc': _now().isoformat(),
             'expires_utc': (_now() + datetime.timedelta(hours=a.hours)).isoformat()}
        json.dump(s, open(SESSION, 'w'), ensure_ascii=False, indent=1); print(json.dumps(s, ensure_ascii=False))
    elif a.cmd == 'status':
        s = _load(); print(json.dumps(s, ensure_ascii=False) if s else 'no open rollback session (Make budget = 0 ops)')
    else:
        if os.path.exists(SESSION): os.remove(SESSION)
        print('rollback session closed (Make budget = 0 ops)')

if __name__ == '__main__':
    main()

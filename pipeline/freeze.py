"""Refuse to write into frozen production-candidate folders (see /home/claude/lab/FROZEN.json).
Override only for a real QC issue: DHAMMALAB_UNFREEZE=1."""
import os, sys
FROZEN_DIRS = ('exp01/v4', 'exp03/v2')
def check(argv=None):
    if os.environ.get('DHAMMALAB_UNFREEZE') == '1':
        return
    for a in (argv or sys.argv[1:]):
        p = os.path.abspath(a)
        if any(('/home/claude/lab/' + d) in p for d in FROZEN_DIRS):
            sys.exit(f'FROZEN: {a} belongs to a production candidate (FROZEN.json). Set DHAMMALAB_UNFREEZE=1 only for a real QC issue.')

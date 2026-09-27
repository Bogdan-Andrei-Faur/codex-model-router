"""Exact, bounded command allowlist for the isolated approval probe."""
import shlex


def exact_approval_command(command, marker):
    try:
        words = shlex.split(command)
        if len(words) == 3 and words[0] in ('/bin/zsh', '/bin/bash', '/bin/sh') and words[1] in ('-lc', '-c'):
            words = shlex.split(words[2])
        return words == ['printf', 'APPROVED', '>', marker]
    except (ValueError, TypeError):
        return False

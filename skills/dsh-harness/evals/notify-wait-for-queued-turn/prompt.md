---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---

hand this to the harness but dont block on it: in this folder, start a dsh session named notify-eval and queue a task telling it to run `sleep 8` and then reply exactly NOTIFY-EVAL-OK. then wait until dsh says its done (no polling loops please) and tell me what it replied. close the session after.

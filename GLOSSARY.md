# dsh-claude-bridge

Connects Claude Code and DeepSeek Harness (dsh) as programs on one machine: each can hand work to the other and learn when the other is done.

## Language

### What gets installed

**dsh side**:
The pieces that serve dsh and scripts: the plugin in each profile, the provider and turn events, acpx, and the wait and lookup commands. Installed whenever dsh is present.
_Avoid_: core, base install

**Claude side**:
The pieces that only make sense with Claude Code: the skill, the MCP registrations, the Stop hook, the channel and its launcher, and the Claude-login helper. Installed only when Claude Code is found.
_Avoid_: Claude Code part, client side

### Delegation

**Provider helper**:
The Claude Code helper inside dsh that runs on the model provider configured for the bridge. Needs no Claude Code installation.
_Avoid_: GLM helper, subagent

**Claude-login helper**:
The Claude Code helper inside dsh that runs on Claude with the user's Claude Code login.
_Avoid_: Claude helper, real Claude

### Signals

**Done signal**:
One line recorded when a turn ends, either a dsh turn or a Claude Code turn, that another program can wait on.
_Avoid_: notification, turn event (when meaning both sides), callback

**Channel**:
dsh pushing a message into a Claude Code session that is already running, so the session reads it at once, even while idle.
_Avoid_: notify, ping, cross-session message (that is Claude Code's own session-to-session messaging)

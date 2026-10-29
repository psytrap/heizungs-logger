# Ticket-First Workflow Rule

## 1. Direct Answers vs. Ticket-First Scope

### A. Immediate Execution / Direct Answers (No Ticket Required)
- **Scope:** General questions, quick code or documentation lookups, repository status checks, log/data inspections, SSH diagnostics, file searches, and short analyses.
- **Action:** Execute immediately and answer the user directly in chat. Do not create an unnecessary ticket for straightforward questions or short analytical lookups.

### B. Ticket Creation Only by Default (Requires Ticket)
- **Scope:**
  - Source code modifications, bug fixes, features, or refactorings.
  - Structural or multi-file documentation changes.
  - Changes to the live Raspberry Pi deployment (`/home/ubuntu/heizungs_logger`, systemd units, log layout).
  - Large, complex architectural investigations requiring an extensive research report or spike.
- **Rule:** Whenever the user requests a change, reports a bug, suggests a feature, or poses a large analytical investigation, the AI agent **MUST ONLY** create a structured ticket in `tickets/open/` without taking unprompted implementation or execution actions.
- **Enforcement:**
  - Do **NOT** modify codebase files, documentation, or configuration without an explicit ticket execution command.
  - Do **NOT** run builds, refactors, deployments, or restarts on the Pi unsolicited.
  - Create the ticket adhering strictly to the repository Ticket Protocol format (`# Ticket NNN: ...` / `T-NNN`), including Description, Criteria (`- [ ]`), and Execution Notes placeholder.
  - After creating the ticket, immediately report the created ticket path and stop.

## 2. 🧭 Explicit Execution Trigger, Pre-Dispatch Evaluation & Subagent Delegation

### A. Explicit Execution Trigger
- **Rule:** The primary/root conversational agent acts as an architectural coordinator and dispatcher. It may **ONLY** initiate implementation, code changes, or documentation updates when the user explicitly commands:
  - `"Execute ticket NNN"`
  - `"Work on ticket NNN"`
  - Or provides equivalent explicit instruction targeting an existing ticket.
- **Subagent Delegation Invariant:**
  - The root coordinator agent does **NOT** execute ticket implementation directly in the root conversation session.
  - Instead, the coordinator evaluates ticket complexity and delegates execution to one or more autonomous subagents.

### B. Pre-Dispatch Evaluation & Concurrency Sizing
Prior to launching execution, the coordinator agent must inspect ticket scope, dependencies, and touched files to determine the optimal execution topology:
1. 🔵 **Single-Subagent Execution (Default / Linear):**
   - **Fit:** Sized for localized, cohesive, or sequential tasks (e.g., single module edits, localized bug fixes, documentation-only updates).
   - **Lifecycle:** A single autonomous subagent encapsulates the full 7-step lifecycle end-to-end and reports back completion notes.
2. 🟣 **Multi-Subagent Execution (Parallel / Specialized):**
   - **Fit:** Sized for multi-faceted tickets with decoupled, non-overlapping concerns.
   - **Topologies:**
     - *Implementation + Independent Verification:* Subagent A implements source changes in `src/`, while Subagent B builds replay fixtures and verification against recorded hardware traces.
     - *Orthogonal Module Decomposition:* Subagents concurrently modify non-overlapping modules (e.g., Subagent A edits `src/heizungslogger/store.py`, Subagent B edits `src/heizungslogger/display.py`).
     - *Code + Documentation Split:* Subagent A modifies codebase and tests, while Subagent B synchronizes architecture and operations documentation.

### C. Coordinator Synthesis & Integration Role
When multi-subagent execution is chosen, the root coordinator agent orchestrates the lifecycle:
- 📋 **Work Packaging:** Decomposes the ticket into discrete, non-overlapping work packages with clear boundaries.
- 🔄 **Progress Tracking & Synthesis:** Receives completion reports from each worker subagent and integrates outputs.
- 🛡️ **Conflict Resolution:** Reconciles any working directory or merge collisions.
- 🧪 **Unified Gate Verification:** Runs complete verification gates (`python -m pytest && python -m ruff check .`) across the integrated result before transitioning the ticket to `tickets/done/` and committing.

### D. Enforcement (7-Step Ticket Execution Protocol)
When dispatched to execute a ticket (or when synthesized by the coordinator):
1. 🟡 **Activate ticket** in `tickets/open/` and set `Status: In Progress` in ticket and `tickets/INDEX.md`.
2. 🔍 **Review criteria** and inspect scoped files.
3. 🛠️ **Implement changes** with clean, minimal edits within scope.
4. 🧪 **Run test suites** (`python -m pytest && python -m ruff check .`) to ensure zero regressions.
5. 📝 **Populate `## Execution Notes`** and check off verified criteria (`[x]`).
6. ✅ **Transition ticket** to `tickets/done/` with `Status: Done`, updating `tickets/INDEX.md` and `tickets/DONE.md`.
7. 💾 **Stage changes** in git working tree and commit locally per project policy.

## 3. 🖥️ Live Deployment Boundary

- **Rule:** The Raspberry Pi (`heizungs-logger`, `ubuntu@192.168.2.123`) is production hardware that is actively collecting data.
- **Enforcement:**
  - `git commit` and `git push` are **not** deployment. No automated deploy step may be added.
  - Installing, restarting `heizungs_logger.service`, stopping the legacy logger, or writing to `/home/ubuntu/heizungs_logger_logs` requires explicit maintainer authorization in the current conversation.
  - The serial port `/dev/ttyUSB0` is exclusive: two readers cannot run concurrently. Any switchover must be covered by a ticket with a documented rollback.

## 4. 🎯 Backlog Ordering
- **Rule:** Tickets carry no phase or tier label. The backlog is one flat list in `tickets/open/`, ordered by priority (`P0` → `High` → `Normal` → `Low`) and then ascending ticket number.
- **Enforcement:** Do not introduce phase, tier, or milestone fields into ticket headers or index tables. Ordering is a reading aid, not a sequencing commitment.

## 5. ✂️ Output Budget
- **Rule:** Write in atomic units, one artefact per tool call, and keep chat narration to a single sentence per group.
- **Enforcement:** See [`chunked-execution.md`](chunked-execution.md). Mandatory for models with a small `max_output_tokens` (the DeepSeek Flash profiles) and recommended for all others.

## 6. 📅 Output Limit Reevaluation
- **Rule:** Re-check the agent model's output budget against current technology every 6 months; next due **2027-04-29**.
- **Enforcement:** See [`output-limit-reevaluation.md`](output-limit-reevaluation.md). It is a settings change, not a ticket.

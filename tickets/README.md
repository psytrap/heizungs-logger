# 📜 Ticket Protocol & Development Workflow

This document codifies the ticket lifecycle and development workflow for the **heizungslogger** project.

## 0. 🛡️ The "Ticket-Only by Default" Golden Rule

> [!IMPORTANT]
> **Golden Rule for Contributors & AI Agents:**
> 1. **Immediate Execution / Direct Answers (No Ticket Required):** Questions, quick code or documentation lookups, repository status checks, log inspections, SSH diagnostics, file searches, and short analyses are answered immediately in chat.
> 2. **Ticket Creation Only by Default (Requires Ticket):** Whenever a user or contributor requests code modifications, bug fixes, refactorings, documentation structural changes, live-deployment changes, or larger investigations requiring an extensive research report or architectural spike:
>    - **Default Action:** The contributor or AI agent **MUST ONLY create a ticket** in `tickets/open/` documenting the request.
>    - **Zero Unsolicited Execution:** Do **NOT** modify codebase files, documentation, or run unprompted execution tasks unless the user explicitly commands:
>      - *"Execute ticket NNN"*
>      - *"Work on ticket NNN"*
>      - Or provides equivalent explicit authorization targeting a specific ticket.

---

## 1. 📂 Directory-Based State Machine & Overviews

All project tasks, bug fixes, refactorings, and hardware initiatives are tracked as individual Markdown ticket files located in the `tickets/` directory hierarchy, with dedicated overview dashboards:

* 📋 **[tickets/INDEX.md](INDEX.md)** – Real-time index and prioritized backlog dashboard (active in-progress tickets + priority-sorted backlog items in `tickets/open/`).
* ✅ **[tickets/DONE.md](DONE.md)** – Complete historical register of all completed and archived tasks (`tickets/done/`).

```
tickets/
├── INDEX.md       # Live index of active and prioritized open tickets
├── DONE.md        # Historical archive register of completed tickets
├── open/          # All active in-progress and prioritized backlog tickets (T-NNN-slug.md)
└── done/          # Completed and verified tickets with execution notes (T-NNN-slug.md)
```

Tickets remain at a stable file path inside `tickets/open/` during development—preventing broken markdown links. State transitions between backlog and in-progress are tracked via header metadata (`Status: Backlog` → `Status: In Progress`). Upon verified completion, tickets are transitioned to `tickets/done/` via Git directory moves (`git mv`).

---

## 2. ⚙️ The 7-Step Ticket Protocol

### 2.1 🧭 Coordinator Pre-Dispatch Evaluation & Concurrency Sizing
The primary/root AI agent acts as an architectural coordinator, dispatcher, and reviewer. When explicitly authorized to work on a ticket (e.g., *"execute ticket T-019"*), the coordinator agent does **not** modify codebase files directly in the root conversation session. Instead, it performs a mandatory **Pre-Dispatch Evaluation** across ticket scope, dependencies, and touched files to size the execution topology:

1. 🔵 **Single-Subagent Execution (Default / Linear):**
   - **Fit:** Sized for localized, cohesive, or sequential tasks (e.g., a single module edit, a focused bug fix, a documentation-only update).
   - **Topology:** A single autonomous subagent encapsulates the full 7-step lifecycle from ticket activation to local git commit, reporting completion back to the coordinator.
2. 🟣 **Multi-Subagent Execution (Parallel / Specialized):**
   - **Fit:** Sized for multi-faceted tickets with decoupled, non-overlapping concerns.
   - **Topology Patterns:**
     - *Implementation + Independent Verification:* Subagent A implements source changes, while Subagent B builds replay fixtures from recorded hardware traces.
     - *Orthogonal Module Decomposition:* Multiple subagents concurrently edit non-overlapping files.
     - *Code + Documentation Split:* Subagent A performs source implementation and unit testing, while Subagent B concurrently updates architecture and operations documentation.

### 2.2 🔄 Coordinator Synthesis & Integration
In a multi-subagent execution topology, the root coordinator agent orchestrates the lifecycle and serves as the synthesizing integrator:
- 📋 **Decomposition & Work Packaging:** Partitions the ticket into discrete, bounded sub-tasks with explicit file boundaries to avoid concurrent edit conflicts.
- 📬 **Progress Coordination:** Receives intermediate completion reports from each worker subagent.
- 🛡️ **Conflict Reconciliation:** Resolves any merge collisions or working directory integration inconsistencies.
- 🧪 **Unified Quality Gates:** Runs the complete verification suite across the consolidated working tree before transitioning the ticket to `tickets/done/`.

### 2.3 📋 Execution Steps (The 7-Step Lifecycle)
When dispatched to execute a ticket:

1. 🟡 **Activate ticket in open directory:**
   Open the ticket in `tickets/open/T-NNN-<slug>.md`, set `- **Status:** In Progress` in the header, and update [**`tickets/INDEX.md`**](INDEX.md) to reflect the active in-progress state. *(No file move is needed during active work, keeping all cross-references stable.)*
2. 🔍 **Read ticket criteria and inspect scoped files:**
   Read the ticket in detail, focusing strictly on its specified criteria and inspecting only the files relevant to that scope.
3. 🛠️ **Implement changes within scope:**
   Implement code and documentation modifications strictly within the specified boundary. Avoid out-of-scope refactorings.
4. 🧪 **Run project tests and linters:**
   ```bash
   python -m pytest && python -m ruff check .
   ```
5. 📝 **Append Execution Notes:**
   Append a concise execution summary, rationale, and test outputs under `## Execution Notes` in the ticket file, and check off all verified criteria (`[x]`).
6. ✅ **Move to done:**
   ```bash
   git mv tickets/open/T-NNN-<slug>.md tickets/done/T-NNN-<slug>.md
   ```
   Set `- **Status:** Done` in the ticket header, remove the ticket from active listings in [**`tickets/INDEX.md`**](INDEX.md), and add its entry to [**`tickets/DONE.md`**](DONE.md).
7. 💾 **Commit changes:**
   ```bash
   git commit -m "feat(scope): resolve T-NNN - <brief title>"
   ```

> [!IMPORTANT]
> **Zero Deployment Automation & Commit Boundary Policy:**
> Step 7 (`git commit`) commits locally. Automated `git push`, tagging, deployment to the Pi, or restarting `heizungs_logger.service` are strictly manual and require explicit maintainer authorization and human sign-off.

---

## 3. 📋 Standard Ticket File Template

Every ticket file follows a standardized structure:

```markdown
# Ticket NNN: <Descriptive Title>

- **Status:** Open | Backlog | In Progress | Done
- **Priority:** P0 | High | Normal | Low
- **Scope & Relevant Files:**
  - `path/to/primary_file.py`
  - `tests/test_file.py`

---

## Description & Context
<Context explaining why this ticket exists, the problem statement, user story, or background findings.>

---

## Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] All test suites passing (`python -m pytest`)
- [ ] Zero Ruff errors or warnings (`python -m ruff check .`)

---

## Execution Notes
<!-- Populated during Step 5 of the Ticket Protocol -->
```

---

## 4. 🏷️ Ticket Naming & Numbering Rules

- **Numbering:** Zero-padded 3-digit integer (`001`, `002`, ..., `999`).
- **Filename:** `T-NNN-kebab-case-slug.md` (e.g. `T-005-monotonic-scheduler.md`).
- **Identifier:** `T-NNN` (canonical ticket identifier notation).
- **Unique Sequence:** Ticket numbers are monotonically increasing and never reused.
- **Traceability:** Related tickets, commits, or PRs are cross-referenced in ticket descriptions to maintain clear architectural lineage.

---

## 5. 🎯 Backlog Ordering

Tickets carry no phase or tier label. The backlog is a single flat list (`tickets/open/`), and [**`tickets/INDEX.md`**](INDEX.md) sorts it by:

1. **Priority:** `P0` → `High` → `Normal` → `Low`
2. **Ticket Number:** Monotonically ascending numerical identifier (`T-NNN`)

Ordering is a reading aid, not a commitment. Any ticket may be executed at any time when explicitly authorized.

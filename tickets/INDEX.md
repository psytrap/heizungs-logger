# 📋 Heizungslogger Ticket Index: Active & Backlog

This document provides a live dashboard and structured overview of all open tickets for the heizungslogger project (`tickets/open/`).

- For ticket development workflow, state machine rules, and the 7-step execution protocol, see [**`tickets/README.md`**](README.md).
- For historical records of completed and archived tickets, see [**`tickets/DONE.md`**](DONE.md).

---

## 1. 🟡 Active In-Progress Tickets (`Status: In Progress`)

| Ticket | Title | Priority | Scope & Deliverables |
| :---: | :--- | :---: | :--- |
| _none_ | – | – | – |

---

## 2. ⏳ Prioritized Backlog (`Status: Backlog` / `Status: Open`)

Tickets are listed as one flat list, ordered by priority (**P0** → **High** → **Normal** → **Low**) and then ascending ticket number. Ordering is a reading aid, not a sequencing commitment.

| Ticket | Title | Priority | Scope & Deliverables |
| :---: | :--- | :---: | :--- |
| _none_ | – | – | – |

---

## 3. 📌 Index Maintenance Rules

1. A ticket appears in **§1** only while its header reads `- **Status:** In Progress`.
2. Activation (step 1 of the protocol) moves the row from **§2** to **§1**; the ticket file itself stays in `tickets/open/`.
3. Completion (step 6) removes the row from **§1** and adds the entry to [**`DONE.md`**](DONE.md).
4. The index never reorders ticket numbers and never introduces grouping beyond the priority order described above.

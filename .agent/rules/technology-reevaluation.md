# Technology Reevaluation Rule

## 1. 📅 Cadence

- **Rule:** Every **6 months** the stack is reviewed against what exists *now*,
  not against what existed when it was chosen.
- **Next due:** **2027-04-29** (last review: 2026-10-29).
- **Enforcement:** When the due date has passed, the root agent raises the
  review as the first item of the session, before taking on new feature work.

## 2. 🔍 Review Surface

| Area | Question to answer |
| :--- | :--- |
| Python runtime | Is the pinned `requires-python` still supported upstream, and does the Pi's distro ship a newer one? |
| `pyserial` | Still maintained? Is there a leaner serial transport worth adopting? |
| Adafruit stack | Do `Adafruit-Blinka` / `adafruit-circuitpython-charlcd` still track current kernel and CircuitPython releases? |
| Arduino toolchain | Is the `.ino` still buildable with the current core, and are the DS1820 libraries current? |
| Storage | Do plain JSONL day files still beat the alternatives for this size and access pattern? |
| Host | Is the Raspberry Pi OS release still receiving security updates? |
| Agent models | Are the configured OpenRouter models and token limits still valid, and are newer models cheaper at the same quality? |

## 3. 🎫 Output of a Review

- **Rule:** A review produces **one** ticket per area that actually needs a
  change, filed with the normal protocol (flat priority, no phases).
- **Enforcement:**
  - Areas that are fine are recorded in a single line in the ticket's
    `Execution Notes` — "reviewed, no action" — not as tickets.
  - Do **not** migrate, upgrade, or refactor during the review itself. The
    review only decides; the tickets execute.
  - If an area is a security risk, file it as **P0** and say so explicitly in
    the review summary.

## 4. 🚫 Out of Scope

- Chasing novelty. A replacement is proposed only when it measurably improves
  one of: data integrity, reliability, maintenance cost, or total cost.
- Rewriting working hardware integration for its own sake. The Pi is
  production hardware that is actively collecting data.

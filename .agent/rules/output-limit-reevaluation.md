# Output Limit Reevaluation Rule

## 1. 📅 Cadence

- **Rule:** The agent's output budget and model configuration are re-checked
  against available technology every **6 months**.
- **Next due:** **2027-04-29** (set 2026-10-29).
- **Trigger:** once the date has passed, the root agent raises the check at the
  start of the session, before taking on new work. No ticket is needed — this
  is configuration, not source code.

## 2. 📸 Baseline Snapshot (2026-10-29)

| Model entry | `max_tokens` | `max_output_tokens` / `max_completion_tokens` |
| :--- | ---: | ---: |
| `DeepSeek Flash 1017` | 128000 | 8192 |
| `DeepSeek Flash 1017 XL` | 128000 | 64000 |

Provider: `OpenRouter Costum` in `~/.config/zed/settings.json`. The XL entry is
the same model with a larger output cap, so it can be picked per thread.

## 3. 🔍 Questions to Answer

1. Does a newer model offer the same quality with a larger native output budget
   or a lower price per token?
2. Have the provider's real per-model limits changed? (The values in the entry
   are what gets *sent*; exceeding the model's real ceiling yields a 400.)
3. Is `8192` still the right default for routine work, and is the `64000` XL cap
   still the right thing to reach for on long tasks?
4. Do the configured models still consume the budget the way the entry claims
   (reasoning/thinking tokens share the same output cap)?
5. Is the context window still accurate, and does the output cap leave enough
   room for input plus history?

## 4. ⚙️ Actions

- **Rule:** The review changes `~/.config/zed/settings.json` only.
- **Enforcement:**
  - Back up the file, re-validate it as JSONC, and report the old and new values.
  - Do **not** touch project files or open tickets for a settings-only change.
  - If the outcome affects documented project behaviour, file a normal ticket
    instead of editing the docs directly.
  - If a turn truncates at any point outside the review, that is an immediate
    cue to inspect the limits; do not wait for the 6-month date.

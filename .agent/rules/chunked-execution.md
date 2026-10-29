# Chunked Execution for Small Output Budgets

## 1. 🎯 Scope & Motivation

Applies to every agent session, and is mandatory for models whose
`max_output_tokens` is modest (the configured DeepSeek Flash variants run at
8192 / 64000). A truncated turn loses the whole message, including any file
content that had not yet been written by a tool call.

**Consequence:** never let prose and file content share a single long turn.
Put work into tools, keep chat text short.

## 2. 📦 Write in Atomic Units

- **One artefact per tool call.** A module, a test file, a config file: one
  `write_file` (or one `edit_file` bundle) each. Never batch a package's worth
  of files into a single reply.
- **Cap file size.** If a file would exceed roughly 120 lines, split it into
  another module rather than writing it in one go.
- **Group only what is trivially small.** Two or three files with fewer than
  ~60 lines each may share a call. Anything larger gets its own.
- **Edits beat rewrites.** Prefer `edit_file` with surgical `old_text` for
  changes; only use `write_file` for new files or a genuine full replace.

## 3. 🗣️ Keep the Narration Minimal

- At most **one sentence** of commentary before a group of tool calls.
- Do **not** restate, quote, or explain code that a tool call just wrote.
  Reference the path instead.
- Do **not** paste code into chat unless the user asked for an excerpt. The
  editor shows the diff.
- Do **not** re-read a file after a successful `write_file` or `edit_file`; a
  failed call would have said so.
- Prefer bullet summaries over long reconstructions of your own work.

## 4. 🔁 Verify Incrementally

- Run the narrowest relevant check as soon as a coherent unit exists, not once
  at the end of the task.
- Keep tool output small: `head_lines` / `tail_lines` on `terminal`, targeted
  `grep`, and `pytest -q`.
- After a red gate, fix **one** cause per turn.

## 5. ✂️ Budget Discipline

- Treat roughly **150 lines of chat text** as the practical ceiling for one
  turn. When a response is heading past that, stop after the current tool call
  and continue next turn.
- When a turn is cut off mid-task, resume with the **exact next unwritten
  artefact** — never restart with a recap. The ticket's `Execution Notes` are
  the only place where progress gets summarised.

## 6. 🧑‍🤝‍🧑 Delegation as a Fallback

- If a subtask cannot be expressed in a handful of small tool calls, or would
  exceed the output budget twice over, delegate it to a subagent with a
  self-contained prompt and a disjoint write scope.
- Do **not** delegate to compensate for a poorly decomposed plan; decompose
  first, then decide.
- State in the final message which parts were delegated.

## 7. 🚫 Anti-Patterns

- One giant turn that writes seven modules, then fails and loses everything.
- An introductory paragraph that restates the request before starting.
- A "here is the full file" dump in chat followed by the same content in a
  `write_file` call.
- Running the full suite and the linter in one command chain, then dumping
  200 lines of output.
- Apologising at length for a time-out instead of continuing with the next
  unit of work.

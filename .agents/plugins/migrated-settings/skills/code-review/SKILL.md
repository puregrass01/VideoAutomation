---
name: code-review
description: "Review the changes since a fixed point (commit, branch, tag, merge-base, or working-tree WIP including untracked files) along two axes: Standards (does the code follow this repo's documented coding standards?) and Spec (optional — only when the user explicitly supplies a spec). Runs reviews in fresh sub-agents and reports them side by side. Use when the user wants to review a branch, a PR, work-in-progress changes, or asks to \"review since X\"."
---

Two-axis review of changes since a fixed point (committed range and/or working-tree WIP including untracked files):

- **Standards**: does the code conform to this repo's documented coding standards?
- **Spec** *(optional)*: does the code faithfully implement a user-supplied spec?

When both axes run, spawn them as **parallel sub-agents** so they don't pollute each other's context, then aggregate their findings. Start every sub-agent with a fresh context window.

## Process

### 1. Pin the fixed point & build a safe diff scope

Always invoke git with `-c core.quotepath=false` so non-ASCII (e.g., Korean) file paths are never escaped.

Whatever the user said is the fixed point (a commit SHA, branch name, tag, `main`, `HEAD`, `WIP`, `HEAD~5`, etc.). If they didn't specify one, ask for it. Confirm non-WIP refs resolve via `git rev-parse <fixed-point>`.

Choose the diff scope once before spawning sub-agents:

1. **Working-tree / WIP scope** — use when the user asks to review work-in-progress / uncommitted changes, passes `HEAD` or `WIP`, OR when `git -c core.quotepath=false status --porcelain` is non-empty and `git diff --quiet <fixed-point>..HEAD` succeeds (identical committed trees, e.g., after a squash merge):
   - Tracked diff (staged + unstaged): `git -c core.quotepath=false diff <fixed-point>` (use `HEAD` if `<fixed-point>` is `WIP` or matches `HEAD`'s tree).
   - Untracked files: list with `git -c core.quotepath=false ls-files --others --exclude-standard` and pass every untracked path (plus its contents or `git diff --no-index /dev/null <path>`) to the sub-agent(s) so new WIP files are never omitted.
   - Commit list: `working tree (uncommitted)` plus `git -c core.quotepath=false log <fixed-point>..HEAD --oneline` if `<fixed-point>` differs from `HEAD`.
   - Confirm at least one of the tracked diff or the untracked file list is non-empty; fail here only if both are empty.
2. **Committed-range scope** — use when the working tree is clean or the user explicitly asks for committed changes only:
   - Check `git -c core.quotepath=false diff --shortstat <fixed-point>...HEAD` vs `git -c core.quotepath=false diff --shortstat <fixed-point>..HEAD`.
   - Default to three-dot `git -c core.quotepath=false diff <fixed-point>...HEAD`. If three-dot explodes due to a diverged or squash-merged base (e.g., `...HEAD` is >2x larger than `..HEAD`, exceeds ~500 KB, or touches >200 files while `..HEAD` is compact), switch to two-dot `git -c core.quotepath=false diff <fixed-point>..HEAD`.
   - If the diff is still oversized because of binary or media assets, filter them out with pathspecs (`-- . ':(exclude)*.png' ':(exclude)*.jpg' ':(exclude)*.jpeg' ':(exclude)*.mp4' ':(exclude)*.mov' ':(exclude)*.wav' ':(exclude)*.mp3' ':(exclude)*.ttf' ':(exclude)*.otf' ':(exclude)*.exe'`) and note any excluded patterns in the prompt.
   - Note the commit list via `git -c core.quotepath=false log <fixed-point>..HEAD --oneline`. Confirm the diff is non-empty before proceeding.

### 2. Spec source (no automatic discovery)

Do **not** search commit messages, issue trackers, PRs, `docs/`, `specs/`, or `.scratch/`, and do **not** block asking the user where the spec is.

- If the user explicitly supplied a spec file path or inline spec text in their request, pass it to the **Spec** sub-agent.
- Otherwise, skip the **Spec** sub-agent and record `Skipped — no spec provided.` under `## Spec`.

### 3. Identify the standards sources

Search the repo for every file that documents how code should be written. When `CODING_STANDARDS.md` or `CONTRIBUTING.md` exists, include it. When neither exists, include repo instruction/rule documents (such as `AGENTS.md`, `GEMINI.md`, and `.agents/rules/*.md`).

On top of whatever the repo documents, the Standards axis always carries the **smell baseline** below: a fixed set of Fowler code smells (_Refactoring_, ch.3) that applies even when a repo documents nothing. Two rules bind it:

- **The repo overrides.** A documented repo standard always wins; where it endorses something the baseline would flag, suppress the smell.
- **Always a judgement call.** Each smell is a labelled heuristic ("possible Feature Envy"), never a hard violation. Like any standard here, skip anything tooling already enforces.

Each smell reads *what it is* → *how to fix*; match it against the diff:

- **Mysterious Name**: a function, variable, or type whose name doesn't reveal what it does or holds. → rename it; if no honest name comes, the design's murky.
- **Duplicated Code**: the same logic shape appears in more than one hunk or file in the change. → extract the shared shape, call it from both.
- **Feature Envy**: a method that reaches into another object's data more than its own. → move the method onto the data it envies.
- **Data Clumps**: the same few fields or params keep travelling together (a type wanting to be born). → bundle them into one type, pass that.
- **Primitive Obsession**: a primitive or string standing in for a domain concept that deserves its own type. → give the concept its own small type.
- **Repeated Switches**: the same `switch`/`if`-cascade on the same type recurs across the change. → replace with polymorphism, or one map both sites share.
- **Shotgun Surgery**: one logical change forces scattered edits across many files in the diff. → gather what changes together into one module.
- **Divergent Change**: one file or module is edited for several unrelated reasons. → split so each module changes for one reason.
- **Speculative Generality**: abstraction, parameters, or hooks added for needs the spec doesn't have. → delete it; inline back until a real need shows.
- **Message Chains**: long `a.b().c().d()` navigation the caller shouldn't depend on. → hide the walk behind one method on the first object.
- **Middle Man**: a class or function that mostly just delegates onward. → cut it, call the real target direct.
- **Refused Bequest**: a subclass or implementer that ignores or overrides most of what it inherits. → drop the inheritance, use composition.

### 4. Spawn sub-agent(s) in parallel

When a spec was explicitly provided, issue both sub-agent calls together in the foreground; otherwise spawn only the **Standards** sub-agent.

**Standards sub-agent prompt** should include:

- The full diff command, commit list, and any untracked WIP file paths (and excluded asset patterns, if any).
- The list of standards-source files you found in step 3, **plus the smell baseline from step 3** pasted in full (the sub-agent has no other access to it).
- The brief: "Report, per file/hunk where relevant, (a) every place the diff violates a documented standard: cite the standard (file + the rule); and (b) any baseline smell you spot: name it and quote the hunk. Distinguish hard violations from judgement calls: documented-standard breaches can be hard, but baseline smells are always judgement calls, and a documented repo standard overrides the baseline. Skip anything tooling enforces. Under 800 words."

**Spec sub-agent prompt** *(only when user provided a spec)* should include:

- The diff command, commit list, and any untracked WIP file paths.
- The path or contents of the user-provided spec.
- The brief: "Report: (a) requirements the spec asked for that are missing or partial; (b) behaviour in the diff that wasn't asked for (scope creep); (c) requirements that look implemented but where the implementation looks wrong. Quote the spec line for each finding. Under 800 words."

### 5. Aggregate

Present the two reports under `## Standards` and `## Spec` headings, verbatim or lightly cleaned (or `Skipped — no spec provided.` under `## Spec`). Do **not** merge or rerank findings, because the two axes are deliberately separate (see _Why two axes_).

End with a one-line summary: total findings per axis, and the worst issue _within each axis_ (if any). Don't pick a single winner across axes: that's the reranking the separation exists to prevent.

## Why two axes

A change can pass one axis and fail the other:

- Code that follows every standard but implements the wrong thing → **Standards pass, Spec fail.**
- Code that does exactly what the issue asked but breaks the project's conventions → **Spec pass, Standards fail.**

Reporting them separately stops one axis from masking the other.

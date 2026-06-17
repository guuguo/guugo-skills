---
name: fact-driven-ai-methodology
description: "Build and iterate fact-driven AI workflow methodologies from confirmed facts instead of subjective self-optimization. Use when designing, auditing, or rebuilding long-running AI workflows such as prompt methodologies, AI content pipelines, animation/script generation systems, coding workflows, evaluation loops, or any process where AI keeps optimizing its own rules and causes drift, regressions, overfitting, lost goals, messy outputs, or scattered intermediate documents. 中文触发：事实驱动、事实库、方法论重建、AI 工作流复盘、提示词方法论治理、规则漂移治理。"
---

# Fact-Driven AI Methodology

Use this skill to keep long-running AI workflows anchored to facts. The core rule is:

> The fact repository is the source of truth. A methodology is a derived view rebuilt from facts, not an authority that gets patched forever.

Do not let AI "optimize the methodology" by editing the previous methodology directly. Rebuild the current methodology from confirmed goals, collected evidence, structured facts, conflict records, and validation results.

## Core Model

Represent every long-running AI effort with this hierarchy:

```text
Goal / Program
  -> Track / Methodology Area
    -> Task / Experiment
      -> Run
        -> Artifact / Evidence
```

Examples:

- Goal: create hit children's animation works
- Track: Seedance 2.0 prompt methodology
- Task: test whether per-shot character anchors reduce character drift
- Run: generate three A/B sample videos with the same script and different prompt structures
- Evidence: prompts, scripts, videos, model settings, ratings, watch-time records, reviewer notes

`Run` is the smallest execution record. It is not the top-level source of truth.

## Workspace Directory

Before writing any intermediate document, resolve one unified workspace directory for the current Goal / Program. Do not scatter Fact Packs, drafts, experiment notes, run summaries, temporary analyses, or methodology rebuild notes across the project root, random `docs/` paths, neighboring projects, or ad hoc scratch files.

Default location:

```text
<project-root>/.fact-driven-ai/<goal-slug>/
```

If the host environment already mandates a scratch or output area, create one unified folder inside that approved area instead, for example:

```text
work/fact-driven-ai/<goal-slug>/
```

Use this layout unless the project already has a better equivalent:

```text
.fact-driven-ai/<goal-slug>/
  goals/
  evidence/
  facts/
  fact-packs/
  judgments/
  experiments/
  runs/
  methodologies/
  reports/
  archive/
```

Folder intent:

- `goals/`: goal candidates, confirmed goal facts, scope decisions, human confirmations.
- `evidence/`: evidence indexes and links to raw artifacts; avoid copying large raw files unless needed.
- `facts/`: structured facts, corrections, conflict groups, supersession records.
- `fact-packs/`: rebuild-ready Fact Packs.
- `judgments/`: temporary AI or human explanations and hypotheses.
- `experiments/`: experiment designs, A/B plans, validation criteria, result comparisons.
- `runs/`: run records, inputs, outputs, parameters, adoption status.
- `methodologies/`: rebuilt methodology versions and their evidence references.
- `reports/`: user-facing summaries that still belong to this methodology workspace.
- `archive/`: deprecated or superseded intermediate files.

If a user requests a final deliverable elsewhere, place only the final deliverable there and keep supporting intermediates in the unified workspace. If a project already contains scattered methodology files, do not keep adding to the sprawl; create the unified workspace and add an index that references the old locations.

## Hard Rules

Apply these rules before producing methodology updates:

1. Treat methodology as a derived view.
   - Old methodology is a historical artifact, not current truth.
   - It may be read as evidence of what was believed before.
   - It must not automatically inherit authority.

2. Separate evidence, facts, and judgments.
   - Evidence: raw materials such as scripts, prompts, model outputs, videos, logs, feedback, metrics, screenshots, code, generated artifacts.
   - Fact: a traceable statement confirmed from evidence or from explicit human confirmation.
   - Judgment: an explanation, quality assessment, or causal claim based on facts. Judgments are temporary by default.

3. Require target facts to be confirmed by a human.
   - AI may propose, ask, compare, and summarize target candidates.
   - AI must not mark a target, success criterion, preference, or boundary as confirmed without human confirmation.
   - If target details are missing, interrogate them before using them as facts.

4. Allow direct data capture, but do not confuse it with target confirmation.
   - Directly collect raw scripts, prompts, outputs, model versions, settings, logs, metrics, feedback, and diffs.
   - Record source, time, version, collection method, and reliability.
   - Do not let collected output data replace a confirmed goal.

5. Make confirmed facts append-only.
   - Do not overwrite confirmed facts in place.
   - If a fact is wrong or outdated, append a correction and mark the old fact as `superseded`, `invalidated`, or `disputed`.
   - Preserve enough history to explain why a previous methodology version was produced.

6. Preserve conflict facts.
   - Do not force conflicting facts into one premature conclusion.
   - Mark conflicts explicitly and make the methodology rebuild distinguish stable, weak, and conflicting conclusions.

7. Keep judgments out of the permanent fact layer.
   - AI explanations such as "this worked because the hook is stronger" are hypotheses unless validated.
   - Store them as temporary judgments or hypotheses with evidence links, confidence, and validation needs.

8. Centralize intermediate documents.
   - Resolve and state the unified workspace path before creating files.
   - Keep all methodology intermediates under that path.
   - Do not place temporary facts, drafts, analysis notes, or generated planning files directly in a project root.
   - When changing an existing workflow, migrate by reference first: create an index to old scattered files before moving anything.

## Fact Levels

Use these levels consistently:

```text
L0 Evidence / Raw Record
L1 Structured Fact
L2 Temporary Judgment / Hypothesis
L3 Validated Rule / Methodology Claim
```

L0 examples:

- script text
- prompt text
- generated video
- model version and settings
- code diff
- user feedback transcript
- play/watch logs

L1 examples:

- script has 12 shots
- hook appears at second 8
- prompt repeats character identity in each shot
- sample v003 watch time is 30 seconds
- Run v021 used Seedance 2.0 with prompt template v5

L2 examples:

- v003 likely failed because the opening conflict was too late
- repeating character identity may reduce drift
- the old coding rule may be causing over-abstraction

L3 examples:

- For this Seedance 2.0 workflow, include a short character anchor in every shot when character consistency is a primary goal.
- For this codebase, do not introduce a new abstraction unless the task fact explicitly requires reuse across at least two confirmed call sites.

L3 rules require multiple supporting facts, known scope, failure conditions, and validation history.

## Fact Intake Workflow

When new information arrives, classify it before using it:

```text
Candidate
  -> source type: collected / human-confirmed / inferred
  -> level: L0 / L1 / L2 / L3
  -> status: draft / confirmed / assumed / disputed / superseded / invalidated
  -> evidence links
  -> owner or confirmer
  -> created_at and version
```

Use this intake policy:

- Write intake records only inside the unified workspace directory.
- Collected raw data can enter as L0 evidence after source metadata is recorded.
- Objective extraction from evidence can enter as L1 structured facts.
- Target, scope, success criteria, constraints, and preferences must be confirmed by a human before becoming confirmed facts.
- AI explanations enter as L2 judgments.
- L3 rules are promoted only after repeated validation or explicit human acceptance with known risk.

## Goal Confirmation

Before rebuilding or designing a methodology, confirm goal facts. If the goal is not already confirmed, ask one decision question at a time.

For each question:

- Provide the recommended answer.
- Explain why it matters.
- Explain what breaks if the assumption is wrong.
- Store unanswered recommendations as assumptions, not facts.

Typical target facts to confirm:

- desired output type
- target audience or user
- success metric
- non-goals
- quality bar
- forbidden directions
- platform/model constraints
- cost/time constraints
- who has authority to accept results

Example:

```text
Question: What does "hit animation" mean for this goal?
Recommended answer: Define it by child watch completion, repeat requests, and parent acceptance before platform metrics.
Why it matters: Different metrics lead to different script structures and evaluation loops.
Risk if wrong: AI may optimize for viral hooks that are not suitable for the actual child-viewing goal.
```

## Fact Pack

Before rebuilding a methodology, create a Fact Pack. The methodology may only rely on facts in this pack or explicitly marked assumptions.

Store Fact Packs under:

```text
<workspace>/fact-packs/
```

Minimum Fact Pack sections:

```text
1. Confirmed Goal Facts
2. Current Assets
3. Evidence Inventory
4. Structured Facts
5. Positive Results
6. Negative Results
7. Objective Diffs Between Better and Worse Outputs
8. Conflict Facts
9. Old Methodology as Historical Artifact
10. Assumptions and Missing Facts
11. Questions This Rebuild Must Answer
```

Do not stuff every raw artifact into the prompt if it is too large. Summarize with traceable IDs and load raw evidence only when needed.

## Methodology Rebuild Workflow

When asked to optimize, improve, update, or rebuild an AI methodology, follow this sequence:

1. Confirm or locate the Goal / Program.
2. Check whether target facts are confirmed; if not, interrogate them first.
3. Build or update the Fact Pack.
4. Treat previous methodology versions as historical artifacts.
5. Rebuild the current methodology from the Fact Pack.
6. Mark each rule as stable, weak, conflicting, or experimental.
7. Generate experiments for unresolved claims.
8. State what evidence would invalidate the new methodology.

The output should include:

```text
Current fact summary
Stable patterns
Weak patterns
Conflict points
Rules kept from old methodology
Rules downgraded or removed
New candidate rules
Current methodology version
Required experiments
Invalidation and rollback conditions
```

## Experiment / Run Records

Every experiment or execution run should preserve enough information to be reused later:

Store experiment records under `<workspace>/experiments/` and run records under `<workspace>/runs/`.

```text
run_id
goal_id
track_id
task_or_experiment_id
input evidence IDs
confirmed goal facts used
assumptions used
model/tool versions
prompt or instruction used
output artifacts
objective diffs from prior version
validation results
human feedback
AI judgments produced
adoption status: adopted / rejected / needs more evidence
```

Never store "it is better" alone. Bind the judgment to facts:

```text
Judgment: v012 is more suitable for 3-5 year old children.
Facts:
- average sentence length decreased from 22 to 11 Chinese characters
- repeated phrase appears 4 times
- main conflict appears at second 12 instead of second 42
Validation needed:
- generate a 30-second sample and observe whether the child can retell the character goal
```

## Status Vocabulary

Use these statuses:

- `draft`: captured but not yet checked
- `assumed`: inferred or recommended, not human-confirmed
- `confirmed`: verified through collection or human confirmation
- `disputed`: credible conflicting evidence exists
- `superseded`: replaced by a newer correction
- `invalidated`: known to be wrong or unusable
- `experimental`: candidate rule awaiting validation

## Relationship To Planning And Harness Workflows

Use this skill above task execution frameworks.

- Use planning workflows to produce a concrete plan when the task is a technical solution or implementation design.
- Use execution harnesses to run implementation loops with plan/build/qa/fix/close.
- Use this skill to decide what facts, goals, evidence, rules, assumptions, and validation records those downstream workflows must obey.

In short:

```text
fact-driven-ai-methodology: establishes source-of-truth and rebuild logic
technical planning: designs one solution from confirmed facts
execution harness: executes one task and records run evidence
```

## Anti-Patterns

Reject or correct these behaviors:

- Creating intermediate methodology files directly in a project root or scattered across unrelated directories.
- Editing the old methodology directly because it "looks cleaner".
- Treating AI causal explanations as facts.
- Confirming target goals from a single vague user phrase.
- Deleting conflicting data to simplify the story.
- Overwriting old facts instead of appending corrections.
- Promoting a rule without scope, evidence, and failure conditions.
- Allowing better wording to hide worse results.
- Optimizing for a proxy metric before the real goal is confirmed.

## Minimal Response Pattern

When using this skill in conversation, keep the user loop tight:

1. State what object is being handled: Goal, Track, Task, Run, Fact Pack, or Methodology.
2. State the unified workspace path if any files will be created.
3. Separate confirmed facts, assumptions, and open questions.
4. Ask only the next necessary goal-confirmation question when blocked.
5. If not blocked, produce the Fact Pack or rebuilt methodology.
6. Label every recommendation as fact-backed, assumption-based, or experimental.

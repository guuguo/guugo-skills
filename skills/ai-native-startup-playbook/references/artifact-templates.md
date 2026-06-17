# Artifact Templates

Copy and adapt these templates when the user asks for concrete execution artifacts.

These templates define structure, not output language. When presenting any artifact to the user, translate all headings, labels, table headers, and explanatory prose into Chinese by default. Keep product names, metrics, commands, file names, and common abbreviations such as PMF, CAC, LTV, SLA, Day 7, and Day 30 in English when clearer.

## Problem Hypothesis

```markdown
# Problem Hypothesis

## User Segment
- Primary persona:
- Context:
- Budget holder:
- Influencers:

## Problem
- Specific problem:
- Frequency:
- Severity:
- Current workaround:
- Cost of inaction:

## Testable Claim
[Persona] at [company/context] experiences [problem] [frequency] because [root cause], causing [measurable pain].

## Assumptions
- Assumption 1:
- Assumption 2:
- Assumption 3:

## Disconfirming Evidence To Seek
- Evidence that would weaken the problem:
- Evidence that would weaken the segment:
- Evidence that would weaken the solution:
```

## Competitive Landscape And Threat Map

```markdown
# Competitive Landscape

## Categories
- Direct competitors:
- Indirect competitors:
- Adjacent players:
- Potential acquirers or entrants:

## Threat Analysis
| Player | Why users choose them | Weakness | Why they could beat us | Evidence needed |
|---|---|---|---|---|

## Open Questions
- Where are users dissatisfied today?
- Which differentiation claims are least defensible?
- Which competitor would a skeptical buyer trust first?
```

## Customer Discovery Interview Guide

```markdown
# Customer Discovery Guide

## Target Profile
- Job titles:
- Company types:
- Team structure:
- Seniority:
- Where to find them:

## Opening
- "Tell me about the last time you dealt with [problem]."

## Past-Behavior Questions
- What happened?
- Who was involved?
- What tools or workarounds did you use?
- How long did it take?
- What did it cost in time, money, risk, or frustration?
- What did you try before?

## Follow-Up Probes
- "Can you walk me through that step by step?"
- "What happened next?"
- "How did you decide that was good enough?"
- "Who else cared about the outcome?"

## Avoid
- "Would you use this?"
- "Would you pay for this?"
- "Is this a big problem?"
- Any question that reveals the desired answer.
```

## Interview Synthesis

```markdown
# Interview Synthesis

## Sample
- Interviews reviewed:
- Segment:
- Date range:

## Evidence Supporting Hypothesis
- Signal:
- Quote or paraphrase:
- Frequency:

## Evidence Challenging Hypothesis
- Signal:
- Quote or paraphrase:
- Frequency:

## Surprises
- Unexpected pattern:
- Implication:

## Segment Differences
- Segment:
- Difference:

## Decision
- Continue:
- Adjust:
- Pivot:
- Return to Idea:

## Next Questions
- Question 1:
- Question 2:
- Question 3:
```

## Lightweight Prototype Brief

```markdown
# Prototype Brief

## Core Interaction
- The one interaction to test:
- User action:
- System response:
- Success signal:

## In Scope
- Item 1:
- Item 2:

## Out Of Scope
- Item 1:
- Item 2:

## Test Plan
- Put in front of:
- Task to ask users to complete:
- What to observe:
- Follow-up questions:
```

## MVP Scope Document

```markdown
# MVP Scope

## Product Promise
- For:
- Who need:
- The MVP provides:
- Unlike:

## In Scope
- Feature:
- Evidence it tests:

## Out Of Scope
- Feature:
- Reason:

## Amendment Criteria
A feature can enter scope only when:
- User evidence:
- Frequency threshold:
- Severity threshold:
- Impact on current value:

## Non-Goals
- Non-goal 1:
- Non-goal 2:
```

## Architecture Context File

Use this for `CLAUDE.md`, `AGENTS.md`, or equivalent code-agent instructions.

```markdown
# Project Context

## Product
- Problem:
- Users:
- MVP scope:
- Expected scale in next 6 months:

## Architecture Principles
- Principle 1:
- Principle 2:
- Principle 3:

## Tech Choices
- Stack:
- Dependencies to prefer:
- Dependencies to avoid:
- Data model:
- Auth/session approach:

## Constraints
- Security:
- Privacy:
- Performance:
- Compliance:

## Patterns
- File/module structure:
- Testing approach:
- Error handling:
- Logging/observability:

## Decisions Log
- Date:
- Decision:
- Rationale:
- Follow-up:
```

## Code-Agent Session Template

```markdown
# Coding Session

## Context
- Link to architecture context:
- Link to MVP scope:

## Task
- Specific outcome:

## Constraints
- Must follow:
- Must not change:

## Verification
- Tests to run:
- Manual check:
- Security check:

## Session Log
- Built:
- Decisions made:
- Assumptions introduced:
- Context file updates needed:
```

## PMF Measurement Framework

```markdown
# PMF Measurement Framework

## Activation
- Activation event:
- Target:
- False positive:

## Retention
- Day 7 target:
- Day 30 target:
- Cohort definition:
- False positive:

## Revenue
- Paid conversion target:
- Expansion/renewal signal:
- False positive:

## Referral
- Referral behavior:
- Target:
- False positive:

## Qualitative Pull
- Users would be very disappointed if removed:
- Founder effort required to retain users:
- Evidence that users are pulling product into workflow:

## Review Cadence
- Data reviewed every:
- Decision threshold:
- Pivot/adjust threshold:
```

## Security Review Checklist

```markdown
# Security Review

## Auth And Sessions
- Authentication flow reviewed:
- Session expiry/rotation:
- Permission checks:

## Data Exposure
- API responses:
- Logs:
- Error messages:
- Exports:

## Input And Injection
- User inputs validated:
- SQL/NoSQL injection:
- Command injection:
- Prompt injection if AI features exist:

## Secrets And Config
- Secrets in code:
- Environment variables:
- Third-party keys:

## Dependencies
- Known vulnerabilities:
- Unused packages:
- Update plan:

## Human Review Needed
- Auth:
- Secrets:
- Sensitive data:
- Regulated data:
```

## Founder Bottleneck Audit

```markdown
# Founder Bottleneck Audit

## Inventory
| Workflow or decision | Frequency | Current owner | If founder absent 1 week | Candidate action |
|---|---:|---|---|---|

## Categories
- Automate entirely:
- Delegate to human:
- Keep with founder:
- Needs clearer rules:

## Automation Spec
- Trigger:
- Inputs:
- Decision rules:
- Output:
- Destination:
- Escalation path:
- Review cadence:
```

## Product Management Operating System

```markdown
# Product Management OS

## Cadence
- Sprint length:
- Planning:
- Review:
- Metrics review:

## Minimum Spec
- Problem:
- User segment:
- Evidence:
- Proposed solution:
- Success metric:
- Risks:
- Out of scope:

## Bug Triage
- Severity levels:
- Routing rules:
- Response targets:
- Escalation:

## Weekly Metrics Brief
- Acquisition:
- Activation:
- Retention:
- Revenue:
- Support:
- Product quality:
- Open decisions:
```

## Enterprise Readiness Gap Analysis

```markdown
# Enterprise Readiness Gap Analysis

## Target Account
- Account:
- Buyer:
- Procurement/security expectations:
- Required integrations:

## Current Gaps
| Area | Expected by buyer | Current state | Gap severity | Owner |
|---|---|---|---|---|

## Required Work
- Documentation:
- SLA/support:
- Security/compliance:
- Reliability/observability:
- Integrations:
- Legal/procurement:

## Sequence
- Before next sales call:
- Before pilot:
- Before contract:
```

## Moat Narrative

```markdown
# Moat Narrative

## Domain Specificity
- Knowledge we have:
- Edge cases generic competitors miss:
- How this is encoded in product:

## Data Flywheel
- User behavior collected:
- Patterns learned:
- Product improvement loop:
- Why it compounds:

## Workflow Lock-In
- Integrations:
- Automations:
- Team processes:
- Switching cost:

## Copycat Test
If a well-funded incumbent copied the product today, users would stay because:
- Reason 1:
- Reason 2:
- Reason 3:
```

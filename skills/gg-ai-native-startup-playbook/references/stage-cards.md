# Stage Cards

Use these cards to diagnose the user's startup stage and choose the next work product.

When using these cards to produce a user-facing report, write the report in Chinese by default. Translate stage explanations, headings, field labels, risks, and recommendations into natural Chinese. Keep short stage names such as Idea, MVP, Launch, and Scale in English when useful.

## Idea Stage

Goal: establish problem-solution fit before committing meaningful build effort.

Core questions:

- Is the problem real, specific, frequent, and painful?
- Who exactly has it, and is that group a market?
- How are they solving it now, and why is that insufficient?
- What must a solution do to address the validated problem?

Exit criteria:

- The user can name who has the problem, how often it occurs, how severe it is, and what people currently do.
- The solution addresses the problem revealed by discovery, not only the founder's original assumption.
- There is enough qualitative evidence from real conversations to justify building an MVP.

Failure modes:

- Mistaking building for validating.
- Prematurely scaling execution ahead of understanding.
- Using AI to confirm a belief rather than pressure-test it.

Best next artifacts:

- Testable problem hypothesis.
- Disconfirming-evidence brief.
- Competitive landscape and threat map.
- Customer discovery target profile.
- Interview guide audited for leading or future-facing questions.
- Interview synthesis after every five interviews.
- Lightweight core-interaction prototype brief.

AI role split:

- Research/chat role: sharpen hypothesis, argue against it, map competitors, design interviews.
- Workflow automation role: prospect list, outreach drafts, scheduling, interview tracking.
- Code agent role: build only the minimum core interaction after validation.

## MVP Stage

Goal: translate a validated problem into the smallest working product that generates real product-market-fit evidence, without creating compounding AI-generated technical debt.

Core questions:

- What exact user behavior would prove value?
- What is the minimum product surface that can produce that evidence?
- What will the product deliberately not do?
- What architecture and context must be written down before coding?
- What security checks are required before real users or real data?

Exit criteria:

- A specific user segment returns, pays, or refers others.
- Retention, activation, revenue, referral, or qualitative pull is visible across multiple cycles.
- The product has a written scope, architecture context, measurement framework, and security review.

Failure modes:

- Agentic technical debt from sessions with no persistent context.
- False product-market fit from launch spikes or friendly-user usage.
- Zero-friction scope creep.
- Insecure-by-inexperience shipping.

Best next artifacts:

- MVP scope document.
- Architecture context file for the code agent, such as `CLAUDE.md`, `AGENTS.md`, or project instructions.
- Code-agent session template and session log.
- Measurement framework with activation, retention, Day 7/Day 30, revenue, referral, and false-positive definitions.
- Feedback loop plan.
- Security review checklist.
- Pivot/adjust/return-to-Idea diagnostic after three weak iteration cycles.

AI role split:

- Research/chat role: architecture principles, scope criteria, PMF benchmarks, adversarial traction analysis.
- Code agent role: build, test, debug, refactor, maintain context, run security review.
- Workflow automation role: feedback outreach, bug/feature intake, weekly synthesis.

PMF checks:

- Sean Ellis style: ask active users how they would feel if they could no longer use the product; 40% "very disappointed" is a meaningful signal.
- Effort test: before PMF, retention needs founder pushing; after PMF, users start pulling the product into their work.
- Pattern test: no single data point is enough; the pattern must hold across multiple cycles.

## Launch Stage

Goal: turn early traction into repeatable, sustainable growth while hardening product, security, infrastructure, and operations.

Core questions:

- Which acquisition channels are repeatable, and what are CAC, LTV, and payback period?
- Can the product handle production workloads reliably?
- Which founder-held workflows are blocking scale?
- What security, compliance, and process gaps would block bigger customers?

Exit criteria:

- Growth is channel-driven and economically understood.
- Infrastructure, reliability, security, and compliance are production-ready.
- Support, triage, sprint planning, reporting, and feedback flows run without founder heroics.

Failure modes:

- MVP technical debt comes due.
- Founder remains the operating bottleneck.
- Security/compliance remain informal.
- Expansion into new markets before the original PMF is durable.

Best next artifacts:

- Technical debt and architecture audit.
- Refactoring and test-coverage sequence.
- Founder bottleneck and recurring-ops audit.
- Workflow automation specs: trigger, decision rules, output, destination, escalation.
- Security/compliance remediation sequence.
- Lightweight product management operating system: sprint cadence, spec template, bug triage tree, metrics brief.

AI role split:

- Research/chat role: prioritize remediation, design processes, define metrics briefs.
- Code agent role: audit codebase, add tests, refactor, harden security and reliability.
- Workflow automation role: run recurring reports, routing, scheduling, feedback, support, and documentation updates.

## Scale Stage

Goal: make the business sustainable beyond founder day-to-day control while deepening moat, governance, enterprise readiness, and GTM motion.

Core questions:

- If the founder is unavailable for a week, what stalls?
- What would an enterprise buyer, auditor, regulator, analyst, acquirer, or public investor need to trust?
- What domain knowledge, user data, and workflow integrations make the product hard to copy or leave?
- Where has organic/founder-led growth hit its ceiling?

Exit criteria:

- Growth is systematic and auditable.
- Governance, compliance, financial controls, support, and reliability satisfy demanding external reviewers.
- The company has a credible answer to why users would stay if a well-funded incumbent copied the product.
- The business is sustainably profitable, IPO-ready, or acquisition-ready.

Failure modes:

- Operational systems require babysitting.
- Founder knowledge remains undocumented.
- Support, documentation, SLAs, monitoring, incident response, or compliance do not match enterprise expectations.
- GTM depends on founder hustle instead of a repeatable engine.

Best next artifacts:

- Founder bottleneck map and delegation plan.
- Enterprise readiness gap analysis for top prospects.
- Support, SLA, documentation, monitoring, observability, and incident-response roadmap.
- GTM system: segmentation, messaging, analyst relations, sales playbooks, CRM/reporting cadence.
- Domain knowledge capture plan and recurring skill/workflow definitions.
- Vertical edge-case test inventory.
- Data flywheel and moat narrative.
- Workflow integration and lock-in audit for top customers.

AI role split:

- Research/chat role: executive narrative, enterprise gap analysis, moat narrative, GTM strategy.
- Code agent role: reliability/security hardening, integrations, API docs, demo environments, observability tooling.
- Workflow automation role: enterprise support routing, docs updates, renewal tracking, GTM cadences, CRM hygiene.

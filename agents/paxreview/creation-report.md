# Creation report: defect-repairer 2.1.0

Where each part of this persona came from.

| Part | Source |
|---|---|
| identity, character, values_and_drives, memory, self_regulation, presentation, work | version 1.0.0 of this persona (the `pax` bundle of wave 1), carried over |
| norm `one-small-edit-at-a-time`, prohibited behaviour on `write_file` | HARNESS_README.md sections 5.3, 6.2 and 10.1 (official) |
| personality, affect, cognition, metacognition | written for 2.1.0 to the Personaxis 2.0 schema; expressions describe working behaviour only |
| knowledge/ (6 topics) | HARNESS_README.md (read 2026-11-12) and the cited works: SWE-bench, Agentless, SWE-agent, pytest and Python documentation |
| PERSONA.md | compiled by hand to `PERSONA_template.md` (professional profile, six sections): the Personaxis CLI is not installed here |
| skills/knowledge/references/ | compiled copies of knowledge/, so the agent can load them through the harness's skill tools |

Nothing here is derived from the competition's public tasks, their reference
patches or their tests.
| 2.1.0 compile | PERSONA.md carries the delivering skill's steps and the knowledge practices inline (no skill loading); two practices come from the official starter prompt of the competition (search_similar_code before grep, docs_src for documentation examples) |
| 2.2.0 gate | Personaxis 2.1 pivot applied: professional profile without personality and affect; PERSONA.md carries a work-acceptance gate (a request check frozen in /tmp before editing, failing first, passing to accept; failure evidence written before each retry; same failure twice closes not accepted); budget 60 calls and 15 minutes |
| 2.3.0 | the request check moves from /tmp to .git/ (write_file refuses /tmp as outside the workspace; the subprocess sandbox also rewrites /tmp in shell commands): 156 of 200 check runs of 2.2.0 failed with No such file |
| review variant | Personaxis review (spec 8.8 review by an independent model) applied: a worker without submit_patch, a reviewer that sees the statement and git diff and answers ACCEPT or REVISE, a closer that applies one revision and submits; worker prompt is the starter prompt with submission removed |

# Coding-Agent Memory — Recent Literature & Industry Work
*Reading list | October 17, 2026*

## 1. Surveys — Start here

| Survey | What it covers |
|---|---|
| [Self-Evolving Coding Agents](https://arxiv.org/abs/2608.03392) (Aug 2026) | Surveys how coding agents improve through persistent memory, skills, tools, workflows and execution feedback. |
| [From Private Experience to Collective State](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7432218) (Sep 2026) | Surveys how private agent experiences become shared knowledge through admission, scoping, propagation, revision and revocation. |

## 2. Research papers

| Paper | What it investigates |
|---|---|
| [SEPM — Self-Evolving Procedural Memory](https://arxiv.org/abs/2610.14515) (Oct 2026) | Learns reusable procedures from multi-agent execution, using task graphs and a shared blackboard to preserve coordination context. |
| [Chronos — Code Agents Reasoning over Software Evolution](https://arxiv.org/abs/2610.11578) (Oct 2026) | Converts historical pull requests into structured, interconnected knowledge that helps coding agents understand repository evolution. |
| [AECG — Asymmetric Experience Consolidation and Governance](https://arxiv.org/abs/2610.05176) (Oct 2026) | Governs shared multi-agent memories using reliability estimates, scope preservation, degradation monitoring and validated revisions. |
| [SEDM — Selective Self-Evolving Distributed Memory](https://arxiv.org/abs/2509.09498v4) (Oct 2026 revision) | Uses execution-based memory admission, utility-aware consolidation and selective recipient exposure to manage transferable experience. |
| [Scope Before You Persist](https://arxiv.org/abs/2609.29144) (Sep 2026) | Shows how a locally valid learned skill can harm unrelated tasks when applied outside its supported scope. |
| [VibeMemBench — Memory Systems for Coding Agents](https://arxiv.org/abs/2609.23570) (Sep 2026) | Benchmarks whether persistent memory actually improves executable repository tasks, finding that most tested configurations fail to beat no memory. |
| [Jev-Mem — System-One-Controlled Agentic Memory](https://arxiv.org/abs/2609.23986) (Sep 2026) | Separates fast memory-control decisions from slower reasoning to make agent memory use more efficient. |
| [Grounding Agent Memory](https://arxiv.org/abs/2609.11060) (Sep 2026) | Checks candidate memories against environment evidence before admitting them into long-term agent memory. |
| [MemGuard — Persisting Verifier Signals](https://arxiv.org/abs/2608.21867) (Aug 2026) | Uses persistent verification signals to decide which agent memories to retain, retrieve, revise or retire, including software-engineering evaluations. |
| [Shared Organizational Memory for Enterprise Coding Agents](https://arxiv.org/abs/2608.00122) (Aug 2026) | Describes an enterprise deployment for capturing, curating and sharing coding knowledge across different agents and sessions. |

## 3. Industry engineering blogs

| Engineering blog | What it describes |
|---|---|
| [Snowflake — Experience Cards](https://www.snowflake.com/en/blog/engineering/ai-agent-memory-experience-cards/) | Extracts team-owned lessons from merged PRs and reviewer feedback for reuse in later AI code reviews. |
| [Snowflake — ArcticMem](https://www.snowflake.com/en/blog/engineering/arcticmem-persistent-memory-ai-agents/) | Combines repository knowledge with automatically extracted lessons from past coding sessions for persistent retrieval. |
| [Mem0 — Coding Agents That Remember](https://mem0.ai/library/coding-agents/ai-coding-agents-that-actually-remember-your-codebase) | Shows how coding assistants can persist repository conventions, architectural decisions and debugging lessons between sessions. |
| [Cognee — Memory Tooling for AI Coding Agents](https://www.cognee.ai/memory-tooling-ai-coding-agents) | Uses graph-based memory to connect source code, dependencies, documentation and historical knowledge for coding agents. |
| [Supermemory — Large-Repository Coding Agents](https://supermemory.ai/blog/memory-bottleneck-large-repo-coding-agents/) | Discusses retrieval and memory reliability challenges in large, changing repositories, emphasizing provenance, freshness and context. |

**Research focus:** How coding agents accumulate experience across tasks, how that experience becomes shared knowledge, and whether retrieving it genuinely improves later software-engineering outcomes.

*These are pointers for discussion, not claims that all the papers address an unsolved research gap. The surveys and research papers include preprints; the company articles are engineering reports rather than independently peer-reviewed studies.*

---

## 4. Promising venues (2027 cycles)

*Checked Oct 17, 2026. Deadlines are in **2026** unless marked ’27. **—** = no separate abstract deadline; **TBA** = workshop call pending. Dates/format may change: use the linked CFP.*

| Research community | Venue / CFP | Abstract | Paper | Asks for | Fit for FleetMem |
|---|---|---|---|---|---|
| Multi-agent | [AAMAS Blue Sky](https://warwick.ac.uk/fac/sci/dcs/aamas2027/calls/call-for-blue-sky-ideas/) | Nov 5¹ | Nov 12 | 4p research vision | **High:** organizational learning |
| Multi-agent | [WMAC @ AAAI](https://multiagents.org/2027/) | — | Nov 20 | 4p early idea / 8p full | **High:** fleet knowledge sharing |
| Multi-agent | [AAMAS Workshops](https://warwick.ac.uk/fac/sci/dcs/aamas2027/) | TBA | TBA (Jan ’27 suggested) | Workshop-specific | **High:** multi-agent memory |
| ML systems | [MLSys Research](https://mlsys.org/Conferences/2027/CallForResearchPapers) | — | Oct 30 | 10p systems research | **Stretch:** scalable memory + measurements |
| Software engineering | [SANER Agentic AI4SE](https://conf.researchr.org/track/saner-2027/saner-2027-agentic-ai4se-track) | Oct 19 | Oct 23 | ≤10p empirical research | **High:** coding agents |
| Software engineering | [ICSE NIER](https://conf.researchr.org/track/icse-2027/icse-2027-new-ideas-and-emerging-results--nier-) | — | Oct 23 | 4p new idea / emerging result | **High:** novel SE question |
| Software engineering | [FORGE New Idea / Research](https://conf.researchr.org/track/forge-2027/forge-2027-research-papers) | Oct 25 | Oct 30 | 4p new idea / 10p full | **High:** coding-agent memory |
| Software engineering | [SANER Registered Reports](https://conf.researchr.org/track/saner-2027/saner-2027-registered-report-track) | Oct 30 | Nov 6 | 6p *pre-study* protocol | **High:** rigorous experiment design |
| Software engineering | [AGENTVERIFY @ ICSE](https://agentverify2027.github.io/cfp.html) | — | Nov 13 | 2p abstract / 4p short / 8p full | **High:** memory reliability |
| Software engineering | [AGENT @ ICSE](https://conf.researchr.org/track/icse-2027/agent-2027-papers) | — | Nov 13 | 5p short / 8p full | **High:** agent memory and coordination |
| Software engineering | [LLM4Code @ ICSE](https://llm4code.github.io/call/) | — | Nov 13 | Short / position / research | **High:** coding-agent context |
| Software engineering | [ICSE Industry Challenge](https://conf.researchr.org/track/icse-2027/icse-2027-industry-challenge) | — | Nov 13 | 5–10p challenge solution | **High topic;** substantial solution required |
| Software engineering | [FORGE Data & Benchmarking](https://conf.researchr.org/track/forge-2027/forge-2027-data-and-benchmarking-track) | — | Nov 15 | 4p benchmark / empirical audit | **High:** executable memory evaluation |
| Software engineering | [MSR Registered Reports](https://2027.msrconf.org/track/msr-2027-registered-reports) | Nov 13 | Nov 20 | 6p *pre-study* protocol | **High:** empirical study design |
| Software engineering | [EASE 2027](https://conf.researchr.org/home/ease-2027) | Jan 15 ’27 | Jan 22 ’27 | Full empirical SE study | **High:** causal evaluation |
| General AI | [AgenticSE @ AAAI](https://agenticse-aaai.github.io/) | — | Nov 20 | 4p short / 8p full | **High:** agentic SE reliability |
| General AI | [IJCAI 2027](https://2027.ijcai.org/) | Jan 4 ’27 | Jan 11 ’27 | Mature full research | **Stretch:** substantial novelty |
| General ML | [ICLR 2027 Workshops](https://iclr.cc/Conferences/2027/WorkshopGuidelines) | TBA | TBA (Feb ’27 suggested) | Workshop-specific | **Conditional:** agent memory / lifelong learning |
| Agents & evaluation | [Agent Evaluation Science Symposium](https://evalscience.org/2026fall-nyc/submissions/) | Oct 20 (register) | Oct 25 | 2p abstract / 4–6p short | **High:** evals or negative findings |

¹ AAMAS Blue Sky also requires **OpenReview author registration by Oct 20**. **Registered Reports** evaluate proposed methodology, not completed results. Agent Evaluation Science, WMAC and AgenticSE are **non-archival**; other venues have their own publication policies.

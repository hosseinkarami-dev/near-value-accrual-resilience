# Setup prompt

Paste this into your coding agent once, before any track prompt.

```text
We're building an entry for NEAR HACKATHON. Before writing any code:

1. Read https://nearhackathon.com/HACKATHON.md in full. It has the tracks, dates, submission rules and the submission API. Follow its "never without the human's confirmation" list exactly.
2. Install the NEAR agent skills: npx skills add near/agent-skills
3. Use https://docs.near.org/llms.txt and https://docs.near-intents.org/llms.txt to find the right doc pages. Look up contract addresses, endpoints and SDK versions in the docs. Never guess them.
4. Build on testnet first. Keys go in .env, never in the repo.
5. Keep a README from day one, written for an AI judge: what it is, the problem, and numbered "do X, see Y" steps to try it. No marketing copy.

Confirm you've read HACKATHON.md by listing the 13 track ids, then wait for my track prompt.
```

## What the agent skills cover

The [NEAR agent skills](https://github.com/near/agent-skills) include `near-ai-cloud`, `near-api-js`, `near-dapp`, `near-intents`, `near-kit` and `near-smart-contracts`. To install one skill instead of all of them, add `--skill <name>`, for example `npx skills add near/agent-skills --skill near-intents`.

# Ask: how concentrated agent requests are on docs pages

For docs hosts (Mintlify, Read the Docs, GitBook, Context7) and maintainers of self-hosted docs sites. It goes out with `scripts/agent_concentration.py` attached, and only the script's output comes back. Not sent yet.

## Message

Subject: one number about AI agents on your docs, from your own logs

Hi [name],

I'm measuring whether AI agents keep looking up the same documentation pages. If they do, one agent could leave a short note on how to get a page's content, and later agents could skip the searching and failed fetches. In my experiments the note saves 15-50% on lookups that take several fetches. Whether that's worth building depends on one thing no public source has: how concentrated agent requests are across a docs site's pages.

Could you run the attached script on 30 days of [your/a site's] access logs? It's one Python file (3.10+) with no dependencies. It reads nginx, Apache, Cloudflare Logpush or CloudFront logs and prints about 20 lines of percentages:
- the share of agent requests (Claude-User, ChatGPT-User, Perplexity-User and similar) on the top 1%, 10% and 25% of pages
- the share of pages fetched by 2+ different clients
- the share of requests for a page another agent client fetched earlier
- the same figures for human traffic, for comparison

It prints no URLs, page names, IP addresses or user agents, so the output is safe to send as is. I'd share the pooled results with everyone who contributes, with each site's figures kept anonymous unless you say otherwise.

If it's easier to answer from a dashboard, even just these two numbers would help: the share of agent requests that land on your top 10% of pages, and the share of pages that 2+ distinct agent clients requested in a month.

Thanks,
[your name]

## Who to send it to

| Recipient | Why them |
|---|---|
| Mintlify | Published Apr 2026 that AI agents are 45% of docs traffic (~790M requests in 30 days, Cloudflare logs), with no breakdown by page. Contact the post's author. |
| Read the Docs | Open source, research-friendly, and have written publicly about AI crawler traffic on hosted docs. |
| GitBook | Large hosted-docs share. Their analytics already rank pages. |
| Context7 | Serves library docs to coding agents directly and publishes no per-library counts. Counts by library rather than page would still show concentration. |
| Self-hosted open-source docs (e.g. curl, Rust, PostgreSQL, Python docs teams) | Maintainers who run their own nginx or Cloudflare logs and can run the script without going through a company process. |

## Before sending

- Run it once on any log you have access to, so the message can show a sample output.
- Ask recipients which user agent their logs show for coding agents (Claude Code, Cursor, Copilot). The script names the ones we know, but agents that shell out to `curl` or use an HTTP library land in `http-client`, mixed with scripts.

# Instagram content scheduler

Owner-approved public repository for @md_ibrahim07_official.

## Current status

- The 30-post content pack and 70 JPEG graphics are being installed by the manual, checksum-verified **Import approved content** workflow.
- **Instagram publishing remains disabled.** No Instagram credentials are included in source files.
- The proposed campaign is 26 November–25 December 2026, targeting 21:00 Asia/Karachi (16:00 UTC). GitHub scheduled runs can be delayed.
- Standard public GitHub-hosted Ubuntu runners only; no paid AI calls, scheduler subscription, larger runners, caches, or uploaded Actions artifacts.

The importer runs offline tests and commits the prepared captions, graphics and automation code. It does not call Instagram. After successful import, this README is replaced with the complete setup and safety documentation.

Before activation, configure the separately authorized Instagram publishing token directly in GitHub Actions Secrets as `INSTAGRAM_ACCESS_TOKEN`, complete a read-only preflight, and obtain approval to activate the exact campaign. Do not put any token in a chat, source file, issue or public log.

[GitHub Actions billing documentation](https://docs.github.com/en/billing/concepts/product-billing/github-actions)

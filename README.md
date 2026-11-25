# Instagram 30-day automation — prepared, NOT deployed or enabled

Account: @md_ibrahim07_official. Proposed repository: Ibrahimbalti/instagram-content-scheduler.
Proposed campaign: 26 November–25 December 2026 at 21:00 Asia/Karachi (16:00 UTC).

## Status and privacy approval
Initial status, 25 November 2026: the public repository has been created with owner approval. Publishing remains disabled. No publishing credentials are included, and this package has not published or scheduled any Instagram posts.

The owner approved public repository creation: it makes all 30 draft captions and 70 graphics publicly readable before their Instagram publication dates. Secrets must never be committed. This template deliberately refuses private repositories for its no-charge configuration.

## Zero-additional-cost design
Use only standard GitHub-hosted ubuntu-24.04 in a public repository. No larger runners, paid AI, Composio API calls, scheduler subscription, caches, uploaded Actions artifacts, container registry, custom runner images, Git LFS, or hosted database are used. Logs are small and media are ordinary JPEG files in Git. No billing settings or payment methods are modified.

GitHub documentation confirms standard hosted runners in public repositories are free:
https://docs.github.com/en/billing/concepts/product-billing/github-actions
Source inspected at:
https://github.com/github/docs/blob/bd60abd2de5c9285e34ce3ea794274e973b0633e/content/billing/concepts/product-billing/github-actions.md

This is a configuration-specific claim, not a promise about future provider pricing or unrelated usage on your account. Stop and re-check costs if repository visibility or the runner configuration changes.

## One-time authorization that is still required
The existing Instagram OAuth connection in the chat is not automatically transferable to GitHub. A separately authorized Instagram Login publishing access token for this Business/Creator account is required. It must have the required basic and content-publishing permissions and remain valid throughout the campaign. A newly generated long-lived token generally covers a 30-day campaign, but its actual expiry must be checked during authorization.

Add the token directly to GitHub Settings > Secrets and variables > Actions as the encrypted repository secret INSTAGRAM_ACCESS_TOKEN. Do not paste it into a chat, source file, caption, issue, README, screenshot, or public log. There are no credentials in this package.

After the repository exists, run workflow_dispatch in check mode, then preflight mode. Preflight only reads the destination account and publishing-limit endpoint. It does not create media. It cannot prove future token validity or guarantee that a future publishing request will succeed.

## Activation requires a separate approval
Both campaign.json enabled/content_approved and the repository variable ENABLE_INSTAGRAM_PUBLISHING must be set true before publishing. Keep them false/missing until the exact content, public visibility, account and dates are approved, and the read-only preflight passes. Do not change the dates silently if the proposed start is in the past.

## How unattended posting works
The workflow targets 16:00 UTC daily. A second run at 17:30 UTC is a recovery attempt, not a second post. GitHub may delay or occasionally skip scheduled runs, so it is not a guaranteed exact-minute publishing service.

Each run selects only the current local day's due post, never backfills multiple missed days, verifies the expected account, checks for an existing matching caption, creates fresh media containers when due, waits for processing, and publishes at most one post. Container creation IDs are not prepared 30 days ahead.

A GitHub-backed ledger records checkpoints before publishing. An uncertain publish result is not blindly retried. The script stops for manual investigation rather than risk duplicating a post. Provider/network failures, expired credentials and permissions errors can still prevent a post. Review GitHub's workflow failure notifications.

After the final post, or after the campaign window ends, the workflow disables its own future scheduled runs. Permissions are limited to this repository's contents and Actions administration for ledger updates and self-disable.

## Local checks (no network, no credentials, no publication)
python -m unittest discover -s tests -v
python publisher.py --mode check
python publisher.py --mode check --at 2026-11-26T16:00:00Z

The live publishing client has NOT been end-to-end tested against Instagram. Only mocked publishing tests and local validation are run before repository approval.

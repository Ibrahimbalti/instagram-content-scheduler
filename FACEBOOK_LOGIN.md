# Instagram authorization route

A read-only diagnostic verified that the existing encrypted INSTAGRAM_ACCESS_TOKEN is accepted by https://graph.facebook.com for the Instagram account @md_ibrahim07_official and its content-publishing-limit endpoint. The Instagram Login host rejected the same credential. This is an API login-family mismatch, not evidence that the user forgot to save a token.

The workflow now runs publisher_facebook.py, an adapter for the Facebook Login route to Instagram. It keeps the original publisher.py campaign approval, fixed-account checks, daily selection, duplicate reconciliation, ledger, safe retry behavior and self-disable behavior. It does not post to Facebook and does not change or disclose the credential.

The campaign flags and ENABLE_INSTAGRAM_PUBLISHING remain off. Passing preflight is not activation and does not prove the token will remain valid for all 30 days. GitHub scheduled jobs can be delayed; the target is 21:00 Asia/Karachi with a single-post recovery attempt at 22:30. No paid services or paid runners are added.

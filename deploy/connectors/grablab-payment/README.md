# GrabLab Payment Webhook Connector (`grablab_payment` v1.1.0)

Data-only GRAB v1.1.0 connector contract for verified payment webhook ingestion (`POST /api/commerce/webhooks/payment`) using GRAB's native `grab-hmac-sha256-v1` signature verification (`Grab-Event-Id`, `Grab-Event-Time`, `Grab-Signature`).

No executable code is included. Integrity is verified offline and at startup via `deploy/grab.connect.lock`:

```powershell
grab connect lock --platform-config deploy/grab.platform.commerce.json
grab connect inspect --platform-config deploy/grab.platform.commerce.json
```

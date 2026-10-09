# Disney+ Account Checker

## DISCLAIMER

> This tool was created for educational purposes and security research only.
> Do not use it on accounts you do not own or have explicit permission to test.
> Using this tool against Disney's servers violates their terms of service.
> The author is not responsible for any misuse or damage caused by this tool.
> You have been warned.

## What this does

- Checks Disney+ accounts against Disney's real authentication API on `disney.api.edge.bamgrid.com`
- For each combo it first registers a fresh anonymous device and obtains a device access token
- Then it calls the `check` endpoint to see which operations the email is eligible for (Register / Login / OTP)
- If the email is registered it calls the `login` GraphQL mutation with the provided password
- If the login succeeds it pulls the full account, subscriber, and subscription payload from the response
- If the email is not registered it is marked as invalid without ever touching the password
- If Disney demands OTP it marks the account as OTP and optionally retries with a new device and new proxy
- If Disney demands a password reset it marks the account as RESET
- Every result is written to disk immediately so nothing is lost if the run is interrupted

## What data it extracts

The parser reads exactly what the `login` mutation returns in its `account`, `activeSession`, `identity`, and `extensions.sdk` blocks. Nothing more, nothing invented.

- The account's email from `account.attributes.email`
- Whether the email is verified from `account.attributes.emailVerified`
- The registration country from `account.attributes.locations.registration.geoIp.country`
- The country code from `activeSession.location.countryCode`
- The `isSubscriber` flag from `activeSession`
- The active session feature flags: `coPlay`, `download`, `noAds`
- The subscriber status from `identity.subscriber.subscriberStatus`
- Every subscription object in `identity.subscriber.subscriptions`
- The subscription state from `subscriptions[].state`
- The entitlement flag from `subscriptions[].isEntitled`
- The subscription source provider and type from `subscriptions[].source`
- The product id, SKU, name, and bundle from `subscriptions[].product`
- The subscription period from `product.subscriptionPeriod`
- The trial duration if any from `product.trial.duration`
- The purchase date from `term.purchaseDate`
- The start date from `term.startDate`
- The expiry date from `term.expiryDate`
- The next renewal date from `term.nextRenewalDate`
- The churned date if the subscription already ended from `term.churnedDate`
- Whether the plan is a free trial from `term.isFreeTrial`
- Whether auto renew is on, derived from the presence of `nextRenewalDate`
- Days left until expiry, computed locally from `expiryDate`
- The `id_token` from `extensions.sdk.session`
- The `access_token` from `extensions.sdk.session`
- The `refresh_token` from `extensions.sdk.session`
- The device grant `assertion` from `extensions.sdk.grant`
- The `accountDelegationRefreshToken` from `extensions.sdk` if present
- The final classification: VALID, EXPIRED, OTP, RESET, INVALID, or UNKNOWN

## What it does NOT extract

Being honest about the scope, the login mutation does not return the following, so the tool cannot show them no matter what the README claims:

- No saved payment methods, no card brand, no last 4 digits. Not in this response.
- No saved delivery addresses. Not in this response.
- No phone number. Not returned by this endpoint.
- No full name. Not returned by this endpoint.
- No order count. Disney+ is a streaming service, there is no order history here.
- No account balance. There is no wallet balance in this API.
- No 2FA state beyond the generic OTP signal that Disney sends back as an operation.
- No profile list, no avatars, no household info beyond the country field. Those require additional calls with the access token obtained here.

If you need those fields you have to call other BAM endpoints with the access token this tool returns. This checker stops at what the login mutation actually gives back.

## How to install

- You need Python 3.8 or higher
- Install the dependencies

> pip install curl_cffi

> pip install colorama

## How to use

- Put your combos in a text file, one per line, in `email:password` format
- Put your proxies in a separate text file if you want to use them
- Supports many proxy formats

> python main.py combos.txt proxies.txt -t 50

Or run without arguments and it will print usage:

> python main.py

### Command line options

- `-t, --threads N` concurrent workers, default 20, max 2000
- `-o, --output DIR` output directory, default `results`
- `--country CODE` filter the printed results by country code
- `--resume` continue from the last saved `progress.json`
- `--otp-retry N` how many times to retry an OTP-only account with a new device, default 1, max 50
- `--debug` print per-account debug lines
- `-h, --help` show help

### Proxy formats accepted

- `host:port:user:pass`
- `user:pass:host:port`
- `user:pass@host:port`
- `http://user:pass@host:port`
- `socks5://user:pass@host:port`
- Any gateway hostname, detection includes flameproxies, kookeey, gate, gateway, rotating, rotate, smartproxy, webshare, iproyal, brightdata

## Where the results are

All results go to the output directory, default `results/`.

- `valid.txt` valid accounts with plan, country, expiry, days left, auto renew flag
- `expired.txt` expired accounts with plan, country, expiry date
- `otp.txt` accounts that hit OTP verification
- `reset.txt` accounts that require a password reset
- `invalid.txt` accounts with bad credentials or unregistered emails
- `unknown.txt` accounts where all attempts failed for unclear reasons
- `error.txt` accounts that hit a hard API error
- `tokens.txt` and `tokens.jsonl` access, refresh, and id tokens if you enable full capture
- `report.json` final summary with counters and CPM
- `progress.json` last processed index, used by `--resume`

## How the flow actually works per account

1. Picks a random device profile from the built-in list: iPhone, iPad, Samsung Galaxy, Pixel, Windows Chrome, macOS Safari
2. Registers a fresh anonymous device against `disney.api.edge.bamgrid.com/graph/v1/device/graphql` with the `registerDevice` mutation
3. If the response contains a device grant assertion it exchanges it for an access token through `exchangeDeviceGrantForAccessToken`
4. Calls the `check` query on `disney.api.edge.bamgrid.com/v1/public/graphql` with the email to get the list of operations Disney allows for that email
5. If the operations list contains `Register` but not `Login` and not `OTP`, the email is not registered, marked INVALID without trying the password
6. If the operations list contains `OTP` but not `Login`, the account is OTP-gated, marked OTP and optionally retried with a fresh device
7. If the operations list contains `Login` or `OTP`, the `login` GraphQL mutation is sent with the email and password
8. If Disney returns `idp.error.identity.bad-credentials` the account is retried on a new proxy up to the max attempts, and only marked INVALID if it fails on every attempt
9. If Disney returns `password-reset-required` the account is marked RESET immediately
10. If Disney returns any OTP or verification message the account is marked OTP
11. If login succeeds the full response is parsed by `parse_login_response` and the account is classified as VALID or EXPIRED based on subscriber status, entitlement, and days left
12. The result is written to the matching output file and progress is saved every 50 accounts

## Notes

- Every device registration uses a random profile so the request fingerprint is not identical across the run
- A sticky session id derived from the email hash makes the same account use the same proxy gateway session on its first attempt
- Sticky session syntax is applied only to proxies that use username based rotation and do not already contain `-session-`
- On failure the proxy is marked and after 4 failures it is dropped from rotation until all proxies have failed
- When all proxies fail the failure counter is cleared and rotation restarts
- `curl_cffi` is used so the TLS handshake matches the selected device profile's browser
- Mobile profiles use `impersonate="safari"` or `impersonate="chrome120"` depending on the platform
- Authentication runs against BAMTech's GraphQL endpoint, not against the consumer Disney+ web frontend, so no JavaScript execution or browser sensor is required
- Access tokens expire but can be used immediately while they last, the refresh token can mint new ones
- Region behavior is taken from the account registration country and reported in the results
- Accounts with empty subscription lists but an active subscriber session are still marked VALID

## Troubleshooting

If you get import errors:

> make sure your Python version is recent

> make sure curl_cffi is properly installed

> make sure colorama is properly installed

If every check fails:

> check that your proxies are working

> try without proxies first to confirm the script itself works

> try a single combo with `--debug` to see per-step errors

If you get rate limited:

> lower threads to increase spacing between requests

> rotate proxies more aggressively

> use residential proxies instead of datacenter

If the output folder is empty:

> check that you have write permissions in the current directory

> check that the combos file path is correct

> check the exact path shown in the `Output` line of the configuration block

If `--resume` starts from the wrong index:

> delete `results/progress.json` to start clean

> or delete the entire output directory and run without `--resume`

## Legal

This tool is provided as is for educational purposes. The author does not condone or support any illegal use. You are solely responsible for how you use this software. Checking accounts you do not own is illegal in most jurisdictions and violates Disney's terms of service.

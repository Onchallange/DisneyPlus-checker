# disney+ account checker

## disclaimer

> this tool was made for educational purposes and security research only
> do not use it on accounts you do not own or have permission to test
> using this tool against disney servers violates their terms of service
> the author is not responsible for any misuse or damage caused by this tool
> you have been warned

## what this does

- checks disney+ accounts against disney real auth api on disney.api.edge.bamgrid.com
- for each combo it first registers a fresh anon device and gets a device access token
- then it calls the check endpoint to see what operations the email is eligible for (register login otp)
- if the email is registered it calls the login graphql mutation with the provided password
- if login succeeds it pulls the full account subscriber and subscription payload from the response
- if the email is not registered it is marked invalid without ever touching the password
- if disney asks for otp it marks the account as otp and optionally retries with a new device and proxy
- if disney asks for a password reset it marks the account as reset
- every result is written to disk right away so nothing is lost if the run is interrupted

## what data it extracts

the parser reads exactly what the login mutation returns in its account activeSession identity and extensions sdk blocks nothing more nothing invented

- the account email from account attributes email
- whether the email is verified from account attributes emailVerified
- the registration country from account attributes locations registration geoIp country
- the country code from activeSession location countryCode
- the isSubscriber flag from activeSession
- the active session feature flags coPlay download noAds
- the subscriber status from identity subscriber subscriberStatus
- every subscription object in identity subscriber subscriptions
- the subscription state from subscriptions state
- the entitlement flag from subscriptions isEntitled
- the subscription source provider and type from subscriptions source
- the product id sku name and bundle from subscriptions product
- the subscription period from product subscriptionPeriod
- the trial duration if any from product trial duration
- the purchase date from term purchaseDate
- the start date from term startDate
- the expiry date from term expiryDate
- the next renewal date from term nextRenewalDate
- the churned date if the subscription already ended from term churnedDate
- whether the plan is a free trial from term isFreeTrial
- whether auto renew is on derived from the presence of nextRenewalDate
- days left until expiry computed locally from expiryDate
- the id_token from extensions sdk session
- the access_token from extensions sdk session
- the refresh_token from extensions sdk session
- the device grant assertion from extensions sdk grant
- the accountDelegationRefreshToken from extensions sdk if present
- the final classification valid expired otp reset invalid or unknown

## what it does not extract

being honest about the scope the login mutation does not return the following so the tool cannot show them no matter what a readme claims

- no saved payment methods no card brand no last 4 digits not in this response
- no saved delivery addresses not in this response
- no phone number not returned by this endpoint
- no full name not returned by this endpoint
- no order count disney+ is a streaming service there is no order history here
- no account balance there is no wallet balance in this api
- no 2fa state beyond the generic otp signal that disney sends back as an operation
- no profile list no avatars no household info beyond the country field those need extra calls with the access token this tool returns

if you need those fields you have to call other bam endpoints with the access token this tool returns this checker stops at what the login mutation actually gives back

## how to install

- you need python 3 8 or higher
- install the dependencies

> pip install curl_cffi

> pip install colorama

## how to use

- put your combos in a text file one per line in email:password format
- put your proxies in a separate text file if you want to use them
- supports many proxy formats

> python main py combos txt proxies txt -t 50

or run without arguments and it will print usage

> python main py

### command line options

- -t --threads n concurrent workers default 20 max 2000
- -o --output dir output directory default results
- --country code filter the printed results by country code
- --resume continue from the last saved progress json
- --otp-retry n how many times to retry an otp only account with a new device default 1 max 50
- --debug print per account debug lines
- -h --help show help

### proxy formats accepted

- host:port:user:pass
- user:pass:host:port
- user:pass@host:port
- http://user:pass@host:port
- socks5://user:pass@host:port
- any gateway hostname detection includes flameproxies kookeey gate gateway rotating rotate smartproxy webshare iproyal brightdata

## where the results are

all results go to the output directory default results

- valid txt valid accounts with plan country expiry days left auto renew flag
- expired txt expired accounts with plan country expiry date
- otp txt accounts that hit otp verification
- reset txt accounts that need a password reset
- invalid txt accounts with bad credentials or unregistered emails
- unknown txt accounts where all attempts failed for unclear reasons
- error txt accounts that hit a hard api error
- tokens txt and tokens jsonl access refresh and id tokens if you enable full capture
- report json final summary with counters and cpm
- progress json last processed index used by resume

## how the flow actually works per account

1 picks a random device profile from the built in list iphone ipad samsung galaxy pixel windows chrome macos safari
2 registers a fresh anon device against disney.api.edge.bamgrid.com/graph/v1/device/graphql with the registerDevice mutation
3 if the response contains a device grant assertion it exchanges it for an access token through exchangeDeviceGrantForAccessToken
4 calls the check query on disney.api.edge.bamgrid.com/v1/public/graphql with the email to get the list of operations disney allows for that email
5 if the operations list contains register but not login and not otp the email is not registered marked invalid without trying the password
6 if the operations list contains otp but not login the account is otp gated marked otp and optionally retried with a fresh device
7 if the operations list contains login or otp the login graphql mutation is sent with the email and password
8 if disney returns idp error identity bad credentials the account is retried on a new proxy up to the max attempts and only marked invalid if it fails on every attempt
9 if disney returns password reset required the account is marked reset right away
10 if disney returns any otp or verification message the account is marked otp
11 if login succeeds the full response is parsed by parse login response and the account is classified as valid or expired based on subscriber status entitlement and days left
12 the result is written to the matching output file and progress is saved every 50 accounts

## notes

- every device registration uses a random profile so the request fingerprint is not the same across the run
- a sticky session id derived from the email hash makes the same account use the same proxy gateway session on its first attempt
- sticky session syntax is applied only to proxies that use username based rotation and do not already contain session
- on failure the proxy is marked and after 4 failures it is dropped from rotation until all proxies have failed
- when all proxies fail the failure counter is cleared and rotation restarts
- curl_cffi is used so the tls handshake matches the selected device profile browser
- mobile profiles use impersonate safari or impersonate chrome120 depending on the platform
- auth runs against bamtech graphql endpoint not against the consumer disney+ web frontend so no javascript execution or browser sensor is needed
- access tokens expire but can be used right away while they last the refresh token can mint new ones
- region behavior is taken from the account registration country and reported in the results
- accounts with empty subscription lists but an active subscriber session are still marked valid

## troubleshooting

if you get import errors

> make sure your python version is recent

> make sure curl_cffi is properly installed

> make sure colorama is properly installed

if every check fails

> check that your proxies are working

> try without proxies first to confirm the script itself works

> try a single combo with debug to see per step errors

if you get rate limited

> lower threads to increase spacing between requests

> rotate proxies more aggressively

> use residential proxies instead of datacenter

if the output folder is empty

> check that you have write permissions in the current directory

> check that the combos file path is correct

> check the exact path shown in the output line of the configuration block

if resume starts from the wrong index

> delete results progress json to start clean

> or delete the entire output directory and run without resume

## legal

this tool is provided as is for educational purposes the author does not condone or support any illegal use you are solely responsible for how you use this software checking accounts you do not own is illegal in most jurisdictions and violates disney terms of service

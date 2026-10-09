BAM_DEVICE = "https://disney.api.edge.bamgrid.com/graph/v1/device/graphql"
BAM_PUBLIC = "https://disney.api.edge.bamgrid.com/v1/public/graphql"
TOKEN = "ZGlzbmV5JmJyb3dzZXImMS4wLjA.Cu56AgSfBTDag5NiRA81oLHkDZfu5L3CKadnefEAY84"
CLIENT_ID = "disney-svod-3d9324fc"
USER_AGENT_SDK = "29a18c42-disneyplus-nsx"
APP_VERSION = "29a18c42"

COUNTRIES = [
    "US","GB","DE","FR","IT","RO","ES","NL","AU","CA",
    "BR","SE","PT","IE","AT","CH","NO","DK","FI","PL",
    "NZ","BE","CZ","HU","GR","HR","SK","SI","BG","EE","LT","LV",
    "MX","AR","CL","CO","PE","ZA","TR","IL","AE","SA","JP","KR",
]

PROFILES = [
    {
        "ua": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
        "browser_ver": "17.5", "os_ver": "17.5",
        "os_name": "ios", "mfg": "apple", "model": "iphone15,4",
        "imp": "safari",
        "device_family": "mobile", "app_runtime": "ios",
        "platform": "ios/iphone", "brand": "apple",
    },
    {
        "ua": "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
        "browser_ver": "17.5", "os_ver": "17.5",
        "os_name": "ios", "mfg": "apple", "model": "ipad14,8",
        "imp": "safari",
        "device_family": "mobile", "app_runtime": "ios",
        "platform": "ios/ipad", "brand": "apple",
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 14; SM-S928U Build/UP1A.231005.007) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.6613.84 Mobile Safari/537.36",
        "browser_ver": "128.0.6613", "os_ver": "14",
        "os_name": "android", "mfg": "samsung", "model": "SM-S928U",
        "imp": "chrome120",
        "device_family": "mobile", "app_runtime": "android",
        "platform": "android/phone", "brand": "samsung",
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro Build/UD1A.230803.041) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.6613.84 Mobile Safari/537.36",
        "browser_ver": "128.0.6613", "os_ver": "14",
        "os_name": "android", "mfg": "google", "model": "Pixel 8 Pro",
        "imp": "chrome120",
        "device_family": "mobile", "app_runtime": "android",
        "platform": "android/phone", "brand": "google",
    },
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "browser_ver": "128.0.0", "os_ver": "10.0",
        "os_name": "windows", "mfg": "microsoft", "model": None,
        "imp": "chrome120",
        "device_family": "browser", "app_runtime": "chrome",
        "platform": "javascript/windows/chrome", "brand": "web",
    },
    {
        "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
        "browser_ver": "17.5", "os_ver": "10.15.7",
        "os_name": "macos", "mfg": "apple", "model": None,
        "imp": "safari",
        "device_family": "browser", "app_runtime": "safari",
        "platform": "javascript/macos/safari", "brand": "apple",
    },
]

LOGIN_QUERY = """mutation login($input:LoginInput!){login(login:$input){
    account{id attributes{email emailVerified locations{registration{geoIp{country}}}}}
    activeSession{isSubscriber location{countryCode} features{coPlay download noAds}}
    identity{subscriber{subscriberStatus subscriptions{
        state isEntitled partner source{sourceProvider sourceType}
        product{id sku name bundle subscriptionPeriod trial{duration}}
        term{purchaseDate startDate expiryDate nextRenewalDate churnedDate isFreeTrial}
    }}}
}}"""

REGISTER_QUERY = "mutation registerDevice($input:RegisterDeviceInput!){registerDevice(registerDevice:$input){grant{grantType assertion}}}"
EXCHANGE_QUERY = "mutation ex($i:ExchangeDeviceGrantForAccessTokenInput!){exchangeDeviceGrantForAccessToken(exchangeDeviceGrantForAccessToken:$i){accepted}}"
CHECK_QUERY = "query check($email:String!){check(email:$email){operations nextOperation}}"

GATEWAY_HINTS = ("flameproxies", "kookeey", "gate.", "gateway.", "rotating", "rotate.", "smartproxy", "webshare", "iproyal", "brightdata")

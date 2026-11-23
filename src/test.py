class QuotaExceeded(Exception):
    """The trial/monthly request quota is used up; retrying won't help."""


QUOTA = {"remaining": None}   # updated after every successful call


def pull_json(endpoint: str, max_retries: int = 3, params: dict | None = None) -> dict:
    url = f"{BASE_URL}/{endpoint}"
    for attempt in range(1, max_retries + 1):
        wait = 2 ** attempt
        try:
            response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            print(f"[{attempt}/{max_retries}] network error {endpoint}: {e}; retrying in {wait}s")
            time.sleep(wait)
            continue

        if response.status_code == 429 and "USAGE_LIMIT_EXCEEDED" in response.text:
            raise QuotaExceeded("Monthly/trial quota used up")

        if response.status_code in RETRY_STATUSES:
            if response.status_code == 429:
                wait = int(response.headers.get("Retry-After", 65)) + 1
            print(f"[{attempt}/{max_retries}] HTTP {response.status_code} on {endpoint}; retrying in {wait}s")
            time.sleep(wait)
            continue

        response.raise_for_status()
        QUOTA["remaining"] = response.headers.get("X-Monthly-Quota-Remaining")
        time.sleep(REQUEST_PAUSE)
        return response.json()

    raise RuntimeError(f"Stopped on {endpoint} after {max_retries} attempts")
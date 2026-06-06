import socket
import time

import requests


HOST = "api.binance.com"
PING_URL = "https://api.binance.com/api/v3/ping"
STATUS_URL = "https://api.binance.com/sapi/v1/system/status"


def check_dns():
    print("DNS")
    print("---")

    try:
        started_at = time.time()
        result = socket.getaddrinfo(HOST, 443)
        elapsed = round(time.time() - started_at, 3)

        addresses = sorted({item[4][0] for item in result})

        print("[OK] DNS resolved:", HOST)
        print("Time:", elapsed, "sec")
        print("Addresses:", ", ".join(addresses[:5]))

        return True
    except Exception as ex:
        print("[FAIL] DNS error:", ex)
        return False


def check_http_ping():
    print()
    print("HTTP PING")
    print("---------")

    try:
        started_at = time.time()
        response = requests.get(PING_URL, timeout=10)
        elapsed = round(time.time() - started_at, 3)

        print("Status code:", response.status_code)
        print("Time:", elapsed, "sec")
        print("Body:", response.text)

        if response.status_code == 200:
            print("[OK] Binance ping доступен")
            return True

        print("[FAIL] Binance ping вернул не 200")
        return False
    except Exception as ex:
        print("[FAIL] HTTP ping error:", ex)
        return False


def check_system_status():
    print()
    print("SYSTEM STATUS")
    print("-------------")

    try:
        started_at = time.time()
        response = requests.get(STATUS_URL, timeout=10)
        elapsed = round(time.time() - started_at, 3)

        print("Status code:", response.status_code)
        print("Time:", elapsed, "sec")
        print("Body:", response.text)

        if response.status_code == 200:
            print("[OK] Binance system status доступен")
            return True

        print("[FAIL] Binance system status вернул не 200")
        return False
    except Exception as ex:
        print("[FAIL] System status error:", ex)
        return False


def main():
    print("NETWORK CHECK")
    print("=============")

    dns_ok = check_dns()
    ping_ok = check_http_ping()
    status_ok = check_system_status()

    print()
    print("RESULT")
    print("------")

    if dns_ok and ping_ok and status_ok:
        print("[OK] Сеть и Binance API доступны")
    else:
        print("[FAIL] Есть проблема с сетью или Binance API")


if __name__ == "__main__":
    main()

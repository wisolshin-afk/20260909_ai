import argparse
import json
import sys
import time
from datetime import datetime
from typing import Dict
from urllib.error import URLError
from urllib.request import urlopen

API_URL = "https://open.er-api.com/v6/latest/KRW"
CURRENCY_OPTIONS = {
    "1": "USD",
    "2": "JPY",
    "3": "CNY",
}


def fetch_rates() -> Dict[str, float]:
    with urlopen(API_URL, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if payload.get("result") != "success":
        raise RuntimeError(f"환율 API 호출 실패: {payload}")

    return payload["rates"]


def get_krw_per_unit(currency_code: str, rates: Dict[str, float]) -> float:
    if currency_code not in rates:
        raise ValueError(f"지원하지 않는 통화입니다: {currency_code}")

    unit_in_krw = 1 / rates[currency_code]
    return unit_in_krw


def print_rate(currency_code: str, interval_seconds: int) -> None:
    try:
        rates = fetch_rates()
        krw_per_unit = get_krw_per_unit(currency_code, rates)
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{updated_at}] {currency_code} 1개당 KRW: {krw_per_unit:,.2f}원")
        print(f"다음 갱신: {interval_seconds}초 후")
    except (URLError, TimeoutError, RuntimeError, ValueError) as exc:
        print(f"환율 조회 실패: {exc}", file=sys.stderr)


def run_loop(currency_code: str, interval_seconds: int, once: bool = False) -> None:
    try:
        while True:
            print_rate(currency_code, interval_seconds)
            if once:
                break
            print("-" * 50)
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\n환율 조회를 종료합니다.")


def show_menu() -> str:
    print("=== 실시간 환율 조회 ===")
    for key, value in CURRENCY_OPTIONS.items():
        print(f"{key}. {value}")
    print("q. 종료")

    while True:
        choice = input("통화를 선택하세요: ").strip().lower()
        if choice == "q":
            raise SystemExit(0)
        if choice in CURRENCY_OPTIONS:
            return CURRENCY_OPTIONS[choice]
        print("잘못된 선택입니다. 1, 2, 3 또는 q를 입력하세요.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KRW 기준 실시간 환율 조회 앱")
    parser.add_argument("--currency", choices=["USD", "JPY", "CNY"], help="조회할 통화 선택")
    parser.add_argument("--interval", type=int, default=30, help="갱신 간격(초), 기본값 30")
    parser.add_argument("--once", action="store_true", help="한 번만 조회하고 종료")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.currency:
        run_loop(args.currency, args.interval, once=args.once)
        return

    while True:
        currency_code = show_menu()
        run_loop(currency_code, 30)


if __name__ == "__main__":
    main()

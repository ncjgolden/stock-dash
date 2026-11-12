"""Produce a short CJ briefing evidence packet from a reconciled public flow file.

No network, scheduling, brokerage, messaging or trading. A matching report only
shows the windows explicitly compared against user-exported official daily data.
"""
import argparse
import json
from pathlib import Path

MARKETS = ("KOSPI", "KOSDAQ", "005930", "000660")
LABELS = {"KOSPI": "코스피", "KOSDAQ": "코스닥",
          "005930": "삼성전자", "000660": "SK하이닉스"}
INVESTORS = {"foreign_krw": "외국인", "institution_krw": "기관",
             "individual_krw": "개인"}


def concise(report, *, target):
    asof = report.get("asof", "UNKNOWN")
    windows = report.get("windows", {})
    status = report.get("verification")
    if target not in MARKETS:
        raise ValueError("Unsupported briefing ticker")
    lines = [f"{LABELS[target]} 수급 기준일 {asof} · 단위 억원"]
    for n in ("5", "20", "60"):
        window = windows.get(n, {})
        if window.get("status") != "MATCHED" or not isinstance(window.get("values"), dict):
            lines.append(f"{n}거래일: UNKNOWN ({window.get('status', '미검증')})")
            continue
        values = window["values"]
        if any(not isinstance(values.get(k), (int, float)) for k in INVESTORS):
            lines.append(f"{n}거래일: UNKNOWN (데이터 형식 오류)")
            continue
        metrics = ", ".join(f"{label} {values[k] / 1e8:+,.1f}" for k, label in INVESTORS.items())
        lines.append(f"{n}거래일: {metrics}")
    lines.append("공식 원자료 대조 범위에만 적용. 해당 시점의 확정 공시·데이터 신선도는 별도 확인.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verified-json", required=True, help="Manual reconciliation output file")
    parser.add_argument("--target", required=True, choices=MARKETS)
    args = parser.parse_args()
    content = json.loads(Path(args.verified_json).read_text(encoding="utf-8"))
    print(concise(content, target=args.target))


if __name__ == "__main__":
    main()

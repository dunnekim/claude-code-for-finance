"""
네이버금융 컨센서스 조회 스크립트

사용법:
    python fetch_naver_consensus.py [종목코드]
    python fetch_naver_consensus.py 316140

출력:
    analysis/[기업명]_컨센서스.md

참고:
    - 네이버금융 웹 스크래핑 방식 (공식 API 없음)
    - HTML 구조 변경 시 스크립트 수정 필요
    - 워크숍 후 확장 실습용으로 제공
"""

import os
import sys
import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def get_company_name(stock_code):
    """종목코드로 기업명 조회"""
    url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
    resp = requests.get(url, headers=HEADERS)
    resp.encoding = "euc-kr"
    soup = BeautifulSoup(resp.text, "html.parser")

    title_tag = soup.select_one("div.wrap_company h2 a")
    if title_tag:
        return title_tag.get_text(strip=True)
    return stock_code


def fetch_consensus(stock_code):
    """증권사 투자의견 컨센서스 조회"""
    url = f"https://finance.naver.com/item/coinfo.naver?code={stock_code}&target=finsum_more"
    resp = requests.get(url, headers=HEADERS)
    resp.encoding = "euc-kr"
    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    tables = soup.select("table.gHead")
    for table in tables:
        rows = table.select("tr")
        for row in rows:
            cols = row.select("td")
            if len(cols) >= 4:
                results.append({
                    "날짜": cols[0].get_text(strip=True),
                    "증권사": cols[1].get_text(strip=True),
                    "의견": cols[2].get_text(strip=True),
                    "목표가": cols[3].get_text(strip=True),
                })

    return results


def fetch_current_price(stock_code):
    """현재 주가 조회"""
    url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
    resp = requests.get(url, headers=HEADERS)
    resp.encoding = "euc-kr"
    soup = BeautifulSoup(resp.text, "html.parser")

    price_tag = soup.select_one("p.no_today span.blind")
    if price_tag:
        return price_tag.get_text(strip=True)
    return "-"


def main():
    if len(sys.argv) < 2:
        print("사용법: python fetch_naver_consensus.py [종목코드]")
        print("예시:   python fetch_naver_consensus.py 316140")
        sys.exit(1)

    stock_code = sys.argv[1]

    print(f"[1/3] 기업 정보 조회 중... (종목코드: {stock_code})")
    corp_name = get_company_name(stock_code)
    current_price = fetch_current_price(stock_code)
    print(f"       → {corp_name} / 현재가: {current_price}원")

    print(f"[2/3] 투자의견 컨센서스 조회 중...")
    consensus = fetch_consensus(stock_code)
    print(f"       → {len(consensus)}건 조회")

    print(f"[3/3] 보고서 생성 중...")
    lines = []
    lines.append(f"# {corp_name} 컨센서스\n")
    lines.append(f"종목코드: {stock_code}")
    lines.append(f"현재가: {current_price}원")
    lines.append("")

    if consensus:
        lines.append("## 증권사 투자의견\n")
        lines.append("| 날짜 | 증권사 | 투자의견 | 목표주가 |")
        lines.append("|------|--------|---------|---------|")
        for item in consensus[:10]:
            lines.append(f"| {item['날짜']} | {item['증권사']} | {item['의견']} | {item['목표가']} |")
        lines.append("")
    else:
        lines.append("*컨센서스 데이터를 가져오지 못했습니다.*")
        lines.append("*네이버금융 HTML 구조가 변경되었을 수 있습니다.*")
        lines.append("")

    lines.append("*데이터 출처: 네이버금융 (finance.naver.com)*")
    lines.append("*웹 스크래핑 데이터이며, 정확성은 원본 출처에서 확인하세요.*")

    os.makedirs("analysis", exist_ok=True)
    output_path = f"analysis/{corp_name}_컨센서스.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"       → 저장 완료: {output_path}")


if __name__ == "__main__":
    main()

"""
OpenDart API 재무제표 조회 스크립트 (캐싱 지원)

사용법:
    python fetch_dart_financials.py [종목코드]
    python fetch_dart_financials.py 316140  # 우리금융지주

환경변수:
    OPENDART_API_KEY — OpenDart API 인증키 (필수)

출력:
    analysis/[기업명]_재무데이터.md

특징:
    - corpCode.xml(약 2MB)을 .cache/ 폴더에 24시간 캐싱
    - 같은 PC에서 두 번째 실행부터는 재다운로드 없이 즉시 시작
"""

import os
import sys
import zipfile
import io
import time
import requests
from xml.etree import ElementTree


CACHE_DIR = ".cache"
CACHE_FILE = os.path.join(CACHE_DIR, "corp_codes.xml")
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24시간


def get_api_key():
    key = os.environ.get("OPENDART_API_KEY")
    if not key:
        print("오류: OPENDART_API_KEY 환경변수가 설정되지 않았습니다.")
        print("설정 방법: setx OPENDART_API_KEY \"your_api_key\"")
        sys.exit(1)
    return key


def load_cached_corp_xml():
    """캐시된 corp_codes.xml을 로드. 없거나 만료되면 None 반환."""
    if not os.path.exists(CACHE_FILE):
        return None
    age = time.time() - os.path.getmtime(CACHE_FILE)
    if age > CACHE_TTL_SECONDS:
        return None
    with open(CACHE_FILE, "rb") as f:
        return f.read()


def save_corp_xml_cache(xml_data):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_FILE, "wb") as f:
        f.write(xml_data)


def get_corp_code(api_key, stock_code):
    """종목코드 → DART 고유번호(corp_code) 변환. 캐시 활용."""
    xml_data = load_cached_corp_xml()

    if xml_data is None:
        print("       (캐시 없음 — corpCode.xml 다운로드 중...)")
        url = "https://opendart.fss.or.kr/api/corpCode.xml"
        params = {"crtfc_key": api_key}
        resp = requests.get(url, params=params)

        if resp.status_code != 200:
            print(f"오류: corpCode.xml 다운로드 실패 (HTTP {resp.status_code})")
            sys.exit(1)

        z = zipfile.ZipFile(io.BytesIO(resp.content))
        xml_data = z.read("CORPCODE.xml")
        save_corp_xml_cache(xml_data)
        print(f"       (캐시 저장 완료: {CACHE_FILE})")
    else:
        print("       (캐시 사용)")

    root = ElementTree.fromstring(xml_data)

    for corp in root.findall("list"):
        code = corp.findtext("stock_code", "").strip()
        if code == stock_code:
            return corp.findtext("corp_code", "").strip(), corp.findtext("corp_name", "").strip()

    print(f"오류: 종목코드 {stock_code}에 해당하는 기업을 찾을 수 없습니다.")
    sys.exit(1)


def fetch_financials(api_key, corp_code, year, report_code="11011"):
    """단일회사 전체 재무제표 조회"""
    url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bsns_year": str(year),
        "reprt_code": report_code,
        "fs_div": "CFS",
    }
    resp = requests.get(url, params=params)
    data = resp.json()

    if data.get("status") != "000":
        return None

    return data.get("list", [])


def extract_key_items(financials):
    """핵심 재무 항목 추출 (제조업 매출액 + 금융업 영업수익 모두 지원)"""
    # 라벨 → (가능한 account_nm 리스트, 가능한 account_id 리스트)
    target_accounts = {
        "영업수익": (
            ["영업수익", "매출액"],  # 금융업·제조업 모두 커버
            ["ifrs-full_Revenue", "ifrs-full_Revenues"],
        ),
        "영업이익": (
            ["영업이익"],
            ["dart_OperatingIncomeLoss"],
        ),
        "당기순이익": (
            ["당기순이익"],
            [
                "ifrs-full_ProfitLoss",
                "ifrs-full_ProfitLossAttributableToOwnersOfParent",
            ],
        ),
        "자산총계": (["자산총계"], ["ifrs-full_Assets"]),
        "부채총계": (["부채총계"], ["ifrs-full_Liabilities"]),
        "자본총계": (["자본총계"], ["ifrs-full_Equity"]),
    }

    results = {}
    for item in financials:
        account_id = item.get("account_id", "")
        account_nm = item.get("account_nm", "")
        amount_str = item.get("thstrm_amount", "")

        if not amount_str or amount_str == "":
            continue

        for label, (names, ids) in target_accounts.items():
            if account_id in ids or account_nm in names:
                if label not in results:
                    try:
                        amount = int(amount_str.replace(",", ""))
                        results[label] = amount
                    except ValueError:
                        pass

    return results


def format_number(num):
    """백만원 단위로 포맷"""
    millions = round(num / 1_000_000)
    return f"{millions:,}"


def main():
    if len(sys.argv) < 2:
        print("사용법: python fetch_dart_financials.py [종목코드]")
        print("예시:   python fetch_dart_financials.py 316140  (우리금융지주)")
        sys.exit(1)

    stock_code = sys.argv[1]
    api_key = get_api_key()

    print(f"[1/4] 기업 고유번호 조회 중... (종목코드: {stock_code})")
    corp_code, corp_name = get_corp_code(api_key, stock_code)
    print(f"       → {corp_name} (corp_code: {corp_code})")

    years = [2022, 2023, 2024]
    all_data = {}

    for year in years:
        print(f"[2/4] {year}년 재무제표 조회 중...")
        financials = fetch_financials(api_key, corp_code, year)
        if financials:
            items = extract_key_items(financials)
            all_data[year] = items
            print(f"       → {len(items)}개 항목 추출")
        else:
            print(f"       → {year}년 데이터 없음 (사업보고서 미제출 가능)")

    if not all_data:
        print("오류: 조회된 데이터가 없습니다.")
        sys.exit(1)

    print("[3/4] 보고서 생성 중...")
    available_years = sorted(all_data.keys())
    items_order = ["영업수익", "영업이익", "당기순이익", "자산총계", "부채총계", "자본총계"]

    lines = []
    lines.append(f"# {corp_name} 재무 데이터\n")
    lines.append(f"종목코드: {stock_code}\n")
    lines.append(f"기준: 연결 재무제표 (사업보고서)\n")
    lines.append(f"단위: 백만원\n")
    lines.append("")

    header = "| 항목 | " + " | ".join(f"{y}년" for y in available_years) + " |"
    separator = "|------|" + "|".join("------:" for _ in available_years) + "|"
    lines.append(header)
    lines.append(separator)

    for item in items_order:
        row = f"| {item} |"
        for year in available_years:
            val = all_data.get(year, {}).get(item)
            if val is not None:
                row += f" {format_number(val)} |"
            else:
                row += " - |"
        lines.append(row)

    lines.append("")
    lines.append("*데이터 출처: 금융감독원 전자공시시스템 (OpenDart API)*")
    lines.append("*이 데이터는 학습용이며, 실제 투자 판단에 사용하지 마세요.*")

    os.makedirs("analysis", exist_ok=True)
    output_path = f"analysis/{corp_name}_재무데이터.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[4/4] 저장 완료 → {output_path}")


if __name__ == "__main__":
    main()

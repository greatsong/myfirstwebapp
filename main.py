# main.py
import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="서울 상권 분기 대시보드", layout="wide", page_icon="📊")

DATA_FILE = "서울시_상권분석서비스_샘플.csv"

RENAME_MAP = {
    "상권_구분_코드_명": "상권유형",
    "상권_코드": "상권코드",
    "상권_코드_명": "상권이름",
    "서비스_업종_코드_명": "업종",
    "당월_매출_금액": "분기매출액",
    "당월_매출_건수": "분기거래건수",
}

REQUIRED_COLS = {
    "기준_년분기_코드",
    "분기매출액",
    "분기거래건수",
    "상권이름",
    "업종",
}

@st.cache_data(show_spinner=False)
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="cp949")
    # 요청한 컬럼명으로 통일
    df = df.rename(columns=RENAME_MAP)
    # 숫자형 변환(문자 섞여 있어도 안전하게)
    for col in ["분기매출액", "분기거래건수"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def fmt_억원(x):
    return f"{(x or 0)/1e8:,.1f} 억원"

def fmt_만건(x):
    return f"{(x or 0)/1e4:,.1f} 만 건"

def fmt_cnt(x):
    return f"{int(x or 0):,} 개"

# ---------------- UI ----------------
st.title("📊 서울 상권 분기 대시보드")
st.caption("필터에서 분기를 선택하면 해당 분기의 메트릭만 반영돼요. (기본: 전체)")

# 데이터 로드
if not Path(DATA_FILE).exists():
    st.error(f"데이터 파일을 찾을 수 없어요: `{DATA_FILE}`\n"
             "파일 이름과 위치를 확인해 주세요. (코드와 같은 폴더)")
    st.stop()

df = load_data(DATA_FILE)

# 필수 컬럼 체크
missing = [c for c in REQUIRED_COLS if c not in df.columns]
if missing:
    st.error(f"아래 필수 컬럼이 누락되어 있어요: {missing}\n"
             "원본 헤더가 다르면 RENAME_MAP을 조정해 주세요.")
    st.stop()

# ---- 필터(분기) ----
q_options = sorted(df["기준_년분기_코드"].dropna().unique())
q_label_all = "전체"
selected = st.selectbox("🗓️ 분기 선택", options=[q_label_all] + list(map(str, q_options)), index=0)

if selected != q_label_all:
    df_view = df[df["기준_년분기_코드"].astype(str) == str(selected)]
else:
    df_view = df

# ---- 메트릭 계산 ----
total_sales = float(df_view["분기매출액"].sum(skipna=True))
total_cnt   = float(df_view["분기거래건수"].sum(skipna=True))
n_areas     = int(df_view["상권이름"].nunique(dropna=True))
n_cats      = int(df_view["업종"].nunique(dropna=True))

# ---- 4칸 메트릭 ----
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("💰 총 분기 매출액", fmt_억원(total_sales))
with c2:
    st.metric("🧾 총 분기 거래건수", fmt_만건(total_cnt))
with c3:
    st.metric("🏙️ 분석 상권 수", fmt_cnt(n_areas))
with c4:
    st.metric("🏷️ 업종 종류", fmt_cnt(n_cats))

# (선택) 하단에 간단 미리보기와 컬럼 설명
with st.expander("🔎 데이터 미리보기 / 컬럼 확인"):
    st.write("변환된 주요 컬럼: `기준_년분기_코드`, `상권유형`, `상권코드`, `상권이름`, `업종`, `분기매출액`, `분기거래건수`")
    st.dataframe(df_view.head(10), use_container_width=True)

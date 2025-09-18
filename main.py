# main.py
import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path

# ---------------- 기본 설정 ----------------
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
REQUIRED_COLS = {"기준_년분기_코드", "분기매출액", "분기거래건수", "상권이름", "업종", "상권유형"}

AGE_COLS = [
    "연령대_10_매출_금액", "연령대_20_매출_금액", "연령대_30_매출_금액",
    "연령대_40_매출_금액", "연령대_50_매출_금액", "연령대_60_이상_매출_금액"
]

# ---------------- 헬퍼 함수 ----------------
@st.cache_data(show_spinner=False)
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="cp949")
    df = df.rename(columns=RENAME_MAP)
    # 숫자형 변환
    num_cols = ["분기매출액", "분기거래건수", "남성_매출_금액", "여성_매출_금액"] + AGE_COLS
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # 문자열 정리
    for col in ["상권유형", "상권이름", "업종", "기준_년분기_코드"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    return df

def fmt_억원(x: float) -> str:
    x = 0 if pd.isna(x) else float(x)
    return f"{x/1e8:,.1f} 억원"

def fmt_만건(x: float) -> str:
    x = 0 if pd.isna(x) else float(x)
    return f"{x/1e4:,.1f} 만 건"

def fmt_cnt(x: int) -> str:
    x = 0 if pd.isna(x) else int(x)
    return f"{x:,} 개"

def add_medal(rank: int) -> str:
    return {1: "🥇 ", 2: "🥈 ", 3: "🥉 "}.get(rank, "")

# ---------------- 본문 ----------------
st.title("📊 서울 상권 분기 대시보드")

# 데이터 로드
if not Path(DATA_FILE).exists():
    st.error(f"데이터 파일을 찾을 수 없어요: `{DATA_FILE}`")
    st.stop()

df = load_data(DATA_FILE)

# 필수 컬럼 체크
missing = [c for c in REQUIRED_COLS if c not in df.columns]
if missing:
    st.error(f"아래 필수 컬럼이 누락되어 있어요: {missing}")
    st.stop()

# ---------------- 사이드바: 데이터 필터 ----------------
st.sidebar.header("🧰 데이터 필터")

# 분기 필터
q_all_label = "전체"
q_options = sorted(df["기준_년분기_코드"].dropna().astype(str).unique().tolist())
selected_quarters = st.sidebar.multiselect(
    "🗓️ 분기 선택",
    options=[q_all_label] + q_options,
    default=[q_all_label],
)

# 상권유형 필터
type_options = sorted(df["상권유형"].dropna().unique().tolist())
default_types = [v for v in ["골목상권", "전통시장"] if v in type_options]
if not default_types:
    default_types = type_options
selected_types = st.sidebar.multiselect(
    "🏙️ 상권유형",
    options=type_options,
    default=default_types,
)

# 업종 필터 (전체 기준 매출 TOP5)
top5_overall = (
    df.groupby("업종", as_index=False)["분기매출액"]
    .sum()
    .sort_values("분기매출액", ascending=False)
    .head(5)["업종"]
    .tolist()
)
biz_options = sorted(df["업종"].dropna().unique().tolist())
default_biz = [b for b in top5_overall if b in biz_options]
if not default_biz:
    default_biz = biz_options[:5]
selected_biz = st.sidebar.multiselect(
    "🏷️ 업종",
    options=biz_options,
    default=default_biz,
)

# ---------------- 필터 적용 (filtered_data) ----------------
filtered_data = df.copy()

if not selected_quarters or (q_all_label not in selected_quarters):
    if selected_quarters:
        filtered_data = filtered_data[filtered_data["기준_년분기_코드"].astype(str).isin(selected_quarters)]

if selected_types:
    filtered_data = filtered_data[filtered_data["상권유형"].isin(selected_types)]

if selected_biz:
    filtered_data = filtered_data[filtered_data["업종"].isin(selected_biz)]

# 데이터 개수 표시
st.sidebar.markdown(f"**필터링된 데이터: {len(filtered_data):,}건**")

# ---------------- CSV 다운로드 버튼 ----------------
csv_data = filtered_data.to_csv(index=False, encoding="cp949")
st.sidebar.download_button(
    label="📥 데이터 다운로드 (CSV)",
    data=csv_data,
    file_name="filtered_data.csv",
    mime="text/csv",
)

# ---------------- 출처 표기 ----------------
st.sidebar.markdown(
    "<small>데이터 출처: <a href='https://data.seoul.go.kr/' target='_blank'>서울 열린데이터광장</a></small>",
    unsafe_allow_html=True
)

if filtered_data.empty:
    st.warning("선택한 조건에 맞는 데이터가 없습니다.")
    st.stop()

# ---------------- 탭 ----------------
tab1, tab2 = st.tabs(["📈 매출 현황", "👥 고객 분석"])

# 매출 현황 탭
with tab1:
    total_sales = float(filtered_data["분기매출액"].sum(skipna=True))
    total_cnt   = float(filtered_data["분기거래건수"].sum(skipna=True))
    n_areas     = int(filtered_data["상권이름"].nunique(dropna=True))
    n_cats      = int(filtered_data["업종"].nunique(dropna=True))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("💰 총 분기 매출액", fmt_억원(total_sales))
    with c2:
        st.metric("🧾 총 분기 거래건수", fmt_만건(total_cnt))
    with c3:
        st.metric("🏙️ 분석 상권 수", fmt_cnt(n_areas))
    with c4:
        st.metric("🏷️ 업종 종류", fmt_cnt(n_cats))

    st.divider()

    # 업종별 매출 TOP 10
    top10 = (
        filtered_data.groupby("업종", as_index=False)["분기매출액"]
        .sum()
        .sort_values("분기매출액", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )
    top10["억원"] = top10["분기매출액"] / 1e8
    top10["순위"] = top10.index + 1
    top10["업종라벨"] = top10["순위"].apply(add_medal) + top10["업종"]

    st.subheader("📊 분기 매출 TOP 10 업종")

    base = alt.Chart(top10).encode(
        y=alt.Y("업종라벨:N", sort="-x", title=None),
        x=alt.X("억원:Q", title="매출액(억원)", axis=alt.Axis(format=",.1f")),
        tooltip=[
            alt.Tooltip("순위:O", title="순위"),
            alt.Tooltip("업종:N", title="업종"),
            alt.Tooltip("분기매출액:Q", title="매출액(원)", format=","),
            alt.Tooltip("억원:Q", title="매출액(억원)", format=",.1f"),
        ],
    )

    bars = base.mark_bar(cornerRadiusEnd=6).properties(height=320)
    labels = base.mark_text(align="left", dx=6, fontSize=12).encode(
        text=alt.Text("억원:Q", format=",.1f")
    )
    st.altair_chart(bars + labels, use_container_width=True)

# 고객 분석 탭
with tab2:
    st.subheader("🧑‍🤝‍🧑 성별 매출 비율")

    if "남성_매출_금액" in filtered_data.columns and "여성_매출_금액" in filtered_data.columns:
        gender_sum = {
            "남성": filtered_data["남성_매출_금액"].sum(skipna=True),
            "여성": filtered_data["여성_매출_금액"].sum(skipna=True),
        }
        gender_df = pd.DataFrame(
            {"성별": list(gender_sum.keys()), "매출액": list(gender_sum.values())}
        )
        gender_df["비율"] = gender_df["매출액"] / gender_df["매출액"].sum()

        gender_chart = alt.Chart(gender_df).mark_arc(innerRadius=60).encode(
            theta=alt.Theta("매출액:Q"),
            color=alt.Color("성별:N", legend=alt.Legend(title="성별")),
            tooltip=[
                alt.Tooltip("성별:N"),
                alt.Tooltip("매출액:Q", format=","),
                alt.Tooltip("비율:Q", format=".1%")
            ],
        )
        st.altair_chart(gender_chart, use_container_width=True)
    else:
        st.info("⚠️ 데이터에 성별 매출 컬럼(남성_매출_금액, 여성_매출_금액)이 없습니다.")

    st.subheader("📊 연령대별 매출 현황")

    age_available = [col for col in AGE_COLS if col in filtered_data.columns]
    if age_available:
        age_df = pd.DataFrame({
            "연령대": [col.replace("_매출_금액", "") for col in age_available],
            "매출액": [filtered_data[col].sum(skipna=True) for col in age_available]
        })

        age_chart = alt.Chart(age_df).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("연령대:N", title="연령대"),
            y=alt.Y("매출액:Q", title="매출액(원)", axis=alt.Axis(format=",")),
            tooltip=[alt.Tooltip("연령대:N"), alt.Tooltip("매출액:Q", format=",")]
        )
        st.altair_chart(age_chart, use_container_width=True)
    else:
        st.info("⚠️ 데이터에 연령대별 매출 컬럼이 없습니다.")

# ---------------- 푸터 ----------------
st.markdown("<hr style='margin-top:40px;margin-bottom:10px'>", unsafe_allow_html=True)
st.markdown("<div style='text-align:center; color:gray;'>Made by 석리송, with AI support</div>", unsafe_allow_html=True)

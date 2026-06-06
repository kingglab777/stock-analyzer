"""
미국 주식 저평가 종목 분석기 - Streamlit 웹앱 버전
=====================================================
실행 방법:
    streamlit run app.py
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# ──────────────────────────────────────────────
# 페이지 기본 설정
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="미국 주식 저평가 분석기",
    page_icon="📊",
    layout="wide",
)

# ──────────────────────────────────────────────
# 종목 데이터
# ──────────────────────────────────────────────
SECTORS = {
    "기술 (Tech)": [
        ("AAPL",  "Apple"),
        ("MSFT",  "Microsoft"),
        ("GOOGL", "Alphabet"),
        ("AMZN",  "Amazon"),
        ("META",  "Meta Platforms"),
    ],
    "반도체 (Semiconductor)": [
        ("NVDA",  "NVIDIA"),
        ("AVGO",  "Broadcom"),
        ("ASML",  "ASML"),
        ("TSM",   "Taiwan Semiconductor"),
    ],
    "금융 (Finance)": [
        ("JPM",   "JPMorgan Chase"),
        ("V",     "Visa"),
        ("MA",    "Mastercard"),
        ("BRK-B", "Berkshire Hathaway"),
    ],
    "소비재 (Consumer)": [
        ("PG",    "Procter & Gamble"),
        ("KO",    "Coca-Cola"),
        ("PEP",   "PepsiCo"),
        ("COST",  "Costco"),
        ("WMT",   "Walmart"),
        ("MCD",   "McDonald's"),
    ],
    "헬스케어 (Healthcare)": [
        ("JNJ",   "Johnson & Johnson"),
        ("UNH",   "UnitedHealth Group"),
        ("LLY",   "Eli Lilly"),
        ("ABBV",  "AbbVie"),
    ],
    "산업재 (Industrial)": [
        ("HON",   "Honeywell"),
        ("CAT",   "Caterpillar"),
        ("UNP",   "Union Pacific"),
    ],
    "소프트웨어/미디어": [
        ("ADBE",  "Adobe"),
        ("CRM",   "Salesforce"),
        ("NFLX",  "Netflix"),
    ],
}

ALL_STOCKS = [(t, n, s) for s, stocks in SECTORS.items() for t, n in stocks]

# ──────────────────────────────────────────────
# 데이터 수집 함수
# ──────────────────────────────────────────────
@st.cache_data(ttl=600)  # 10분 캐시 (같은 데이터 반복 호출 방지)
def fetch_all_data():
    results = []
    for ticker, name, sector in ALL_STOCKS:
        try:
            hist = yf.Ticker(ticker).history(period="1y", interval="1d")
            if hist.empty:
                continue
            current    = float(hist["Close"].iloc[-1])
            prev_close = float(hist["Close"].iloc[-2])
            high_52w   = float(hist["High"].max())
            low_52w    = float(hist["Low"].min())
            drop_pct   = (high_52w - current) / high_52w * 100
            day_change = (current - prev_close) / prev_close * 100
            results.append({
                "티커":          ticker,
                "종목명":        name,
                "섹터":          sector,
                "현재가($)":     round(current, 2),
                "52주 고가($)":  round(high_52w, 2),
                "52주 저가($)":  round(low_52w, 2),
                "신고가 대비 하락(%)": round(drop_pct, 1),
                "당일 변동(%)":  round(day_change, 2),
            })
        except Exception:
            continue
    return pd.DataFrame(results)


@st.cache_data(ttl=600)
def fetch_chart(ticker):
    hist = yf.Ticker(ticker).history(period="1y", interval="1d")
    return hist


# ──────────────────────────────────────────────
# 사이드바 — 필터 설정
# ──────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ 설정")
    st.markdown("---")

    threshold = st.slider(
        "저평가 기준 (%)",
        min_value=5, max_value=60, value=20, step=1,
        help="신고가 대비 이 % 이상 하락한 종목을 저평가로 분류합니다"
    )

    selected_sectors = st.multiselect(
        "섹터 필터",
        options=list(SECTORS.keys()),
        default=list(SECTORS.keys()),
    )

    sort_col = st.selectbox(
        "정렬 기준",
        ["신고가 대비 하락(%)", "현재가($)", "당일 변동(%)", "종목명"],
        index=0,
    )

    st.markdown("---")
    run = st.button("🔍  조회하기", use_container_width=True, type="primary")
    st.caption("버튼을 누를 때마다 최신 데이터로 조회합니다.")
    st.caption("데이터 출처: Yahoo Finance")


# ──────────────────────────────────────────────
# 메인 화면
# ──────────────────────────────────────────────
st.title("📊 미국 주식 저평가 종목 분석기")
st.caption(f"일봉 기준 최근 1년 | 신고가 대비 {threshold}% 이상 하락 종목을 저평가로 분류")

if run:
    # 캐시 초기화 후 새로 불러오기
    fetch_all_data.clear()
    fetch_chart.clear()

with st.spinner("야후 파이낸스에서 데이터 불러오는 중..."):
    df = fetch_all_data()

if df.empty:
    st.error("데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")
    st.stop()

# 섹터 필터 적용
df = df[df["섹터"].isin(selected_sectors)]

# 정렬
ascending = sort_col == "종목명"
df_sorted = df.sort_values(sort_col, ascending=ascending)

# 저평가 / 전체 분리
df_under = df_sorted[df_sorted["신고가 대비 하락(%)"] >= threshold]
df_all   = df_sorted.copy()

# ── 요약 지표 카드 ─────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("전체 종목",   f"{len(df_all)}개")
col2.metric("저평가 종목", f"{len(df_under)}개",
            delta=f"기준: -{threshold}%", delta_color="inverse")
col3.metric("평균 하락률",
            f"{df_all['신고가 대비 하락(%)'].mean():.1f}%")
col4.metric("최대 하락",
            f"{df_all['신고가 대비 하락(%)'].max():.1f}%  "
            f"({df_all.loc[df_all['신고가 대비 하락(%)'].idxmax(), '티커']})")

st.markdown("---")

# ── 탭 구성 ───────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    f"🔴 저평가 종목 ({len(df_under)}개)",
    f"📋 전체 종목 ({len(df_all)}개)",
    "📈 차트 조회",
])

# ── 탭1: 저평가 종목 ──────────────────────────
with tab1:
    if df_under.empty:
        st.info(f"현재 기준({threshold}%) 이상 하락한 종목이 없습니다. 사이드바에서 기준을 낮춰보세요.")
    else:
        # 하락률 막대 차트
        fig = go.Figure(go.Bar(
            x=df_under["티커"],
            y=df_under["신고가 대비 하락(%)"],
            marker_color=[
                "#E24B4A" if v >= 30 else "#EF9F27" if v >= 20 else "#378ADD"
                for v in df_under["신고가 대비 하락(%)"]
            ],
            text=df_under["신고가 대비 하락(%)"].apply(lambda x: f"-{x}%"),
            textposition="outside",
        ))
        fig.update_layout(
            title="저평가 종목 신고가 대비 하락률",
            yaxis_title="하락률 (%)",
            xaxis_title="",
            height=350,
            margin=dict(t=40, b=20),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        fig.add_hline(y=threshold, line_dash="dash",
                      line_color="gray", annotation_text=f"기준선 -{threshold}%")
        st.plotly_chart(fig, use_container_width=True)

        # 테이블
        st.dataframe(
            df_under.reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
            column_config={
                "신고가 대비 하락(%)": st.column_config.ProgressColumn(
                    "신고가 대비 하락(%)", min_value=0, max_value=60, format="%.1f%%"
                ),
                "당일 변동(%)": st.column_config.NumberColumn(
                    "당일 변동(%)", format="%.2f%%"
                ),
            }
        )

        # 섹터별 요약
        st.markdown("#### 섹터별 분포")
        sector_summary = (
            df_under.groupby("섹터")
            .agg(종목수=("티커", "count"),
                 평균하락률=("신고가 대비 하락(%)", "mean"))
            .sort_values("평균하락률", ascending=False)
            .reset_index()
        )
        sector_summary["평균하락률"] = sector_summary["평균하락률"].round(1)
        st.dataframe(sector_summary, use_container_width=True, hide_index=True)

# ── 탭2: 전체 종목 ────────────────────────────
with tab2:
    # 색상 강조 함수
    def highlight_row(row):
        drop = row["신고가 대비 하락(%)"]
        if drop >= 30:
            return ["background-color: #fff0f0"] * len(row)
        elif drop >= threshold:
            return ["background-color: #fff8ee"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df_all.reset_index(drop=True).style.apply(highlight_row, axis=1),
        use_container_width=True,
        hide_index=True,
        column_config={
            "신고가 대비 하락(%)": st.column_config.ProgressColumn(
                "신고가 대비 하락(%)", min_value=0, max_value=60, format="%.1f%%"
            ),
            "당일 변동(%)": st.column_config.NumberColumn(
                "당일 변동(%)", format="%.2f%%"
            ),
        }
    )

# ── 탭3: 차트 조회 ────────────────────────────
with tab3:
    st.markdown("#### 개별 종목 캔들차트 (1년)")

    all_tickers = [t for t, _, _ in ALL_STOCKS]
    all_names   = {t: n for t, n, _ in ALL_STOCKS}

    selected = st.selectbox(
        "종목 선택",
        options=all_tickers,
        format_func=lambda x: f"{x}  —  {all_names.get(x, '')}",
    )

    if selected:
        with st.spinner(f"{selected} 차트 불러오는 중..."):
            hist = fetch_chart(selected)

        if not hist.empty:
            high_52w = hist["High"].max()
            current  = hist["Close"].iloc[-1]
            drop     = (high_52w - current) / high_52w * 100

            m1, m2, m3 = st.columns(3)
            m1.metric("현재가",    f"${current:.2f}")
            m2.metric("52주 고가", f"${high_52w:.2f}")
            m3.metric("신고가 대비 하락", f"-{drop:.1f}%",
                      delta_color="inverse",
                      delta=f"{'⚠️ 저평가' if drop >= threshold else '✅ 양호'}")

            fig2 = go.Figure(data=[go.Candlestick(
                x=hist.index,
                open=hist["Open"],
                high=hist["High"],
                low=hist["Low"],
                close=hist["Close"],
                increasing_line_color="#1a7a1a",
                decreasing_line_color="#cc3333",
            )])
            fig2.add_hline(
                y=high_52w, line_dash="dot", line_color="orange",
                annotation_text=f"52주 고가 ${high_52w:.2f}",
                annotation_position="top left",
            )
            fig2.add_hline(
                y=current, line_dash="dot", line_color="#378ADD",
                annotation_text=f"현재가 ${current:.2f}",
                annotation_position="bottom left",
            )
            fig2.update_layout(
                title=f"{selected} — {all_names.get(selected, '')} 1년 캔들차트",
                yaxis_title="가격 ($)",
                xaxis_rangeslider_visible=False,
                height=480,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig2, use_container_width=True)

# ── 푸터 ──────────────────────────────────────
st.markdown("---")
st.caption(f"마지막 조회: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  데이터: Yahoo Finance  |  10분 캐시 적용")
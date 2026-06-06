"""
미국 주식 저평가 종목 분석기
==============================
yfinance로 야후 파이낸스 데이터를 가져와
일봉 기준 최근 1년 최고가 대비 20% 이상 하락 종목을 "저평가 종목"으로 분류합니다.

설치 방법:
    pip install yfinance

실행 방법:
    python stock_analyzer.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import datetime

try:
    import yfinance as yf
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance"])
    import yfinance as yf


# ──────────────────────────────────────────────
# 분석 대상 종목 (섹터별 분류)
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

ALL_STOCKS = [(ticker, name) for stocks in SECTORS.values() for ticker, name in stocks]

THRESHOLD_DEFAULT = 20  # 저평가 기준 (%)


# ──────────────────────────────────────────────
# 데이터 수집 함수
# ──────────────────────────────────────────────
def fetch_stock_data(ticker: str) -> dict:
    """야후 파이낸스에서 1년 일봉 데이터를 가져와 분석 결과를 반환합니다."""
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1y", interval="1d")

    if hist.empty:
        raise ValueError(f"{ticker}: 데이터 없음")

    high_52w    = float(hist["High"].max())
    low_52w     = float(hist["Low"].min())
    current     = float(hist["Close"].iloc[-1])
    prev_close  = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
    day_change  = (current - prev_close) / prev_close * 100
    drop_pct    = (high_52w - current) / high_52w * 100
    data_date   = hist.index[-1].strftime("%Y-%m-%d")

    return {
        "ticker":     ticker,
        "current":    current,
        "high_52w":   high_52w,
        "low_52w":    low_52w,
        "drop_pct":   drop_pct,
        "day_change": day_change,
        "date":       data_date,
    }


def analyze_all(threshold: float, progress_cb=None) -> tuple[list, list]:
    """
    모든 종목을 조회해 저평가 / 전체 결과를 반환합니다.
    progress_cb(done, total) 콜백으로 진행 상황을 알립니다.
    """
    undervalued = []
    all_results = []
    errors      = []
    total       = len(ALL_STOCKS)

    for i, (ticker, name) in enumerate(ALL_STOCKS):
        try:
            d = fetch_stock_data(ticker)
            d["name"] = name
            d["sector"] = next(
                sec for sec, stocks in SECTORS.items()
                if any(t == ticker for t, _ in stocks)
            )
            all_results.append(d)
            if d["drop_pct"] >= threshold:
                undervalued.append(d)
        except Exception as e:
            errors.append(f"{ticker}: {e}")

        if progress_cb:
            progress_cb(i + 1, total)

    undervalued.sort(key=lambda x: x["drop_pct"], reverse=True)
    return undervalued, all_results, errors


# ──────────────────────────────────────────────
# Tkinter GUI
# ──────────────────────────────────────────────
class StockAnalyzerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("미국 주식 저평가 종목 분석기")
        self.geometry("1080x720")
        self.minsize(800, 500)
        self.configure(bg="#f5f5f0")
        self._build_ui()

    # ── UI 구성 ────────────────────────────────
    def _build_ui(self):
        BG   = "#f5f5f0"
        CARD = "#ffffff"
        ACCENT = "#1a1a1a"

        # 헤더
        header = tk.Frame(self, bg=ACCENT, pady=14)
        header.pack(fill="x")
        tk.Label(header, text="📊  미국 주식 저평가 종목 분석기",
                 font=("Helvetica", 16, "bold"), fg="white", bg=ACCENT).pack(side="left", padx=20)
        tk.Label(header, text="Yahoo Finance | 일봉 1년 기준",
                 font=("Helvetica", 10), fg="#aaaaaa", bg=ACCENT).pack(side="right", padx=20)

        # 컨트롤 바
        ctrl = tk.Frame(self, bg=BG, pady=12)
        ctrl.pack(fill="x", padx=20)

        tk.Label(ctrl, text="저평가 기준 (신고가 대비 하락률):",
                 font=("Helvetica", 11), bg=BG).pack(side="left")
        self.threshold_var = tk.IntVar(value=THRESHOLD_DEFAULT)
        tk.Spinbox(ctrl, from_=1, to=90, textvariable=self.threshold_var,
                   width=5, font=("Helvetica", 11)).pack(side="left", padx=6)
        tk.Label(ctrl, text="% 이상", font=("Helvetica", 11), bg=BG).pack(side="left")

        self.btn_fetch = tk.Button(
            ctrl, text="  조회하기  ", font=("Helvetica", 11, "bold"),
            bg=ACCENT, fg="white", relief="flat", cursor="hand2",
            padx=12, pady=4, command=self._start_fetch
        )
        self.btn_fetch.pack(side="left", padx=20)

        self.status_var = tk.StringVar(value="조회 버튼을 누르면 분석을 시작합니다.")
        tk.Label(ctrl, textvariable=self.status_var,
                 font=("Helvetica", 10), fg="#666666", bg=BG).pack(side="left")

        # 진행 바
        self.progress = ttk.Progressbar(self, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=20, pady=(0, 6))

        # 탭
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        # 탭1: 저평가 종목
        self.tab_under = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(self.tab_under, text="🔴  저평가 종목")
        self._build_table(self.tab_under, "under")

        # 탭2: 전체 종목
        self.tab_all = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(self.tab_all, text="📋  전체 종목")
        self._build_table(self.tab_all, "all")

        # 탭3: 섹터 요약
        self.tab_sector = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(self.tab_sector, text="🗂  섹터 요약")
        self._build_sector_panel()

    def _build_table(self, parent, key):
        cols = ("ticker", "name", "sector", "current", "high_52w", "low_52w",
                "drop_pct", "day_change", "date")
        headers = ("티커", "종목명", "섹터", "현재가($)", "52주 고가($)", "52주 저가($)",
                   "신고가 대비 하락(%)", "당일 변동(%)", "기준일")

        frame = tk.Frame(parent, bg="#f5f5f0")
        frame.pack(fill="both", expand=True, padx=0, pady=0)

        scrolly = ttk.Scrollbar(frame, orient="vertical")
        scrolly.pack(side="right", fill="y")
        scrollx = ttk.Scrollbar(frame, orient="horizontal")
        scrollx.pack(side="bottom", fill="x")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                         background="white", foreground="#1a1a1a",
                         rowheight=26, fieldbackground="white",
                         font=("Helvetica", 10))
        style.configure("Treeview.Heading",
                         background="#1a1a1a", foreground="white",
                         font=("Helvetica", 10, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", "#dce8ff")])

        tv = ttk.Treeview(frame, columns=cols, show="headings",
                          yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        col_widths = [60, 190, 140, 90, 100, 100, 130, 100, 90]
        for col, hdr, w in zip(cols, headers, col_widths):
            tv.heading(col, text=hdr,
                       command=lambda c=col, t=tv: self._sort_col(t, c))
            tv.column(col, width=w, anchor="center", minwidth=60)

        tv.tag_configure("danger",  background="#fff0f0")
        tv.tag_configure("warn",    background="#fff8ee")
        tv.tag_configure("ok",      background="#f0fff4")
        tv.tag_configure("down",    foreground="#cc3333")
        tv.tag_configure("up",      foreground="#1a7a1a")
        tv.pack(fill="both", expand=True)
        scrolly.config(command=tv.yview)
        scrollx.config(command=tv.xview)

        setattr(self, f"tv_{key}", tv)

    def _build_sector_panel(self):
        self.sector_text = tk.Text(self.tab_sector, font=("Courier", 11),
                                   bg="white", fg="#1a1a1a",
                                   relief="flat", wrap="none",
                                   padx=16, pady=12)
        self.sector_text.pack(fill="both", expand=True)
        self.sector_text.insert("end", "조회 후 섹터 요약이 표시됩니다.\n")
        self.sector_text.config(state="disabled")

    # ── 정렬 ───────────────────────────────────
    def _sort_col(self, tv, col):
        items = [(tv.set(k, col), k) for k in tv.get_children("")]
        try:
            items.sort(key=lambda x: float(x[0].replace(",", "")), reverse=True)
        except ValueError:
            items.sort()
        for idx, (_, k) in enumerate(items):
            tv.move(k, "", idx)

    # ── 데이터 조회 ────────────────────────────
    def _start_fetch(self):
        self.btn_fetch.config(state="disabled", text="  조회 중...  ")
        self.progress["value"] = 0
        self.tv_under.delete(*self.tv_under.get_children())
        self.tv_all.delete(*self.tv_all.get_children())
        threshold = self.threshold_var.get()
        threading.Thread(target=self._fetch_thread, args=(threshold,), daemon=True).start()

    def _fetch_thread(self, threshold):
        total = len(ALL_STOCKS)

        def progress_cb(done, total):
            pct = done / total * 100
            self.after(0, lambda: self.progress.configure(value=pct))
            self.after(0, lambda: self.status_var.set(
                f"조회 중... {done}/{total}  ({pct:.0f}%)"))

        undervalued, all_results, errors = analyze_all(threshold, progress_cb)
        self.after(0, lambda: self._update_ui(undervalued, all_results, errors, threshold))

    def _update_ui(self, undervalued, all_results, errors, threshold):
        # 저평가 탭
        self.tv_under.delete(*self.tv_under.get_children())
        for d in undervalued:
            tag = "danger" if d["drop_pct"] >= 30 else "warn"
            self.tv_under.insert("", "end", values=(
                d["ticker"], d["name"], d["sector"],
                f"{d['current']:.2f}",
                f"{d['high_52w']:.2f}",
                f"{d['low_52w']:.2f}",
                f"{d['drop_pct']:.1f}%",
                f"{d['day_change']:+.2f}%",
                d["date"],
            ), tags=(tag,))

        # 전체 탭
        self.tv_all.delete(*self.tv_all.get_children())
        sorted_all = sorted(all_results, key=lambda x: x["drop_pct"], reverse=True)
        for d in sorted_all:
            tag = "danger" if d["drop_pct"] >= 30 else "warn" if d["drop_pct"] >= threshold else "ok"
            self.tv_all.insert("", "end", values=(
                d["ticker"], d["name"], d["sector"],
                f"{d['current']:.2f}",
                f"{d['high_52w']:.2f}",
                f"{d['low_52w']:.2f}",
                f"{d['drop_pct']:.1f}%",
                f"{d['day_change']:+.2f}%",
                d["date"],
            ), tags=(tag,))

        # 섹터 요약
        self._update_sector(all_results, threshold)

        # 탭 제목 업데이트
        self.notebook.tab(0, text=f"🔴  저평가 종목  ({len(undervalued)}개)")
        self.notebook.tab(1, text=f"📋  전체 종목  ({len(all_results)}개)")

        # 상태 업데이트
        now = datetime.datetime.now().strftime("%H:%M:%S")
        msg = (f"✅  완료 ({now}) — "
               f"전체 {len(all_results)}개 중 저평가 {len(undervalued)}개 (기준: -{threshold}%)")
        if errors:
            msg += f"  |  오류 {len(errors)}개: {', '.join(errors[:3])}"
        self.status_var.set(msg)
        self.progress["value"] = 100
        self.btn_fetch.config(state="normal", text="  조회하기  ")

    def _update_sector(self, all_results, threshold):
        lines = []
        lines.append(f"{'섹터':<22} {'종목수':>5}  {'저평가':>5}  {'평균하락':>8}  {'최대하락':>8}")
        lines.append("─" * 58)

        for sector in SECTORS:
            sector_stocks = [d for d in all_results if d["sector"] == sector]
            if not sector_stocks:
                continue
            uv = [d for d in sector_stocks if d["drop_pct"] >= threshold]
            avg_drop = sum(d["drop_pct"] for d in sector_stocks) / len(sector_stocks)
            max_drop = max(d["drop_pct"] for d in sector_stocks)
            lines.append(
                f"{sector:<22} {len(sector_stocks):>5}  {len(uv):>5}  "
                f"{avg_drop:>7.1f}%  {max_drop:>7.1f}%"
            )

        lines.append("")
        lines.append("─" * 58)
        lines.append("[ 저평가 종목 상세 ]")
        lines.append("")

        by_sector = {}
        for d in all_results:
            if d["drop_pct"] >= threshold:
                by_sector.setdefault(d["sector"], []).append(d)

        if not by_sector:
            lines.append(f"  기준({threshold}%) 이상 하락 종목 없음")
        else:
            for sector, stocks in by_sector.items():
                lines.append(f"  ▶ {sector}")
                for d in sorted(stocks, key=lambda x: x["drop_pct"], reverse=True):
                    bar = "█" * int(d["drop_pct"] / 5)
                    lines.append(
                        f"     {d['ticker']:<6} {d['name']:<28} "
                        f"-{d['drop_pct']:.1f}%  {bar}"
                    )
                lines.append("")

        self.sector_text.config(state="normal")
        self.sector_text.delete("1.0", "end")
        self.sector_text.insert("end", "\n".join(lines))
        self.sector_text.config(state="disabled")


# ──────────────────────────────────────────────
# 실행 진입점
# ──────────────────────────────────────────────
if __name__ == "__main__":
    app = StockAnalyzerApp()
    app.mainloop()
import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import datetime
import altair as alt
import json
import os
import streamlit.components.v1 as components 

# ---------------------------------------------------------
# 페이지 기본 설정 (제목 이모지 🚀)
# ---------------------------------------------------------
st.set_page_config(page_title="미국 주식 대시보드 V47.1", layout="wide")

# =========================================================
# [PWA 설정] 스마트폰에서 앱처럼 보이게 하는 코드 📱
# =========================================================
def inject_pwa_meta():
    pwa_html = """
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, minimal-ui">
    
    <link rel="apple-touch-icon" href="https://cdn-icons-png.flaticon.com/512/2503/2503939.png">
    <link rel="icon" type="image/png" href="https://cdn-icons-png.flaticon.com/512/2503/2503939.png">
    
    <style>
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 5rem;
        }
    </style>
    """
    st.markdown(pwa_html, unsafe_allow_html=True)

inject_pwa_meta()

# [핵심] 자동 새로고침 스크립트 (600초 = 10분마다 새로고침)
components.html(
    """
        <script>
            setTimeout(function(){
                window.location.reload();
            }, 600000);
        </script>
    """,
    height=0
)

col_title, col_time = st.columns([3, 1])
with col_title:
    st.title("곤삼's 2030-50 마스터플랜 🚀")
with col_time:
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"🔄 Last Updated: {now_str}")

# ---------------------------------------------------------
# [Session State 초기화]
# ---------------------------------------------------------
if 'total_family_asset' not in st.session_state:
    st.session_state['total_family_asset'] = 0.0
if 'total_loan_balance' not in st.session_state:
    st.session_state['total_loan_balance'] = 0.0
if 'asset_breakdown' not in st.session_state:
    st.session_state['asset_breakdown'] = {"주식(달러포함)": 0.0, "현금(원화)": 0.0, "부동산": 0.0}
if 'core_tickers' not in st.session_state:
    st.session_state['core_tickers'] = "NVDA, TSLA, AAPL, MSFT"
if 'watch_tickers' not in st.session_state:
    st.session_state['watch_tickers'] = "PLTR, SOXL, TQQQ, AMD"

if 'sim_ticker_main' not in st.session_state:
    st.session_state['sim_ticker_main'] = "NVDA"

# ---------------------------------------------------------
# [함수] 데이터 가져오기 및 계산
# ---------------------------------------------------------
@st.cache_data(ttl=600)
def get_exchange_rate():
    try:
        df = yf.Ticker("KRW=X").history(period="5d")
        if df.empty: return 1400.0, 0.0
        return df['Close'].iloc[-1], df['Close'].iloc[-1] - df['Close'].iloc[-2]
    except:
        return 1400.0, 0.0

@st.cache_data(ttl=300)
def get_current_price_only(ticker):
    try:
        if not ticker: return 0.0
        df = yf.Ticker(ticker).history(period="1d")
        if df.empty: return 0.0
        return df['Close'].iloc[-1]
    except:
        return 0.0

@st.cache_data(ttl=300)
def get_daily_diff_amount(ticker):
    try:
        if not ticker: return 0.0
        df = yf.Ticker(ticker).history(period="5d")
        if len(df) < 2: return 0.0
        curr = df['Close'].iloc[-1]
        prev = df['Close'].iloc[-2]
        return curr - prev 
    except:
        return 0.0

def calculate_daily_stock_change_total(usd_krw):
    total_diff_krw = 0.0
    for key in st.session_state:
        if key.startswith("t_") and len(key.split("_")) >= 3:
            ticker = st.session_state[key]
            qty_key = key.replace("t_", "q_")
            qty = st.session_state.get(qty_key, 0)
            if ticker and qty > 0:
                diff_per_share = get_daily_diff_amount(ticker)
                total_diff_usd = diff_per_share * qty
                total_diff_krw += total_diff_usd * usd_krw
    return total_diff_krw

def calculate_and_render_portfolio(user_key, default_name, usd_krw):
    st.markdown(f"### 👤 {default_name}")
    name = st.text_input("이름", value=default_name, key=f"nm_{user_key}")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        cash_usd = st.number_input("예수금 (현금 $)", value=500.0, step=100.0, key=f"csh_{user_key}")
    with col_c2:
        cash_krw = st.number_input("예수금 (현금 ₩)", value=0, step=10000, format="%d", key=f"csh_krw_{user_key}")

    stock_count = st.number_input("보유 종목 수", min_value=1, max_value=10, value=1, step=1, key=f"cnt_{user_key}")
    
    total_stock_value = 0.0
    total_daily_change_usd = 0.0 
    
    portfolio_list = []

    for i in range(stock_count):
        st.markdown(f"**종목 {i+1}**")
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            tick = st.text_input(f"티커", value="AAPL" if i==0 else "", key=f"t_{user_key}_{i}").upper()
        with c2: 
            qty = st.number_input(f"수량", value=5 if i==0 else 0, step=1, key=f"q_{user_key}_{i}")
        with c3: 
            buy_price = st.number_input(f"매수가($)", value=150.0, step=0.1, key=f"p_{user_key}_{i}")

        if tick and qty > 0:
            cur_price = get_current_price_only(tick)
            if cur_price > 0:
                invest_amt = buy_price * qty
                eval_amt = cur_price * qty
                profit = eval_amt - invest_amt
                rate = (profit / invest_amt * 100) if invest_amt > 0 else 0
                total_stock_value += eval_amt
                
                daily_diff = get_daily_diff_amount(tick) * qty
                total_daily_change_usd += daily_diff

                portfolio_list.append({
                    "티커": tick, "수량": qty, 
                    "평가금($)": eval_amt, "손익($)": profit, "수익률": f"{rate:.1f}%"
                })
                st.caption(f"└ 현재가 ${cur_price:.2f} | 평가금 ${eval_amt:,.0f} ({rate:+.1f}%)")
    
    st.divider()
    
    total_asset_usd = total_stock_value + cash_usd + (cash_krw / usd_krw if usd_krw > 0 else 0)
    total_asset_krw = (total_stock_value + cash_usd) * usd_krw + cash_krw
    
    st.metric(
        f"{name} 총 자산 ($)", 
        f"${total_asset_usd:,.2f}", 
        delta=f"${total_daily_change_usd:,.2f} (전일대비)"
    )
    st.markdown(f"<span style='color:green; font-size:1.1em; font-weight:bold'>🇰🇷 원화 환산: {total_asset_krw:,.0f}원</span>", unsafe_allow_html=True)
    
    with st.expander(f"{name} 상세 포트폴리오"):
            if portfolio_list: st.dataframe(pd.DataFrame(portfolio_list))
            else: st.info("종목을 입력해주세요.")

    return total_asset_usd

# ---------------------------------------------------------
# [핵심] 데이터 저장 및 불러오기 시스템 (히스토리 기능 개선)
# ---------------------------------------------------------
DATA_FILE = "stock_dashboard_data.json"
HISTORY_FILE = "asset_history.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
                for key, value in saved_data.items():
                    st.session_state[key] = value
        except Exception as e:
            st.error(f"데이터 로드 실패: {e}")

# [수정된 함수] 자산 이력 기록 함수 (타입 에러 해결 및 호환성 강화)
def log_asset_history(total_asset_krw, net_asset_krw):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # 새로 들어갈 데이터도 명확하게 float(실수)로 변환해서 DataFrame 생성
    new_data = pd.DataFrame({
        "Date": [today], 
        "TotalAsset": [float(total_asset_krw)], 
        "NetAsset": [float(net_asset_krw)]
    })
    
    try:
        if os.path.exists(HISTORY_FILE):
            df = pd.read_csv(HISTORY_FILE)
            
            # -------------------------------------------------------
            # [마이그레이션 & 타입 강제 변환]
            # -------------------------------------------------------
            # 1. 구버전 컬럼명(Asset)이 있으면 신버전(TotalAsset)으로 변경
            if 'Asset' in df.columns:
                df.rename(columns={'Asset': 'TotalAsset'}, inplace=True)
            
            # 2. TotalAsset 컬럼이 없으면 생성, 있으면 실수형(float)으로 변환 ★핵심 해결책★
            if 'TotalAsset' not in df.columns:
                df['TotalAsset'] = 0.0
            else:
                df['TotalAsset'] = df['TotalAsset'].astype(float)

            # 3. NetAsset 컬럼이 없으면 TotalAsset 값으로 채움, 있으면 실수형(float)으로 변환 ★핵심 해결책★
            if 'NetAsset' not in df.columns:
                df['NetAsset'] = df['TotalAsset']
            else:
                df['NetAsset'] = df['NetAsset'].astype(float)
            # -------------------------------------------------------

            if today in df['Date'].values:
                # 오늘 날짜 행 업데이트
                idx = df[df['Date'] == today].index
                # 이제 컬럼이 float 설정이 되어 있으므로 소수점을 넣어도 경고가 뜨지 않습니다.
                df.loc[idx, 'TotalAsset'] = float(total_asset_krw)
                df.loc[idx, 'NetAsset'] = float(net_asset_krw)
            else:
                df = pd.concat([df, new_data], ignore_index=True)
        else:
            df = new_data
        
        df.to_csv(HISTORY_FILE, index=False)
    except Exception as e:
        st.error(f"히스토리 저장 실패: {e}")

def save_data():
    try:
        data_to_save = {k: v for k, v in st.session_state.items() if isinstance(v, (int, float, str, bool, dict, list))}
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        
        # [수정] 저장 시 총자산과 순자산을 함께 기록
        current_total = st.session_state.get('total_family_asset', 0.0)
        current_loan = st.session_state.get('total_loan_balance', 0.0)
        current_net = current_total - current_loan
        log_asset_history(current_total, current_net)
        
        st.toast("✅ 데이터 및 자산 추세가 저장되었습니다!", icon="💾")
    except Exception as e:
        st.error(f"데이터 저장 실패: {e}")

if 'data_loaded' not in st.session_state:
    load_data()
    st.session_state['data_loaded'] = True

# ---------------------------------------------------------
# 메인 화면: 탭 구성
# ---------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🎯 목표 달성 현황",
    "📈 주식 분석", 
    "🧮 물타기 시뮬레이터", 
    "💰 가족 자산", 
    "👶 자녀 자산",
    "🏦 대출 현황"
])

usd_krw, rate_diff = get_exchange_rate()
if usd_krw == 0: usd_krw = 1400.0

# =========================================================
# 탭 1: 목표 달성 현황 (날짜축 고정 & 점 항상 표시 수정판)
# =========================================================
with tab1:
    st.header("🏆 FIRE족을 향한 여정")
    
    total_asset_krw = st.session_state.get('total_family_asset', 0.0)
    total_loan_krw = st.session_state.get('total_loan_balance', 0.0)
    breakdown = st.session_state.get('asset_breakdown', {"주식(달러포함)": 0.0, "현금(원화)": 0.0, "부동산": 0.0})
    
    current_net_worth = total_asset_krw - total_loan_krw
    target_net_worth = 5000000000.0 

    daily_change_krw = calculate_daily_stock_change_total(usd_krw)

    st.subheader("🚩 최종 목표: 순자산 50억")
    
    if target_net_worth > 0:
        progress_pct = max(0.0, min(current_net_worth / target_net_worth, 1.0))
    else:
        progress_pct = 0.0
        
    st.progress(progress_pct)
    
    col_goal1, col_goal2, col_goal3 = st.columns(3)
    
    col_goal1.metric(
        "현재 순자산 (자동)", 
        f"{current_net_worth:,.0f}원", 
        delta=f"{daily_change_krw:,.0f}원 (전일대비)"
    )
    col_goal2.metric("목표 달성률", f"{progress_pct*100:.2f}%")
    col_goal3.metric("남은 금액", f"{target_net_worth - current_net_worth:,.0f}원")
    
    st.divider()

    # [NEW] 자산 추세 그래프 영역 (수정 완료)
    st.subheader("📈 내 자산 성장 추세")
    if os.path.exists(HISTORY_FILE):
        try:
            # 1. 데이터 불러오기
            df_hist = pd.read_csv(HISTORY_FILE)
            
            # 2. 날짜 컬럼을 강제로 '날짜 형식(datetime)'으로 변환 (★핵심 수정★)
            df_hist['Date'] = pd.to_datetime(df_hist['Date'])

            if not df_hist.empty:
                # 3. 컬럼 이름 및 데이터 정리
                if 'Asset' in df_hist.columns:
                    df_hist.rename(columns={'Asset': 'TotalAsset'}, inplace=True)
                
                # 없는 컬럼 0으로 채우고 float로 변환
                if 'TotalAsset' not in df_hist.columns: df_hist['TotalAsset'] = 0.0
                if 'NetAsset' not in df_hist.columns: df_hist['NetAsset'] = df_hist['TotalAsset']

                df_hist['TotalAsset'] = df_hist['TotalAsset'].astype(float)
                df_hist['NetAsset'] = df_hist['NetAsset'].astype(float)

                # 4. 차트용 데이터 변환 (Wide -> Long)
                df_long = df_hist.melt('Date', value_vars=['TotalAsset', 'NetAsset'], var_name='Type', value_name='Value')
                df_long['Type'] = df_long['Type'].replace({'TotalAsset': '총 자산', 'NetAsset': '순자산'})

                # 5. 차트 그리기
                # X축 설정을 'Date:T'(Temporal)로 명시하여 날짜로 인식시킴
                base = alt.Chart(df_long).encode(
                    x=alt.X('Date:T', title='날짜', axis=alt.Axis(format='%Y-%m-%d', tickCount='day')), 
                    y=alt.Y('Value:Q', title='금액 (원)', axis=alt.Axis(format=",d")),
                    color=alt.Color('Type:N', title='구분', scale={'domain': ['총 자산', '순자산'], 'range': ['#1f77b4', '#00bfa0']})
                )

                # 선 그리기
                line = base.mark_line(interpolate='monotone', size=3)
                
                # 점 그리기 (항상 보이도록 opacity=1로 설정) (★핵심 수정★)
                points = base.mark_circle(size=80, opacity=1).encode(
                    tooltip=[
                        alt.Tooltip('Date:T', title='날짜', format='%Y-%m-%d'),
                        alt.Tooltip('Type:N', title='구분'),
                        alt.Tooltip('Value:Q', title='금액', format=",.0f")
                    ]
                )

                # 최종 차트 결합
                chart = (line + points).properties(height=350).configure_axis(
                    grid=True, # 격자 표시 (보기 편하게)
                    labelFontSize=12,
                    titleFontSize=14
                ).configure_legend(
                    titleFontSize=14,
                    labelFontSize=12,
                    orient='bottom'
                ).interactive()

                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("데이터 파일은 있지만 내용은 비어있습니다. 다시 저장해주세요.")
        except Exception as e:
            st.error(f"차트 로딩 오류: {e}")
            # 에러가 계속되면 파일 삭제 권고
            st.warning("오류가 지속되면 'asset_history.csv' 파일을 삭제 후 다시 저장해주세요.")
    else:
        st.info("💡 [가족 자산] 탭에서 '데이터 저장하기'를 누르면 그래프가 시작됩니다.")

    st.divider()
    
    # ... (이하 파이 차트 코드는 기존과 동일) ...
    st.subheader("🎨 내 자산 포트폴리오")
    st.caption("자산 비중을 한눈에 확인하세요.")
    
    if total_asset_krw > 0:
        try:
            df_chart = pd.DataFrame({
                "Category": list(breakdown.keys()),
                "Value": list(breakdown.values())
            })
            df_chart = df_chart[df_chart["Value"] > 0].copy()
            df_chart = df_chart.sort_values(by="Value", ascending=False)
            
            total_val = df_chart["Value"].sum()
            df_chart["Percent"] = df_chart["Value"] / total_val if total_val > 0 else 0
            
            if total_val >= 100000000:
                center_text = f"{total_val/100000000:.1f}억"
            else:
                center_text = f"{total_val:,.0f}원"

            col_chart, col_details = st.columns([1.3, 1])
            
            with col_chart:
                base = alt.Chart(df_chart).encode(theta=alt.Theta("Value", stack=True))
                pie = base.mark_arc(innerRadius=80, outerRadius=130).encode(
                    color=alt.Color("Category", scale=alt.Scale(scheme='category10'), legend=None),
                    order=alt.Order("Value", sort="descending"),
                    tooltip=["Category", alt.Tooltip("Value", format=",.0f")]
                )
                text = base.mark_text(radius=0, size=24, fontWeight='bold', color='black').encode(
                    text=alt.value(center_text)
                )
                chart_combined = alt.layer(pie, text).properties(padding={"top": 10, "bottom": 10, "left": 10, "right": 10})
                st.altair_chart(chart_combined, use_container_width=True)

            with col_details:
                st.markdown("#### 📊 상세 구성")
                for i, row in df_chart.iterrows():
                    cat = row['Category']
                    val = row['Value']
                    pct = row['Percent'] * 100
                    with st.container():
                        st.metric(label=f"{cat} ({pct:.1f}%)", value=f"{val:,.0f}원")
                        st.progress(row['Percent'])
                        st.markdown("---")
        except Exception as e:
            st.error(f"차트 오류: {e}")
    else:
        st.warning("아직 자산 데이터가 없습니다.")

# =========================================================
# 탭 2: 주식 분석
# =========================================================
with tab2:
    st.markdown("### 📊 관심 종목 이원화 분석")
    st.caption("보유 중인 '주력 종목'과 지켜보는 '와치리스트'를 나누어 관리하세요.")
    
    # [수정] 안내 메시지에 저장 버튼 위치 변경 알림
    st.info("💡 티커를 수정하고 [가족 자산] 탭의 [데이터 저장하기] 버튼을 눌러야 유지됩니다.")

    col_input_main, col_input_watch = st.columns(2)
    with col_input_main:
        st.markdown("#### 💎 주력 종목 (Core)")
        st.text_area("주력 티커 입력", key="core_tickers", height=100)
    with col_input_watch:
        st.markdown("#### 👀 와치리스트 (Watch)")
        st.text_area("관심 티커 입력", key="watch_tickers", height=100)

    st.divider()

    def analyze_and_display(group_name, ticker_str):
        t_list = [t.strip().upper() for t in ticker_str.split(',') if t.strip()]
        if not t_list:
            st.info(f"{group_name}에 입력된 종목이 없습니다.")
            return

        result_data = []
        fixed_period = "max"

        for t in t_list:
            try:
                stock = yf.Ticker(t)
                df = stock.history(period=fixed_period)
                if not df.empty:
                    curr_price = df['Close'].iloc[-1]
                    ath_price = df['Close'].max()
                    mdd_rate = ((curr_price - ath_price) / ath_price) * 100
                    if len(df) >= 2:
                        prev_close = df['Close'].iloc[-2]
                        daily_change = ((curr_price - prev_close) / prev_close) * 100
                    else:
                        daily_change = 0.0

                    result_data.append({
                        "티커": t, "현재가 ($)": curr_price, "전일대비": daily_change,
                        "전고점 (종가)": ath_price, "괴리율 (MDD)": mdd_rate 
                    })
            except:
                continue 

        if result_data:
            st.subheader(f"{group_name} 현황")
            df_res = pd.DataFrame(result_data)
            def color_arrow(val):
                if pd.isna(val): return ''
                color = 'green' if val > 0 else 'red' if val < 0 else 'black'
                return f'color: {color}; font-weight: bold;'
            styled_df = df_res.style.format({
                "현재가 ($)": "${:,.2f}", "전일대비": "{:+.2f}%",
                "전고점 (종가)": "${:,.2f}", "괴리율 (MDD)": "{:.2f}%"
            }).map(color_arrow, subset=['전일대비']).set_properties(**{'text-align': 'right'}) 
            st.dataframe(styled_df, use_container_width=True, hide_index=True,
                column_config={
                    "티커": st.column_config.TextColumn("종목명", width="small"),
                    "현재가 ($)": st.column_config.NumberColumn("현재가", format="$%.2f"),
                    "전일대비": st.column_config.TextColumn("전일대비", help="어제 종가 대비"),
                    "전고점 (종가)": st.column_config.NumberColumn("전고점 (종가)", format="$%.2f", help="상장 이후 전체 기간(Max) 종가 최고가"),
                    "괴리율 (MDD)": st.column_config.NumberColumn("전고점 대비 하락률", format="%.2f%%")
                })
        else:
            st.warning(f"{group_name}: 데이터를 불러올 수 없습니다.")

    if st.button("분석 실행 (새로고침)", type="primary", use_container_width=True):
        st.cache_data.clear() 
    with st.spinner("전체 기간(Max) 데이터 분석 중..."):
        analyze_and_display("💎 주력 종목", st.session_state['core_tickers'])
        st.markdown("---") 
        analyze_and_display("👀 와치리스트", st.session_state['watch_tickers'])

# =========================================================
# 탭 3: 물타기 시뮬레이터
# =========================================================
with tab3:
    st.subheader("🧮 스마트 분할 매수 계산기")
    def get_data_and_calculate_sim(ticker, period):
        try:
            if not ticker: return None, None, None, "티커 입력 필요"
            stock = yf.Ticker(ticker)
            df = stock.history(period=period)
            if df.empty: return None, None, None, "데이터 없음"
            return df, 0, 0, None
        except Exception as e:
            return None, None, None, f"에러: {e}"

    col_sim_input1, col_sim_input2 = st.columns([1, 2])
    with col_sim_input1:
        ticker_input = st.text_input("시뮬레이션 할 티커", key="sim_ticker_main").upper()
    st.divider()

    if not ticker_input:
        st.info("👈 티커를 입력해주세요.")
    else:
        df, _, _, _ = get_data_and_calculate_sim(ticker_input, "1y")
        with st.expander("📝 설정 (자산 및 전략)", expanded=True):
            col_set1, col_set2, col_set3, col_set4, col_set5 = st.columns(5)
            with col_set1: my_price = st.number_input("내 평단가 ($)", value=0.0, step=0.1, format="%.2f", key="sim_p")
            with col_set2: my_qty = st.number_input("보유 수량", value=0, step=1, key="sim_q")
            with col_set3: my_cash = st.number_input("보유 예수금 ($)", value=1000.0, step=100.0, key="sim_c")
            with col_set4: split_cnt = st.number_input("분할 횟수", min_value=1, max_value=20, value=5, step=1, key="sim_cnt")
            with col_set5: drop_rate = st.number_input("매수 간격 (-%)", min_value=1.0, value=5.0, step=0.5, key="sim_drop")
            budget_per_round = my_cash / split_cnt
            st.caption(f"💡 1회당 배정 예산: **${budget_per_round:,.2f}**")
        st.divider()
        st.markdown(f"### 🚀 {ticker_input} 매수 및 매도 계획")
        c_base1, c_base2 = st.columns(2)
        with c_base1:
            def_p = df['Close'].iloc[-1] if (df is not None and not df.empty) else 0.0
            start_price = st.number_input("🔵 1회차 매수가 ($)", value=float(def_p), step=0.1, format="%.2f", key="sim_start_p")
        with c_base2:
            target_sell_price = st.number_input("🔴 목표 매도 가격 ($)", value=float(def_p)*1.1, step=0.1, format="%.2f", key="sim_target_p")
        
        st.divider()
        st.markdown("#### 📋 단계별 매수/매도 시나리오")
        
        def format_color_text(val, prefix="", suffix=""):
            color = "green" if val >= 0 else "red"
            fmt = "{:,.2f}"
            formatted_num = fmt.format(val)
            if val > 0: formatted_num = "+" + formatted_num
            text = f"{prefix}{formatted_num}{suffix}"
            return f"<span style='color:{color}; font-weight:bold;'>{text}</span>"

        cols = st.columns([0.6, 0.8, 0.6, 0.8, 0.8, 0.8, 1.6])
        headers = ["회차", "매수가", "수량", "누적평단", "현재 수익률", "매도 수익률", "매도 금액 (달러/원화)"]
        for c, h in zip(cols, headers): c.markdown(f"**{h}**")

        accum_qty = my_qty
        accum_amt = my_price * my_qty
        rem_cash = my_cash
        
        for i in range(split_cnt):
            cur_drop = i * drop_rate
            tgt_p = start_price * ((1 - drop_rate/100) ** i)
            tgt_q = int(budget_per_round // tgt_p) if tgt_p > 0 else 0
            inv = tgt_p * tgt_q
            accum_qty += tgt_q
            accum_amt += inv
            rem_cash -= inv
            new_avg = accum_amt / accum_qty if accum_qty > 0 else 0
            curr_profit_pct = ((tgt_p - new_avg) / new_avg * 100) if new_avg > 0 else 0
            sell_profit_pct = ((target_sell_price - new_avg) / new_avg * 100) if new_avg > 0 else 0
            sell_total_usd = accum_qty * target_sell_price
            sell_total_krw = sell_total_usd * usd_krw

            cols = st.columns([0.6, 0.8, 0.6, 0.8, 0.8, 0.8, 1.6])
            with cols[0]: st.markdown(f"{i+1}차 (-{cur_drop:.1f}%)")
            with cols[1]: st.markdown(f"${tgt_p:,.2f}")
            with cols[2]: st.markdown(f"{tgt_q}주")
            with cols[3]: st.markdown(f"${new_avg:,.2f}")
            with cols[4]: st.markdown(format_color_text(curr_profit_pct, suffix="%"), unsafe_allow_html=True)
            with cols[5]: st.markdown(format_color_text(sell_profit_pct, suffix="%"), unsafe_allow_html=True)
            with cols[6]:
                val_usd = f"${sell_total_usd:,.0f}"
                val_krw = f"{sell_total_krw:,.0f}원"
                st.markdown(f"<span style='font-size:1.2em; font-weight:bold;'>{val_usd}</span> <br> <span style='color:gray; font-size:0.9em'>({val_krw})</span>", unsafe_allow_html=True)

        st.divider()
        if rem_cash < 0: st.error(f"⚠️ 예수금이 ${abs(rem_cash):,.2f} 부족합니다.")
        else: st.success(f"✅ 모든 매수 후 남은 예수금: ${rem_cash:,.2f}")

# =========================================================
# 탭 4: 가족 자산 (부동산 포함) - [수정됨: 저장하기 버튼 추가]
# =========================================================
with tab4:
    total_container = st.container()

    def calculate_family_assets(user_key, default_name):
        st.markdown(f"### 👤 {default_name}")
        name = st.text_input("이름", value=default_name, key=f"nm_{user_key}")
        
        st.markdown("**1. 주식 및 현금**")
        col_c1, col_c2 = st.columns(2)
        with col_c1: cash_usd = st.number_input("달러 예수금 ($)", value=1000.0, step=100.0, key=f"csh_usd_{user_key}")
        with col_c2: cash_krw = st.number_input("원화 현금 (₩)", value=0, step=100000, key=f"csh_krw_{user_key}")

        stock_count = st.number_input("보유 종목 수", min_value=1, max_value=10, value=1, step=1, key=f"cnt_{user_key}")
        
        total_stock_value = 0.0
        daily_diff_sum_usd = 0.0
        
        for i in range(stock_count):
            st.markdown(f"종목 {i+1}")
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1: tick = st.text_input(f"티커", value="NVDA" if i==0 else "", key=f"t_{user_key}_{i}").upper()
            with c2: qty = st.number_input(f"수량", value=10 if i==0 else 0, step=1, key=f"q_{user_key}_{i}")
            with c3: buy_price = st.number_input(f"매수가($)", value=100.0, step=0.1, key=f"p_{user_key}_{i}")
            
            if tick and qty > 0:
                cur_price = get_current_price_only(tick)
                if cur_price > 0:
                    eval_amt = cur_price * qty
                    total_stock_value += eval_amt
                    
                    diff = get_daily_diff_amount(tick) * qty
                    daily_diff_sum_usd += diff
                    
                    st.caption(f"└ 현재가 ${cur_price:.2f} | 평가금 ${eval_amt:,.0f}")
        
        st.divider()
        st.markdown("**2. 부동산**")
        st.link_button("KB부동산 시세 확인 🏠", "https://kbland.kr/")
        
        has_re = st.checkbox("보유 여부", key=f"has_re_{user_key}")
        re_val_krw = 0.0
        
        if has_re:
            st.text_input("아파트명", value="OO아파트", key=f"re_n_{user_key}")
            c_re1, c_re2 = st.columns(2)
            with c_re1: st.number_input("매입가 (원)", value=500000000, step=10000000, key=f"re_bp_{user_key}")
            with c_re2: re_cur = st.number_input("현재 시세 (원)", value=700000000, step=10000000, key=f"re_cp_{user_key}")
            re_val_krw = re_cur
            st.info(f"🏡 자산 가치: {re_val_krw/100000000:.1f}억")

        st.divider()
        stock_krw = (total_stock_value * usd_krw) + (cash_usd * usd_krw)
        cash_group_krw = cash_krw
        re_group_krw = re_val_krw
        final_krw = stock_krw + cash_group_krw + re_group_krw
        
        daily_diff_sum_krw = daily_diff_sum_usd * usd_krw
        
        st.metric(
            f"{name} 자산 합계", 
            f"{final_krw:,.0f}원", 
            delta=f"{daily_diff_sum_krw:,.0f}원 (전일대비)"
        )
        
        return stock_krw, cash_group_krw, re_group_krw, daily_diff_sum_krw

    col_a, col_b = st.columns(2)
    with col_a: s_a, c_a, r_a, diff_a = calculate_family_assets("FA", "가족 1")
    with col_b: s_b, c_b, r_b, diff_b = calculate_family_assets("FB", "가족 2")

    tot_s = s_a + s_b
    tot_c = c_a + c_b
    tot_r = r_a + r_b
    
    total_diff_family = diff_a + diff_b
    
    gross_krw = tot_s + tot_c + tot_r
    loan_krw = st.session_state.get('total_loan_balance', 0.0)
    net_krw = gross_krw - loan_krw

    st.session_state['total_family_asset'] = gross_krw
    st.session_state['asset_breakdown'] = {"주식(달러포함)": tot_s, "현금(원화)": tot_c, "부동산": tot_r}

    with total_container:
        st.subheader("🏡 우리 가족 순자산")
        c1, c2, c3 = st.columns(3)
        c1.metric("총 자산", f"{gross_krw:,.0f}원", delta=f"{total_diff_family:,.0f}원 (전일대비)")
        c2.metric("총 부채", f"{loan_krw:,.0f}원", delta="변동 없음", delta_color="off")
        c3.metric("순자산", f"{net_krw:,.0f}원", delta=f"{total_diff_family:,.0f}원 (전일대비)")
        st.markdown(f"<div style='background-color:#e6fffa; padding:15px; border-radius:10px; text-align:center;'><h1>{net_krw:,.0f}원</h1></div>", unsafe_allow_html=True)
        st.divider()
        
        # [핵심] 저장 버튼이 눌리면 JSON 데이터와 함께 히스토리 CSV도 업데이트됨
        if st.button("💾 데이터 저장하기", type="primary", use_container_width=True):
            save_data()

# =========================================================
# 탭 5: 자녀 자산
# =========================================================
with tab5:
    st.subheader("👶 자녀 자산 현황")
    c1, c2 = st.columns(2)
    with c1: calculate_and_render_portfolio("C1", "자녀 1", usd_krw)
    with c2: calculate_and_render_portfolio("C2", "자녀 2", usd_krw)

# =========================================================
# 탭 6: 대출 현황
# =========================================================
with tab6:
    smry = st.container()
    st.markdown("### 📝 대출 리스트")
    l_cnt = st.number_input("대출 건수", min_value=1, value=1, step=1, key="l_cnt")
    tot_loan = 0
    l_list = []
    for i in range(l_cnt):
        st.markdown(f"**대출 {i+1}**")
        c1, c2, c3 = st.columns([1.5, 1.5, 1])
        with c1: ln = st.text_input("이름", value="담보대출" if i==0 else "", key=f"ln_{i}")
        with c2: lb = st.number_input("잔액 (원)", value=100000000 if i==0 else 0, step=1000000, key=f"lb_{i}")
        with c3: lr = st.number_input("이율 (%)", value=4.5, step=0.1, key=f"lr_{i}")
        tot_loan += lb
        if ln and lb > 0: l_list.append({"이름":ln, "잔액":f"{lb:,.0f}", "이율":f"{lr}%"})
    st.session_state['total_loan_balance'] = tot_loan
    
    with smry:
        st.subheader("🏦 총 대출 현황")
        st.markdown(f"<div style='background-color:#fff5f5; padding:15px; border-radius:10px; text-align:center;'><h1>{tot_loan:,.0f}원</h1></div>", unsafe_allow_html=True)
        st.divider()
    if l_list:
        with st.expander("목록 보기"): st.dataframe(pd.DataFrame(l_list))
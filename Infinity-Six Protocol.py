import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots # FIXED: Re-added missing import
import json
import os
import shutil
from datetime import datetime, timedelta
import random

# --- 1. SYSTEM CONFIGURATION ---
st.set_page_config(page_title="Infinity-6 Protocol", page_icon="🛡️", layout="wide")

# HACKER / PRO THEME CSS
st.markdown("""
    <style>
    .stApp { background-color: #0b0d11; color: #e6e6e6; }
    
    /* Action Plan Boxes */
    .action-box-crit { background-color: #440d0d; border-left: 5px solid #ff4d4d; padding: 15px; margin-bottom: 10px; border-radius: 5px; }
    .action-box-warn { background-color: #44330d; border-left: 5px solid #ffaa00; padding: 15px; margin-bottom: 10px; border-radius: 5px; }
    .action-box-ok { background-color: #0d2e1a; border-left: 5px solid #00ff7f; padding: 15px; margin-bottom: 10px; border-radius: 5px; }
    .action-text { font-size: 1.1em; font-weight: bold; margin: 0; }
    .action-sub { font-size: 0.9em; opacity: 0.8; margin: 0; }
    
    /* Metrics */
    div.stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px; }
    
    /* VERDICT CARD DESIGN */
    .verdict-card {
        background-color: #161b22;
        border-radius: 12px;
        padding: 25px;
        margin-top: 20px;
        border: 1px solid #30363d;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .verdict-header {
        font-size: 1.8em;
        font-weight: 800;
        margin-bottom: 20px;
        letter-spacing: 1px;
    }
    .horizon-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 0;
        border-bottom: 1px solid #2d333b;
    }
    .horizon-row:last-child { border-bottom: none; }
    .horizon-title {
        font-weight: 600;
        color: #8b949e;
        font-size: 0.95em;
        width: 35%;
    }
    .horizon-signal {
        font-weight: 800;
        font-size: 1.1em;
        text-align: right;
        width: 15%;
    }
    .horizon-desc {
        font-size: 0.85em;
        color: #6e7681;
        text-align: right;
        width: 50%;
        font-style: italic;
    }
    
    h1, h2, h3 { color: #00ff7f; font-family: 'Segoe UI', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ADVANCED MEMORY ENGINE ---
MAIN_FILE = "infinity_data.json"
BACKUP_FILE = "infinity_backup.json"

def generate_demo_history(current_nw, current_invested):
    """Generates a synthetic 5-year history for visualization."""
    history = []
    for i in range(60):
        date = (datetime.now() - timedelta(days=i*30)).strftime("%Y-%m-%d")
        factor_nw = (1 - (0.012 * i)) 
        factor_inv = (1 - (0.010 * i)) 
        noise = random.uniform(0.98, 1.02)
        
        hist_nw = max(0, current_nw * factor_nw * noise)
        hist_inv = max(0, current_invested * factor_inv)
        
        history.append({"date": date, "nw": hist_nw, "invested": hist_inv})
    return history[::-1] 

def load_data():
    """Smart Loader"""
    default_data = {
        "properties": [{"name": "Primary Home", "value": 300000.0}],
        "cspx_qty": 50.0, "cspx_manual": 0.0,
        "bond_val": 150000.0,
        "gold_qty": 20.0, "gold_manual": 0.0,
        "stocks": [{"ticker": "TSLA", "qty": 5.0, "manual": 0.0}],
        "btc_q": 0.05, "btc_m": 0.0,
        "eth_q": 1.0, "eth_m": 0.0,
        "pension": 50000.0,
        "usd_myr_manual": 0.0,
        "manual_mode": False,
        "history": []
    }
    
    loaded = default_data.copy()
    
    file_data = {}
    if os.path.exists(MAIN_FILE):
        try:
            with open(MAIN_FILE, "r") as f: file_data = json.load(f)
        except: pass
    elif os.path.exists(BACKUP_FILE):
        try:
            with open(BACKUP_FILE, "r") as f: file_data = json.load(f)
        except: pass
    
    if "prop_val" in file_data and "properties" not in file_data:
        loaded["properties"] = [{"name": "Main Property", "value": float(file_data["prop_val"])}]
    elif "properties" in file_data:
        loaded["properties"] = file_data["properties"]
        
    for k, v in file_data.items():
        if k != "prop_val" and k != "properties":
            loaded[k] = v
    
    if "history" not in loaded: loaded["history"] = []
            
    return loaded

def save_data():
    try:
        with open(MAIN_FILE, "w") as f: json.dump(st.session_state['data'], f)
        shutil.copyfile(MAIN_FILE, BACKUP_FILE)
        st.toast("✅ DATA SECURED (Main + Backup)")
    except Exception as e: st.error(f"Save Error: {e}")

if 'data' not in st.session_state:
    st.session_state['data'] = load_data()

d = st.session_state['data']

# --- 3. INTELLIGENCE CORE ---
def get_price(ticker, manual_mode, manual_price):
    if manual_mode: return manual_price
    if not ticker or ticker == "NEW": return 0.0
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        if not hist.empty: 
            return hist['Close'].iloc[-1]
        info_price = stock.info.get('regularMarketPrice')
        if info_price: return info_price
        return 0.0 
    except: return 0.0

def get_forex_rate():
    if d.get('manual_mode', False): return d.get('usd_myr_manual', 0.0)
    try:
        return yf.Ticker("MYR=X").history(period="1d")['Close'].iloc[-1]
    except: return d.get('usd_myr_manual', 0.0)

def smart_ticker_resolver(raw_ticker):
    """Auto-converts '1155' to '1155.KL'"""
    if not raw_ticker: return None
    clean = raw_ticker.strip().upper()
    if clean.isdigit() and len(clean) == 4:
        return f"{clean}.KL"
    return clean

def get_stock_data_smart(ticker, manual_mode, manual_price, fx_rate):
    """Returns (Price in MYR, Raw Price, Currency Symbol, Long Name)"""
    if manual_mode:
        return manual_price * fx_rate, manual_price, "$", ticker
    
    if not ticker or ticker == "NEW": return 0.0, 0.0, "?", ticker
    
    try:
        resolved_ticker = smart_ticker_resolver(ticker)
        stock = yf.Ticker(resolved_ticker)
        
        hist = stock.history(period="1d")
        if hist.empty: return 0.0, 0.0, "ERR", ticker
        price = hist['Close'].iloc[-1]
        
        # Get Metadata
        info = stock.info
        currency = info.get('currency', 'USD')
        # Try to get the long name, fall back to short name, fall back to ticker
        long_name = info.get('longName', info.get('shortName', resolved_ticker))
        
        if currency == 'MYR':
            return price, price, "RM", long_name
        else:
            return price * fx_rate, price, "$", long_name
            
    except: return 0.0, 0.0, "ERR", ticker

# --- 4. SIDEBAR ---
st.sidebar.title("🛡️ CONTROLS")
d['manual_mode'] = st.sidebar.checkbox("⚠️ MANUAL OVERRIDE", value=d.get('manual_mode', False))
if d['manual_mode']:
    d['usd_myr_manual'] = st.sidebar.number_input("🇺🇸 USD/MYR", value=float(d.get('usd_myr_manual', 0.0)), step=0.01)

if st.sidebar.button("💾 SAVE DATA"): save_data()
st.sidebar.divider()

st.sidebar.caption("1. REAL ESTATE (DYNAMIC)")
for i, prop in enumerate(d['properties']):
    c1, c2 = st.sidebar.columns([1.5, 1])
    with c1: prop['name'] = st.text_input(f"Name {i+1}", prop['name'], key=f"pn_{i}")
    with c2: prop['value'] = st.number_input(f"Val {i+1}", value=float(prop['value']), key=f"pv_{i}", step=1000.0)

c_padd, c_prem = st.sidebar.columns(2)
if c_padd.button("➕ Add"): d['properties'].append({"name": "New Property", "value": 0.0}); st.rerun()
if c_prem.button("➖ Remove"): 
    if len(d['properties'])>0: d['properties'].pop(); st.rerun()

st.sidebar.caption("2. S&P 500")
d['cspx_qty'] = st.sidebar.number_input("Units", value=float(d['cspx_qty']), step=1.0)
if d['manual_mode']: d['cspx_manual'] = st.sidebar.number_input("CSPX $", value=float(d['cspx_manual']), step=1.0)

st.sidebar.caption("3. CASH/BONDS")
d['bond_val'] = st.sidebar.number_input("Total Cash (MYR)", value=float(d['bond_val']), step=1000.0)

st.sidebar.caption("4. GOLD")
d['gold_qty'] = st.sidebar.number_input("Units", value=float(d['gold_qty']), step=1.0)
if d['manual_mode']: d['gold_manual'] = st.sidebar.number_input("Gold $", value=float(d['gold_manual']), step=1.0)

st.sidebar.caption("5. STOCKS (DYNAMIC)")
for i, stock in enumerate(d['stocks']):
    c1, c2 = st.sidebar.columns([1, 1])
    with c1: stock['ticker'] = st.text_input(f"T{i+1}", stock['ticker'], key=f"t_{i}")
    with c2: stock['qty'] = st.number_input(f"Q{i+1}", value=float(stock['qty']), key=f"q_{i}", step=1.0)
    if d['manual_mode']: stock['manual'] = st.sidebar.number_input(f"P{i+1}", value=float(stock['manual']), key=f"m_{i}", step=1.0)

c_sadd, c_srem = st.sidebar.columns(2)
if c_sadd.button("➕ Add Stock"): d['stocks'].append({"ticker":"NEW","qty":0.0,"manual":0.0}); st.rerun()
if c_srem.button("➖ Del Stock"): 
    if len(d['stocks'])>0: d['stocks'].pop(); st.rerun()

st.sidebar.caption("6. CRYPTO")
d['btc_q'] = st.sidebar.number_input("BTC", value=float(d['btc_q']), step=0.001, format="%.6f")
if d['manual_mode']: d['btc_m'] = st.sidebar.number_input("BTC $", value=float(d['btc_m']), step=100.0)
d['eth_q'] = st.sidebar.number_input("ETH", value=float(d['eth_q']), step=0.001, format="%.6f")
if d['manual_mode']: d['eth_m'] = st.sidebar.number_input("ETH $", value=float(d['eth_m']), step=100.0)

st.sidebar.caption("7. PENSION")
d['pension'] = st.sidebar.number_input("Value (MYR)", value=float(d['pension']), step=1000.0)

# --- MAIN ENGINE ---
tab1, tab2 = st.tabs(["📊 MAIN DASHBOARD", "🔭 TACTICAL MARKET SCANNER"])

with tab1:
    st.title("🛡️ Infinity-6 Protocol")
    
    with st.spinner("Syncing Global Assets..."):
        curr_rate = get_forex_rate()
        p_cspx = get_price("CSPX.L", d['manual_mode'], d['cspx_manual'])
        p_gold = get_price("GLD", d['manual_mode'], d['gold_manual'])
        p_btc = get_price("BTC-USD", d['manual_mode'], d['btc_m'])
        p_eth = get_price("ETH-USD", d['manual_mode'], d['eth_m'])
        
        stock_val_usd = 0
        stock_prices = {} 
        for s in d['stocks']:
            t = s['ticker']
            qty = s['qty']
            price_myr, price_raw, sym, name = get_stock_data_smart(t, d['manual_mode'], s['manual'], curr_rate)
            
            if sym == "ERR" and t != "NEW" and not d['manual_mode']:
                st.toast(f"⚠️ Warning: Invalid Ticker '{t}'. Check spelling.")
            
            stock_val_usd += price_myr * qty
            if price_raw > 0 and t != "NEW":
                stock_prices[t] = (price_raw, sym, name)

    # 2. CALCULATIONS
    v_prop = sum(p['value'] for p in d['properties'])
    v_cspx = p_cspx * d['cspx_qty'] * curr_rate
    v_bond = d['bond_val']
    v_gold = p_gold * d['gold_qty'] * curr_rate
    v_stock = stock_val_usd
    v_crypto = (p_btc * d['btc_q'] + p_eth * d['eth_q']) * curr_rate
    total = v_prop + v_cspx + v_bond + v_gold + v_stock + v_crypto
    net_worth = total + d['pension']
    
    invested_est = v_prop + v_bond + d['pension'] + ((v_cspx + v_gold + v_stock + v_crypto) * 0.85)

    today_str = datetime.now().strftime("%Y-%m-%d")
    hist = d.get('history', [])
    if not hist:
        hist = generate_demo_history(net_worth, invested_est)
        d['history'] = hist
    if len(hist) > 0 and hist[-1]['date'] == today_str:
        hist[-1]['nw'] = net_worth
        hist[-1]['invested'] = invested_est
    else:
        hist.append({'date': today_str, 'nw': net_worth, 'invested': invested_est})
    d['history'] = hist

    # --- LIVE INTEL FEED ---
    st.markdown("### 📡 LIVE INTEL FEED")
    cols = st.columns(4)
    cols[0].metric("🇺🇸 USD/MYR", f"{curr_rate:.4f}")
    cols[1].metric("₿ BITCOIN", f"${p_btc:,.0f}")
    cols[2].metric("⟠ ETHEREUM", f"${p_eth:,.0f}")
    
    col_idx = 3
    for t, data in stock_prices.items():
        price, sym, name = data
        if col_idx >= 4: 
            cols = st.columns(4) 
            col_idx = 0
        
        # DISPLAY: Full Name + (Ticker)
        display_label = f"{name} ({t.upper()})"
        cols[col_idx].metric(display_label, f"{sym} {price:,.2f}")
        col_idx += 1
            
    st.divider()
    
    # --- METRICS & PIE ---
    c_m1, c_m2, c_m3 = st.columns(3)
    c_m1.metric("TOTAL NET WORTH", f"RM {net_worth:,.2f}")
    c_m2.metric("INVESTED ASSETS", f"RM {total:,.2f}")
    c_m3.metric("LIQUID RESERVES", f"RM {v_bond:,.2f}")
    
    st.divider()

    # --- ACTION PLAN ---
    df_port = pd.DataFrame({
        "Asset": ["Property", "CSPX", "Bonds", "Gold", "Stocks", "Crypto"],
        "Value": [v_prop, v_cspx, v_bond, v_gold, v_stock, v_crypto],
        "Target": [0.30, 0.40, 0.15, 0.05, 0.05, 0.05]
    })
    df_port["Current %"] = df_port["Value"] / total
    df_port["Drift"] = df_port["Current %"] - df_port["Target"]
    df_port["Action"] = (df_port["Target"] * total) - df_port["Value"]

    c_chart, c_plan = st.columns([1, 1.2])
    
    with c_chart:
        fig = go.Figure(data=[go.Pie(labels=df_port['Asset'], values=df_port['Value'], hole=.5)])
        fig.update_layout(template="plotly_dark", margin=dict(t=0,b=0,l=0,r=0), height=400)
        st.plotly_chart(fig, use_container_width=True)

    with c_plan:
        st.subheader("⚔️ OVERALL ACTION PLAN")
        for i, row in df_port.iterrows():
            drift = row['Drift']
            act = row['Action']
            name = row['Asset']
            if abs(drift) > 0.05:
                status = f"CRITICAL ({drift:+.1%})"
                instr = f"👉 BUY RM {act:,.2f}" if act > 0 else f"👉 SELL RM {abs(act):,.2f}"
                st.markdown(f"<div class='action-box-crit'><p class='action-text'>🚨 {name}: {status}</p><p class='action-sub'>{instr}</p></div>", unsafe_allow_html=True)
            elif abs(drift) > 0.02:
                status = f"WARNING ({drift:+.1%})"
                instr = f"👉 BUY RM {act:,.2f}" if act > 0 else f"👉 SELL RM {abs(act):,.2f}"
                st.markdown(f"<div class='action-box-warn'><p class='action-text'>⚠️ {name}: {status}</p><p class='action-sub'>{instr}</p></div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("📂 Advanced Mission Ledger")
    disp_df = df_port.copy()
    disp_df['Drift Status'] = disp_df['Drift'].apply(lambda x: "CRITICAL" if abs(x)>0.05 else ("WARNING" if abs(x)>0.02 else "OK"))
    st.dataframe(disp_df.style.format({
        "Value": "RM {:,.2f}", "Target": "{:.1%}", "Current %": "{:.1%}", 
        "Drift": "{:+.1%}", "Action": "RM {:+,.2f}"
    }).applymap(lambda v: 'color: #ff4d4d; font-weight: bold' if v == 'CRITICAL' else ('color: orange' if v == 'WARNING' else 'color: #00ff7f'), subset=['Drift Status']), use_container_width=True)

    st.divider()

    # --- GROWTH GRAPH ---
    if len(hist) > 1:
        hist_df = pd.DataFrame(hist)
        hist_df['date_dt'] = pd.to_datetime(hist_df['date'])
        
        try:
            sp500 = yf.Ticker("^GSPC").history(period="5y")['Close']
            start_val = hist_df['nw'].iloc[0]
            if not sp500.empty:
                sp_start_price = sp500.iloc[0]
                sp_norm = (sp500 / sp_start_price) * start_val
                sp_norm = sp_norm[sp_norm.index >= hist_df['date_dt'].min()]
        except: sp_norm = pd.Series()

        fig_growth = go.Figure()
        fig_growth.add_trace(go.Scatter(x=hist_df['date_dt'], y=hist_df['nw'], mode='lines', name='Your Net Worth', line=dict(color='#00ff7f', width=3), fill='tozeroy', fillcolor='rgba(0, 255, 127, 0.1)'))
        if not sp_norm.empty:
            fig_growth.add_trace(go.Scatter(x=sp_norm.index, y=sp_norm.values, mode='lines', name='S&P 500 Benchmark', line=dict(color='#ffaa00', width=2, dash='dot')))
        fig_growth.add_trace(go.Scatter(x=hist_df['date_dt'], y=hist_df['invested'], mode='lines', name='Total Invested', line=dict(color='#00bfff', width=2, dash='dash')))

        fig_growth.update_layout(title=dict(text="Growth Trajectory vs Market Benchmark", y=0.9), template="plotly_dark", height=400, margin=dict(l=20, r=20, t=50, b=20), hovermode="x unified", xaxis=dict(tickformat="%d/%m/%y", title="Time Period", nticks=10), yaxis=dict(title="Value (RM)"), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_growth, use_container_width=True)

with tab2:
    st.title("🔭 TACTICAL MARKET SCANNER")
    
    c_sw, c_inp = st.columns([1, 2])
    is_bursa = c_sw.toggle("🇲🇾 BURSA MALAYSIA MODE", False)
    scan_ticker = c_inp.text_input("ENTER TICKER (e.g. NVDA or 1155)", "").upper()
    
    if st.button("RUN DEEP SCAN"): 
        if scan_ticker: st.session_state['scan_run'] = True
        else: st.toast("⚠️ Please enter a ticker symbol.")
    
    if st.session_state.get('scan_run') and scan_ticker:
        try:
            # Smart Resolver
            final_ticker = smart_ticker_resolver(scan_ticker)
            if is_bursa and not final_ticker.endswith(".KL") and not final_ticker.isdigit():
                 final_ticker = f"{final_ticker}.KL"

            stock = yf.Ticker(final_ticker)
            df = stock.history(period="1y")
            
            if df.empty:
                st.error(f"❌ Error: Ticker '{final_ticker}' not found.")
            else:
                # Metadata
                info = stock.info
                long_name = info.get('longName', info.get('shortName', final_ticker))
                currency = info.get('currency', 'USD')
                
                # Calc Technicals
                df['MA10'] = df['Close'].rolling(10).mean()
                df['MA50'] = df['Close'].rolling(50).mean()
                df['MA200'] = df['Close'].rolling(200).mean()
                delta = df['Close'].diff()
                df['RSI'] = 100 - (100 / (1 + (delta.where(delta>0,0).rolling(14).mean() / (-delta.where(delta<0,0).rolling(14).mean()))))
                exp1 = df['Close'].ewm(span=12).mean(); exp2 = df['Close'].ewm(span=26).mean()
                df['MACD'] = exp1 - exp2; df['Signal'] = df['MACD'].ewm(span=9).mean()
                
                curr = df.iloc[-1]
                price = curr['Close']
                
                # Display Price logic
                if currency == 'MYR':
                    final_price = price
                    disp_price = f"RM {price:,.2f}"
                else:
                    final_price = price * curr_rate
                    disp_price = f"${price:,.2f} (RM {final_price:,.2f})"
                
                # UPDATED: Show Full Name
                st.metric(f"{long_name} ({final_ticker})", disp_price)
                
                # --- VERDICT LOGIC ---
                st_cond = (curr['Close'] > curr['MA50']) and (curr['MACD'] > curr['Signal'])
                st_sig = "BUY" if st_cond else "HOLD/SELL"
                st_col = "#00ff7f" if st_cond else "#ffaa00"
                st_desc = "Driven by: Price > MA50 + Positive MACD Momentum"
                
                mt_cond = (curr['Close'] > curr['MA200']) and (curr['MA50'] > curr['MA200'])
                mt_sig = "BUY" if mt_cond else "HOLD/SELL"
                mt_col = "#00ff7f" if mt_cond else "#ffaa00"
                mt_desc = "Driven by: Golden Cross (MA50 > MA200) + Structural Support"
                
                ma200_prev = df['MA200'].iloc[-20]
                lt_cond = (curr['MA200'] > ma200_prev) and (curr['Close'] > curr['MA200'])
                lt_sig = "BUY" if lt_cond else "HOLD/SELL"
                lt_col = "#00ff7f" if lt_cond else "#ffaa00"
                lt_desc = "Driven by: 200-Day Trend Slope (Secular Growth)"

                score = (1 if st_cond else 0) + (1 if mt_cond else 0) + (1 if lt_cond else 0)
                final_verdict = "STRONG BUY" if score == 3 else ("ACCUMULATE" if score >= 1 else "DISTRIBUTE")
                verdict_color = "#00ff7f" if score >= 2 else ("#ffaa00" if score == 1 else "#ff4d4d")
                
                html_block = f"""
<div class='verdict-card' style='border-left: 6px solid {verdict_color};'>
<div class='verdict-header' style='color:{verdict_color};'>🤖 AI VERDICT: {final_verdict}</div>
<div class='horizon-row'>
<div class='horizon-title'>Short-Term Investment ({'<1-3 years' if not is_bursa else 'Weeks'})</div>
<div class='horizon-signal' style='color:{st_col};'>{st_sig}</div>
<div class='horizon-desc'>{st_desc}</div>
</div>
<div class='horizon-row'>
<div class='horizon-title'>Medium-Term Investment (3-10 years)</div>
<div class='horizon-signal' style='color:{mt_col};'>{mt_sig}</div>
<div class='horizon-desc'>{mt_desc}</div>
</div>
<div class='horizon-row'>
<div class='horizon-title'>Long-Term Investment (>10 years)</div>
<div class='horizon-signal' style='color:{lt_col};'>{lt_sig}</div>
<div class='horizon-desc'>{lt_desc}</div>
</div>
</div>
"""
                st.markdown(html_block, unsafe_allow_html=True)
                
                # Charts
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
                fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MA50'], line=dict(color='cyan'), name="MA50"), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MA200'], line=dict(color='orange'), name="MA200"), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name="MACD"), row=2, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], name="Signal"), row=2, col=1)
                fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
                
                # Simulator (LINKED FIX)
                st.divider()
                st.subheader("🛒 Deep-Dive Simulator")
                
                c_sim_in, c_sim_res = st.columns([1, 2])
                with c_sim_in:
                    sim_qty = st.number_input("Quantity to Buy:", value=100.0, step=10.0, min_value=-1000000000.0)
                    cost = sim_qty * final_price
                    st.info(f"💵 Cost: RM {cost:,.2f}")
                    
                with c_sim_res:
                    stock_limit_pct = 0.05
                    current_stock_pct = v_stock / total
                    simulated_stock_pct = cost / total 
                    new_alloc_pct = (v_stock + cost) / total
                    pct_used_of_limit = new_alloc_pct / stock_limit_pct
                    
                    st.markdown("#### 📊 Allocation Impact")
                    col_i1, col_i2 = st.columns(2)
                    col_i1.metric("Stock Allocation", f"{new_alloc_pct:.2%}", f"Target: {stock_limit_pct:.0%}")
                    
                    remaining_cash = v_bond - cost
                    if remaining_cash < 0:
                        col_i2.metric("Liquid Reserves", "INSUFFICIENT", f"Deficit: RM {remaining_cash:,.2f}", delta_color="inverse")
                    else:
                        col_i2.metric("Liquid Reserves", f"RM {remaining_cash:,.2f}", f"- RM {cost:,.2f}")
                    
                    fig_bar = go.Figure()
                    fig_bar.add_trace(go.Bar(y=['Stock Allocation'], x=[current_stock_pct], orientation='h', name='Current Holdings', marker=dict(color='#4d4d4d')))
                    fig_bar.add_trace(go.Bar(y=['Stock Allocation'], x=[simulated_stock_pct], orientation='h', name='New Purchase', marker=dict(color='#00ff7f')))
                    fig_bar.add_vline(x=stock_limit_pct, line_dash="dot", line_color="red", annotation_text="5% Limit")
                    fig_bar.update_layout(title=f"You are using {pct_used_of_limit:.0%} of your 5% Safety Limit", template="plotly_dark", barmode='stack', height=200, xaxis=dict(tickformat=".1%", range=[0, max(0.1, new_alloc_pct*1.2)]))
                    st.plotly_chart(fig_bar, use_container_width=True)
                
        except Exception as e: st.error(f"Analysis Failed: {e}")
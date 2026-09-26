# =====================================================================
# V2 AGY QUANT PLATFORM: DOCX EXPORT GENERATOR (ZERO-DEPENDENCY)
# =====================================================================
import os
import io
import zipfile
import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

def escape_xml(text):
    if text is None:
        return ""
    text = str(text)
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
    )

def build_p(text, style=None, bold=False, italic=False, color=None, size_pt=None, space_after=120):
    p_pr = f'<w:pPr><w:spacing w:after="{space_after}"/>'
    if style:
        p_pr += f'<w:pStyle w:val="{style}"/>'
    p_pr += '</w:pPr>'
    
    r_pr = '<w:rPr>'
    if bold:
        r_pr += '<w:b/>'
    if italic:
        r_pr += '<w:i/>'
    if color:
        r_pr += f'<w:color w:val="{color}"/>'
    if size_pt:
        r_pr += f'<w:sz w:val="{int(size_pt * 2)}"/>'
    r_pr += '</w:rPr>'
    
    return f'<w:p>{p_pr}<w:r>{r_pr}<w:t xml:space="preserve">{escape_xml(text)}</w:t></w:r></w:p>'

def build_bullet(text, bold_prefix=None, space_after=80):
    content = '<w:pPr><w:spacing w:after="' + str(space_after) + '"/><w:ind w:left="360" w:hanging="240"/></w:pPr>'
    content += '<w:r><w:rPr><w:color w:val="2563EB"/></w:rPr><w:t>• </w:t></w:r>'
    if bold_prefix:
        content += f'<w:r><w:rPr><w:b/><w:color w:val="0F172A"/></w:rPr><w:t xml:space="preserve">{escape_xml(bold_prefix)} </w:t></w:r>'
    content += f'<w:r><w:rPr><w:color w:val="334155"/></w:rPr><w:t xml:space="preserve">{escape_xml(text)}</w:t></w:r>'
    return f'<w:p>{content}</w:p>'

def build_table(headers, rows):
    xml = ['<w:tbl>']
    xml.append('<w:tblPr>')
    xml.append('<w:tblW w:w="5000" w:type="pct"/>')
    xml.append('<w:tblBorders>')
    xml.append('<w:top w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>')
    xml.append('<w:bottom w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>')
    xml.append('<w:insideH w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>')
    xml.append('<w:insideV w:val="none"/>')
    xml.append('<w:left w:val="none"/><w:right w:val="none"/>')
    xml.append('</w:tblBorders>')
    xml.append('</w:tblPr>')

    # Header Row
    xml.append('<w:tr>')
    for h in headers:
        xml.append('<w:tc><w:tcPr>')
        xml.append('<w:shd w:val="clear" w:color="auto" w:fill="0F172A"/>')
        xml.append('<w:tcMar><w:top w:w="120"/><w:bottom w:w="120"/><w:left w:w="160"/><w:right w:w="160"/></w:tcMar>')
        xml.append('</w:tcPr>')
        xml.append(f'<w:p><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:rPr><w:b/><w:color w:val="FFFFFF"/><w:sz w:val="19"/></w:rPr><w:t>{escape_xml(h)}</w:t></w:r></w:p>')
        xml.append('</w:tc>')
    xml.append('</w:tr>')

    # Data Rows
    for idx, row in enumerate(rows):
        bg = "F8FAFC" if idx % 2 == 1 else "FFFFFF"
        xml.append('<w:tr>')
        for c in row:
            xml.append('<w:tc><w:tcPr>')
            xml.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{bg}"/>')
            xml.append('<w:tcMar><w:top w:w="100"/><w:bottom w:w="100"/><w:left w:w="160"/><w:right w:w="160"/></w:tcMar>')
            xml.append('</w:tcPr>')
            xml.append(f'<w:p><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:rPr><w:color w:val="1E293B"/><w:sz w:val="18"/></w:rPr><w:t>{escape_xml(c)}</w:t></w:r></w:p>')
            xml.append('</w:tc>')
        xml.append('</w:tr>')

    xml.append('</w:tbl>')
    return "".join(xml)

def generate_v2_docx_content():
    now_str = datetime.datetime.now(IST).strftime("%B %d, %Y - %I:%M %p IST")
    body_elements = []

    # Title & Subtitle
    body_elements.append(build_p("⚡ AGY Quant Platform V2: Comprehensive Platform Guide", style="Title", bold=True, color="0F172A", size_pt=24, space_after=60))
    body_elements.append(build_p(f"Public Testbed Edition • High-Conviction Tactical Engine • Generated on: {now_str}", italic=True, color="64748B", size_pt=10, space_after=240))

    # Section 1: Overview
    body_elements.append(build_p("1. Platform Overview & Architecture", bold=True, color="1E3A8A", size_pt=15, space_after=120))
    body_elements.append(build_p(
        "The AGY Quant Platform V2 is an institutional-grade, zero-credential tactical screening and paper trading system. "
        "Engineered for the Indian equities and ETF universe, V2 operates autonomously without requiring third-party cloud secrets, "
        "relying on high-performance local CSV persistence and standard HTTP triggers.",
        space_after=120
    ))
    body_elements.append(build_bullet("52 NSE Large & Midcap Equities + 35 Liquid NSE ETFs (Total 87 active instruments).", "Active Universe:"))
    body_elements.append(build_bullet("Zero Cloud Secrets (No Google Service Accounts or Telegram tokens needed in V2).", "Security Model:"))
    body_elements.append(build_bullet("cron-job.org HTTP GET/POST queries, GitHub Actions, or standalone Python scheduler.", "Automation Engine:"))
    body_elements.append(build_bullet("Target Achieved, Stop Loss, Dynamic Trailing Profit Lock, Overbought Swing Exit, and 3:10 PM Square-off.", "Exit Rules:"))
    body_elements.append(build_bullet("Dividend Yield % tracking with high-yield badges (>= 3.0%) for value & compounding.", "Dividend Analytics:"))

    # Section 2: Universal Safety Guards
    body_elements.append(build_p("2. Universal Safety Guards & Pre-Screening", bold=True, color="1E3A8A", size_pt=15, space_after=120))
    body_elements.append(build_p(
        "Before any asset is ranked, it passes through four non-negotiable safety filters to eliminate structural decline and illiquidity:",
        space_after=100
    ))
    body_elements.append(build_bullet("Requires min 10 historical trading bars with non-zero Close prices.", "Data Integrity Guard:"))
    body_elements.append(build_bullet("Requires RSI_t > RSI_{t-1} or Close > Prev Day High. Discards free-falling knife assets.", "Falling Knife Reversal Guard:"))
    body_elements.append(build_bullet("Checks price dislocation vs 5-day median. Flags ETFs with premium > +0.35% over fair value.", "iNAV Dislocation Filter (ETFs):"))
    body_elements.append(build_bullet("Separates stocks into Trend Healthy (>200 DMA) vs Trend Broken (<200 DMA).", "Structural 200 DMA Guard (Stocks):"))

    # Section 3: Preset Logic & Formulas
    body_elements.append(build_p("3. Category & Preset Filter Mathematical Logic", bold=True, color="1E3A8A", size_pt=15, space_after=120))
    body_elements.append(build_p(
        "Each preset applies custom technical and fundamental weightings to identify high-probability entries:",
        space_after=120
    ))

    preset_headers = ["Preset / Category", "Tech / Fund Weight", "Primary Quantitative Drivers", "ATR Stop", "ATR Target", "Exit Rules"]
    preset_rows = [
        ["Intraday", "85% Tech / 15% Fund", "Volume Surge (35%), RSI (30%), BB %B (20%), VWAP (15%)", "1.0x ATR", "1.8x ATR", "Mandatory Auto Square-off at 03:10 PM IST"],
        ["Swing / Positional", "80% Tech / 20% Fund", "RSI (30%), 200 DMA (25%), BB %B (20%), VWAP (15%), Stoch (10%)", "1.5x ATR", "3.0x ATR", "Trailing Stop (+3% gain locks +0.5%); RSI >= 76 exit"],
        ["Long-Term", "40% Tech / 60% Fund", "200 DMA Discount (45%), RSI (20%), BB %B (20%), Fund Score (15%)", "2.5x ATR", "5.0x ATR", "Hard Filter: Excludes stocks > 10% below 200 DMA"],
        ["Default", "60% Tech / 40% Fund", "Balanced Swing Technical Model + 40% Fundamental Liquidity", "1.5x ATR", "3.0x ATR", "Standard Target, Stop Loss, Trailing Stop"],
        ["AI / RAG", "Confluence Model", "RSI (35%) + BB %B (25%) + Volume Surge (25%) + MACD Hist (15%)", "1.6x ATR", "3.2x ATR", "Confidence-ranked conviction targets"]
    ]
    body_elements.append(build_table(preset_headers, preset_rows))
    body_elements.append(build_p("", space_after=120))

    # Section 4: Indicator Directionality & Color Coding
    body_elements.append(build_p("4. Screener Depth: Directionality & Top 5 Color Coding", bold=True, color="1E3A8A", size_pt=15, space_after=120))
    body_elements.append(build_p(
        "In Tab 1, every column header includes a rich help tooltip (?). Cell-level styling highlights Top 5 BUY candidates in Soft Green (#d4edda) "
        "and Top 5 SELL candidates in Soft Red (#f8d7da):",
        space_after=120
    ))

    color_headers = ["Indicator Column", "Direction for BUY (Green)", "Direction for SELL (Red)", "Financial / Quantitative Edge"]
    color_rows = [
        ["Composite Buy Score", "LOWER is Better (Top 5 Lowest)", "HIGHER is Better (Top 5 Highest)", "Lower score = multi-indicator oversold discount. Higher = stretched rally."],
        ["Technical Score", "LOWER is Better (Top 5 Lowest)", "HIGHER is Better (Top 5 Highest)", "Lower score = oversold across moving averages and oscillators."],
        ["Fundamental Score", "LOWER is Better (Top 5 Lowest)", "HIGHER is Better (Top 5 Highest)", "Lower score = high turnover, tight spreads, minimal expense friction."],
        ["RSI (14D)", "LOWER is Better (< 35)", "HIGHER is Better (> 65)", "Oversold capitulation dip vs overbought momentum distribution."],
        ["Bollinger %B", "LOWER is Better (< 0.15)", "HIGHER is Better (> 0.85)", "Lower 2-sigma band compression vs upper band test."],
        ["Dist VWAP %", "LOWER / NEGATIVE (Deep Discount)", "HIGHER / POSITIVE (Premium)", "Negative spread buys below institutional volume-weighted benchmark."],
        ["Dist 20/50/200 DMA %", "LOWER / NEGATIVE (Deep Pullback)", "HIGHER / POSITIVE (Extended)", "Institutional pullbacks to support vs mean-reversion risk."],
        ["Dist 52W Low %", "LOWER is Better (< 6%)", "HIGHER is Better (> 40%)", "Tight structural floor with tight risk vs mature bull move."],
        ["Volume Surge Ratio", "HIGHER is Better (> 1.5x)", "N/A", "Confirms institutional accumulation and buying conviction."],
        ["RS Spread 21D %", "HIGHER is Better (Alpha Leader)", "LOWER is Better (Lagging)", "Positive spread indicates stock is outperforming Nifty 50 benchmark."],
        ["Dividend Yield %", "HIGHER is Better (Top 5 Highest)", "N/A", "Higher yield indicates cash-flow support, defensive value, and dividend compounding."]
    ]
    body_elements.append(build_table(color_headers, color_rows))
    body_elements.append(build_p("", space_after=120))

    # Section 5: Dividend Yield Indication
    body_elements.append(build_p("5. Dividend Indication & High-Yield Asset Guide", bold=True, color="1E3A8A", size_pt=15, space_after=120))
    body_elements.append(build_p(
        "Dividend yields provide a powerful cash-flow cushion during market corrections. V2 classifies assets into four dividend tiers:",
        space_after=100
    ))
    body_elements.append(build_bullet("Coal India (7.5%), ONGC (5.2%), BPCL (5.8%), Power Grid (3.6%), NTPC (3.3%), ITC (3.5%), CPSE ETF (4.5%), Div Opp ETF (4.2%).", "💰 High Yield (>= 3.0%):"))
    body_elements.append(build_bullet("TCS (2.6%), HCL Tech (3.1%), Infosys (2.5%), Tech Mahindra (2.8%), Tata Steel (2.7%), Nifty 50 BeES (1.2%).", "💵 Moderate Yield (1.0% - 3.0%):"))
    body_elements.append(build_bullet("Reliance (0.3%), HDFC Bank (1.2%), Bharti Airtel (0.7%), L&T (0.9%), Titan (0.4%), Midcap 150 ETF (0.8%).", "🌱 Growth / Low Yield (< 1.0%):"))
    body_elements.append(build_bullet("Gold BeES, Silver BeES, International Nasdaq/NYSE FANG+ ETFs.", "⚪ Zero Dividend (Commodities / US Tech):"))

    # Section 6: Inbuilt Auto-Exit Engine
    body_elements.append(build_p("6. Comprehensive Auto-Exit Engine", bold=True, color="1E3A8A", size_pt=15, space_after=120))
    body_elements.append(build_p(
        "Every trade lifecycle is guarded by 5 automated exit mechanisms evaluated continuously on cron triggers and page loads:",
        space_after=100
    ))
    body_elements.append(build_bullet("Triggered when CMP >= Volatility Target Price. Locks in gain.", "1. Target Price Achieved (TARGET_ACHIEVED):"))
    body_elements.append(build_bullet("Triggered when CMP <= Volatility Stop Loss Price. Preserves capital.", "2. Stop Loss Hit (STOP_LOSS_HIT):"))
    body_elements.append(build_bullet("Once unrealized profit reaches +3.0%, the stop loss moves to +0.5% above entry.", "3. Dynamic Trailing Profit Lock (TRAILING_STOP_HIT):"))
    body_elements.append(build_bullet("For swing trades, if RSI(14) >= 76 and profit > +1.5%, gains are locked early.", "4. Overbought Swing Exhaustion (OVERBOUGHT_EXIT):"))
    body_elements.append(build_bullet("Triggered at 03:10 PM IST to close all intraday trades at current market price.", "5. Intraday Auto Square-off (INTRADAY_SQUAREOFF):"))

    # Section 7: External Cron Setup
    body_elements.append(build_p("7. External Cron Automation (cron-job.org)", bold=True, color="1E3A8A", size_pt=15, space_after=120))
    body_elements.append(build_p(
        "You can automate the platform for free using https://cron-job.org/en/ via two methods:",
        space_after=100
    ))
    body_elements.append(build_bullet("Ping your Streamlit app directly with GET: https://<your-app>.streamlit.app/?cron_trigger=1&mode=PAPER_TRADE_3PM&token=agy_quant_secure_token_2026", "Method 1: Direct App Query (No extra server needed):"))
    body_elements.append(build_bullet("Host cron_webhook.py on Render/VPS and point cron-job.org POST to /trigger with JSON payload: {\"mode\": \"PAPER_TRADE_3PM\", \"token\": \"...\"}", "Method 2: Standalone Webhook Server:"))
    body_elements.append(build_bullet("09:45 AM IST (Intraday Entry), 03:00 PM IST (3 PM Accumulation & AI/RAG), 03:10 PM IST (Intraday Square-off).", "Daily Schedule:"))

    # Section 8: Multi-Regime KPI Matrix
    body_elements.append(build_p("8. Multi-Regime & Category Performance Matrix", bold=True, color="1E3A8A", size_pt=15, space_after=120))
    body_elements.append(build_p(
        "Tab 2 provides a dual-axis KPI matrix slicing performance by Strategy Preset and Market Regime at Entry "
        "(Strong Bull, Bear / Correction, Sideways Consolidation). It computes Win Rate %, Profit Factor, Realized Net PnL, "
        "Unrealized MTM, and Average Holding Duration.",
        space_after=120
    ))

    # Section 9: Parameter Calibration Studio & Monthly Tuning Evolution
    body_elements.append(build_p("9. Interactive Parameter Calibration Studio & Strategy Evolution", bold=True, color="1E3A8A", size_pt=15, space_after=120))
    body_elements.append(build_bullet("Adjust indicator weights (DMA, RSI, Low, Volume, %B, VWAP) via GUI sliders in real time without modifying source code.", "Interactive Sliders:"))
    body_elements.append(build_bullet("Clear specifications explain whether higher or lower values indicate a stronger BUY edge vs SELL edge across all 34 parameters.", "Directionality Matrix:"))
    body_elements.append(build_bullet("AI/RAG diagnoses paper ledger bottlenecks and recommends optimized parameters with a one-click apply button.", "Empirical AI/RAG Auto-Tuner:"))
    body_elements.append(build_bullet("Automated cron background tasks run strictly on weekdays (Mon-Fri) and safely bypass weekends.", "Weekday Schedule Guard:"))
    body_elements.append(build_bullet("Tracks month-over-month Win Rate %, Profit Factor, Realized PnL, and parameter tuning event frequencies.", "Monthly Performance Evolution:"))
    body_elements.append(build_bullet("Chronological audit trail logging every manual adjustment, AI auto-tune, and baseline reset.", "Parameter Change Audit Log:"))

    body_elements.append(build_p("", space_after=180))
    body_elements.append(build_p("© 2026 AGY Quantitative Research Team • Designed for Antigravity Platform", italic=True, color="94A3B8", size_pt=9))

    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    {''.join(body_elements)}
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>
    </w:sectPr>
  </w:body>
</w:document>"""

    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

    rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

    doc_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault>
      <w:rPr>
        <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>
        <w:sz w:val="21"/>
        <w:color w:val="334155"/>
      </w:rPr>
    </w:rPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:styleId="Normal" w:default="1">
    <w:name w:val="Normal"/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
      <w:b/>
      <w:sz w:val="48"/>
      <w:color w:val="0F172A"/>
    </w:rPr>
  </w:style>
</w:styles>"""

    # Build ZIP archive in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", rels_xml)
        zf.writestr("word/_rels/document.xml.rels", doc_rels_xml)
        zf.writestr("word/styles.xml", styles_xml)
        zf.writestr("word/document.xml", document_xml)

    return buf.getvalue()

def export_v2_docx_file(output_filepath=None):
    if output_filepath is None:
        output_filepath = os.path.join(os.path.dirname(__file__), "AGY_Quant_Platform_V2_Guide.docx")
    content_bytes = generate_v2_docx_content()
    with open(output_filepath, "wb") as f:
        f.write(content_bytes)
    return output_filepath, content_bytes

if __name__ == "__main__":
    out_path, _ = export_v2_docx_file()
    print(f"Successfully generated DOCX at: {out_path}")

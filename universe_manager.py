"""
AGY Quant Platform V2 - Dynamic Universe Management & Expansion Engine
======================================================================
Provides standard Core universe (87 assets) and Expanded NIFTY 250 universe
(250 liquid Large & Midcap stocks + 47 Non-Sectoral ETFs).
Supports 1-click analytical universe expansion for all platform tabs.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
import streamlit as st

logger = logging.getLogger("UniverseManager")

UNIVERSE_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "data", "universe_config.json")
RUNTIME_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "runtime_config.json")

# =====================================================================
# 1. CORE UNIVERSE (35 NON-SECTORAL ETFs + 52 STOCKS)
# =====================================================================
CORE_ETF_CONFIG = [
    {"ticker": "NIFTYBEES.NS", "name": "Nippon Nifty 50 BeES", "category": "Large Cap", "expense": 0.04},
    {"ticker": "SETFNIF50.NS", "name": "SBI Nifty 50 ETF", "category": "Large Cap", "expense": 0.04},
    {"ticker": "ICICINIFTY.NS", "name": "ICICI Nifty 50 ETF", "category": "Large Cap", "expense": 0.03},
    {"ticker": "HDFCNIFTY.NS", "name": "HDFC Nifty 50 ETF", "category": "Large Cap", "expense": 0.05},
    {"ticker": "NEXT50IETF.NS", "name": "ICICI Nifty Next 50", "category": "Next 50", "expense": 0.30},
    {"ticker": "JUNIORBEES.NS", "name": "Nippon Junior BeES", "category": "Next 50", "expense": 0.12},
    {"ticker": "MIDCAPIETF.NS", "name": "Mirae Nifty Midcap 150", "category": "Midcap", "expense": 0.21},
    {"ticker": "MID150BEES.NS", "name": "Nippon Midcap 150 BeES", "category": "Midcap", "expense": 0.20},
    {"ticker": "HDFCMID150.NS", "name": "HDFC Nifty Midcap 150", "category": "Midcap", "expense": 0.20},
    {"ticker": "HDFCSML250.NS", "name": "HDFC Smallcap 250", "category": "Smallcap", "expense": 0.20},
    {"ticker": "SMALLCAP.NS", "name": "Mirae Smallcap 250", "category": "Smallcap", "expense": 0.26},
    {"ticker": "NV20IETF.NS", "name": "ICICI Nifty50 Value 20", "category": "Value", "expense": 0.27},
    {"ticker": "MOVALUE.NS", "name": "Motilal Enhanced Value", "category": "Value", "expense": 0.35},
    {"ticker": "ICICIB22.NS", "name": "ICICI BHARAT 22 ETF", "category": "CPSE / PSU", "expense": 0.05},
    {"ticker": "CPSEETF.NS", "name": "CPSE ETF (Nippon)", "category": "CPSE / PSU", "expense": 0.05},
    {"ticker": "DIVOPPBEES.NS", "name": "Nippon Dividend Opp 50", "category": "Dividend", "expense": 0.37},
    {"ticker": "NIFTYQLITY.NS", "name": "SBI Nifty 200 Quality 30", "category": "Smart Beta", "expense": 0.30},
    {"ticker": "QUAL30IETF.NS", "name": "ICICI Nifty 200 Quality 30", "category": "Smart Beta", "expense": 0.30},
    {"ticker": "ALPHAETF.NS", "name": "Mirae Nifty 200 Alpha 30", "category": "Smart Beta", "expense": 0.41},
    {"ticker": "ALPL30IETF.NS", "name": "ICICI Alpha Low Vol 30", "category": "Smart Beta", "expense": 0.35},
    {"ticker": "KOTAKALPHA.NS", "name": "Kotak Nifty 200 Alpha 30", "category": "Smart Beta", "expense": 0.36},
    {"ticker": "MOM30IETF.NS", "name": "ICICI Nifty200 Momentum 30", "category": "Smart Beta", "expense": 0.38},
    {"ticker": "MOMENTUM50.NS", "name": "Nippon Nifty 500 Momentum 50", "category": "Smart Beta", "expense": 0.39},
    {"ticker": "HDFCMOM30.NS", "name": "HDFC Nifty200 Momentum 30", "category": "Smart Beta", "expense": 0.40},
    {"ticker": "MOM500.NS", "name": "Motilal Nifty 500 ETF", "category": "Broad Market", "expense": 0.35},
    {"ticker": "GOLDBEES.NS", "name": "Nippon Gold BeES", "category": "Commodity", "expense": 0.79},
    {"ticker": "SETFGOLD.NS", "name": "SBI Gold ETF", "category": "Commodity", "expense": 0.50},
    {"ticker": "SILVERBEES.NS", "name": "Nippon Silver BeES", "category": "Commodity", "expense": 0.50},
    {"ticker": "SILVERIETF.NS", "name": "ICICI Silver ETF", "category": "Commodity", "expense": 0.45},
    {"ticker": "MON100.NS", "name": "Motilal Nasdaq 100", "category": "International", "expense": 0.58},
    {"ticker": "MONQ50.NS", "name": "Motilal Nasdaq Q 50", "category": "International", "expense": 0.60},
    {"ticker": "MASPTOP50.NS", "name": "Mirae S&P 500 Top 50", "category": "International", "expense": 0.70},
    {"ticker": "MAFANG.NS", "name": "Mirae NYSE FANG+ ETF", "category": "International", "expense": 0.65},
    {"ticker": "HNGSNGBEES.NS", "name": "Nippon Hang Seng BeES", "category": "International", "expense": 0.78},
    {"ticker": "MAHKTECH.NS", "name": "Mirae Hang Seng TECH ETF", "category": "International", "expense": 0.70},
]

CORE_STOCK_CONFIG = [
    {"ticker": "RELIANCE.NS", "name": "Reliance Industries", "category": "Energy & Retail", "expense": np.nan},
    {"ticker": "TCS.NS", "name": "Tata Consultancy Services", "category": "IT Services", "expense": np.nan},
    {"ticker": "HDFCBANK.NS", "name": "HDFC Bank", "category": "Banking", "expense": np.nan},
    {"ticker": "ICICIBANK.NS", "name": "ICICI Bank", "category": "Banking", "expense": np.nan},
    {"ticker": "INFY.NS", "name": "Infosys Ltd", "category": "IT Services", "expense": np.nan},
    {"ticker": "BHARTIARTL.NS", "name": "Bharti Airtel", "category": "Telecom", "expense": np.nan},
    {"ticker": "ITC.NS", "name": "ITC Ltd", "category": "FMCG", "expense": np.nan},
    {"ticker": "SBIN.NS", "name": "State Bank of India", "category": "PSU Banking", "expense": np.nan},
    {"ticker": "LT.NS", "name": "Larsen & Toubro", "category": "Infrastructure", "expense": np.nan},
    {"ticker": "HINDUNILVR.NS", "name": "Hindustan Unilever", "category": "FMCG", "expense": np.nan},
    {"ticker": "AXISBANK.NS", "name": "Axis Bank", "category": "Banking", "expense": np.nan},
    {"ticker": "KOTAKBANK.NS", "name": "Kotak Mahindra Bank", "category": "Banking", "expense": np.nan},
    {"ticker": "M&M.NS", "name": "Mahindra & Mahindra", "category": "Automobile", "expense": np.nan},
    {"ticker": "MARUTI.NS", "name": "Maruti Suzuki", "category": "Automobile", "expense": np.nan},
    {"ticker": "TATAMOTORS.NS", "name": "Tata Motors", "category": "Automobile", "expense": np.nan},
    {"ticker": "SUNPHARMA.NS", "name": "Sun Pharma", "category": "Pharma", "expense": np.nan},
    {"ticker": "TITAN.NS", "name": "Titan Company", "category": "Consumer Discretionary", "expense": np.nan},
    {"ticker": "BAJFINANCE.NS", "name": "Bajaj Finance", "category": "NBFC", "expense": np.nan},
    {"ticker": "BAJAJFINSV.NS", "name": "Bajaj Finserv", "category": "Financial Services", "expense": np.nan},
    {"ticker": "NTPC.NS", "name": "NTPC Ltd", "category": "Power / PSU", "expense": np.nan},
    {"ticker": "POWERGRID.NS", "name": "Power Grid Corp", "category": "Power / PSU", "expense": np.nan},
    {"ticker": "ONGC.NS", "name": "ONGC", "category": "Oil & Gas / PSU", "expense": np.nan},
    {"ticker": "COALINDIA.NS", "name": "Coal India", "category": "Mining / PSU", "expense": np.nan},
    {"ticker": "TATASTEEL.NS", "name": "Tata Steel", "category": "Metals", "expense": np.nan},
    {"ticker": "JSWSTEEL.NS", "name": "JSW Steel", "category": "Metals", "expense": np.nan},
    {"ticker": "HINDALCO.NS", "name": "Hindalco Industries", "category": "Metals", "expense": np.nan},
    {"ticker": "ADANIENT.NS", "name": "Adani Enterprises", "category": "Conglomerate", "expense": np.nan},
    {"ticker": "ADANIPORTS.NS", "name": "Adani Ports & SEZ", "category": "Infrastructure", "expense": np.nan},
    {"ticker": "ULTRACEMCO.NS", "name": "UltraTech Cement", "category": "Cement", "expense": np.nan},
    {"ticker": "GRASIM.NS", "name": "Grasim Industries", "category": "Materials", "expense": np.nan},
    {"ticker": "WIPRO.NS", "name": "Wipro", "category": "IT Services", "expense": np.nan},
    {"ticker": "HCLTECH.NS", "name": "HCL Technologies", "category": "IT Services", "expense": np.nan},
    {"ticker": "TECHM.NS", "name": "Tech Mahindra", "category": "IT Services", "expense": np.nan},
    {"ticker": "DRREDDY.NS", "name": "Dr. Reddy's Labs", "category": "Pharma", "expense": np.nan},
    {"ticker": "CIPLA.NS", "name": "Cipla Ltd", "category": "Pharma", "expense": np.nan},
    {"ticker": "APOLLOHOSP.NS", "name": "Apollo Hospitals", "category": "Healthcare", "expense": np.nan},
    {"ticker": "ASIANPAINT.NS", "name": "Asian Paints", "category": "Paints / Consumer", "expense": np.nan},
    {"ticker": "NESTLEIND.NS", "name": "Nestle India", "category": "FMCG", "expense": np.nan},
    {"ticker": "BRITANNIA.NS", "name": "Britannia Industries", "category": "FMCG", "expense": np.nan},
    {"ticker": "TATACONSUM.NS", "name": "Tata Consumer Products", "category": "FMCG", "expense": np.nan},
    {"ticker": "EICHERMOT.NS", "name": "Eicher Motors", "category": "Automobile", "expense": np.nan},
    {"ticker": "HEROMOTOCO.NS", "name": "Hero MotoCorp", "category": "Automobile", "expense": np.nan},
    {"ticker": "BPCL.NS", "name": "BPCL", "category": "Oil & Gas / PSU", "expense": np.nan},
    {"ticker": "BEL.NS", "name": "Bharat Electronics", "category": "Defense / PSU", "expense": np.nan},
    {"ticker": "HAL.NS", "name": "Hindustan Aeronautics", "category": "Defense / PSU", "expense": np.nan},
    {"ticker": "TRENT.NS", "name": "Trent Ltd", "category": "Retail", "expense": np.nan},
    {"ticker": "VBL.NS", "name": "Varun Beverages", "category": "Beverages", "expense": np.nan},
    {"ticker": "CHOLAFIN.NS", "name": "Cholamandalam Inv", "category": "NBFC", "expense": np.nan},
    {"ticker": "CUMMINSIND.NS", "name": "Cummins India", "category": "Capital Goods", "expense": np.nan},
    {"ticker": "POLYCAB.NS", "name": "Polycab India", "category": "Cables & Electricals", "expense": np.nan},
    {"ticker": "PERSISTENT.NS", "name": "Persistent Systems", "category": "IT Midcap", "expense": np.nan},
    {"ticker": "DIXON.NS", "name": "Dixon Technologies", "category": "EMS / Electronics", "expense": np.nan},
]

# =====================================================================
# 2. EXPANDED NON-SECTORAL ETF CONFIGURATION (47 ETFs)
# (Strictly broad indices, factor/smart-beta, commodities, international)
# =====================================================================
EXPANDED_NON_SECTORAL_ETF_CONFIG = CORE_ETF_CONFIG + [
    {"ticker": "KOTAKNIFTY.NS", "name": "Kotak Nifty 50 ETF", "category": "Large Cap", "expense": 0.04},
    {"ticker": "UTINIFTETF.NS", "name": "UTI Nifty 50 ETF", "category": "Large Cap", "expense": 0.05},
    {"ticker": "HDFCNEXT50.NS", "name": "HDFC Nifty Next 50", "category": "Next 50", "expense": 0.25},
    {"ticker": "LOWVOLIETF.NS", "name": "ICICI Nifty 100 Low Vol 30", "category": "Smart Beta", "expense": 0.35},
    {"ticker": "ICICILOVOL.NS", "name": "ICICI Alpha Low-Vol 30", "category": "Smart Beta", "expense": 0.36},
    {"ticker": "NIFTYEQL.NS", "name": "DSP Nifty 50 Equal Weight", "category": "Smart Beta", "expense": 0.25},
    {"ticker": "HDFCGOLD.NS", "name": "HDFC Gold ETF", "category": "Commodity", "expense": 0.55},
    {"ticker": "KOTAKGOLD.NS", "name": "Kotak Gold ETF", "category": "Commodity", "expense": 0.55},
    {"ticker": "SETFSILVER.NS", "name": "SBI Silver ETF", "category": "Commodity", "expense": 0.48},
    {"ticker": "HDFCSILVER.NS", "name": "HDFC Silver ETF", "category": "Commodity", "expense": 0.48},
    {"ticker": "HDFCNIF500.NS", "name": "HDFC Nifty 500 ETF", "category": "Broad Market", "expense": 0.32},
    {"ticker": "KOTAKNV20.NS", "name": "Kotak Nifty 50 Value 20", "category": "Smart Beta", "expense": 0.30},
]

# =====================================================================
# 3. COMPLETE NIFTY 250 UNIVERSE (250 LARGE & MIDCAP STOCKS)
# =====================================================================
# Cleaned, liquid NIFTY LargeMidcap 250 universe
_NIFTY_250_RAW = [
    # --- Top 50 (Nifty 50 Benchmark) ---
    ("RELIANCE.NS", "Reliance Industries", "Energy & Retail"),
    ("TCS.NS", "Tata Consultancy Services", "IT Services"),
    ("HDFCBANK.NS", "HDFC Bank", "Banking"),
    ("ICICIBANK.NS", "ICICI Bank", "Banking"),
    ("INFY.NS", "Infosys Ltd", "IT Services"),
    ("BHARTIARTL.NS", "Bharti Airtel", "Telecom"),
    ("ITC.NS", "ITC Ltd", "FMCG"),
    ("SBIN.NS", "State Bank of India", "PSU Banking"),
    ("LT.NS", "Larsen & Toubro", "Infrastructure"),
    ("HINDUNILVR.NS", "Hindustan Unilever", "FMCG"),
    ("AXISBANK.NS", "Axis Bank", "Banking"),
    ("KOTAKBANK.NS", "Kotak Mahindra Bank", "Banking"),
    ("M&M.NS", "Mahindra & Mahindra", "Automobile"),
    ("MARUTI.NS", "Maruti Suzuki", "Automobile"),
    ("TATAMOTORS.NS", "Tata Motors", "Automobile"),
    ("SUNPHARMA.NS", "Sun Pharma", "Pharma"),
    ("TITAN.NS", "Titan Company", "Consumer Discretionary"),
    ("BAJFINANCE.NS", "Bajaj Finance", "NBFC"),
    ("BAJAJFINSV.NS", "Bajaj Finserv", "Financial Services"),
    ("NTPC.NS", "NTPC Ltd", "Power / PSU"),
    ("POWERGRID.NS", "Power Grid Corp", "Power / PSU"),
    ("ONGC.NS", "ONGC", "Oil & Gas / PSU"),
    ("COALINDIA.NS", "Coal India", "Mining / PSU"),
    ("TATASTEEL.NS", "Tata Steel", "Metals"),
    ("JSWSTEEL.NS", "JSW Steel", "Metals"),
    ("HINDALCO.NS", "Hindalco Industries", "Metals"),
    ("ADANIENT.NS", "Adani Enterprises", "Conglomerate"),
    ("ADANIPORTS.NS", "Adani Ports & SEZ", "Infrastructure"),
    ("ULTRACEMCO.NS", "UltraTech Cement", "Cement"),
    ("GRASIM.NS", "Grasim Industries", "Materials"),
    ("WIPRO.NS", "Wipro", "IT Services"),
    ("HCLTECH.NS", "HCL Technologies", "IT Services"),
    ("TECHM.NS", "Tech Mahindra", "IT Services"),
    ("DRREDDY.NS", "Dr. Reddy's Labs", "Pharma"),
    ("CIPLA.NS", "Cipla Ltd", "Pharma"),
    ("APOLLOHOSP.NS", "Apollo Hospitals", "Healthcare"),
    ("ASIANPAINT.NS", "Asian Paints", "Paints / Consumer"),
    ("NESTLEIND.NS", "Nestle India", "FMCG"),
    ("BRITANNIA.NS", "Britannia Industries", "FMCG"),
    ("TATACONSUM.NS", "Tata Consumer Products", "FMCG"),
    ("EICHERMOT.NS", "Eicher Motors", "Automobile"),
    ("HEROMOTOCO.NS", "Hero MotoCorp", "Automobile"),
    ("BPCL.NS", "BPCL", "Oil & Gas / PSU"),
    ("BEL.NS", "Bharat Electronics", "Defense / PSU"),
    ("HAL.NS", "Hindustan Aeronautics", "Defense / PSU"),
    ("TRENT.NS", "Trent Ltd", "Retail"),
    ("VBL.NS", "Varun Beverages", "Beverages"),
    ("SHRIRAMFIN.NS", "Shriram Finance", "NBFC"),
    ("JSWENERGY.NS", "JSW Energy", "Power"),
    ("BAJAJ-AUTO.NS", "Bajaj Auto", "Automobile"),

    # --- Next 50 (Nifty Next 50 Large Caps) ---
    ("ABB.NS", "ABB India", "Capital Goods"),
    ("ADANIENSOL.NS", "Adani Energy Solutions", "Power"),
    ("ADANIGREEN.NS", "Adani Green Energy", "Renewable Energy"),
    ("ADANIPOWER.NS", "Adani Power", "Power"),
    ("AMBUJACEM.NS", "Ambuja Cements", "Cement"),
    ("BANKBARODA.NS", "Bank of Baroda", "PSU Banking"),
    ("BHEL.NS", "Bharat Heavy Electricals", "Capital Goods / PSU"),
    ("BOSCHLTD.NS", "Bosch Ltd", "Auto Ancillary"),
    ("CANBK.NS", "Canara Bank", "PSU Banking"),
    ("CHOLAFIN.NS", "Cholamandalam Inv", "NBFC"),
    ("COFORGE.NS", "Coforge Ltd", "IT Services"),
    ("COLPAL.NS", "Colgate-Palmolive India", "FMCG"),
    ("CUMMINSIND.NS", "Cummins India", "Capital Goods"),
    ("DABUR.NS", "Dabur India", "FMCG"),
    ("DIVISLAB.NS", "Divi's Laboratories", "Pharma"),
    ("DIXON.NS", "Dixon Technologies", "EMS / Electronics"),
    ("DLF.NS", "DLF Ltd", "Realty"),
    ("DMART.NS", "Avenue Supermarts (DMart)", "Retail"),
    ("GAIL.NS", "GAIL India", "Gas & Energy / PSU"),
    ("GODREJCP.NS", "Godrej Consumer Products", "FMCG"),
    ("HAVELLS.NS", "Havells India", "Consumer Electricals"),
    ("HDFCLIFE.NS", "HDFC Life Insurance", "Insurance"),
    ("ICICIGI.NS", "ICICI Lombard General Ins", "Insurance"),
    ("ICICIPRULI.NS", "ICICI Prudential Life Ins", "Insurance"),
    ("INDIANB.NS", "Indian Bank", "PSU Banking"),
    ("INDIGO.NS", "InterGlobe Aviation (IndiGo)", "Aviation"),
    ("INDUSINDBK.NS", "IndusInd Bank", "Banking"),
    ("IOC.NS", "Indian Oil Corp", "Oil & Gas / PSU"),
    ("IRFC.NS", "Indian Railway Finance", "Railway / PSU"),
    ("JINDALSTEL.NS", "Jindal Steel & Power", "Metals"),
    ("JIOFIN.NS", "Jio Financial Services", "Financial Services"),
    ("LTIM.NS", "LTIMindtree", "IT Services"),
    ("LUPIN.NS", "Lupin Ltd", "Pharma"),
    ("MARICO.NS", "Marico Ltd", "FMCG"),
    ("MAXHEALTH.NS", "Max Healthcare Institute", "Healthcare"),
    ("MOTHERSON.NS", "Samvardhana Motherson", "Auto Ancillary"),
    ("NAUKRI.NS", "Info Edge (Naukri)", "Platform / Tech"),
    ("NHPC.NS", "NHPC Ltd", "Power / PSU"),
    ("NMDC.NS", "NMDC Ltd", "Mining / PSU"),
    ("PFC.NS", "Power Finance Corp", "NBFC / PSU"),
    ("PIDILITIND.NS", "Pidilite Industries", "Chemicals"),
    ("PNB.NS", "Punjab National Bank", "PSU Banking"),
    ("POLYCAB.NS", "Polycab India", "Cables & Electricals"),
    ("RECLTD.NS", "REC Ltd", "NBFC / PSU"),
    ("SBILIFE.NS", "SBI Life Insurance", "Insurance"),
    ("SIEMENS.NS", "Siemens India", "Capital Goods"),
    ("TATAPOWER.NS", "Tata Power", "Power & Energy"),
    ("TORNTPHARM.NS", "Torrent Pharmaceuticals", "Pharma"),
    ("TVSMOTOR.NS", "TVS Motor Company", "Automobile"),
    ("VEDL.NS", "Vedanta Ltd", "Metals & Mining"),
    ("ZOMATO.NS", "Zomato Ltd", "Platform / Food Delivery"),

    # --- High-Conviction Midcaps 150 (Industrials, Defense, Tech, Chemicals, Financials) ---
    ("PERSISTENT.NS", "Persistent Systems", "IT Midcap"),
    ("KPITTECH.NS", "KPIT Technologies", "Automotive Software"),
    ("TATAELXSI.NS", "Tata Elxsi", "IT Design & Tech"),
    ("MPHASIS.NS", "Mphasis Ltd", "IT Services"),
    ("LTTS.NS", "L&T Technology Services", "ER&D IT"),
    ("CYIENT.NS", "Cyient Ltd", "Engineering Tech"),
    ("SONACOMS.NS", "Sona BLW Precision", "EV & Auto Ancillary"),
    ("MAZDOCK.NS", "Mazagon Dock Shipbuilders", "Defense / PSU"),
    ("COCHINSHIP.NS", "Cochin Shipyard", "Defense / PSU"),
    ("BDL.NS", "Bharat Dynamics", "Defense / PSU"),
    ("GRSE.NS", "Garden Reach Shipbuilders", "Defense / PSU"),
    ("ASTRAL.NS", "Astral Ltd", "Building Materials"),
    ("SUPREMEIND.NS", "Supreme Industries", "Plastic Products"),
    ("KEI.NS", "KEI Industries", "Cables & Wire"),
    ("RRKABEL.NS", "R R Kabel", "Cables & Electricals"),
    ("BHARATFORG.NS", "Bharat Forge", "Industrial Forgings"),
    ("SCHAEFFLER.NS", "Schaeffler India", "Bearings & Auto"),
    ("TIMKEN.NS", "Timken India", "Bearings"),
    ("SKFINDIA.NS", "SKF India", "Bearings"),
    ("AIAENG.NS", "AIA Engineering", "Capital Goods"),
    ("THERMAX.NS", "Thermax Ltd", "Clean Energy & Infra"),
    ("CGPOWER.NS", "CG Power & Industrial", "Electrical Goods"),
    ("KAYNES.NS", "Kaynes Technology", "EMS / Electronics"),
    ("SUZLON.NS", "Suzlon Energy", "Renewable Energy"),
    ("INOXWIND.NS", "Inox Wind", "Renewable Energy"),
    ("EXIDEIND.NS", "Exide Industries", "Batteries"),
    ("AMARAJABAT.NS", "Amara Raja Energy", "Batteries"),

    # --- Financials & Fintech Leaders ---
    ("MUTHOOTFIN.NS", "Muthoot Finance", "Gold Loans / NBFC"),
    ("MANAPPURAM.NS", "Manappuram Finance", "Gold Loans / NBFC"),
    ("M&MFIN.NS", "Mahindra Financial Services", "NBFC"),
    ("POONAWALLA.NS", "Poonawalla Fincorp", "NBFC"),
    ("SUNDARMFIN.NS", "Sundaram Finance", "NBFC"),
    ("LICHSGFIN.NS", "LIC Housing Finance", "Housing Finance"),
    ("CANFINHOME.NS", "Can Fin Homes", "Housing Finance"),
    ("AUBANK.NS", "AU Small Finance Bank", "Banking"),
    ("FEDERALBNK.NS", "Federal Bank", "Banking"),
    ("IDFCFIRSTB.NS", "IDFC First Bank", "Banking"),
    ("BANDHANBNK.NS", "Bandhan Bank", "Banking"),
    ("KARURVYSYA.NS", "Karur Vysya Bank", "Banking"),
    ("RBLBANK.NS", "RBL Bank", "Banking"),
    ("SBICARD.NS", "SBI Cards & Payment", "Financial Services"),
    ("ANGELONE.NS", "Angel One", "Broking / Fintech"),
    ("BSE.NS", "BSE Ltd", "Financial Exchange"),
    ("MCX.NS", "Multi Commodity Exchange", "Commodity Exchange"),
    ("CDSL.NS", "CDSL", "Depository Services"),
    ("CAMS.NS", "CAMS", "MF Registrar / Fintech"),
    ("HDFCAMC.NS", "HDFC Asset Management", "Asset Management"),
    ("NAM-INDIA.NS", "Nippon Life India AMC", "Asset Management"),
    ("POLICYBZR.NS", "PB Fintech (Policybazaar)", "Fintech / Insurtech"),
    ("PAYTM.NS", "One97 Communications (Paytm)", "Fintech"),
    ("NYKAA.NS", "FSN E-Commerce (Nykaa)", "Beauty / E-Commerce"),
    ("DELHIVERY.NS", "Delhivery Ltd", "Logistics"),

    # --- Pharma, Hospitals & Diagnostics ---
    ("ALKEM.NS", "Alkem Laboratories", "Pharma"),
    ("AUROPHARMA.NS", "Aurobindo Pharma", "Pharma"),
    ("BIOCON.NS", "Biocon Ltd", "Biopharma"),
    ("GLENMARK.NS", "Glenmark Pharmaceuticals", "Pharma"),
    ("IPCLAB.NS", "IPCA Laboratories", "Pharma"),
    ("LAURUSLABS.NS", "Laurus Labs", "Pharma & API"),
    ("MANKIND.NS", "Mankind Pharma", "Pharma"),
    ("NATCOPHARM.NS", "Natco Pharma", "Pharma"),
    ("SYNGENE.NS", "Syngene International", "Contract Research / CRO"),
    ("AJANTPHARM.NS", "Ajanta Pharma", "Pharma"),
    ("JBCHEPHARM.NS", "JB Chemicals & Pharma", "Pharma"),
    ("FORTIS.NS", "Fortis Healthcare", "Hospitals"),
    ("MEDANTA.NS", "Global Health (Medanta)", "Hospitals"),
    ("ASTERDM.NS", "Aster DM Healthcare", "Hospitals"),
    ("KIMS.NS", "Krishna Institute of Med Sci", "Hospitals"),
    ("METROPOLIS.NS", "Metropolis Healthcare", "Diagnostics"),
    ("LALPATHLAB.NS", "Dr. Lal PathLabs", "Diagnostics"),

    # --- Consumer Discretionary, Quick Service & Realty ---
    ("JUBLFOOD.NS", "Jubilant FoodWorks (Domino's)", "QSR"),
    ("DEVYANI.NS", "Devyani International (KFC)", "QSR"),
    ("WESTLIFE.NS", "Westlife Foodworld (McDonald's)", "QSR"),
    ("RADICO.NS", "Radico Khaitan", "Alcohol / Spirits"),
    ("MCDOWELL-N.NS", "United Spirits", "Alcohol / Spirits"),
    ("PAGEIND.NS", "Page Industries (Jockey)", "Apparel"),
    ("BATAINDIA.NS", "Bata India", "Footwear"),
    ("RELAXO.NS", "Relaxo Footwears", "Footwear"),
    ("VGUARD.NS", "V-Guard Industries", "Consumer Electricals"),
    ("CROMPTON.NS", "Crompton Greaves Consumer", "Consumer Electricals"),
    ("KAJARIACER.NS", "Kajaria Ceramics", "Ceramics"),
    ("CENTURYPLY.NS", "Century Plyboards", "Building Materials"),
    ("OBEROIRLTY.NS", "Oberoi Realty", "Realty"),
    ("GODREJPROP.NS", "Godrej Properties", "Realty"),
    ("PHOENIXLTD.NS", "The Phoenix Mills", "Malls & Realty"),
    ("BRIGADE.NS", "Brigade Enterprises", "Realty"),
    ("PRESTIGE.NS", "Prestige Estates Projects", "Realty"),
    ("SOBHA.NS", "Sobha Ltd", "Realty"),

    # --- Specialty Chemicals & Agro ---
    ("DEEPAKNTR.NS", "Deepak Nitrite", "Specialty Chemicals"),
    ("PIIND.NS", "PI Industries", "Agrochem / CSM"),
    ("SRF.NS", "SRF Ltd", "Chemicals & Packaging"),
    ("NAVINFLUOR.NS", "Navin Fluorine International", "Fluorochemicals"),
    ("TATACHEM.NS", "Tata Chemicals", "Inorganic Chemicals"),
    ("GUJGASLTD.NS", "Gujarat Gas", "City Gas"),
    ("IGL.NS", "Indraprastha Gas", "City Gas"),
    ("MGL.NS", "Mahanagar Gas", "City Gas"),
    ("PETRONET.NS", "Petronet LNG", "Gas Transmission / PSU"),
    ("ATGL.NS", "Adani Total Gas", "City Gas"),
    ("COROMANDEL.NS", "Coromandel International", "Fertilizers & Nutrients"),
    ("CHAMBLFERT.NS", "Chambal Fertilisers", "Fertilizers"),
    ("UPL.NS", "UPL Ltd", "Crop Protection"),
    ("FACT.NS", "Fertilisers and Chem Travancore", "Fertilizers / PSU"),
    ("CLEAN.NS", "Clean Science & Technology", "Specialty Chemicals"),
    ("FINEORG.NS", "Fine Organic Industries", "Specialty Chemicals"),
    ("FLUOROCHEM.NS", "Gujarat Fluorochemicals", "Specialty Chemicals"),

    # --- Metals, Power, Energy & Shipping ---
    ("SAIL.NS", "Steel Authority of India", "Metals / PSU"),
    ("HINDZINC.NS", "Hindustan Zinc", "Metals / PSU"),
    ("NATIONALUM.NS", "National Aluminium (NALCO)", "Aluminium / PSU"),
    ("JINDALSAW.NS", "Jindal Saw", "Pipes & Tubes"),
    ("APLLTD.NS", "APL Apollo Tubes", "Structural Tubes"),
    ("RATNAMANI.NS", "Ratnamani Metals & Tubes", "Pipes & Tubes"),
    ("OIL.NS", "Oil India", "Oil & Gas Exploration / PSU"),
    ("MRPL.NS", "Mangalore Refinery & Petrochem", "Refinery / PSU"),
    ("CHENNPETRO.NS", "Chennai Petroleum Corp", "Refinery / PSU"),
    ("CESC.NS", "CESC Ltd", "Power Distribution"),
    ("TORNTPOWER.NS", "Torrent Power", "Power Generation"),
    ("SJVN.NS", "SJVN Ltd", "Hydro Power / PSU"),
    ("NLCINDIA.NS", "NLC India", "Lignite & Power / PSU"),

    # --- Auto Ancillary, Engineering & Logistics ---
    ("TUBEINVEST.NS", "Tube Investments of India", "Auto & Engineering"),
    ("BALKRISIND.NS", "Balkrishna Industries", "Tyres / Off-Highway"),
    ("MRF.NS", "MRF Ltd", "Tyres"),
    ("APOLLOTYRE.NS", "Apollo Tyres", "Tyres"),
    ("CEATLTD.NS", "CEAT Ltd", "Tyres"),
    ("ENDURANCE.NS", "Endurance Technologies", "Auto Components"),
    ("CONCOR.NS", "Container Corp of India", "Rail Logistics / PSU"),
    ("BLUESTARCO.NS", "Blue Star Ltd", "AC & Cooling"),
    ("VOLTAS.NS", "Voltas Ltd", "AC & Engineering"),
    ("ASHOKLEY.NS", "Ashok Leyland", "Commercial Vehicles"),
    ("CASTROLIND.NS", "Castrol India", "Lubricants"),
    ("UNIONBANK.NS", "Union Bank of India", "PSU Banking"),
    ("BSOFT.NS", "Birlasoft Ltd", "IT Services"),
    ("LATENTVIEW.NS", "Latent View Analytics", "Data & AI"),
    ("MAPMYINDIA.NS", "CE Info Systems (MapmyIndia)", "Geospatial Tech"),
    ("AFFLE.NS", "Affle India", "AdTech & Mobile"),
    ("ELGIEQUIP.NS", "Elgi Equipments", "Compressors & Machinery"),
    ("FINCABLES.NS", "Finolex Cables", "Cables & Wire"),
    ("CARBORUNIV.NS", "Carborundum Universal", "Abrasives & Ceramics"),
    ("RVNL.NS", "Rail Vikas Nigam", "Railways / PSU"),
    ("IRCON.NS", "Ircon International", "Railways / PSU"),
    ("HUDCO.NS", "Housing & Urban Dev Corp", "Housing Finance / PSU"),
    ("HINDPETRO.NS", "Hindustan Petroleum (HPCL)", "Oil & Gas / PSU"),
    ("KALYANKJIL.NS", "Kalyan Jewellers", "Jewellery & Retail"),
    ("TITAGARH.NS", "Titagarh Rail Systems", "Railways & Wagons"),
    ("TRITURBINE.NS", "Triveni Turbine", "Industrial Machinery"),
    ("PVRINOX.NS", "PVR INOX", "Entertainment & Media"),
    ("CREDITACC.NS", "CreditAccess Grameen", "Microfinance"),
    ("HOMEFIRST.NS", "Home First Finance", "Affordable Housing"),
    ("AAVAS.NS", "Aavas Financiers", "Housing Finance"),
    ("GLAXO.NS", "GlaxoSmithKline Pharma", "Pharma"),
    ("SANOFI.NS", "Sanofi India", "Pharma")
]

# Build dictionary config for Nifty 250
NIFTY_250_STOCK_CONFIG = [
    {"ticker": t, "name": n, "category": c, "expense": np.nan}
    for t, n, c in _NIFTY_250_RAW
]

# Ensure uniqueness while preserving order
_seen_stk = set()
_dedup_nifty_250 = []
for item in NIFTY_250_STOCK_CONFIG:
    if item["ticker"] not in _seen_stk:
        _seen_stk.add(item["ticker"])
        _dedup_nifty_250.append(item)
NIFTY_250_STOCK_CONFIG = _dedup_nifty_250
NIFTY_100_STOCK_CONFIG = _dedup_nifty_250[:100]

# =====================================================================
# 4. CONFIG LOADER & PERSISTENCE
# =====================================================================
def get_universe_mode():
    """Returns 'EXPANDED_NIFTY_250' or 'STANDARD_CORE' from config."""
    if os.path.exists(RUNTIME_CONFIG_FILE):
        try:
            with open(RUNTIME_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("universe_mode", "EXPANDED_NIFTY_250")
        except Exception:
            pass
    return "EXPANDED_NIFTY_250"

def set_universe_mode(new_mode):
    """Saves new universe mode to runtime_config.json and universe_config.json."""
    cfg = {}
    if os.path.exists(RUNTIME_CONFIG_FILE):
        try:
            with open(RUNTIME_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
    cfg["universe_mode"] = new_mode
    cfg["active_stocks_count"] = len(NIFTY_250_STOCK_CONFIG) if new_mode == "EXPANDED_NIFTY_250" else len(CORE_STOCK_CONFIG)
    cfg["active_etfs_count"] = len(EXPANDED_NON_SECTORAL_ETF_CONFIG) if new_mode == "EXPANDED_NIFTY_250" else len(CORE_ETF_CONFIG)
    
    with open(RUNTIME_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)
        
    os.makedirs(os.path.dirname(UNIVERSE_CONFIG_FILE), exist_ok=True)
    with open(UNIVERSE_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "mode": new_mode,
            "stocks_count": cfg["active_stocks_count"],
            "etfs_count": cfg["active_etfs_count"],
            "last_updated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        }, f, indent=4)

def get_active_universe():
    """Returns (active_stocks, active_etfs) according to current configuration."""
    mode = get_universe_mode()
    if mode == "EXPANDED_NIFTY_250":
        return NIFTY_250_STOCK_CONFIG, EXPANDED_NON_SECTORAL_ETF_CONFIG
    return CORE_STOCK_CONFIG, CORE_ETF_CONFIG

# =====================================================================
# 5. UNIVERSE COVERAGE & COMPARATIVE ANALYZER
# =====================================================================
def analyze_universe_coverage():
    """Compares Core vs Expanded NIFTY 250 + Non-Sectoral ETFs."""
    core_stk_tickers = {x["ticker"] for x in CORE_STOCK_CONFIG}
    exp_stk_tickers = {x["ticker"] for x in NIFTY_250_STOCK_CONFIG}
    missing_in_core = exp_stk_tickers - core_stk_tickers
    
    core_etf_tickers = {x["ticker"] for x in CORE_ETF_CONFIG}
    exp_etf_tickers = {x["ticker"] for x in EXPANDED_NON_SECTORAL_ETF_CONFIG}
    added_etfs = exp_etf_tickers - core_etf_tickers
    
    # Categorize stocks
    stock_cats = {}
    for s in NIFTY_250_STOCK_CONFIG:
        cat = s["category"].split("/")[0].strip()
        stock_cats[cat] = stock_cats.get(cat, 0) + 1
        
    # Categorize ETFs
    etf_cats = {}
    for e in EXPANDED_NON_SECTORAL_ETF_CONFIG:
        c = e["category"]
        etf_cats[c] = etf_cats.get(c, 0) + 1
        
    return {
        "core_stocks_count": len(CORE_STOCK_CONFIG),
        "core_etfs_count": len(CORE_ETF_CONFIG),
        "core_total": len(CORE_STOCK_CONFIG) + len(CORE_ETF_CONFIG),
        "expanded_stocks_count": len(NIFTY_250_STOCK_CONFIG),
        "expanded_etfs_count": len(EXPANDED_NON_SECTORAL_ETF_CONFIG),
        "expanded_total": len(NIFTY_250_STOCK_CONFIG) + len(EXPANDED_NON_SECTORAL_ETF_CONFIG),
        "newly_added_stocks_count": len(missing_in_core),
        "newly_added_etfs_count": len(added_etfs),
        "stock_category_distribution": stock_cats,
        "etf_category_distribution": etf_cats,
        "sample_added_stocks": sorted(list(missing_in_core))[:20],
        "sample_added_etfs": sorted(list(added_etfs)),
    }

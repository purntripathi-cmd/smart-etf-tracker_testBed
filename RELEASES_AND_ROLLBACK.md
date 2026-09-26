# 🛡️ Release Versioning & Quick Rollback Guide

This document maintains the snapshot of all certified stable releases, their commit hashes, tags, release branches, and step-by-step instructions for rolling back in case of emergency.

---

## 📌 Release Version Matrix

| Version Tag | Release Branch | Commit SHA | Status | Key Highlights & Description |
| :--- | :--- | :--- | :--- | :--- |
| **`v2.2-stable-current`** | `release/v2.2-current` | `7fc376e` | 🟢 **Current Production Stable** | • Real-time **iNAV & color-coded distance** across ETFs (Cat 1, 3, 5; Stocks show `NA`)<br>• Compact single-line Market Regime & VIX status banner<br>• Preserved 5-strategy conviction tabs (`Default`, `Swing`, `Long-Term`, `Intraday`, `AI / RAG`)<br>• Removed redundant overview glance grids for clean layout |
| **`v2.1-stable-previous`** | `release/v2.1-stable-previous` | `22fcfd5` | 🟡 **2nd Stable Version (Fallback)** | • Anti-conflict engine (avoids simultaneous Buy & Sell recommendations for same ticker)<br>• Multi-AMC Precious Metals (Nippon, SBI, HDFC, ICICI, Kotak, Axis, Tata)<br>• Multi-preset paper trading execution console (1 Buy + 1 Sell per asset category across selected presets)<br>• Full ledger + audit trail reset functionality |
| **`v2.0-working-baseline`** | `main` (initial) | `3c76b47` | ⚪ **Initial Working Baseline** | • Initial monolithic migration from legacy V1 to V2 modular architecture |

---

## 🔄 How to Roll Back

### Option 1: One-Click Rollback on Streamlit Cloud (Zero CLI)
1. Open your [Streamlit Cloud Dashboard](https://share.streamlit.io).
2. Locate the app: **`smart-etf-tracker_testBed`**.
3. Click the **3 dots `...`** next to your app and choose **Edit settings**.
4. In the **Branch** field:
   - Change from `main` to **`release/v2.1-stable-previous`**.
5. Click **Save**. Streamlit Cloud will instantly redeploy the 2nd stable version.
6. *(To switch back to current, simply change the branch back to `main` or `release/v2.2-current`)*.

---

### Option 2: Local Git Checkout (Inspect or Run Locally)
To test or run the 2nd stable version locally:
```bash
# Switch to the 2nd stable release
git checkout v2.1-stable-previous

# Or switch using the branch name:
git checkout release/v2.1-stable-previous

# Run the app locally
streamlit run app.py
```

To return to the current latest version:
```bash
git checkout main
```

---

### Option 3: Hard-Reset Main Branch to 2nd Stable Version (Permanent Git Rollback)
If you wish to make the `main` branch itself point permanently back to the 2nd stable version:
```bash
# 1. Fetch all remote tags and branches
git fetch origin

# 2. Hard reset your local main branch to v2.1
git checkout main
git reset --hard v2.1-stable-previous

# 3. Force-push to GitHub origin main
git push origin main --force
```

---

### Option 4: Quick Re-sync via Antigravity Sync Script
If you ever want to re-push or sync changes between `Gravity/v2` and the testbed repository:
```powershell
python "C:\Users\epurntr\.gemini\antigravity\brain\011c45b6-0254-4db0-992a-475f2699c906\scratch\sync_v2.py"
```

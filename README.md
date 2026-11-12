# Month-End Regime Checklist Auto-Fetcher & Offline HTML Injector

This repository hosts:
1. **`regime_checklist_fetcher.html` / `index.html`**: Self-contained Month-End Regime Checklist calculator & JSON builder that works both hosted on **GitHub Pages** and **100% offline** when downloaded as a single HTML file.
2. **`fetch_regime_data.py`**: Server-side Python data fetcher that retrieves the latest live metrics (Nifty Smallcap 250 P/E and 12m drawdown, BSE Clean Environment drawdown, Brent Crude 3m % change, Hang Seng TECH % above 3y low, RBI MPC stance, MAHKTECH premium vs iNAV, and MAHKTECH 20d avg turnover), writes `regime_inputs.json`, and **automatically injects the latest values directly into the HTML file's `/* AUTO_INJECT_START */ ... /* AUTO_INJECT_END */` block**.
3. **`.github/workflows/update_regime_data.yml`**: GitHub Actions workflow that runs automatically after market close (or on-demand via **Actions → Run workflow**) to fetch the latest live data and commit the updated self-contained HTML back to the repository.

## How to Host on GitHub & Download for Offline Use
1. Create a new GitHub repository and push all files in this folder (`index.html`, `regime_checklist_fetcher.html`, `fetch_regime_data.py`, `regime_inputs.json`, and `.github/workflows/update_regime_data.yml`).
2. In your GitHub repository, go to **Settings → Actions → General → Workflow permissions** and select **Read and write permissions**.
3. Go to the **Actions** tab and click **Run workflow** (or let it run on schedule). The workflow runs `python3 fetch_regime_data.py --inject-html regime_checklist_fetcher.html`, which embeds the freshest live market data straight into the HTML code.
4. Whenever you want to run the app offline, either:
   - Click **Download Offline HTML (Data Baked In)** inside the hosted GitHub Pages app, or
   - Download `regime_checklist_fetcher.html` directly from your GitHub repository (or workflow artifacts) and open it offline in any browser.

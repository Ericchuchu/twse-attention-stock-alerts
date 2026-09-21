# TWSE Attention-Stock Alerts

A monitoring bot for the Taiwan stock market. It watches the Market Observation Post System (MOPS) for companies that were asked by the exchange to disclose recent financial figures after abnormal trading, extracts the disclosed EPS from the free-form announcement text, compares it with the previous quarter, and pushes a summary to a Telegram chat.

## Background

When a stock's price or volume moves abnormally, the Taiwan Stock Exchange (TWSE) or Taipei Exchange (TPEx) can require the company to publish its most recent unaudited figures (monthly revenue, EPS) as a material-information announcement on MOPS. These announcements

- appear at irregular times during and after the trading day,
- are written as unstructured Chinese text with inconsistent formatting, and
- often contain earnings information before the regular monthly or quarterly reports.

Reading them by hand is slow. This project turns each announcement into a structured alert within seconds of publication, which is the input an event-driven trading process needs.

## How it works

`stock_warning.py` runs an endless polling loop:

1. **Fetch.** Opens the MOPS daily material-information page (`t05st02`) for today's date (ROC calendar) in a headless browser driven by Selenium.
2. **Filter.** Keeps the rows whose subject matches a list of attention-stock phrases, for example 「達公布注意交易資訊標準」 or 「近期股價異常，故公告相關訊息」. Each phrase is compiled into a regular expression that tolerates irregular whitespace between characters.
3. **Parse.** Opens every matching announcement, takes the longest table cell as the body, and extracts EPS with a regular expression that handles full-width and half-width brackets, loss markers such as 「(虧損)」, US-cent units, and negative values written in parentheses.
4. **De-duplicate.** Skips tickers that were already reported in the current month.
5. **Enrich.** Reads the latest monthly revenue and the previous quarter's revenue and EPS from Yahoo Finance Taiwan, trying the listed suffix (`.TW`) first and the OTC suffix (`.TWO`) second, and converts the quarterly figures into monthly averages.
6. **Alert.** Computes the growth of the latest month against the previous quarter's monthly average for both revenue and EPS, and sends the result to Telegram.

The loop retries on failure and stops after five consecutive errors.

Alert format (field names are sent in Chinese):

```
<ticker><company name>
Latest monthly revenue (NT$ thousand): ...
Previous quarter, average monthly revenue (NT$ thousand): ...
Growth: ...%
Latest monthly EPS (NT$): ...
Previous quarter, average monthly EPS (NT$): ...
Growth: ...%
```

## Repository layout

| File | Purpose |
|---|---|
| `stock_warning.py` | Main program: MOPS polling, keyword filter, EPS extraction, Yahoo Finance enrichment, Telegram alert |
| `revenue_scraping.py` | Experimental, work in progress: classifies announcement subjects as monthly-revenue releases with an LLM (DeepSeek through the OpenAI-compatible API) instead of fixed keywords; defines the `RevenueInfo` record (revenue, MoM, YoY). The downstream steps are not finished |
| `Dockerfile` | Ubuntu 20.04 image with Microsoft Edge and the Python dependencies; runs `stock_warning.py` |
| `requirements.txt` | Python dependencies |
| `.env.example` | Names of the required environment variables |

## Setup

Credentials are read from environment variables. Nothing secret is stored in the code.

| Variable | Used by | Meaning |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | both scripts | Bot token issued by @BotFather |
| `TELEGRAM_CHAT_ID` | both scripts | Numeric id of the chat, group or channel that receives the alerts |
| `DEEPSEEK_API_KEY` | `revenue_scraping.py` only | DeepSeek API key |

Run locally (Python 3.8+ and Microsoft Edge required; the matching WebDriver is downloaded automatically by `webdriver_manager`):

```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...
python stock_warning.py
```

Run with Docker:

```bash
cp .env.example .env        # then fill in the values
docker build -t twse-alerts .
docker run --env-file .env twse-alerts
```

## Limitations

- The scraper depends on the current HTML structure of MOPS and Yahoo Finance Taiwan (several absolute XPaths). A redesign of either site requires updating the selectors.
- EPS extraction is rule-based. Announcements that use an unseen format are skipped rather than guessed.
- The previous-quarter monthly average is a simple quarter-divided-by-three baseline; it ignores seasonality.
- The list of already-reported tickers is kept in memory, so a restart can repeat an alert within the same month.
- This is an information tool. It does not place orders and is not investment advice.

## License

MIT, see [LICENSE](LICENSE).

# Workora BI Dashboard

## Run locally
1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Run `python -m venv .venv` and activate it.
4. Run `pip install -r requirements.txt`.
5. Run `streamlit run app.py`.

## Publish
Push this folder to a GitHub repository. In Streamlit Community Cloud, create an app from that repository, set the main file path to `app.py`, and deploy. Keep the `data/` folder in the repository. The deployed app URL is the public submission link.

## Included pages
Executive overview, Acquisition & engagement, Customer retention, Regional market, Checkout experiment.

## Data notes
All data is synthetic. Cleaning and metric assumptions are documented in the dashboard's expandable "Data quality..." section. `Active users` is shown as an engaged-session proxy because there is no persistent user ID in the traffic dataset.

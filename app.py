import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(page_title="Workora | Business Intelligence", page_icon="📊", layout="wide")
ROOT = Path(__file__).parent
DATA = ROOT / "data"

@st.cache_data
def load_data():
    traffic = pd.read_csv(DATA / "web_traffic.csv", parse_dates=["Date"])
    churn = pd.read_csv(DATA / "customer_churn.csv")
    market = pd.read_csv(DATA / "regional_market.csv")
    ab = pd.read_csv(DATA / "checkout_ab_test.csv", parse_dates=["Timestamp"])
    # Clean customer file: numeric coercion, remove duplicate IDs, impute selected fields.
    churn["TotalChargesINR"] = pd.to_numeric(churn["TotalChargesINR"], errors="coerce")
    churn = churn.drop_duplicates(subset=["CustomerID"]).copy()
    for c in ["Age", "TenureMonths", "MonthlyChargesINR", "TotalChargesINR", "SupportTickets", "LatePayments"]:
        churn[c] = churn[c].fillna(churn[c].median())
    for c in ["Region", "SubscriptionType", "ContractType", "PaymentMethod", "AutoPay", "Churn"]:
        churn[c] = churn[c].fillna(churn[c].mode().iloc[0] if not churn[c].mode().empty else "Unknown")
    # Winsorize charge outliers at the 1st/99th percentiles for robust summaries.
    for c in ["MonthlyChargesINR", "TotalChargesINR"]:
        lo, hi = churn[c].quantile([.01, .99])
        churn[c] = churn[c].clip(lo, hi)
    traffic["Date"] = pd.to_datetime(traffic["Date"], errors="coerce")
    ab["Timestamp"] = pd.to_datetime(ab["Timestamp"], errors="coerce")
    ab["OrderValueINR"] = pd.to_numeric(ab["OrderValueINR"], errors="coerce").fillna(0)
    return traffic, churn, market, ab

traffic, churn, market, ab = load_data()
st.markdown("""
<style>
.block-container{padding-top:1.5rem;padding-bottom:2rem}
[data-testid="stMetric"]{background:linear-gradient(135deg,#172554,#1e3a8a);padding:17px 18px;border-radius:14px;color:white;border:1px solid #334b83}
[data-testid="stMetricLabel"],[data-testid="stMetricValue"],[data-testid="stMetricDelta"]{color:white}
section[data-testid="stSidebar"]{background:#f3f6fb}
h1,h2,h3{letter-spacing:-.025em}
.small-note{color:#64748b;font-size:.85rem}
</style>
""", unsafe_allow_html=True)

st.title("📊 Workora | Business Intelligence")
st.caption("Acquisition • Customer retention • Regional opportunity • Checkout experimentation")
with st.sidebar:
    st.header("Dashboard controls")
    page = st.radio("Explore", ["Executive overview", "Acquisition & engagement", "Customer retention", "Regional market", "Checkout experiment"], index=0)
    st.divider()
    min_date = min(traffic.Date.min().date(), ab.Timestamp.min().date())
    max_date = max(traffic.Date.max().date(), ab.Timestamp.max().date())
    date_range = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    regions = sorted(set(traffic.Region.dropna().unique()) | set(churn.Region.dropna().unique()))
    region_choice = st.multiselect("Region", regions, default=regions)
    categories = sorted(churn.SubscriptionType.dropna().unique().tolist())
    category_choice = st.multiselect("Customer category", categories, default=categories)
    st.caption("Date applies to traffic and checkout data. Region applies where a region field exists. Customer category filters subscription type.")
    st.divider()
    st.caption("Learning dataset • All records are synthetic")

if isinstance(date_range, tuple) and len(date_range)==2:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
else:
    start, end = pd.Timestamp(min_date), pd.Timestamp(max_date)+pd.Timedelta(days=1)
t = traffic[(traffic.Date>=start)&(traffic.Date<=end)&(traffic.Region.isin(region_choice))]
c = churn[churn.Region.isin(region_choice)&churn.SubscriptionType.isin(category_choice)]
a = ab[(ab.Timestamp>=start)&(ab.Timestamp<=end)]
m = market[market.State.isin(region_choice) | market.City.isin(region_choice)]
# A session that did not bounce is used as an engagement proxy; it is not a unique-user count.
active_sessions = int((t.Bounced.astype(str).str.lower()=="no").sum())
revenue = float(a.loc[a.Converted.astype(str).str.lower()=="yes","OrderValueINR"].sum())
converted = a[a.Converted.astype(str).str.lower()=="yes"]
avg_ticket = float(converted.OrderValueINR.mean()) if len(converted) else 0
churn_rate = float((c.Churn.astype(str).str.lower()=="yes").mean()*100) if len(c) else 0
fmt_inr = lambda x: f"₹{x:,.0f}"

def kpis():
    cols=st.columns(4)
    cols[0].metric("Total revenue",fmt_inr(revenue),help="Sum of order values for converted checkout visitors in the selected date range.")
    cols[1].metric("Active users*",f"{active_sessions:,}",help="Proxy: non-bounced web sessions. SessionID is not a person-level user ID.")
    cols[2].metric("Churn rate",f"{churn_rate:.1f}%",help="Share of cleaned customer records marked Churn = Yes.")
    cols[3].metric("Average ticket size",fmt_inr(avg_ticket),help="Mean order value among converted checkout visitors.")
    st.caption("*Active users is represented by engaged (non-bounced) sessions because the traffic dataset contains session IDs, not persistent user IDs.")

def chart(fig, height=330):
    fig.update_layout(height=height, margin=dict(l=12,r=12,t=48,b=12),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(color="#334155"),legend_title_text="")
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

if page=="Executive overview":
    kpis()
    st.subheader("Business pulse")
    x,y=st.columns([1.45,1])
    with x:
        daily=t.groupby(t.Date.dt.date).size().rename("Sessions").reset_index(name="Sessions")
        daily.columns=["Date","Sessions"]
        fig=px.area(daily,x="Date",y="Sessions",title="Daily website sessions")
        chart(fig,350)
    with y:
        src=t.groupby("Source").size().reset_index(name="Sessions").sort_values("Sessions",ascending=False)
        chart(px.pie(src,names="Source",values="Sessions",hole=.58,title="Traffic mix"),350)
    x,y=st.columns(2)
    with x:
        reg=t.groupby("Region").agg(Sessions=("SessionID","count"),Registrations=("Registered",lambda s:(s.astype(str).str.lower()=="yes").sum())).reset_index()
        chart(px.bar(reg,x="Region",y=["Sessions","Registrations"],barmode="group",title="Regional acquisition"),330)
    with y:
        subs=c.groupby("SubscriptionType").Churn.apply(lambda s:(s.astype(str).str.lower()=="yes").mean()*100).reset_index(name="Churn rate")
        chart(px.bar(subs,x="SubscriptionType",y="Churn rate",title="Churn by subscription type",text_auto=".1f"),330)
    st.info("Use the left-side controls to explore the same reporting period and regional/customer segments across the dashboard.")

elif page=="Acquisition & engagement":
    st.subheader("Acquisition and engagement")
    x,y,z=st.columns(3)
    x.metric("Sessions",f"{len(t):,}")
    y.metric("Registration starts",f"{(t.StartedRegistration.astype(str).str.lower()=='yes').sum():,}")
    z.metric("Registrations",f"{(t.Registered.astype(str).str.lower()=='yes').sum():,}")
    a1,a2=st.columns(2)
    with a1:
        source=t.groupby("Source").agg(Sessions=("SessionID","count"),Registrations=("Registered",lambda s:(s.astype(str).str.lower()=="yes").sum())).reset_index()
        chart(px.bar(source,x="Source",y=["Sessions","Registrations"],barmode="group",title="Source performance"),350)
    with a2:
        device=t.groupby("DeviceCategory").agg(Sessions=("SessionID","count"),AvgDuration=("SessionDurationSec","mean")).reset_index()
        chart(px.bar(device,x="DeviceCategory",y="Sessions",color="AvgDuration",title="Sessions by device (colour = avg duration)"),350)
    landing=t.groupby("LandingPage").agg(Sessions=("SessionID","count"),BounceRate=("Bounced",lambda s:(s.astype(str).str.lower()=="yes").mean()*100),AvgPages=("PageViews","mean")).reset_index()
    chart(px.scatter(landing,x="Sessions",y="BounceRate",size="AvgPages",hover_name="LandingPage",title="Landing page engagement",labels={"BounceRate":"Bounce rate (%)"}),340)

elif page=="Customer retention":
    st.subheader("Customer retention and churn")
    x,y,z=st.columns(3)
    x.metric("Customers",f"{len(c):,}")
    y.metric("Churned",f"{(c.Churn.astype(str).str.lower()=='yes').sum():,}")
    z.metric("Avg monthly charges",fmt_inr(c.MonthlyChargesINR.mean() if len(c) else 0))
    a1,a2=st.columns(2)
    with a1:
        by_contract=c.groupby("ContractType").Churn.apply(lambda s:(s.astype(str).str.lower()=="yes").mean()*100).reset_index(name="Churn rate")
        chart(px.bar(by_contract,x="ContractType",y="Churn rate",title="Churn rate by contract",text_auto=".1f"),350)
    with a2:
        by_tenure=c.copy()
        by_tenure["Tenure band"]=pd.cut(by_tenure.TenureMonths,bins=[-1,12,24,48,120],labels=["0–12","13–24","25–48","49+"])
        band=by_tenure.groupby("Tenure band",observed=False).Churn.apply(lambda s:(s.astype(str).str.lower()=="yes").mean()*100).reset_index(name="Churn rate")
        chart(px.line(band,x="Tenure band",y="Churn rate",markers=True,title="Churn by customer tenure"),350)
    risk=c.groupby("SupportTickets").Churn.apply(lambda s:(s.astype(str).str.lower()=="yes").mean()*100).reset_index(name="Churn rate")
    chart(px.scatter(risk,x="SupportTickets",y="Churn rate",size="Churn rate",title="Support contacts and churn risk"),330)

elif page=="Regional market":
    st.subheader("Regional market opportunity")
    x,y,z=st.columns(3)
    x.metric("Market records",f"{len(m):,}")
    y.metric("Avg monthly search demand",f"{m.MonthlySearchDemand.mean():,.0f}" if len(m) else "—")
    z.metric("Avg lead conversion",f"{m.LeadConversionRate.mean()*100:.1f}%" if len(m) else "—")
    if len(m):
        fig=px.scatter_mapbox(m,lat="Latitude",lon="Longitude",size="MonthlySearchDemand",color="LeadConversionRate",hover_name="City",hover_data=["State","ExistingCompetitors","EstimatedAcquisitionCostINR"],zoom=3.4,height=470,mapbox_style="open-street-map",title="Demand and lead conversion by market")
        chart(fig,500)
        agg=m.groupby("State").agg(SearchDemand=("MonthlySearchDemand","sum"),LeadConversion=("LeadConversionRate","mean"),AcquisitionCost=("EstimatedAcquisitionCostINR","mean")).reset_index()
        chart(px.bar(agg,x="State",y="SearchDemand",color="LeadConversion",title="Search demand by state"),340)
    else:
        st.warning("No market rows match the selected region names. Select a broader region filter.")

elif page=="Checkout experiment":
    st.subheader("Checkout A/B experiment")
    x,y,z=st.columns(3)
    x.metric("Visitors",f"{len(a):,}")
    y.metric("Checkout starts",f"{(a.CheckoutStarted.astype(str).str.lower()=='yes').sum():,}")
    z.metric("Conversions",f"{(a.Converted.astype(str).str.lower()=='yes').sum():,}")
    exp=a.groupby("Variant").agg(Visitors=("VisitorID","count"),Conversions=("Converted",lambda s:(s.astype(str).str.lower()=="yes").sum()),Revenue=("OrderValueINR","sum")).reset_index()
    exp["Conversion rate"]=exp.Conversions/exp.Visitors*100
    exp["Revenue per visitor"]=exp.Revenue/exp.Visitors
    b1,b2=st.columns(2)
    with b1:
        chart(px.bar(exp,x="Variant",y="Conversion rate",text_auto=".2f",title="Conversion rate by variant (%)"),350)
    with b2:
        chart(px.bar(exp,x="Variant",y="Revenue per visitor",text_auto=".0f",title="Revenue per visitor (₹)"),350)
    st.markdown("**Experiment summary**")
    st.dataframe(exp.style.format({"Revenue":"₹{:,.0f}","Conversion rate":"{:.2f}%","Revenue per visitor":"₹{:,.2f}"}),use_container_width=True,hide_index=True)
    st.caption("Descriptive comparison only; no statistical significance test is implied.")

st.divider()
with st.expander("Data quality, metric definitions and assumptions"):
    st.markdown("""
    - **Synthetic data:** all four supplied CSVs are fictional learning data, not actual Workora business performance.
    - **Customer cleaning:** duplicate CustomerIDs removed; `TotalChargesINR` coerced to numeric; missing numeric fields filled with medians; missing categorical fields filled with modes; monthly and total charges clipped at the 1st/99th percentiles.
    - **Revenue / ticket size:** checkout `OrderValueINR` summed / averaged for rows with `Converted = Yes`.
    - **Active users:** displayed as a non-bounced session proxy because `web_traffic.csv` has unique SessionIDs, not a persistent user identifier.
    - **Churn:** proportion of cleaned customer rows with `Churn = Yes`. Customer data has no date, so the date filter does not affect churn.
    - **Relationships:** files are analyzed as separate subject areas; no unsupported row-level joins are created because the datasets do not share a common customer/session key.
    - **Market view:** regional-market data is aggregated independently; Region filter matches either State or City names where possible.
    """)

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="EduInsight | Student Analytics", page_icon="📊", layout="wide")

DATA_PATH = Path(__file__).parent / "eduinsight_simulated_student_data.csv"
REQUIRED_COLUMNS = ["Student_ID", "Year", "Grade", "Subject", "Term_1", "Term_2", "Annual"]

@st.cache_data
def load_default_data():
    return pd.read_csv(DATA_PATH)

def validate_data(df):
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return False, f"Missing required columns: {', '.join(missing)}"
    for col in ["Year", "Grade", "Term_1", "Term_2", "Annual"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if df[["Year", "Grade", "Term_1", "Term_2", "Annual"]].isna().any().any():
        return False, "Some required numeric fields contain blank or non-numeric values."
    if not df[["Term_1", "Term_2", "Annual"]].apply(lambda s: s.between(0, 100).all()).all():
        return False, "Marks must be between 0 and 100."
    return True, ""

def make_recommendation(row, pass_mark=40):
    marks = {"Term 1": row["Term_1"], "Term 2": row["Term_2"], "Annual": row["Annual"]}
    avg = sum(marks.values()) / 3
    if avg < pass_mark:
        return "Priority support: review core concepts, provide guided practice, and follow up individually."
    if row["Annual"] < row["Term_1"] and row["Annual"] < row["Term_2"]:
        return "Check for a possible decline; discuss challenges and assign targeted revision."
    if row["Term_2"] < row["Term_1"] - 10:
        return "Term 2 dropped noticeably; check understanding and offer focused practice."
    if avg < 60:
        return "Provide extra practice and short formative checks on difficult topics."
    if avg >= 80:
        return "Offer enrichment tasks and extension activities."
    return "Continue regular learning activities and monitor progress."

st.title("📊 EduInsight")
st.caption("Smart Student Performance Analytics and Recommendation System")
st.info("Demonstration app using simulated student data. The dataset contains fictional records and must not be treated as real student information.")

with st.sidebar:
    st.header("Data")
    uploaded = st.file_uploader("Upload a CSV file", type=["csv"])
    if uploaded is not None:
        try:
            data = pd.read_csv(uploaded)
            valid, message = validate_data(data)
            if not valid:
                st.error(message)
                st.stop()
            st.success("Uploaded data loaded.")
        except Exception as e:
            st.error(f"Could not read the CSV: {e}")
            st.stop()
    else:
        data = load_default_data()
    st.divider()
    st.header("Filters")
    years = sorted(data["Year"].dropna().unique().tolist())
    selected_years = st.multiselect("Academic year", years, default=years)
    grades = sorted(data["Grade"].dropna().unique().tolist())
    selected_grades = st.multiselect("Grade", grades, default=grades)
    subjects = sorted(data["Subject"].dropna().unique().tolist())
    selected_subjects = st.multiselect("Subject", subjects, default=subjects)
    pass_mark = st.number_input("Support threshold (average mark below)", min_value=0, max_value=100, value=40)

filtered = data[
    data["Year"].isin(selected_years)
    & data["Grade"].isin(selected_grades)
    & data["Subject"].isin(selected_subjects)
].copy()

if filtered.empty:
    st.warning("No records match the selected filters. Adjust the filters in the sidebar.")
    st.stop()

filtered["Average"] = filtered[["Term_1", "Term_2", "Annual"]].mean(axis=1).round(1)
filtered["Recommendation"] = filtered.apply(lambda row: make_recommendation(row, pass_mark), axis=1)

students_count = filtered["Student_ID"].nunique()
overall_avg = filtered["Annual"].mean()
needs_support = filtered.groupby("Student_ID")["Annual"].mean().lt(pass_mark).sum()
pass_rate = (filtered["Annual"] >= pass_mark).mean() * 100

k1, k2, k3, k4 = st.columns(4)
k1.metric("Students", f"{students_count}")
k2.metric("Average annual mark", f"{overall_avg:.1f}/100")
k3.metric("Students needing support", f"{needs_support}")
k4.metric(f"Annual marks ≥ {pass_mark}", f"{pass_rate:.1f}%")

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Student analysis", "Recommendations", "Data table"])

with tab1:
    left, right = st.columns(2)
    with left:
        subject_avg = filtered.groupby("Subject", as_index=False)["Annual"].mean().sort_values("Annual", ascending=False)
        fig = px.bar(subject_avg, x="Subject", y="Annual", title="Average annual mark by subject",
                     labels={"Annual": "Average annual mark"}, range_y=[0, 100], text_auto=".1f")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        yearly = filtered.groupby(["Year", "Subject"], as_index=False)["Annual"].mean()
        fig = px.line(yearly, x="Year", y="Annual", color="Subject", markers=True,
                      title="Annual performance by year", labels={"Annual": "Average annual mark"})
        fig.update_yaxes(range=[0, 100])
        st.plotly_chart(fig, use_container_width=True)

    distribution = px.histogram(filtered, x="Annual", color="Subject", nbins=10,
                                title="Distribution of annual marks", range_x=[0, 100])
    st.plotly_chart(distribution, use_container_width=True)

with tab2:
    st.subheader("Student performance")
    student_summary = (filtered.groupby(["Student_ID", "Grade"], as_index=False)
                       .agg(Term_1=("Term_1", "mean"), Term_2=("Term_2", "mean"),
                            Annual=("Annual", "mean")))
    student_summary[["Term_1", "Term_2", "Annual"]] = student_summary[["Term_1", "Term_2", "Annual"]].round(1)
    student_summary["Status"] = student_summary["Annual"].apply(lambda x: "Needs support" if x < pass_mark else "On track")
    st.dataframe(student_summary.sort_values("Annual"), use_container_width=True, hide_index=True)

    student_ids = sorted(filtered["Student_ID"].unique())
    chosen = st.selectbox("View one student's subject history", student_ids)
    one = filtered[filtered["Student_ID"] == chosen].sort_values(["Year", "Subject"])
    st.dataframe(one[["Year", "Grade", "Subject", "Term_1", "Term_2", "Annual", "Average"]], use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Teacher support recommendations")
    recs = filtered.copy()
    recs["Recommendation"] = recs.apply(lambda row: make_recommendation(row, pass_mark), axis=1)
    st.caption("Recommendations are rule-based suggestions to support teacher judgment.")
    st.dataframe(recs[["Student_ID", "Year", "Grade", "Subject", "Term_1", "Term_2", "Annual", "Recommendation"]]
                 .sort_values(["Annual", "Student_ID"]), use_container_width=True, hide_index=True)

with tab4:
    st.subheader("Filtered dataset")
    st.dataframe(filtered.sort_values(["Year", "Student_ID", "Subject"]), use_container_width=True, hide_index=True)
    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button("Download filtered data as CSV", data=csv, file_name="eduinsight_filtered_data.csv", mime="text/csv")

st.divider()
st.caption("EduInsight prototype • Synthetic data • Recommendations are educational decision support, not automated diagnoses.")

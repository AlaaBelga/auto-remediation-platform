import pandas as pd
import requests
import streamlit as st
import os

from dashboard_analytics import (
    baseline_index,
    degradation_index,
    informative_sensors,
    normalized_trend,
    sensor_diagnostics,
)

API_URL = os.getenv("PREDICTION_API_URL", "http://127.0.0.1:8000/predict")
API_KEY = os.getenv("PREDICTION_API_KEY") or os.getenv("P1_API_KEY") or os.getenv("PLATFORM_API_KEY")
WARNING_THRESHOLD = float(os.getenv("RISK_WARNING_THRESHOLD", "0.60"))
CRITICAL_THRESHOLD = float(os.getenv("RISK_CRITICAL_THRESHOLD", "0.80"))

FEATURES = [f"sensor_{i}" for i in range(1, 22)] + [
    f"op_setting_{i}" for i in range(1, 4)
]


@st.cache_data
def load_data():
    columns = (
        ["unit_number", "time_cycle"]
        + [f"op_setting_{i}" for i in range(1, 4)]
        + [f"sensor_{i}" for i in range(1, 22)]
    )
    return pd.read_csv("train_FD001.txt", sep=r"\s+", header=None, names=columns)


def build_payload(machine_data, position):
    sample = machine_data.head(1) if position == "start" else machine_data.tail(1)
    return sample[FEATURES].iloc[0].to_dict(), int(sample["time_cycle"].iloc[0])


def call_api(payload):
    headers = {"X-API-Key": API_KEY} if API_KEY else None
    response = requests.post(API_URL, json=payload, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()


def recommended_action(prediction, risk_score):
    if prediction == 1 or risk_score >= CRITICAL_THRESHOLD:
        return (
            "RISQUE_DE_PANNE",
            "#d62828",
            "Alerte maintenance + creation incident simule",
            "Planifier une intervention, prevenir l'equipe maintenance et prioriser la machine.",
            "La derive progressive des capteurs indique une degradation avancee du systeme.",
        )
    if risk_score >= WARNING_THRESHOLD:
        return (
            "WARNING",
            "#f77f00",
            "Surveillance renforcee",
            "Surveillance renforcee + nouvelle verification au prochain cycle.",
            "Debut de derive detecte : surveillance renforcee recommandee.",
        )
    return (
        "OK",
        "#2a9d8f",
        "Continuer surveillance",
        "Aucune intervention immediate. Continuer le monitoring normal.",
        "Comportement stable : les capteurs restent compatibles avec un fonctionnement normal.",
    )


def show_prediction(result):
    prediction = int(result.get("prediction", 0))
    risk_score = float(result.get("risk_score", 0) or 0)
    status, badge_color, action, detail, explanation = recommended_action(prediction, risk_score)

    rul_cycles = result.get("rul_cycles")
    anomaly_detected = result.get("anomaly_detected")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Risk score", f"{risk_score:.2f}")
    col2.metric("Prediction", prediction)
    col3.metric(
        "RUL estime",
        f"{float(rul_cycles):.1f} cycles" if rul_cycles is not None else "N/A",
    )
    col4.markdown(
        f"""
        <div style="padding: 0.75rem 1rem; border-radius: 8px; background: {badge_color}; color: white; text-align: center; font-weight: 700;">
            {status}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.progress(min(max(risk_score, 0), 1))
    st.info(explanation)

    if anomaly_detected is True:
        st.warning("Anomalie multivariee detectee par Isolation Forest.")
    elif anomaly_detected is False:
        st.success("Aucune anomalie multivariee detectee.")

    contributors = result.get("top_contributing_sensors", [])
    if contributors:
        st.caption("Capteurs contributeurs : " + ", ".join(contributors))

    st.subheader("Action recommandee")
    if status == "RISQUE_DE_PANNE":
        st.error(action)
    elif status == "WARNING":
        st.warning(action)
    else:
        st.success(action)
    st.write(detail)

    st.subheader("Reponse API")
    st.json(result)


st.set_page_config(page_title="Predictive Maintenance", layout="wide")

st.title("Predictive Maintenance Dashboard")
st.write("Surveillance des tendances capteurs et prediction du risque sur NASA CMAPSS.")

df = load_data()
control_machine, control_window = st.columns([2, 1])
machine_id = control_machine.selectbox(
    "Machine",
    sorted(df["unit_number"].unique()),
    index=0,
)
machine_data = df[df["unit_number"] == machine_id]
rolling_window = control_window.slider(
    "Fenetre de lissage",
    min_value=1,
    max_value=20,
    value=7,
)

default_sensors = informative_sensors(machine_data, limit=4)
selected_sensors = st.multiselect(
    "Capteurs a analyser",
    [f"sensor_{i}" for i in range(1, 22)],
    default=default_sensors,
    max_selections=6,
)

if not selected_sensors:
    st.warning("Selectionnez au moins un capteur.")
    st.stop()

st.subheader("Evolution des capteurs")
st.caption(
    "Les valeurs brutes utilisent des unites et des echelles differentes. "
    "Les vues normalisees rendent les petites derives visibles sans modifier les donnees sources."
)

tab_normalized, tab_index, tab_raw, tab_degradation = st.tabs(
    [
        "Tendance normalisee",
        "Variation base 100",
        "Valeurs brutes",
        "Indice de degradation",
    ]
)

indexed_machine = machine_data.set_index("time_cycle")
with tab_normalized:
    st.line_chart(
        normalized_trend(
            indexed_machine,
            selected_sensors,
            window=rolling_window,
        )
    )
    st.caption("Z-score lisse : les capteurs deviennent comparables malgre leurs unites differentes.")

with tab_index:
    st.line_chart(baseline_index(indexed_machine, selected_sensors))
    st.caption("Chaque capteur commence a 100. Une valeur de 102 correspond a une hausse de 2 %.")

with tab_raw:
    raw_columns = st.columns(2)
    for index, sensor in enumerate(selected_sensors):
        with raw_columns[index % 2]:
            st.markdown(f"**{sensor}**")
            st.line_chart(indexed_machine[[sensor]], height=220)

with tab_degradation:
    degradation = degradation_index(
        indexed_machine,
        selected_sensors,
        window=rolling_window,
    )
    degradation.index = indexed_machine.index
    st.line_chart(degradation, height=320)
    st.caption(
        "Indice synthetique de 0 a 100 calcule a partir de l'eloignement normalise "
        "des capteurs selectionnes. Il sert a visualiser la derive, pas a remplacer le risk score ML."
    )

st.subheader("Diagnostic des tendances")
diagnostics = sensor_diagnostics(machine_data, selected_sensors)
st.dataframe(diagnostics, hide_index=True, use_container_width=True)

col_ok, col_warning, col_critical = st.columns(3)

if col_ok.button("Test Machine OK", use_container_width=True):
    try:
        payload, cycle = build_payload(machine_data, "start")
        st.caption(f"Machine {machine_id} - cycle {cycle}")
        show_prediction(call_api(payload))
    except requests.exceptions.RequestException as e:
        st.error("Impossible de contacter l'API FastAPI.")
        st.code(str(e))

if col_warning.button("Test Machine Warning", use_container_width=True):
    st.caption("Scenario intermediaire simule pour demontrer la politique de decision")
    show_prediction(
        {
            "prediction": 0,
            "status": "WARNING",
            "risk_score": 0.7,
            "rul_cycles": 45.0,
            "estimated_time_to_failure_hours": 45.0,
            "anomaly_detected": True,
            "anomaly_score": -0.02,
            "top_contributing_sensors": ["sensor_4", "sensor_11", "sensor_15"],
        }
    )

if col_critical.button("Test Machine Critique", use_container_width=True):
    try:
        payload, cycle = build_payload(machine_data, "end")
        st.caption(f"Machine {machine_id} - cycle {cycle}")
        show_prediction(call_api(payload))
    except requests.exceptions.RequestException as e:
        st.error("Impossible de contacter l'API FastAPI.")
        st.code(str(e))

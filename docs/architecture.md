# System Architecture & Design Document

This document outlines the architectural decisions, data flows, and technical specifications of the Auto-Remediation Platform. The system is designed to be a highly resilient, event-driven cyber-physical ecosystem that bridges Machine Learning with DevOps automation.

## 1. High-Level Architecture

The platform is built on a loosely coupled microservices architecture, separated into two primary engines:

1. **Predictive Engine**: Responsible for data ingestion, feature engineering, and real-time Machine Learning inference (Risk Score & RUL).
2. **Remediation Engine**: Acts as the "Self-Healing" brain, consuming predictions and orchestrating automated responses (physical commands, K8s scaling, ticketing).

### Technology Stack
- **Message Broker / Streaming**: Apache Kafka (Alternative: MQTT)
- **Time-Series Database**: InfluxDB / TimescaleDB
- **Machine Learning**: Scikit-learn, XGBoost, Isolation Forest
- **APIs**: FastAPI, Pydantic, Uvicorn
- **Containerization & Orchestration**: Docker, Kubernetes (HPA, Deployments)
- **Observability**: Prometheus, Grafana
- **Alerting & UI**: Slack Webhooks, Streamlit

---

## 2. Core Data Flow

The end-to-end data pipeline operates asynchronously to ensure high throughput and fault tolerance:

1. **Ingestion**: A Sensor Simulator reads raw CMAPSS (NASA Turbofan) data and publishes time-series metrics to the Message Broker.
2. **Processing**: The Predictive Engine consumes this stream, handles missing values (interpolation), normalizes the data, and stores it in the Time-Series DB.
3. **Inference**: The Predictive API (`/predict`) calculates a real-time risk score and RUL (Remaining Useful Life).
4. **Decision**: The Remediation Engine continuously evaluates the predictions against configured thresholds.
5. **Action**: If a threshold is breached, the Remediation Engine triggers automated actions without human intervention.

---

## 3. The Self-Healing Decision Engine

The Remediation Engine acts as the sole authority for triggering physical and logical state changes. It operates based on strict thresholds to prevent false positives while ensuring rapid response times.

### Action Thresholds

| Status | Risk Score | Priority | Triggered Actions |
| :--- | :--- | :--- | :--- |
| **OK** | `< 0.60` | None | Informational logging only |
| **WARNING** | `0.60 - 0.79` | P3 | Slack Alert (Warning channel) |
| **CRITICAL** | `>= 0.80` | P1 | Hardware Command (Actuator) + Slack Alert + Kubernetes Scale-Up + Incident Ticket |

### Pseudo-Code Logic
```python
LOOP continuously over machine data:
    payload = build_payload(machine_id, latest_sensors)
    response = POST /predict (payload)
    score = response.failure_risk_score

    IF score >= 0.80:
        # Physical Action
        POST /actuators/turbine_command (machine_id, "REDUCE_RPM_BY_20")
        
        # DevOps / Logical Actions
        POST /alerts/slack (machine_id, score, ETA)
        KUBECTL scale deployment monitoring --replicas=5
        INSERT INTO incidents (machine_id, 'MAINTENANCE_REQUIRED', score)
        
    ELIF score >= 0.60:
        POST /alerts/slack (machine_id, score, 'WARNING')
        LOG WARN (machine_id, score)
```

---

## 4. API Contracts

Communication between the engines relies on strict JSON contracts validated by Pydantic to prevent malformed data from triggering unsafe commands.

### `POST /predict`
**Request Payload:**
```json
{
  "machine_id": "TURBINE_042",
  "timestamp": "2026-04-09T10:30:00Z",
  "cycle_number": 287,
  "sensor_data": {
    "vibration_hz": 120.4,
    "temp_celsius": 85.2,
    "pressure_psi": 34.1,
    "speed_rpm": 3200.0
  }
}
```

**Response Payload:**
```json
{
  "machine_id": "TURBINE_042",
  "status": "CRITICAL",
  "failure_risk_score": 0.89,
  "estimated_time_to_failure_hours": 2.5,
  "rul_cycles": 12,
  "anomaly_detected": true
}
```

---

## 5. Non-Functional Requirements & Constraints

To ensure production viability, the platform adheres to the following constraints:

- **Statelessness**: All microservices are entirely stateless, allowing Kubernetes to seamlessly restart or scale them horizontally.
- **Strict Latency (SLA)**: The API prediction endpoint (`/predict`) must maintain a response time of `< 100ms` at the 95th percentile (P95).
- **Security**: 
  - Kubernetes Network Policies isolate the Streamlit UI from directly querying the internal databases.
  - Inter-service communication is restricted to authorized API keys (or OAuth2).
- **Automated Recovery**: Kubernetes Liveness and Readiness probes are configured on all pods to guarantee self-healing at the infrastructure layer (automatic pod restarts on failure).

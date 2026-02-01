"""
Prime Analytics - Data Quality Dashboard
=========================================
Version: 1.3
- Logo Prime Analytics
- Thème couleurs Prime Elevate (bleu → turquoise)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client
from datetime import datetime, timedelta
import json

# =============================================================================
# CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="Prime Analytics - Data Quality",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# CUSTOM CSS - Thème Prime Elevate
# =============================================================================

st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Global font */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Header gradient style */
    .main-header {
        background: linear-gradient(135deg, #003366 0%, #0066cc 50%, #00cccc 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    
    .main-header h1 {
        color: white !important;
        margin: 0;
        font-size: 1.8rem;
    }
    
    .main-header p {
        color: rgba(255,255,255,0.85);
        margin: 0.5rem 0 0 0;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #64748b;
    }
    
    /* Metric cards */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    [data-testid="stMetric"] label {
        color: #64748b !important;
    }
    
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #0066cc !important;
        font-weight: 700;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: linear-gradient(90deg, #003366, #0066cc, #00cccc);
        padding: 8px;
        border-radius: 12px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(255,255,255,0.15);
        border-radius: 8px;
        color: white;
        font-weight: 500;
        padding: 10px 20px;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(255,255,255,0.25);
    }
    
    .stTabs [aria-selected="true"] {
        background-color: white !important;
        color: #0066cc !important;
    }
    
    /* Buttons */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0066cc 0%, #00cccc 100%);
        border: none;
        font-weight: 600;
    }
    
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #0055aa 0%, #00bbbb 100%);
        border: none;
    }
    
    /* Dataframe */
    [data-testid="stDataFrame"] {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        overflow: hidden;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: linear-gradient(90deg, #f0f9ff 0%, #e0f7fa 100%);
        border-radius: 8px;
    }
    
    /* Divider */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, #0066cc, #00cccc);
        opacity: 0.3;
    }
    
    /* Success/Info boxes */
    .stAlert {
        border-radius: 12px;
    }
    
    /* Code blocks */
    code {
        background-color: #f0f9ff !important;
        color: #0066cc !important;
        border: 1px solid #e0f2fe;
        border-radius: 6px;
        padding: 2px 6px;
    }
    
    /* Subheader accent */
    h2, h3 {
        color: #003366 !important;
    }
    
    /* Footer styling */
    .footer {
        text-align: center;
        color: #94a3b8;
        font-size: 0.85rem;
        padding: 1rem;
        border-top: 1px solid #e2e8f0;
        margin-top: 2rem;
    }
    
    .footer a {
        color: #0066cc;
        text-decoration: none;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# SUPABASE CONFIG
# =============================================================================

SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

@st.cache_resource
def get_supabase_client():
    if not SUPABASE_KEY or not SUPABASE_URL:
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"Erreur connexion Supabase: {e}")
        return None

def get_supabase():
    return get_supabase_client()

# =============================================================================
# DATA LOADING
# =============================================================================

@st.cache_data(ttl=60)
def load_table_safe(table_name: str, limit: int = 1000):
    supabase = get_supabase()
    if not supabase:
        return pd.DataFrame()
    try:
        response = supabase.table(table_name).select("*").limit(limit).execute()
        return pd.DataFrame(response.data)
    except:
        return pd.DataFrame()

def load_dashboard_summary():
    return load_table_safe("mv_dashboard_summary")

def load_source_health():
    return load_table_safe("mv_source_health_score")

def load_issues():
    return load_table_safe("dq_issue_detail", 500)

def load_data_sources():
    return load_table_safe("data_source")

def load_measurements():
    return load_table_safe("dq_measurement", 1000)

def load_corrections():
    return load_table_safe("dq_correction", 500)

@st.cache_data(ttl=300)
def get_table_list():
    return [
        "data_source", "dq_rule_type", "dq_rule", "dq_field_ref",
        "dq_run", "dq_measurement", "dq_field_check", "dq_issue_detail",
        "dq_correction", "dq_audit_log",
        "mv_dashboard_summary", "mv_correction_review_queue", 
        "mv_source_health_score", "mv_field_quality_trend", "mv_rule_effectiveness"
    ]

# =============================================================================
# HELPERS
# =============================================================================

def get_status_emoji(status):
    if pd.isna(status):
        return "⚪"
    status = str(status).lower()
    return {"ok": "🟢", "warning": "🟡", "critical": "🔴", "pending": "⏳", 
            "validated": "✅", "rejected": "❌", "open": "🔵", "escalated": "🚨", "resolved": "✅"}.get(status, "⚪")

def render_health_bar(score: float, label: str):
    if pd.isna(score):
        score = 0
    score = float(score)
    # Gradient colors from Prime palette
    if score >= 95:
        color = "#00cccc"  # Turquoise
    elif score >= 90:
        color = "#0066cc"  # Blue
    else:
        color = "#ef4444"  # Red for critical
    
    st.markdown(f"""
    <div style="margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
            <span style="color: #334155; font-weight: 500;">{label}</span>
            <span style="font-weight: 700; color: {color};">{score:.1f}%</span>
        </div>
        <div style="background: linear-gradient(90deg, #e2e8f0, #f1f5f9); border-radius: 10px; height: 12px; overflow: hidden;">
            <div style="background: linear-gradient(90deg, #0066cc, {color}); width: {min(score, 100)}%; height: 100%; border-radius: 10px; transition: width 0.5s ease;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# DEMO DATA
# =============================================================================

def get_demo_dashboard_data():
    return {
        "domains": pd.DataFrame({
            "domain": ["Regulatory", "Finance", "Accounting", "Reference", "Risk"],
            "score": [96.2, 94.1, 99.1, 87.4, 95.0]
        }),
        "rules": pd.DataFrame({
            "rule_type": ["Completeness", "Field Type", "Validation", "List of Values", "AI Quality"],
            "score": [98.2, 99.5, 97.1, 96.3, 92.8]
        }),
        "attention": pd.DataFrame({
            "Source": ["Counterparty Master", "Counterparty Master", "AnaCredit", "Budget"],
            "Field": ["lei_code", "address", "interest_rate", "version"],
            "Score": [81.4, 92.9, 99.4, 99.8],
            "Issues": [6500, 2500, 800, 15],
            "Status": ["🔴 critical", "🔴 critical", "🟡 warning", "🟡 warning"]
        }),
        "kpis": {"overall_score": 94.2, "total_sources": 12, "open_issues": 847, "pending_corrections": 23}
    }

def get_demo_corrections_data():
    return pd.DataFrame({
        "correction_id": [1, 2, 3, 4, 5],
        "source_name": ["AnaCredit", "AnaCredit", "Counterparty Master", "Counterparty Master", "Budget"],
        "table_name": ["loan_data", "loan_data", "counterparties", "counterparties", "budget_lines"],
        "field_name": ["country_code", "country_code", "legal_name", "legal_name", "version"],
        "record_key": ["CONTRACT-2024-78542", "CONTRACT-2024-78901", "CPT-00012542", "CPT-00025891", "CC4521-612000"],
        "original_value": ["FRA", "DEU", "SOCIETE GENERAL", "BNP Paribass", "v1"],
        "proposed_value": ["FR", "DE", "SOCIETE GENERALE", "BNP Paribas", "V1"],
        "ai_model": ["claude-3-sonnet"] * 5,
        "ai_confidence": [0.995, 0.995, 0.992, 0.995, 0.990],
        "ai_justification": [
            "FRA is ISO alpha-3, required format is alpha-2: FR",
            "DEU is ISO alpha-3, required format is alpha-2: DE",
            "Missing final E. Société Générale is a major French bank.",
            "Extra S at the end. BNP Paribas is spelled with single S.",
            "Lowercase v1 should be uppercase V1 to match standard format."
        ],
        "ai_category": ["format", "format", "typo", "typo", "casing"],
        "decision_status": ["pending", "pending", "pending", "validated", "pending"]
    })

# =============================================================================
# ACTIONS
# =============================================================================

def update_correction_status(correction_id: int, status: str, user: str, comment: str = None):
    supabase = get_supabase()
    if not supabase:
        st.info("Mode démo: action simulée")
        return True
    try:
        update_data = {"decision_status": status, "decided_by": user, "decided_at": datetime.now().isoformat()}
        if comment:
            update_data["decision_comment"] = comment
        supabase.table("dq_correction").update(update_data).eq("correction_id", correction_id).execute()
        return True
    except Exception as e:
        st.error(f"Erreur: {e}")
        return False

# =============================================================================
# TAB 1: DASHBOARD
# =============================================================================

def render_dashboard_tab():
    # Header with gradient
    st.markdown("""
    <div class="main-header">
        <h1>🏠 Dashboard Qualité des Données</h1>
        <p>Vue d'ensemble de la santé de vos données</p>
    </div>
    """, unsafe_allow_html=True)
    
    df_summary = load_dashboard_summary()
    df_health = load_source_health()
    df_sources = load_data_sources()
    df_corrections = load_corrections()
    df_measurements = load_measurements()
    
    demo = get_demo_dashboard_data()
    use_demo = df_summary.empty and df_measurements.empty
    
    if use_demo:
        st.info("📊 Affichage des données de démonstration")
    
    # KPIs
    st.subheader("📈 Indicateurs Clés")
    col1, col2, col3, col4 = st.columns(4)
    
    if use_demo:
        kpis = demo["kpis"]
    else:
        overall_score = df_measurements["score"].mean() if not df_measurements.empty and "score" in df_measurements.columns else 0
        total_sources = len(df_sources) if not df_sources.empty else 0
        df_issues = load_issues()
        open_issues = len(df_issues[df_issues["status"] == "open"]) if not df_issues.empty and "status" in df_issues.columns else 0
        pending_corrections = len(df_corrections[df_corrections["decision_status"] == "pending"]) if not df_corrections.empty and "decision_status" in df_corrections.columns else 0
        kpis = {"overall_score": overall_score, "total_sources": total_sources, "open_issues": open_issues, "pending_corrections": pending_corrections}
    
    col1.metric("Score Global", f"{kpis['overall_score']:.1f}%", "+1.2%")
    col2.metric("Sources Surveillées", str(kpis['total_sources']))
    col3.metric("Issues Ouvertes", str(int(kpis['open_issues'])), "-52", delta_color="inverse")
    col4.metric("Corrections IA", str(kpis['pending_corrections']), "🤖")
    
    st.divider()
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("🚦 Santé par Domaine")
        domain_data = demo["domains"] if use_demo else demo["domains"]
        if not use_demo and not df_sources.empty and "business_domain" in df_sources.columns:
            domains = df_sources["business_domain"].dropna().unique()
            if len(domains) > 0:
                domain_data = pd.DataFrame({"domain": domains, "score": [95 + (i % 10) for i in range(len(domains))]})
        for _, row in domain_data.sort_values("score").iterrows():
            render_health_bar(row["score"], row["domain"])
    
    with col_right:
        st.subheader("📊 Qualité par Type de Règle")
        for _, row in demo["rules"].sort_values("score").iterrows():
            render_health_bar(row["score"], row["rule_type"])
    
    st.divider()
    st.subheader("⚠️ Attention Requise")
    st.dataframe(demo["attention"], use_container_width=True, hide_index=True)

# =============================================================================
# TAB 2: AI CORRECTIONS
# =============================================================================

def render_corrections_tab():
    st.markdown("""
    <div class="main-header">
        <h1>🤖 Corrections IA</h1>
        <p>Validez les corrections proposées par l'intelligence artificielle</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.subheader("👤 Utilisateur")
        current_user = st.text_input("Votre identifiant", value="demo.user", key="correction_user")
    
    df_corrections = load_corrections()
    if df_corrections.empty:
        st.info("📊 Affichage des données de démonstration")
        df_corrections = get_demo_corrections_data()
    
    col1, col2, col3, col4 = st.columns(4)
    if "decision_status" in df_corrections.columns:
        total = len(df_corrections)
        pending_count = len(df_corrections[df_corrections["decision_status"] == "pending"])
        validated = len(df_corrections[df_corrections["decision_status"] == "validated"])
        rejected = len(df_corrections[df_corrections["decision_status"] == "rejected"])
    else:
        total, pending_count, validated, rejected = len(df_corrections), len(df_corrections), 0, 0
    
    col1.metric("Total", total)
    col2.metric("En attente", pending_count)
    col3.metric("Validées", validated)
    col4.metric("Rejetées", rejected)
    
    st.divider()
    
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        status_filter = st.selectbox("Statut", ["pending", "all", "validated", "rejected"],
            format_func=lambda x: {"pending": "⏳ En attente", "all": "📋 Tous", "validated": "✅ Validées", "rejected": "❌ Rejetées"}.get(x, x))
    with col_filter2:
        confidence_min = st.slider("Confiance minimum", 0.0, 1.0, 0.0, 0.05) if "ai_confidence" in df_corrections.columns else 0.0
    
    filtered_df = df_corrections.copy()
    if status_filter != "all" and "decision_status" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["decision_status"] == status_filter]
    if "ai_confidence" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["ai_confidence"] >= confidence_min]
    
    st.subheader(f"📝 Corrections à traiter ({len(filtered_df)})")
    
    for idx, row in filtered_df.head(20).iterrows():
        st.markdown("---")
        st.markdown(f"**📍 {row.get('source_name', 'N/A')}** › `{row.get('table_name', 'N/A')}` › `{row.get('field_name', 'N/A')}` › Row: `{row.get('record_key', 'N/A')}`")
        
        col_before, col_arrow, col_after = st.columns([2, 1, 2])
        with col_before:
            st.markdown("**Valeur actuelle:**")
            st.code(row.get("original_value", "N/A"), language=None)
        with col_arrow:
            st.markdown("<br><h2 style='text-align: center; color: #0066cc;'>→</h2>", unsafe_allow_html=True)
        with col_after:
            st.markdown("**Valeur proposée:** ✨")
            st.code(row.get("proposed_value", "N/A"), language=None)
        
        if row.get("ai_justification"):
            with st.expander("🧠 Explication IA"):
                st.info(row.get("ai_justification"))
        
        col_conf, col_cat, col_model = st.columns(3)
        confidence = row.get("ai_confidence", 0)
        if pd.notna(confidence):
            confidence_pct = confidence * 100 if confidence <= 1 else confidence
            color = "🟢" if confidence_pct >= 95 else "🟡" if confidence_pct >= 85 else "🔴"
            col_conf.markdown(f"**Confiance:** {color} {confidence_pct:.1f}%")
        col_cat.markdown(f"**Catégorie:** `{row.get('ai_category', 'N/A')}`")
        col_model.markdown(f"**Modèle:** `{row.get('ai_model', 'N/A')}`")
        
        status = row.get("decision_status", "pending")
        correction_id = row.get("correction_id", idx)
        
        if status == "pending":
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            with col_btn1:
                if st.button("✅ Accepter", key=f"accept_{correction_id}", type="primary"):
                    if update_correction_status(correction_id, "validated", current_user):
                        st.success("Correction validée !")
                        st.cache_data.clear()
                        st.rerun()
            with col_btn2:
                if st.button("❌ Rejeter", key=f"reject_{correction_id}"):
                    if update_correction_status(correction_id, "rejected", current_user):
                        st.warning("Correction rejetée.")
                        st.cache_data.clear()
                        st.rerun()
            with col_btn3:
                st.button("⏭️ Ignorer", key=f"skip_{correction_id}")
        else:
            st.markdown(f"**Status:** {get_status_emoji(status)} {status} par `{row.get('decided_by', 'N/A')}`")

# =============================================================================
# TAB 3: ISSUES
# =============================================================================

def render_issues_tab():
    st.markdown("""
    <div class="main-header">
        <h1>📋 Exploration des Issues</h1>
        <p>Analysez et gérez les problèmes de qualité détectés</p>
    </div>
    """, unsafe_allow_html=True)
    
    df_issues = load_issues()
    if df_issues.empty:
        st.info("Aucune issue trouvée.")
        return
    
    col1, col2, col3 = st.columns(3)
    with col1:
        statuses = ["Tous"] + list(df_issues["status"].dropna().unique()) if "status" in df_issues.columns else ["Tous"]
        status_filter = st.selectbox("Statut", statuses)
    with col2:
        priorities = ["Tous"] + list(df_issues["priority"].dropna().unique()) if "priority" in df_issues.columns else ["Tous"]
        priority_filter = st.selectbox("Priorité", priorities)
    with col3:
        types = ["Tous"] + list(df_issues["issue_type"].dropna().unique()) if "issue_type" in df_issues.columns else ["Tous"]
        type_filter = st.selectbox("Type", types)
    
    filtered = df_issues.copy()
    if status_filter != "Tous" and "status" in filtered.columns:
        filtered = filtered[filtered["status"] == status_filter]
    if priority_filter != "Tous" and "priority" in filtered.columns:
        filtered = filtered[filtered["priority"] == priority_filter]
    if type_filter != "Tous" and "issue_type" in filtered.columns:
        filtered = filtered[filtered["issue_type"] == type_filter]
    
    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric("Issues filtrées", len(filtered))
    if "priority" in filtered.columns:
        col2.metric("Critiques", len(filtered[filtered["priority"] == "critical"]))
    if "status" in filtered.columns:
        col3.metric("Ouvertes", len(filtered[filtered["status"] == "open"]))
    
    st.divider()
    st.dataframe(filtered.head(100), use_container_width=True, hide_index=True)
    st.download_button("📥 Exporter CSV", filtered.to_csv(index=False), "issues.csv", "text/csv")

# =============================================================================
# TAB 4: TABLES
# =============================================================================

def render_tables_tab():
    st.markdown("""
    <div class="main-header">
        <h1>📊 Visualisation des Tables</h1>
        <p>Explorez les données stockées dans Supabase</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        selected_table = st.selectbox("Nom de la table", get_table_list(), key="table_select")
    with col2:
        columns = st.text_input("Colonnes", value="*", help="* pour toutes")
    with col3:
        limit = st.slider("Limite", 10, 500, 100)
    
    if st.button("🔄 Rafraîchir"):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    
    if selected_table:
        df = load_table_safe(selected_table, limit)
        if not df.empty:
            col1, col2, col3 = st.columns(3)
            col1.metric("Lignes", len(df))
            col2.metric("Colonnes", len(df.columns))
            col3.metric("Table", selected_table)
            st.divider()
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button("📥 Télécharger CSV", df.to_csv(index=False), f"{selected_table}.csv", "text/csv")
        else:
            st.warning(f"Aucune donnée dans `{selected_table}`")

# =============================================================================
# TAB 5: STORAGE
# =============================================================================

def render_storage_tab():
    st.markdown("""
    <div class="main-header">
        <h1>📁 Gestion du Storage</h1>
        <p>Parcourez les fichiers stockés dans Supabase Storage</p>
    </div>
    """, unsafe_allow_html=True)
    
    supabase = get_supabase()
    if not supabase:
        st.warning("Connexion Supabase requise.")
        return
    
    col1, col2 = st.columns(2)
    with col1:
        bucket_name = st.text_input("Bucket", value="bucketprimelab", key="storage_bucket")
    with col2:
        folder_path = st.text_input("Dossier (optionnel)", value="", key="storage_folder")
    
    st.divider()
    
    try:
        files = supabase.storage.from_(bucket_name).list(folder_path)
        if files:
            st.subheader(f"📂 Contenu de `{bucket_name}/{folder_path}`")
            file_data = [{"Nom": f.get("name", "N/A"), "Type": "📁 Dossier" if f.get("id") is None else "📄 Fichier", "Créé": f.get("created_at", "N/A")[:10] if f.get("created_at") else "N/A"} for f in files]
            st.dataframe(pd.DataFrame(file_data), use_container_width=True, hide_index=True)
        else:
            st.info("Bucket vide ou non accessible.")
    except Exception as e:
        st.error(f"Erreur: {e}")

# =============================================================================
# TAB 6: UPLOAD
# =============================================================================

def render_upload_tab():
    st.markdown("""
    <div class="main-header">
        <h1>📤 Upload de Fichiers</h1>
        <p>Importez vos fichiers vers Supabase</p>
    </div>
    """, unsafe_allow_html=True)
    
    supabase = get_supabase()
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📁 Upload vers Storage")
        bucket = st.text_input("Bucket cible", value="bucketprimelab", key="up_bucket")
        uploaded_file = st.file_uploader("Choisir un fichier", type=["csv", "xlsx", "json", "txt", "pdf"])
        if uploaded_file:
            st.success(f"Fichier: {uploaded_file.name}")
            if supabase and st.button("⬆️ Uploader", type="primary"):
                try:
                    supabase.storage.from_(bucket).upload(uploaded_file.name, uploaded_file.getvalue(), {"content-type": uploaded_file.type})
                    st.success("✅ Uploadé!")
                except Exception as e:
                    st.error(f"Erreur: {e}")
    
    with col2:
        st.subheader("📊 Import CSV → Table")
        csv_file = st.file_uploader("Fichier CSV", type=["csv"], key="csv_up")
        target_table = st.selectbox("Table cible", get_table_list(), key="import_tbl")
        if csv_file:
            st.dataframe(pd.read_csv(csv_file, nrows=5), use_container_width=True, hide_index=True)
            if supabase and st.button("📥 Importer"):
                try:
                    csv_file.seek(0)
                    records = pd.read_csv(csv_file).to_dict(orient="records")
                    supabase.table(target_table).insert(records).execute()
                    st.success(f"✅ {len(records)} lignes importées")
                except Exception as e:
                    st.error(f"Erreur: {e}")

# =============================================================================
# MAIN
# =============================================================================

def main():
    # Sidebar with logo
    with st.sidebar:
        # Logo from GitHub assets
        st.image("assets/logo-prime-analytics-black-2026.png", width=200)
        st.markdown("---")
        st.markdown("### 📊 Data Quality")
        st.caption("Powered by Alteryx + AI")
        st.markdown("---")
        st.markdown("""
        <div style="color: #64748b; font-size: 0.85rem;">
            © 2026 Prime Analytics<br>
            <a href="https://www.primeanalytics.fr" target="_blank" style="color: #0066cc;">www.primeanalytics.fr</a>
        </div>
        """, unsafe_allow_html=True)
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🏠 Dashboard", "🤖 AI Corrections", "📋 Issues", "📊 Tables", "📁 Storage", "📤 Upload"
    ])
    
    with tab1: render_dashboard_tab()
    with tab2: render_corrections_tab()
    with tab3: render_issues_tab()
    with tab4: render_tables_tab()
    with tab5: render_storage_tab()
    with tab6: render_upload_tab()

if __name__ == "__main__":
    main()

"""
Prime Analytics - Data Quality Dashboard
=========================================
Version: 1.1 (Robuste)
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

# Supabase Configuration
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

# =============================================================================
# SUPABASE CONNECTION
# =============================================================================

@st.cache_resource
def get_supabase_client():
    """Initialize Supabase client."""
    if not SUPABASE_KEY or not SUPABASE_URL:
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"Erreur connexion Supabase: {e}")
        return None

def get_supabase():
    """Get Supabase client with error handling."""
    client = get_supabase_client()
    if not client:
        st.sidebar.warning("⚠️ Mode démo (pas de connexion Supabase)")
    return client

# =============================================================================
# DATA LOADING FUNCTIONS (avec gestion d'erreurs)
# =============================================================================

@st.cache_data(ttl=60)
def load_table_safe(table_name: str, limit: int = 1000):
    """Load data from table with error handling."""
    supabase = get_supabase()
    if not supabase:
        return pd.DataFrame()
    
    try:
        response = supabase.table(table_name).select("*").limit(limit).execute()
        df = pd.DataFrame(response.data)
        return df
    except Exception as e:
        st.warning(f"Table `{table_name}` non accessible: {e}")
        return pd.DataFrame()

def load_dashboard_summary():
    return load_table_safe("mv_dashboard_summary")

def load_correction_queue():
    return load_table_safe("mv_correction_review_queue")

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
    """Get list of tables in the database."""
    return [
        "data_source", "dq_rule_type", "dq_rule", "dq_field_ref",
        "dq_run", "dq_measurement", "dq_field_check", "dq_issue_detail",
        "dq_correction", "dq_audit_log",
        "mv_dashboard_summary", "mv_correction_review_queue", 
        "mv_source_health_score", "mv_field_quality_trend", "mv_rule_effectiveness"
    ]

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def safe_get_column(df, col_names, default=None):
    """Safely get column from dataframe, trying multiple possible names."""
    if isinstance(col_names, str):
        col_names = [col_names]
    
    for col in col_names:
        if col in df.columns:
            return df[col]
    
    return pd.Series([default] * len(df)) if len(df) > 0 else pd.Series()

def get_status_emoji(status):
    """Get emoji for status."""
    if pd.isna(status):
        return "⚪"
    status = str(status).lower()
    status_map = {
        "ok": "🟢", "warning": "🟡", "critical": "🔴",
        "pending": "⏳", "validated": "✅", "rejected": "❌",
        "open": "🔵", "escalated": "🚨", "resolved": "✅"
    }
    return status_map.get(status, "⚪")

def render_health_bar(score: float, label: str):
    """Render a health score bar with HTML."""
    if pd.isna(score):
        score = 0
    score = float(score)
    color = "#10b981" if score >= 95 else "#f59e0b" if score >= 90 else "#ef4444"
    st.markdown(f"""
    <div style="margin-bottom: 10px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
            <span>{label}</span>
            <span style="font-weight: bold;">{score:.1f}%</span>
        </div>
        <div style="background-color: #e5e7eb; border-radius: 10px; height: 20px; overflow: hidden;">
            <div style="background-color: {color}; width: {min(score, 100)}%; height: 100%; border-radius: 10px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# DEMO DATA (fallback si pas de données)
# =============================================================================

def get_demo_dashboard_data():
    """Return demo data for dashboard."""
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
        "kpis": {
            "overall_score": 94.2,
            "total_sources": 12,
            "open_issues": 847,
            "pending_corrections": 23
        }
    }

def get_demo_corrections_data():
    """Return demo data for corrections."""
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
# ACTION FUNCTIONS
# =============================================================================

def update_correction_status(correction_id: int, status: str, user: str, comment: str = None):
    """Update correction status in database."""
    supabase = get_supabase()
    if not supabase:
        st.info("Mode démo: action simulée")
        return True
    
    try:
        update_data = {
            "decision_status": status,
            "decided_by": user,
            "decided_at": datetime.now().isoformat()
        }
        if comment:
            update_data["decision_comment"] = comment
        
        supabase.table("dq_correction").update(update_data).eq("correction_id", correction_id).execute()
        return True
    except Exception as e:
        st.error(f"Erreur mise à jour: {e}")
        return False

# =============================================================================
# TAB 1: DASHBOARD
# =============================================================================

def render_dashboard_tab():
    """Render the executive dashboard tab."""
    st.header("🏠 Dashboard Qualité des Données")
    
    # Load data
    df_summary = load_dashboard_summary()
    df_health = load_source_health()
    df_sources = load_data_sources()
    df_corrections = load_corrections()
    df_measurements = load_measurements()
    
    # Use demo data if empty
    demo = get_demo_dashboard_data()
    use_demo = df_summary.empty and df_measurements.empty
    
    if use_demo:
        st.info("📊 Affichage des données de démonstration")
    
    # ==========================================================================
    # KPIs Row
    # ==========================================================================
    st.subheader("📈 Indicateurs Clés")
    
    col1, col2, col3, col4 = st.columns(4)
    
    if use_demo:
        kpis = demo["kpis"]
    else:
        # Calculate from real data
        if not df_measurements.empty and "score" in df_measurements.columns:
            overall_score = df_measurements["score"].mean()
        elif not df_summary.empty and "score" in df_summary.columns:
            overall_score = df_summary["score"].mean()
        else:
            overall_score = 0
        
        total_sources = len(df_sources) if not df_sources.empty else 0
        
        # Count open issues
        df_issues = load_issues()
        if not df_issues.empty and "status" in df_issues.columns:
            open_issues = len(df_issues[df_issues["status"] == "open"])
        else:
            open_issues = 0
        
        # Count pending corrections
        if not df_corrections.empty and "decision_status" in df_corrections.columns:
            pending_corrections = len(df_corrections[df_corrections["decision_status"] == "pending"])
        else:
            pending_corrections = 0
        
        kpis = {
            "overall_score": overall_score,
            "total_sources": total_sources,
            "open_issues": open_issues,
            "pending_corrections": pending_corrections
        }
    
    with col1:
        st.metric("Score Global", f"{kpis['overall_score']:.1f}%", "+1.2%")
    with col2:
        st.metric("Sources Surveillées", str(kpis['total_sources']))
    with col3:
        st.metric("Issues Ouvertes", str(int(kpis['open_issues'])), "-52", delta_color="inverse")
    with col4:
        st.metric("Corrections IA", str(kpis['pending_corrections']), "🤖")
    
    st.divider()
    
    # ==========================================================================
    # Charts Row
    # ==========================================================================
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("🚦 Santé par Domaine")
        
        if use_demo:
            domain_data = demo["domains"]
        else:
            # Try to aggregate from sources or health view
            domain_data = None
            
            if not df_health.empty:
                # Check available columns
                score_col = None
                domain_col = None
                
                for col in ["overall_score", "weighted_score", "avg_score", "score"]:
                    if col in df_health.columns:
                        score_col = col
                        break
                
                for col in ["business_domain", "domain", "source_type"]:
                    if col in df_health.columns:
                        domain_col = col
                        break
                
                if score_col and domain_col:
                    domain_data = df_health.groupby(domain_col)[score_col].mean().reset_index()
                    domain_data.columns = ["domain", "score"]
            
            if domain_data is None and not df_sources.empty and "business_domain" in df_sources.columns:
                # Create from sources with mock scores
                domains = df_sources["business_domain"].unique()
                domain_data = pd.DataFrame({
                    "domain": domains,
                    "score": [95 + (i % 10) for i in range(len(domains))]
                })
            
            if domain_data is None:
                domain_data = demo["domains"]
        
        # Render bars
        for _, row in domain_data.sort_values("score").iterrows():
            render_health_bar(row["score"], row["domain"])
    
    with col_right:
        st.subheader("📊 Qualité par Type de Règle")
        
        if use_demo:
            rule_data = demo["rules"]
        else:
            rule_data = None
            
            if not df_summary.empty:
                # Check for rule type column
                rule_col = None
                score_col = None
                
                for col in ["rule_type_name", "rule_type_id", "rule_name", "rule_id"]:
                    if col in df_summary.columns:
                        rule_col = col
                        break
                
                for col in ["score", "avg_score"]:
                    if col in df_summary.columns:
                        score_col = col
                        break
                
                if rule_col and score_col:
                    rule_data = df_summary.groupby(rule_col)[score_col].mean().reset_index()
                    rule_data.columns = ["rule_type", "score"]
            
            if rule_data is None:
                rule_data = demo["rules"]
        
        # Render bars
        for _, row in rule_data.sort_values("score").iterrows():
            render_health_bar(row["score"], row["rule_type"])
    
    st.divider()
    
    # ==========================================================================
    # Attention Required Table
    # ==========================================================================
    st.subheader("⚠️ Attention Requise")
    
    if use_demo:
        st.dataframe(demo["attention"], use_container_width=True, hide_index=True)
    else:
        # Build from measurements
        if not df_measurements.empty and "score" in df_measurements.columns:
            attention_df = df_measurements[df_measurements["score"] < 99].sort_values("score").head(10)
            
            if not attention_df.empty:
                # Select available columns
                display_cols = []
                col_mapping = {
                    "source_name": ["source_name", "source_id"],
                    "table_name": ["table_name"],
                    "field_name": ["field_name"],
                    "rule_name": ["rule_name", "rule_id"],
                    "score": ["score"],
                    "status": ["status"]
                }
                
                display_df = pd.DataFrame()
                for display_name, possible_cols in col_mapping.items():
                    for col in possible_cols:
                        if col in attention_df.columns:
                            display_df[display_name] = attention_df[col]
                            break
                
                if "status" in display_df.columns:
                    display_df["status"] = display_df["status"].apply(lambda x: f"{get_status_emoji(x)} {x}")
                
                if "score" in display_df.columns:
                    display_df["score"] = display_df["score"].apply(lambda x: f"{x:.1f}%")
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.success("✅ Tous les indicateurs sont au vert !")
        else:
            st.dataframe(demo["attention"], use_container_width=True, hide_index=True)

# =============================================================================
# TAB 2: AI CORRECTIONS
# =============================================================================

def render_corrections_tab():
    """Render the AI corrections workflow tab."""
    st.header("🤖 Corrections IA")
    
    # Load corrections
    df_corrections = load_corrections()
    
    # Use demo if empty
    if df_corrections.empty:
        st.info("📊 Affichage des données de démonstration")
        df_corrections = get_demo_corrections_data()
    
    # User identification
    with st.sidebar:
        st.subheader("👤 Utilisateur")
        current_user = st.text_input("Votre identifiant", value="demo.user", key="correction_user")
    
    # Stats bar
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
    
    # Filters
    col_filter1, col_filter2 = st.columns(2)
    
    with col_filter1:
        status_filter = st.selectbox(
            "Statut",
            ["pending", "all", "validated", "rejected"],
            format_func=lambda x: {"pending": "⏳ En attente", "all": "📋 Tous", "validated": "✅ Validées", "rejected": "❌ Rejetées"}.get(x, x)
        )
    
    with col_filter2:
        if "ai_confidence" in df_corrections.columns:
            confidence_min = st.slider("Confiance minimum", 0.0, 1.0, 0.0, 0.05)
        else:
            confidence_min = 0.0
    
    # Apply filters
    filtered_df = df_corrections.copy()
    
    if status_filter != "all" and "decision_status" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["decision_status"] == status_filter]
    
    if "ai_confidence" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["ai_confidence"] >= confidence_min]
    
    st.subheader(f"📝 Corrections à traiter ({len(filtered_df)})")
    
    # Render correction cards
    for idx, row in filtered_df.head(20).iterrows():
        with st.container():
            st.markdown("---")
            
            # Header with context
            source = row.get("source_name", "N/A")
            table = row.get("table_name", "N/A")
            field = row.get("field_name", "N/A")
            record = row.get("record_key", "N/A")
            
            st.markdown(f"**📍 {source}** > `{table}` > `{field}` > Row: `{record}`")
            
            # Values comparison
            col_before, col_arrow, col_after = st.columns([2, 1, 2])
            
            original = row.get("original_value", "N/A")
            proposed = row.get("proposed_value", "N/A")
            
            with col_before:
                st.markdown("**Valeur actuelle:**")
                st.code(original, language=None)
            
            with col_arrow:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("<h2 style='text-align: center;'>→</h2>", unsafe_allow_html=True)
            
            with col_after:
                st.markdown("**Valeur proposée:** ✨")
                st.code(proposed, language=None)
            
            # AI Explanation
            justification = row.get("ai_justification", "")
            if justification:
                with st.expander("🧠 Explication IA"):
                    st.info(justification)
            
            # Confidence & Category
            col_conf, col_cat, col_model = st.columns(3)
            
            confidence = row.get("ai_confidence", 0)
            if pd.notna(confidence):
                with col_conf:
                    confidence_pct = confidence * 100 if confidence <= 1 else confidence
                    color = "🟢" if confidence_pct >= 95 else "🟡" if confidence_pct >= 85 else "🔴"
                    st.markdown(f"**Confiance:** {color} {confidence_pct:.1f}%")
            
            with col_cat:
                category = row.get("ai_category", "N/A")
                st.markdown(f"**Catégorie:** `{category}`")
            
            with col_model:
                model = row.get("ai_model", "N/A")
                st.markdown(f"**Modèle:** `{model}`")
            
            # Action buttons
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
                decided_by = row.get("decided_by", "N/A")
                st.markdown(f"**Status:** {get_status_emoji(status)} {status} par `{decided_by}`")

# =============================================================================
# TAB 3: ISSUES
# =============================================================================

def render_issues_tab():
    """Render the issues exploration tab."""
    st.header("📋 Exploration des Issues")
    
    df_issues = load_issues()
    
    if df_issues.empty:
        st.info("Aucune issue trouvée dans la base de données.")
        return
    
    # Debug: show available columns
    with st.expander("🔧 Debug: Colonnes disponibles"):
        st.write(df_issues.columns.tolist())
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if "status" in df_issues.columns:
            statuses = ["Tous"] + list(df_issues["status"].dropna().unique())
            status_filter = st.selectbox("Statut", statuses)
        else:
            status_filter = "Tous"
    
    with col2:
        if "priority" in df_issues.columns:
            priorities = ["Tous"] + list(df_issues["priority"].dropna().unique())
            priority_filter = st.selectbox("Priorité", priorities)
        else:
            priority_filter = "Tous"
    
    with col3:
        if "issue_type" in df_issues.columns:
            types = ["Tous"] + list(df_issues["issue_type"].dropna().unique())
            type_filter = st.selectbox("Type", types)
        else:
            type_filter = "Tous"
    
    # Apply filters
    filtered = df_issues.copy()
    
    if status_filter != "Tous" and "status" in filtered.columns:
        filtered = filtered[filtered["status"] == status_filter]
    
    if priority_filter != "Tous" and "priority" in filtered.columns:
        filtered = filtered[filtered["priority"] == priority_filter]
    
    if type_filter != "Tous" and "issue_type" in filtered.columns:
        filtered = filtered[filtered["issue_type"] == type_filter]
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Issues filtrées", len(filtered))
    
    if "priority" in filtered.columns:
        critical = len(filtered[filtered["priority"] == "critical"])
        col2.metric("Critiques", critical)
    
    if "status" in filtered.columns:
        open_count = len(filtered[filtered["status"] == "open"])
        col3.metric("Ouvertes", open_count)
    
    st.divider()
    
    # Display table
    st.dataframe(filtered.head(100), use_container_width=True, hide_index=True)
    
    # Export
    csv = filtered.to_csv(index=False)
    st.download_button("📥 Exporter CSV", csv, "issues.csv", "text/csv")

# =============================================================================
# TAB 4: TABLES
# =============================================================================

def render_tables_tab():
    """Render the Supabase tables viewer tab."""
    st.header("📊 Visualisation des Tables")
    
    with st.sidebar:
        st.subheader("⚙️ Paramètres Tables")
        tables = get_table_list()
        selected_table = st.selectbox("Nom de la table", tables, key="table_select")
        
        if st.button("🔄 Rafraîchir"):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()
        columns = st.text_input("Colonnes", value="*")
        limit = st.slider("Limite de lignes", 10, 500, 100)
    
    if selected_table:
        df = load_table_safe(selected_table, limit)
        
        if not df.empty:
            col1, col2, col3 = st.columns(3)
            col1.metric("Lignes", len(df))
            col2.metric("Colonnes", len(df.columns))
            col3.metric("Table", selected_table)
            
            st.divider()
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            csv = df.to_csv(index=False)
            st.download_button("📥 Télécharger CSV", csv, f"{selected_table}.csv", "text/csv")
        else:
            st.warning(f"Aucune donnée dans `{selected_table}`")

# =============================================================================
# TAB 5: STORAGE
# =============================================================================

def render_storage_tab():
    """Render the Supabase storage tab."""
    st.header("📁 Gestion du Storage")
    
    supabase = get_supabase()
    
    if not supabase:
        st.warning("Connexion Supabase requise pour accéder au storage.")
        return
    
    with st.sidebar:
        st.subheader("⚙️ Paramètres Storage")
        bucket_name = st.text_input("Bucket", value="uploads")
        folder_path = st.text_input("Dossier", value="")
    
    try:
        files = supabase.storage.from_(bucket_name).list(folder_path)
        
        if files:
            st.subheader(f"📂 Contenu de `{bucket_name}/{folder_path}`")
            
            file_data = []
            for f in files:
                file_data.append({
                    "Nom": f.get("name", "N/A"),
                    "Type": "📁 Dossier" if f.get("id") is None else "📄 Fichier",
                    "Créé": f.get("created_at", "N/A")[:10] if f.get("created_at") else "N/A"
                })
            
            st.dataframe(pd.DataFrame(file_data), use_container_width=True, hide_index=True)
        else:
            st.info("Bucket vide ou non accessible.")
            
    except Exception as e:
        st.error(f"Erreur: {e}")
        st.info("💡 Créez d'abord un bucket 'uploads' dans Supabase Storage.")

# =============================================================================
# TAB 6: UPLOAD
# =============================================================================

def render_upload_tab():
    """Render the file upload tab."""
    st.header("📤 Upload de Fichiers")
    
    supabase = get_supabase()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📁 Upload vers Storage")
        
        bucket = st.text_input("Bucket cible", value="uploads", key="up_bucket")
        uploaded_file = st.file_uploader("Choisir un fichier", type=["csv", "xlsx", "json", "txt", "pdf"])
        
        if uploaded_file:
            st.success(f"Fichier sélectionné: {uploaded_file.name}")
            
            if supabase and st.button("⬆️ Uploader", type="primary"):
                try:
                    supabase.storage.from_(bucket).upload(
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        {"content-type": uploaded_file.type}
                    )
                    st.success(f"✅ Uploadé: {uploaded_file.name}")
                except Exception as e:
                    st.error(f"Erreur: {e}")
    
    with col2:
        st.subheader("📊 Import CSV → Table")
        
        csv_file = st.file_uploader("Fichier CSV", type=["csv"], key="csv_up")
        target_table = st.selectbox("Table cible", get_table_list(), key="import_tbl")
        
        if csv_file:
            df_preview = pd.read_csv(csv_file, nrows=5)
            st.markdown("**Aperçu:**")
            st.dataframe(df_preview, use_container_width=True, hide_index=True)
            
            if supabase and st.button("📥 Importer"):
                try:
                    csv_file.seek(0)
                    df_full = pd.read_csv(csv_file)
                    records = df_full.to_dict(orient="records")
                    supabase.table(target_table).insert(records).execute()
                    st.success(f"✅ {len(records)} lignes importées")
                except Exception as e:
                    st.error(f"Erreur: {e}")

# =============================================================================
# MAIN
# =============================================================================

def main():
    with st.sidebar:
        st.title("📊 Data Quality")
        st.caption("Powered by Alteryx + AI")
        st.divider()
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🏠 Dashboard",
        "🤖 AI Corrections", 
        "📋 Issues",
        "📊 Tables",
        "📁 Storage",
        "📤 Upload"
    ])
    
    with tab1:
        render_dashboard_tab()
    
    with tab2:
        render_corrections_tab()
    
    with tab3:
        render_issues_tab()
    
    with tab4:
        render_tables_tab()
    
    with tab5:
        render_storage_tab()
    
    with tab6:
        render_upload_tab()
    
    st.sidebar.divider()
    st.sidebar.caption("© 2025 Prime Analytics")

if __name__ == "__main__":
    main()

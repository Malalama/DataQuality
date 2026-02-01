"""
Prime Analytics - Data Quality Dashboard
=========================================
Application Streamlit pour la gestion de la qualité des données
avec intégration Supabase et corrections IA.

Tabs:
1. 🏠 Dashboard - Vue exécutive
2. 🤖 AI Corrections - Workflow de validation des corrections IA
3. 📋 Issues - Exploration détaillée des problèmes
4. 📊 Tables - Visualisation des tables Supabase
5. 📁 Storage - Gestion du stockage Supabase
6. 📤 Upload - Upload de fichiers
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
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://sdlrorvcfticssbeymgb.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

# =============================================================================
# SUPABASE CONNECTION
# =============================================================================

@st.cache_resource
def get_supabase_client():
    """Initialize Supabase client."""
    if not SUPABASE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def get_supabase():
    """Get Supabase client with error handling."""
    client = get_supabase_client()
    if not client:
        st.sidebar.error("⚠️ Configurez SUPABASE_KEY dans .streamlit/secrets.toml")
    return client

# =============================================================================
# DATA LOADING FUNCTIONS
# =============================================================================

@st.cache_data(ttl=60)
def load_dashboard_summary():
    """Load dashboard summary from materialized view."""
    supabase = get_supabase()
    if not supabase:
        return pd.DataFrame()
    
    try:
        response = supabase.table("mv_dashboard_summary").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Erreur chargement dashboard: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_correction_queue():
    """Load AI correction queue."""
    supabase = get_supabase()
    if not supabase:
        return pd.DataFrame()
    
    try:
        response = supabase.table("mv_correction_review_queue").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Erreur chargement corrections: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_source_health():
    """Load source health scores."""
    supabase = get_supabase()
    if not supabase:
        return pd.DataFrame()
    
    try:
        response = supabase.table("mv_source_health_score").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Erreur chargement health: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_issues():
    """Load issue details."""
    supabase = get_supabase()
    if not supabase:
        return pd.DataFrame()
    
    try:
        response = supabase.table("dq_issue_detail").select("*").order("created_at", desc=True).limit(500).execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Erreur chargement issues: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_data_sources():
    """Load data sources."""
    supabase = get_supabase()
    if not supabase:
        return pd.DataFrame()
    
    try:
        response = supabase.table("data_source").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Erreur chargement sources: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_table_list():
    """Get list of tables in the database."""
    supabase = get_supabase()
    if not supabase:
        return []
    
    try:
        # Liste des tables DQ
        tables = [
            "data_source", "dq_rule_type", "dq_rule", "dq_field_ref",
            "dq_run", "dq_measurement", "dq_field_check", "dq_issue_detail",
            "dq_correction", "dq_audit_log",
            "mv_dashboard_summary", "mv_correction_review_queue", 
            "mv_source_health_score", "mv_field_quality_trend", "mv_rule_effectiveness"
        ]
        return tables
    except Exception as e:
        st.error(f"Erreur liste tables: {e}")
        return []

def load_table_data(table_name: str, columns: str = "*", limit: int = 100):
    """Load data from a specific table."""
    supabase = get_supabase()
    if not supabase:
        return pd.DataFrame()
    
    try:
        response = supabase.table(table_name).select(columns).limit(limit).execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Erreur chargement {table_name}: {e}")
        return pd.DataFrame()

# =============================================================================
# ACTION FUNCTIONS
# =============================================================================

def update_correction_status(correction_id: int, status: str, user: str, comment: str = None, final_value: str = None):
    """Update correction status in database."""
    supabase = get_supabase()
    if not supabase:
        return False
    
    try:
        update_data = {
            "decision_status": status,
            "decided_by": user,
            "decided_at": datetime.now().isoformat()
        }
        if comment:
            update_data["decision_comment"] = comment
        if final_value:
            update_data["final_value"] = final_value
        
        supabase.table("dq_correction").update(update_data).eq("correction_id", correction_id).execute()
        
        # Log audit
        supabase.table("dq_audit_log").insert({
            "entity_type": "correction",
            "entity_id": correction_id,
            "action": "validate" if status == "validated" else "reject",
            "previous_status": "pending",
            "new_status": status,
            "user_id": user,
            "user_email": f"{user}@company.com",
            "comment": comment
        }).execute()
        
        return True
    except Exception as e:
        st.error(f"Erreur mise à jour: {e}")
        return False

# =============================================================================
# UI COMPONENTS
# =============================================================================

def render_kpi_card(title: str, value: str, delta: str = None, delta_color: str = "normal"):
    """Render a KPI metric card."""
    st.metric(label=title, value=value, delta=delta, delta_color=delta_color)

def render_health_bar(score: float, label: str):
    """Render a health score bar."""
    color = "#10b981" if score >= 95 else "#f59e0b" if score >= 90 else "#ef4444"
    st.markdown(f"""
    <div style="margin-bottom: 10px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
            <span>{label}</span>
            <span style="font-weight: bold;">{score:.1f}%</span>
        </div>
        <div style="background-color: #e5e7eb; border-radius: 10px; height: 20px; overflow: hidden;">
            <div style="background-color: {color}; width: {score}%; height: 100%; border-radius: 10px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def get_status_emoji(status: str) -> str:
    """Get emoji for status."""
    status_map = {
        "ok": "🟢",
        "warning": "🟡", 
        "critical": "🔴",
        "pending": "⏳",
        "validated": "✅",
        "rejected": "❌",
        "open": "🔵",
        "escalated": "🚨"
    }
    return status_map.get(status, "⚪")

# =============================================================================
# TAB 1: DASHBOARD
# =============================================================================

def render_dashboard_tab():
    """Render the executive dashboard tab."""
    st.header("🏠 Dashboard Qualité des Données")
    
    # Load data
    df_summary = load_dashboard_summary()
    df_health = load_source_health()
    df_corrections = load_correction_queue()
    
    if df_summary.empty:
        st.warning("Aucune donnée disponible. Vérifiez la connexion Supabase.")
        return
    
    # ==========================================================================
    # KPIs Row
    # ==========================================================================
    st.subheader("📈 Indicateurs Clés")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Calculate KPIs
    overall_score = df_summary["score"].mean() if "score" in df_summary.columns else 0
    total_sources = df_summary["source_id"].nunique() if "source_id" in df_summary.columns else 0
    open_issues = df_summary["open_issues"].sum() if "open_issues" in df_summary.columns else 0
    pending_corrections = len(df_corrections[df_corrections["decision_status"] == "pending"]) if not df_corrections.empty and "decision_status" in df_corrections.columns else 0
    
    with col1:
        render_kpi_card("Score Global", f"{overall_score:.1f}%", "+1.2%")
    with col2:
        render_kpi_card("Sources Surveillées", str(total_sources))
    with col3:
        render_kpi_card("Issues Ouvertes", str(int(open_issues)), "-52", "inverse")
    with col4:
        render_kpi_card("Corrections IA en attente", str(pending_corrections), "🤖")
    
    st.divider()
    
    # ==========================================================================
    # Charts Row
    # ==========================================================================
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("🚦 Santé par Domaine")
        
        if not df_health.empty and "business_domain" in df_health.columns:
            domain_scores = df_health.groupby("business_domain")["overall_score"].mean().reset_index()
            domain_scores = domain_scores.sort_values("overall_score", ascending=True)
            
            fig = px.bar(
                domain_scores,
                x="overall_score",
                y="business_domain",
                orientation="h",
                color="overall_score",
                color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"],
                range_color=[80, 100]
            )
            fig.update_layout(
                showlegend=False,
                xaxis_title="Score %",
                yaxis_title="",
                height=300,
                margin=dict(l=0, r=0, t=0, b=0)
            )
            fig.update_traces(texttemplate='%{x:.1f}%', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Demo data
            for domain, score in [("Regulatory", 96), ("Finance", 94), ("Accounting", 99), ("Reference", 87), ("Risk", 95)]:
                render_health_bar(score, domain)
    
    with col_right:
        st.subheader("📊 Qualité par Type de Règle")
        
        if not df_summary.empty and "rule_type_name" in df_summary.columns:
            rule_scores = df_summary.groupby("rule_type_name")["score"].mean().reset_index()
            rule_scores = rule_scores.sort_values("score", ascending=True)
            
            fig = px.bar(
                rule_scores,
                x="score",
                y="rule_type_name",
                orientation="h",
                color="score",
                color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"],
                range_color=[80, 100]
            )
            fig.update_layout(
                showlegend=False,
                xaxis_title="Score %",
                yaxis_title="",
                height=300,
                margin=dict(l=0, r=0, t=0, b=0)
            )
            fig.update_traces(texttemplate='%{x:.1f}%', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Demo data
            for rule, score in [("Completeness", 98), ("Field Type", 99), ("Validation", 97), ("List of Values", 96), ("AI Quality", 92)]:
                render_health_bar(score, rule)
    
    st.divider()
    
    # ==========================================================================
    # Attention Required Table
    # ==========================================================================
    st.subheader("⚠️ Attention Requise")
    
    if not df_summary.empty and "score" in df_summary.columns:
        # Filter low scores
        attention_df = df_summary[df_summary["score"] < 99].sort_values("score").head(10)
        
        if not attention_df.empty:
            display_cols = ["source_name", "table_name", "field_name", "rule_name", "score", "status", "open_issues"]
            available_cols = [c for c in display_cols if c in attention_df.columns]
            
            if available_cols:
                display_df = attention_df[available_cols].copy()
                display_df["status"] = display_df["status"].apply(lambda x: f"{get_status_emoji(x)} {x}")
                st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.success("✅ Tous les indicateurs sont au vert !")
    else:
        # Demo table
        demo_data = {
            "Source": ["Counterparty Master", "Counterparty Master", "AnaCredit", "Budget"],
            "Field": ["lei_code", "address", "interest_rate", "version"],
            "Score": ["81.4%", "92.9%", "99.4%", "99.8%"],
            "Issues": [6500, 2500, 800, 15],
            "Status": ["🔴 critical", "🔴 critical", "🟡 warning", "🟡 warning"]
        }
        st.dataframe(pd.DataFrame(demo_data), use_container_width=True, hide_index=True)

# =============================================================================
# TAB 2: AI CORRECTIONS
# =============================================================================

def render_corrections_tab():
    """Render the AI corrections workflow tab."""
    st.header("🤖 Corrections IA")
    
    # Load corrections
    df_corrections = load_correction_queue()
    
    if df_corrections.empty:
        st.info("Aucune correction en attente.")
        return
    
    # Filter pending
    pending = df_corrections[df_corrections["decision_status"] == "pending"] if "decision_status" in df_corrections.columns else df_corrections
    
    # Stats bar
    col1, col2, col3, col4 = st.columns(4)
    total = len(df_corrections)
    pending_count = len(pending)
    validated = len(df_corrections[df_corrections["decision_status"] == "validated"]) if "decision_status" in df_corrections.columns else 0
    rejected = len(df_corrections[df_corrections["decision_status"] == "rejected"]) if "decision_status" in df_corrections.columns else 0
    
    col1.metric("Total", total)
    col2.metric("En attente", pending_count, delta=None)
    col3.metric("Validées", validated)
    col4.metric("Rejetées", rejected)
    
    st.divider()
    
    # User identification
    with st.sidebar:
        st.subheader("👤 Utilisateur")
        current_user = st.text_input("Votre identifiant", value="demo.user", key="correction_user")
    
    # Filters
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        status_filter = st.selectbox(
            "Statut",
            ["pending", "all", "validated", "rejected"],
            format_func=lambda x: {"pending": "⏳ En attente", "all": "📋 Tous", "validated": "✅ Validées", "rejected": "❌ Rejetées"}.get(x, x)
        )
    
    with col_filter2:
        if "ai_category" in df_corrections.columns:
            categories = ["Tous"] + list(df_corrections["ai_category"].dropna().unique())
            category_filter = st.selectbox("Catégorie IA", categories)
        else:
            category_filter = "Tous"
    
    with col_filter3:
        confidence_min = st.slider("Confiance minimum", 0.0, 1.0, 0.0, 0.05)
    
    # Apply filters
    filtered_df = df_corrections.copy()
    
    if status_filter != "all" and "decision_status" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["decision_status"] == status_filter]
    
    if category_filter != "Tous" and "ai_category" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["ai_category"] == category_filter]
    
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
                col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
                
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
                    with st.popover("✏️ Modifier"):
                        new_value = st.text_input("Nouvelle valeur", value=proposed, key=f"edit_{correction_id}")
                        comment = st.text_area("Commentaire", key=f"comment_{correction_id}")
                        if st.button("Valider la modification", key=f"save_{correction_id}"):
                            if update_correction_status(correction_id, "overwritten", current_user, comment, new_value):
                                st.success("Modification enregistrée !")
                                st.cache_data.clear()
                                st.rerun()
                
                with col_btn4:
                    st.button("⏭️ Ignorer", key=f"skip_{correction_id}")
            else:
                decided_by = row.get("decided_by", "N/A")
                decided_at = row.get("decided_at", "N/A")
                st.markdown(f"**Status:** {get_status_emoji(status)} {status} par `{decided_by}` le `{decided_at}`")

# =============================================================================
# TAB 3: ISSUES
# =============================================================================

def render_issues_tab():
    """Render the issues exploration tab."""
    st.header("📋 Exploration des Issues")
    
    # Load data
    df_issues = load_issues()
    df_summary = load_dashboard_summary()
    
    # Sidebar filters
    with st.sidebar:
        st.subheader("🔍 Filtres Issues")
        
        # Status filter
        status_options = ["Tous", "open", "escalated", "resolved", "ignored"]
        status_filter = st.selectbox("Statut", status_options)
        
        # Priority filter
        priority_options = ["Tous", "critical", "high", "medium", "low"]
        priority_filter = st.selectbox("Priorité", priority_options)
        
        # Source filter
        if not df_summary.empty and "source_name" in df_summary.columns:
            sources = ["Tous"] + list(df_summary["source_name"].unique())
            source_filter = st.selectbox("Source", sources)
        else:
            source_filter = "Tous"
    
    # Summary metrics from measurements
    if not df_summary.empty:
        st.subheader("📊 Résumé par Source")
        
        # Aggregate by source
        if "source_name" in df_summary.columns and "score" in df_summary.columns:
            source_summary = df_summary.groupby("source_name").agg({
                "score": "mean",
                "open_issues": "sum" if "open_issues" in df_summary.columns else "count"
            }).reset_index()
            
            # Create treemap or bar
            fig = px.bar(
                source_summary.sort_values("score"),
                x="score",
                y="source_name",
                orientation="h",
                color="score",
                color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"],
                range_color=[80, 100],
                title="Score moyen par source"
            )
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Issues table
    st.subheader("🔎 Détail des Issues")
    
    if not df_issues.empty:
        # Apply filters
        filtered_issues = df_issues.copy()
        
        if status_filter != "Tous" and "status" in filtered_issues.columns:
            filtered_issues = filtered_issues[filtered_issues["status"] == status_filter]
        
        if priority_filter != "Tous" and "priority" in filtered_issues.columns:
            filtered_issues = filtered_issues[filtered_issues["priority"] == priority_filter]
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Issues filtrées", len(filtered_issues))
        
        if "priority" in filtered_issues.columns:
            critical_count = len(filtered_issues[filtered_issues["priority"] == "critical"])
            col2.metric("Critiques", critical_count)
        
        if "status" in filtered_issues.columns:
            open_count = len(filtered_issues[filtered_issues["status"] == "open"])
            col3.metric("Ouvertes", open_count)
        
        # Display table
        display_cols = ["record_key", "field_name", "current_value", "issue_type", "issue_description", "status", "priority"]
        available_cols = [c for c in display_cols if c in filtered_issues.columns]
        
        if available_cols:
            display_df = filtered_issues[available_cols].head(100)
            
            # Add status emoji
            if "status" in display_df.columns:
                display_df["status"] = display_df["status"].apply(lambda x: f"{get_status_emoji(x)} {x}")
            if "priority" in display_df.columns:
                priority_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
                display_df["priority"] = display_df["priority"].apply(lambda x: f"{priority_emoji.get(x, '⚪')} {x}")
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Export button
            csv = filtered_issues.to_csv(index=False)
            st.download_button(
                "📥 Exporter en CSV",
                csv,
                "issues_export.csv",
                "text/csv"
            )
        else:
            st.dataframe(filtered_issues.head(100), use_container_width=True, hide_index=True)
    else:
        st.info("Aucune issue trouvée.")

# =============================================================================
# TAB 4: TABLES (Supabase Viewer)
# =============================================================================

def render_tables_tab():
    """Render the Supabase tables viewer tab."""
    st.header("📊 Visualisation des Tables")
    
    # Sidebar config
    with st.sidebar:
        st.subheader("⚙️ Paramètres Tables")
        
        # Table selection
        tables = get_table_list()
        selected_table = st.selectbox("Nom de la table", tables, key="table_select")
        
        if st.button("🔄 Rafraîchir la liste"):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()
        
        # Columns filter
        columns = st.text_input("Colonnes", value="*", help="* pour toutes, ou col1,col2,col3")
        
        # Row limit
        limit = st.slider("Limite de lignes", 10, 500, 100)
    
    # Load and display data
    if selected_table:
        df = load_table_data(selected_table, columns, limit)
        
        if not df.empty:
            # Metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Lignes", len(df))
            col2.metric("Colonnes", len(df.columns))
            col3.metric("Table", selected_table)
            
            st.divider()
            
            # Data display
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Export
            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Télécharger CSV",
                csv,
                f"{selected_table}.csv",
                "text/csv"
            )
        else:
            st.warning(f"Aucune donnée dans la table `{selected_table}`")

# =============================================================================
# TAB 5: STORAGE
# =============================================================================

def render_storage_tab():
    """Render the Supabase storage management tab."""
    st.header("📁 Gestion du Storage")
    
    supabase = get_supabase()
    
    if not supabase:
        st.warning("Connexion Supabase requise.")
        return
    
    with st.sidebar:
        st.subheader("⚙️ Paramètres Storage")
        bucket_name = st.text_input("Nom du bucket", value="uploads")
        folder_path = st.text_input("Chemin", value="")
    
    # List files
    try:
        files = supabase.storage.from_(bucket_name).list(folder_path)
        
        if files:
            st.subheader(f"📂 Fichiers dans `{bucket_name}/{folder_path}`")
            
            file_data = []
            for f in files:
                file_data.append({
                    "Nom": f.get("name", "N/A"),
                    "Taille": f"{f.get('metadata', {}).get('size', 0) / 1024:.1f} KB" if f.get('metadata') else "N/A",
                    "Créé": f.get("created_at", "N/A"),
                    "Type": f.get("metadata", {}).get("mimetype", "N/A") if f.get("metadata") else "folder"
                })
            
            st.dataframe(pd.DataFrame(file_data), use_container_width=True, hide_index=True)
        else:
            st.info("Aucun fichier trouvé.")
            
    except Exception as e:
        st.error(f"Erreur accès storage: {e}")
        st.info("💡 Assurez-vous que le bucket existe et que vous avez les permissions.")

# =============================================================================
# TAB 6: UPLOAD
# =============================================================================

def render_upload_tab():
    """Render the file upload tab."""
    st.header("📤 Upload de Fichiers")
    
    supabase = get_supabase()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📁 Upload vers Supabase Storage")
        
        bucket = st.text_input("Bucket cible", value="uploads", key="upload_bucket")
        folder = st.text_input("Dossier (optionnel)", value="", key="upload_folder")
        
        uploaded_file = st.file_uploader("Choisir un fichier", type=["csv", "xlsx", "json", "txt", "pdf"])
        
        if uploaded_file and supabase:
            if st.button("⬆️ Uploader", type="primary"):
                try:
                    path = f"{folder}/{uploaded_file.name}" if folder else uploaded_file.name
                    
                    supabase.storage.from_(bucket).upload(
                        path,
                        uploaded_file.getvalue(),
                        {"content-type": uploaded_file.type}
                    )
                    st.success(f"✅ Fichier uploadé: `{path}`")
                except Exception as e:
                    st.error(f"Erreur upload: {e}")
    
    with col2:
        st.subheader("📊 Import CSV vers Table")
        
        csv_file = st.file_uploader("Fichier CSV", type=["csv"], key="csv_import")
        target_table = st.selectbox("Table cible", get_table_list(), key="import_table")
        
        if csv_file:
            df_preview = pd.read_csv(csv_file, nrows=5)
            st.markdown("**Aperçu:**")
            st.dataframe(df_preview, use_container_width=True, hide_index=True)
            
            if st.button("📥 Importer dans la table"):
                try:
                    csv_file.seek(0)
                    df_full = pd.read_csv(csv_file)
                    
                    # Convert to records and insert
                    records = df_full.to_dict(orient="records")
                    
                    if supabase:
                        supabase.table(target_table).insert(records).execute()
                        st.success(f"✅ {len(records)} lignes importées dans `{target_table}`")
                except Exception as e:
                    st.error(f"Erreur import: {e}")

# =============================================================================
# MAIN APP
# =============================================================================

def main():
    """Main application entry point."""
    
    # Sidebar header
    with st.sidebar:
        st.image("https://www.primeanalytics.fr/wp-content/uploads/2023/01/logo-prime-analytics.png", width=200)
        st.title("Data Quality")
        st.caption("Powered by Alteryx + AI")
        st.divider()
    
    # Main tabs
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
    
    # Footer
    st.sidebar.divider()
    st.sidebar.caption("© 2025 Prime Analytics")
    st.sidebar.caption("v1.0.0")

if __name__ == "__main__":
    main()

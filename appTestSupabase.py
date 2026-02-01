"""
Supabase Table Viewer - Streamlit App
Affiche les résultats d'une requête Supabase dans une interface web.
Inclut également un explorateur de fichiers pour les buckets Supabase Storage.
"""

import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

# Configuration de la page
st.set_page_config(
    page_title="Supabase Viewer",
    page_icon="🗃️",
    layout="wide"
)

@st.cache_resource
def get_supabase_client() -> Client:
    """Crée et retourne un client Supabase (mis en cache)."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

@st.cache_data(ttl=300)  # Cache pendant 5 minutes
def get_available_tables() -> list[str]:
    """
    Récupère la liste des tables disponibles dans le schéma public.
    
    Returns:
        Liste des noms de tables
    """
    supabase = get_supabase_client()
    
    try:
        # Utilise la fonction RPC pour exécuter une requête SQL brute
        response = supabase.rpc('get_public_tables').execute()
        return [row['table_name'] for row in response.data]
    except Exception:
        try:
            # Tente d'accéder à pg_tables si accessible
            response = supabase.from_('pg_tables').select('tablename').eq('schemaname', 'public').execute()
            return [row['tablename'] for row in response.data]
        except Exception:
            return []

@st.cache_data(ttl=300)  # Cache pendant 5 minutes
def get_available_buckets() -> list[dict]:
    """
    Récupère la liste des buckets disponibles dans Supabase Storage.
    
    Returns:
        Liste des buckets avec leurs informations
    """
    supabase = get_supabase_client()
    
    try:
        buckets = supabase.storage.list_buckets()
        return buckets
    except Exception as e:
        st.error(f"Erreur lors de la récupération des buckets : {e}")
        return []

def get_bucket_files(bucket_name: str, path: str = "") -> list[dict]:
    """
    Récupère la liste des fichiers dans un bucket Supabase.
    
    Args:
        bucket_name: Nom du bucket
        path: Chemin dans le bucket (pour naviguer dans les dossiers)
    
    Returns:
        Liste des fichiers et dossiers
    """
    supabase = get_supabase_client()
    
    try:
        files = supabase.storage.from_(bucket_name).list(path)
        return files
    except Exception as e:
        st.error(f"Erreur lors de la récupération des fichiers : {e}")
        return []

def get_file_public_url(bucket_name: str, file_path: str) -> str:
    """
    Génère l'URL publique d'un fichier.
    
    Args:
        bucket_name: Nom du bucket
        file_path: Chemin complet du fichier
    
    Returns:
        URL publique du fichier
    """
    supabase = get_supabase_client()
    return supabase.storage.from_(bucket_name).get_public_url(file_path)

def format_file_size(size_bytes: int) -> str:
    """Formate la taille d'un fichier en unités lisibles."""
    if size_bytes is None:
        return "-"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"

def format_datetime(dt_string: str) -> str:
    """Formate une date ISO en format lisible."""
    if not dt_string:
        return "-"
    try:
        dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return dt_string

def query_table(table_name: str, columns: str = "*", limit: int = 100) -> pd.DataFrame:
    """
    Effectue une requête sur une table Supabase.
    
    Args:
        table_name: Nom de la table à interroger
        columns: Colonnes à sélectionner (par défaut: toutes)
        limit: Nombre maximum de lignes à retourner
    
    Returns:
        DataFrame avec les résultats
    """
    supabase = get_supabase_client()
    response = supabase.table(table_name).select(columns).limit(limit).execute()
    return pd.DataFrame(response.data)

def render_tables_tab():
    """Affiche l'onglet de visualisation des tables."""
    st.header("📊 Visualisation des Tables")
    
    # Récupération des tables disponibles
    available_tables = get_available_tables()
    
    # Sidebar pour les paramètres
    with st.sidebar:
        st.header("⚙️ Paramètres Tables")
        
        # Dropdown pour sélectionner la table
        if available_tables:
            table_name = st.selectbox(
                "Nom de la table",
                options=available_tables,
                help="Sélectionnez la table Supabase à interroger",
                key="table_select"
            )
        else:
            st.warning("Impossible de récupérer la liste des tables automatiquement.")
            table_name = st.text_input(
                "Nom de la table",
                value="users",
                help="Entrez le nom de la table Supabase à interroger",
                key="table_input"
            )
        
        # Bouton pour rafraîchir la liste des tables
        if st.button("🔄 Rafraîchir la liste", use_container_width=True, key="refresh_tables"):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()
        
        columns = st.text_input(
            "Colonnes",
            value="*",
            help="Colonnes à sélectionner (* pour toutes)",
            key="columns_input"
        )
        
        limit = st.slider(
            "Limite de lignes",
            min_value=10,
            max_value=1000,
            value=100,
            step=10,
            key="limit_slider"
        )
        
        query_button = st.button("🔍 Exécuter la requête", type="primary", use_container_width=True, key="query_btn")
    
    # Zone principale
    if query_button:
        try:
            with st.spinner("Chargement des données..."):
                df = query_table(table_name, columns, limit)
            
            if df.empty:
                st.warning("Aucune donnée trouvée dans cette table.")
            else:
                # Métriques
                col1, col2, col3 = st.columns(3)
                col1.metric("Lignes", len(df))
                col2.metric("Colonnes", len(df.columns))
                col3.metric("Table", table_name)
                
                st.divider()
                
                # Affichage de la table
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Option de téléchargement
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Télécharger en CSV",
                    data=csv,
                    file_name=f"{table_name}_export.csv",
                    mime="text/csv",
                    key="download_csv"
                )
                
        except Exception as e:
            st.error(f"Erreur lors de la requête : {e}")
    else:
        st.info("👈 Configurez les paramètres dans la barre latérale et cliquez sur 'Exécuter la requête'")

def render_storage_tab():
    """Affiche l'onglet de visualisation des fichiers Storage."""
    st.header("📁 Explorateur de Fichiers Storage")
    
    # Initialisation de l'état de session pour la navigation
    if 'current_path' not in st.session_state:
        st.session_state.current_path = ""
    if 'selected_bucket' not in st.session_state:
        st.session_state.selected_bucket = None
    
    # Récupération des buckets disponibles
    buckets = get_available_buckets()
    
    with st.sidebar:
        st.header("⚙️ Paramètres Storage")
        
        if buckets:
            bucket_names = [b.name if hasattr(b, 'name') else b.get('name', str(b)) for b in buckets]
            selected_bucket = st.selectbox(
                "Bucket",
                options=bucket_names,
                help="Sélectionnez le bucket à explorer",
                key="bucket_select"
            )
            
            # Reset du chemin si on change de bucket
            if st.session_state.selected_bucket != selected_bucket:
                st.session_state.selected_bucket = selected_bucket
                st.session_state.current_path = ""
        else:
            st.warning("Aucun bucket trouvé ou accès non autorisé.")
            selected_bucket = st.text_input(
                "Nom du bucket",
                value="",
                help="Entrez le nom du bucket à explorer",
                key="bucket_input"
            )
            st.session_state.selected_bucket = selected_bucket
        
        # Bouton pour rafraîchir
        if st.button("🔄 Rafraîchir", use_container_width=True, key="refresh_storage"):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()
        
        # Navigation manuelle
        manual_path = st.text_input(
            "Chemin",
            value=st.session_state.current_path,
            help="Chemin dans le bucket (laisser vide pour la racine)",
            key="path_input"
        )
        if manual_path != st.session_state.current_path:
            st.session_state.current_path = manual_path
        
        if st.button("📂 Aller au chemin", use_container_width=True, key="goto_path"):
            st.rerun()
    
    # Zone principale
    if selected_bucket:
        # Fil d'Ariane (breadcrumb)
        st.markdown("**📍 Chemin actuel:**")
        breadcrumb_cols = st.columns([1, 10])
        with breadcrumb_cols[0]:
            if st.button("🏠", help="Retour à la racine", key="home_btn"):
                st.session_state.current_path = ""
                st.rerun()
        
        with breadcrumb_cols[1]:
            if st.session_state.current_path:
                path_parts = st.session_state.current_path.split('/')
                breadcrumb = f"`{selected_bucket}` / "
                for i, part in enumerate(path_parts):
                    if part:
                        breadcrumb += f"`{part}` / "
                st.markdown(breadcrumb)
            else:
                st.markdown(f"`{selected_bucket}` (racine)")
        
        # Bouton retour
        if st.session_state.current_path:
            if st.button("⬆️ Dossier parent", key="parent_btn"):
                path_parts = st.session_state.current_path.rstrip('/').split('/')
                st.session_state.current_path = '/'.join(path_parts[:-1])
                st.rerun()
        
        st.divider()
        
        # Récupération et affichage des fichiers
        with st.spinner("Chargement des fichiers..."):
            files = get_bucket_files(selected_bucket, st.session_state.current_path)
        
        if not files:
            st.info("📭 Ce dossier est vide ou inaccessible.")
        else:
            # Séparation des dossiers et fichiers
            folders = [f for f in files if f.get('id') is None]
            regular_files = [f for f in files if f.get('id') is not None]
            
            # Métriques
            col1, col2, col3 = st.columns(3)
            col1.metric("Dossiers", len(folders))
            col2.metric("Fichiers", len(regular_files))
            total_size = sum(f.get('metadata', {}).get('size', 0) or 0 for f in regular_files)
            col3.metric("Taille totale", format_file_size(total_size))
            
            st.divider()
            
            # Affichage des dossiers
            if folders:
                st.subheader("📁 Dossiers")
                folder_cols = st.columns(4)
                for i, folder in enumerate(folders):
                    folder_name = folder.get('name', 'Unknown')
                    with folder_cols[i % 4]:
                        if st.button(f"📁 {folder_name}", key=f"folder_{folder_name}", use_container_width=True):
                            if st.session_state.current_path:
                                st.session_state.current_path = f"{st.session_state.current_path}/{folder_name}"
                            else:
                                st.session_state.current_path = folder_name
                            st.rerun()
            
            # Affichage des fichiers dans un tableau
            if regular_files:
                st.subheader("📄 Fichiers")
                
                # Préparation des données pour le tableau
                file_data = []
                for f in regular_files:
                    metadata = f.get('metadata', {}) or {}
                    file_path = f"{st.session_state.current_path}/{f.get('name', '')}" if st.session_state.current_path else f.get('name', '')
                    
                    file_data.append({
                        "Nom": f.get('name', 'Unknown'),
                        "Taille": format_file_size(metadata.get('size')),
                        "Type": metadata.get('mimetype', '-'),
                        "Dernière modification": format_datetime(f.get('updated_at', '')),
                        "Chemin": file_path
                    })
                
                df_files = pd.DataFrame(file_data)
                
                # Affichage du tableau
                st.dataframe(
                    df_files,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Nom": st.column_config.TextColumn("Nom", width="medium"),
                        "Taille": st.column_config.TextColumn("Taille", width="small"),
                        "Type": st.column_config.TextColumn("Type MIME", width="medium"),
                        "Dernière modification": st.column_config.TextColumn("Modifié le", width="medium"),
                        "Chemin": st.column_config.TextColumn("Chemin complet", width="large"),
                    }
                )
                
                # Section pour obtenir les URLs des fichiers
                st.divider()
                st.subheader("🔗 Obtenir l'URL d'un fichier")
                
                file_names = [f.get('name', '') for f in regular_files]
                selected_file = st.selectbox(
                    "Sélectionnez un fichier",
                    options=file_names,
                    key="file_url_select"
                )
                
                if selected_file:
                    file_path = f"{st.session_state.current_path}/{selected_file}" if st.session_state.current_path else selected_file
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🔗 Générer URL publique", key="gen_url_btn"):
                            try:
                                url = get_file_public_url(selected_bucket, file_path)
                                st.code(url, language=None)
                                st.success("URL générée avec succès!")
                            except Exception as e:
                                st.error(f"Erreur : {e}")
    else:
        st.info("👈 Sélectionnez un bucket dans la barre latérale pour explorer les fichiers")

def main():
    st.title("🗃️ Supabase Viewer")
    st.markdown("Visualisez les données de vos tables et fichiers Supabase")
    
    # Création des onglets
    tab1, tab2 = st.tabs(["📊 Tables", "📁 Storage"])
    
    with tab1:
        render_tables_tab()
    
    with tab2:
        render_storage_tab()

if __name__ == "__main__":
    main()

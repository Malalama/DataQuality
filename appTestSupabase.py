"""
Supabase Table Viewer - Streamlit App
Affiche les résultats d'une requête Supabase dans une interface web.
"""

import streamlit as st
from supabase import create_client, Client
import pandas as pd

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

def list_bucket_files(bucket_name: str, folder: str = "") -> pd.DataFrame:
    """
    Liste les fichiers d'un bucket Supabase Storage.
    
    Args:
        bucket_name: Nom du bucket
        folder: Chemin du dossier (vide pour la racine)
    
    Returns:
        DataFrame avec la liste des fichiers
    """
    supabase = get_supabase_client()
    response = supabase.storage.from_(bucket_name).list(folder)
    
    if not response:
        return pd.DataFrame()
    
    # Transformer en DataFrame avec colonnes utiles
    files_data = []
    for item in response:
        files_data.append({
            "name": item.get("name", ""),
            "id": item.get("id", ""),
            "size": item.get("metadata", {}).get("size", 0) if item.get("metadata") else 0,
            "mimetype": item.get("metadata", {}).get("mimetype", "") if item.get("metadata") else "",
            "created_at": item.get("created_at", ""),
            "updated_at": item.get("updated_at", ""),
        })
    
    return pd.DataFrame(files_data)

def list_buckets() -> list:
    """Liste tous les buckets disponibles."""
    supabase = get_supabase_client()
    response = supabase.storage.list_buckets()
    return [bucket.name for bucket in response]

def main():
    st.title("🗃️ Supabase Viewer")
    
    # Création des onglets
    tab1, tab2 = st.tabs(["📊 Tables", "📁 Storage"])
    
    # ===== ONGLET 1: TABLES =====
    with tab1:
        st.markdown("Visualisez les données de vos tables Supabase")
        
        # Sidebar pour les paramètres des tables
        with st.sidebar:
            st.header("⚙️ Paramètres Tables")
            
            table_name = st.text_input(
                "Nom de la table",
                value="users",
                help="Entrez le nom de la table Supabase à interroger"
            )
            
            columns = st.text_input(
                "Colonnes",
                value="*",
                help="Colonnes à sélectionner (* pour toutes)"
            )
            
            limit = st.slider(
                "Limite de lignes",
                min_value=10,
                max_value=1000,
                value=100,
                step=10
            )
            
            query_button = st.button("🔍 Exécuter la requête", type="primary", use_container_width=True)
        
        # Zone principale tables
        if query_button:
            try:
                with st.spinner("Chargement des données..."):
                    df = query_table(table_name, columns, limit)
                
                if df.empty:
                    st.warning("Aucune donnée trouvée dans cette table.")
                else:
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Lignes", len(df))
                    col2.metric("Colonnes", len(df.columns))
                    col3.metric("Table", table_name)
                    
                    st.divider()
                    
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Télécharger en CSV",
                        data=csv,
                        file_name=f"{table_name}_export.csv",
                        mime="text/csv"
                    )
                    
            except Exception as e:
                st.error(f"Erreur lors de la requête : {e}")
        else:
            st.info("👈 Configurez les paramètres dans la barre latérale et cliquez sur 'Exécuter la requête'")
    
    # ===== ONGLET 2: STORAGE =====
    with tab2:
        st.markdown("Visualisez les fichiers de vos buckets Supabase Storage")
        
        try:
            # Récupérer la liste des buckets
            buckets = list_buckets()
            
            if not buckets:
                st.warning("Aucun bucket trouvé.")
            else:
                col1, col2 = st.columns([2, 3])
                
                with col1:
                    selected_bucket = st.selectbox(
                        "Sélectionner un bucket",
                        options=buckets,
                        help="Choisissez le bucket à explorer"
                    )
                
                with col2:
                    folder_path = st.text_input(
                        "Chemin du dossier (optionnel)",
                        value="",
                        help="Laissez vide pour la racine, ou entrez un chemin comme 'images/2024'"
                    )
                
                if st.button("📂 Lister les fichiers", type="primary"):
                    with st.spinner("Chargement des fichiers..."):
                        df_files = list_bucket_files(selected_bucket, folder_path)
                    
                    if df_files.empty:
                        st.warning("Aucun fichier trouvé dans ce bucket/dossier.")
                    else:
                        # Métriques
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Fichiers", len(df_files))
                        col2.metric("Taille totale", f"{df_files['size'].sum() / 1024:.1f} KB")
                        col3.metric("Bucket", selected_bucket)
                        
                        st.divider()
                        
                        # Affichage de la table des fichiers
                        st.dataframe(df_files, use_container_width=True, hide_index=True)
                        
                        # Option de téléchargement de la liste
                        csv = df_files.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Télécharger la liste en CSV",
                            data=csv,
                            file_name=f"{selected_bucket}_files.csv",
                            mime="text/csv"
                        )
                        
        except Exception as e:
            st.error(f"Erreur lors de l'accès au storage : {e}")

if __name__ == "__main__":
    main()

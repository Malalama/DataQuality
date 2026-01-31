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

@st.cache_data(ttl=300)  # Cache pendant 5 minutes
def get_available_tables() -> list[str]:
    """
    Récupère la liste des tables disponibles dans le schéma public.
    
    Returns:
        Liste des noms de tables
    """
    supabase = get_supabase_client()
    
    # Requête pour obtenir les tables du schéma public
    query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """
    
    try:
        # Utilise la fonction RPC pour exécuter une requête SQL brute
        # Note: nécessite une fonction SQL côté Supabase, sinon on utilise une alternative
        response = supabase.rpc('get_public_tables').execute()
        return [row['table_name'] for row in response.data]
    except Exception:
        # Alternative: essayer via PostgREST si la fonction RPC n'existe pas
        # On peut créer une fonction ou utiliser une table système accessible
        try:
            # Tente d'accéder à pg_tables si accessible
            response = supabase.from_('pg_tables').select('tablename').eq('schemaname', 'public').execute()
            return [row['tablename'] for row in response.data]
        except Exception:
            # Fallback: retourne une liste vide ou des tables par défaut
            return []

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

def main():
    st.title("🗃️ Supabase Table Viewer")
    st.markdown("Visualisez les données de vos tables Supabase")
    
    # Récupération des tables disponibles
    available_tables = get_available_tables()
    
    # Sidebar pour les paramètres
    with st.sidebar:
        st.header("⚙️ Paramètres")
        
        # Dropdown pour sélectionner la table
        if available_tables:
            table_name = st.selectbox(
                "Nom de la table",
                options=available_tables,
                help="Sélectionnez la table Supabase à interroger"
            )
        else:
            st.warning("Impossible de récupérer la liste des tables automatiquement.")
            table_name = st.text_input(
                "Nom de la table",
                value="users",
                help="Entrez le nom de la table Supabase à interroger"
            )
        
        # Bouton pour rafraîchir la liste des tables
        if st.button("🔄 Rafraîchir la liste", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()
        
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
                    mime="text/csv"
                )
                
        except Exception as e:
            st.error(f"Erreur lors de la requête : {e}")
    else:
        st.info("👈 Configurez les paramètres dans la barre latérale et cliquez sur 'Exécuter la requête'")

if __name__ == "__main__":
    main()

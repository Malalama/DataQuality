import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
from pathlib import Path
from PIL import Image

# Configuration de la page
st.set_page_config(
    page_title="Matching CV - Fiche de Poste",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1e3a5f;
        text-align: center;
        padding: 1rem 0;
        margin-bottom: 1.5rem;
        border-bottom: 3px solid #3498db;
    }
    .section-header {
        font-size: 1.3rem;
        font-weight: 600;
        color: #2c3e50;
        padding: 0.5rem 0;
        border-bottom: 2px solid #e0e0e0;
        margin-bottom: 1rem;
    }
    .pdf-container {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 10px;
        background-color: #fafafa;
        max-height: 700px;
        overflow-y: auto;
    }
    .stButton > button {
        border-radius: 8px;
        padding: 0.3rem 0.6rem;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# Mapping des noms vers les fichiers CV
CV_FILES_MAPPING = {
    ("Marie", "DUPONT"): "CV_01_Marie_Dupont.pdf",
    ("Sophie", "MARTIN"): "CV_02_Sophie_Martin.pdf",
    ("Thomas", "BERNARD"): "CV_03_Thomas_Bernard.pdf",
    ("Alexandre", "PETIT"): "CV_04_Alexandre_Petit.pdf",
    ("Claire", "LEROY"): "CV_05_Claire_Leroy.pdf",
    ("Emma", "GARCIA"): "CV_06_Emma_Garcia.pdf",
    ("Jean-Pierre", "MULLER"): "CV_07_Jean_Pierre_Muller.pdf",
}

# Chemin des fichiers
DATA_PATH = Path(r"C:\Users\corte\Downloads\data")
FICHE_POSTE = DATA_PATH / "DIG - URO - Fiche de poste IDE Annonce.pdf"
CV_PARSED_FILE = DATA_PATH / "CV_Parsed.xlsx"
MATCHING_FILE = DATA_PATH / "Compatibilité_CV_et_Fiche_de_poste.xlsx"
LOGO_FILE = DATA_PATH / "Logo_CHRU_Nancy.png"


def get_score_color(score):
    """Retourne la couleur selon le score"""
    if score >= 85:
        return "#27ae60"  # Vert
    elif score >= 75:
        return "#f1c40f"  # Jaune
    elif score >= 60:
        return "#e67e22"  # Orange
    elif score >= 40:
        return "#e74c3c"  # Rouge
    else:
        return "#c0392b"  # Rouge foncé


def get_score_bg_color(score):
    """Retourne la couleur de fond selon le score (version claire)"""
    if score >= 85:
        return "#d4edda"  # Vert clair
    elif score >= 75:
        return "#fff3cd"  # Jaune clair
    elif score >= 60:
        return "#ffeaa7"  # Orange clair
    elif score >= 40:
        return "#f8d7da"  # Rouge clair
    else:
        return "#f5c6cb"  # Rouge foncé clair


def pdf_to_images(pdf_path):
    """Convertit un PDF en liste d'images"""
    images = []
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            mat = fitz.Matrix(1.5, 1.5)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
        doc.close()
    except Exception as e:
        st.error(f"Erreur lors de la lecture du PDF: {e}")
    return images


def display_pdf(pdf_path, container_key="pdf"):
    """Affiche un PDF dans Streamlit"""
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        st.warning(f"Fichier non trouvé: {pdf_path}")
        st.info(f"Vérifiez que le fichier existe dans: {DATA_PATH}")
        return
    
    images = pdf_to_images(pdf_path)
    if images:
        for i, img in enumerate(images):
            st.image(img, use_container_width=True, caption=f"Page {i+1}/{len(images)}")


@st.cache_data
def load_matching_results():
    """Charge les résultats de matching depuis le fichier Excel"""
    if MATCHING_FILE.exists():
        df = pd.read_excel(MATCHING_FILE)
        return df
    return None


@st.cache_data
def load_parsed_cvs():
    """Charge les CVs parsés depuis le fichier Excel"""
    if CV_PARSED_FILE.exists():
        df = pd.read_excel(CV_PARSED_FILE)
        # Ajouter le 0 devant les numéros de téléphone
        if 'telephone' in df.columns:
            df['telephone'] = df['telephone'].apply(lambda x: f"0{int(x)}" if pd.notna(x) else x)
        return df
    return None


def get_cv_file(prenom, nom):
    """Retourne le nom du fichier CV pour un candidat"""
    return CV_FILES_MAPPING.get((prenom, nom), None)


def style_score(val):
    """Style pour les colonnes de score"""
    try:
        score = float(val)
        color = get_score_color(score)
        return f'background-color: {color}; color: white; font-weight: bold; text-align: center;'
    except:
        return ''


def view_matching():
    """Vue principale de matching"""
    # Vérification du dossier data
    if not DATA_PATH.exists():
        st.error(f"❌ Dossier non trouvé: `{DATA_PATH}`")
        st.info("Créez ce dossier et placez-y les fichiers PDF.")
        return
    
    # Charger les données de matching
    df_matching = load_matching_results()
    
    if df_matching is None:
        st.error(f"❌ Fichier non trouvé: `{MATCHING_FILE}`")
        st.info("Placez le fichier Compatibilité_CV_et_Fiche_de_poste.xlsx dans le dossier data.")
        return
    
    # Initialisation du state
    if 'selected_candidate' not in st.session_state:
        st.session_state.selected_candidate = None
    if 'col_ratio' not in st.session_state:
        st.session_state.col_ratio = 65
    
    # Slider pour ajuster la largeur des colonnes
    col_ratio = st.slider("📐 Ajuster la largeur (Résultats ↔ CV)", 30, 85, st.session_state.col_ratio, key="col_slider")
    st.session_state.col_ratio = col_ratio
    
    # Layout principal en 2 colonnes avec ratio ajustable
    col_left, col_cv = st.columns([col_ratio, 100 - col_ratio])
    
    with col_left:
        # Section Fiche de poste (collapsible)
        with st.expander("📄 Voir la Fiche de Poste", expanded=False):
            if FICHE_POSTE.exists():
                display_pdf(FICHE_POSTE, "fiche_poste")
            else:
                st.info("📄 **Poste:** Infirmier(e) d'Annonce en Urologie")
                st.info("🏥 **Structure:** CHRU Nancy - Pôle Digestif")
        
        st.markdown('<div class="section-header">📊 Résultats du Matching</div>', unsafe_allow_html=True)
        
        # Filtres
        col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
        
        with col_f1:
            models = ['Tous'] + sorted(df_matching['Model'].unique().tolist())
            model_filter = st.selectbox("🤖 Modèle", models)
        
        with col_f2:
            sort_options = {
                'Score global ↓': ('Score global', False),
                'Score global ↑': ('Score global', True),
                'Nom ↓': ('Nom', False),
                'Nom ↑': ('Nom', True),
                'Prénom ↓': ('Prénom', False),
                'Prénom ↑': ('Prénom', True),
                'Modèle': ('Model', False),
                'Compétences tech. ↓': ('Compétences techniques', False),
                'Expérience ↓': ('Expérience', False),
                'Soft skills ↓': ('Soft skills', False),
            }
            sort_choice = st.selectbox("🔀 Trier par", list(sort_options.keys()))
        
        with col_f3:
            # Colonnes à afficher
            all_score_cols = ['Score global', 'Compétences techniques', 'Contexte métier', 
                            'Disponibilité', 'Expérience', 'Formation et certifications', 'Soft skills']
            score_col_labels = {
                'Score global': 'Score global (/100)',
                'Compétences techniques': 'Compétences techniques (/30)',
                'Contexte métier': 'Contexte métier (/10)',
                'Disponibilité': 'Disponibilité (/5)',
                'Expérience': 'Expérience (/25)',
                'Formation et certifications': 'Formation et certifications (/15)',
                'Soft skills': 'Soft skills (/15)'
            }
            default_cols = ['Score global', 'Compétences techniques', 'Expérience', 'Soft skills']
            selected_score_cols = st.multiselect("📊 Scores à afficher", all_score_cols, default=default_cols)
        
        # Appliquer les filtres
        df_filtered = df_matching.copy()
        
        if model_filter != 'Tous':
            df_filtered = df_filtered[df_filtered['Model'] == model_filter]
        
        # Appliquer le tri
        sort_col, sort_asc = sort_options[sort_choice]
        df_filtered = df_filtered.sort_values(by=sort_col, ascending=sort_asc)
        
        st.markdown(f"**{len(df_filtered)} résultat(s)**")
        
        st.markdown("---")
        
        # En-tête (sans Compatibilité)
        header_cols = st.columns([1.5, 1, 1] + [1]*len(selected_score_cols) + [0.5])
        header_labels = ['Modèle', 'Prénom', 'Nom'] + [score_col_labels.get(c, c) for c in selected_score_cols] + ['CV']
        for col, header in zip(header_cols, header_labels):
            col.markdown(f"**{header}**")
        
        st.markdown("---")
        
        # Lignes du tableau (sans Compatibilité)
        for idx, row in df_filtered.iterrows():
            row_cols = st.columns([1.5, 1, 1] + [1]*len(selected_score_cols) + [0.5])
            
            # Modèle
            row_cols[0].write(row['Model'])
            
            # Prénom
            row_cols[1].write(row['Prénom'])
            
            # Nom
            row_cols[2].write(row['Nom'])
            
            # Scores avec couleurs
            for i, score_col in enumerate(selected_score_cols):
                score_val = row[score_col]
                
                # Normaliser pour la couleur
                if score_col == 'Score global':
                    normalized = score_val
                else:
                    max_scores = {
                        'Compétences techniques': 30,
                        'Contexte métier': 10,
                        'Disponibilité': 5,
                        'Expérience': 25,
                        'Formation et certifications': 15,
                        'Soft skills': 15
                    }
                    max_val = max_scores.get(score_col, 100)
                    normalized = (score_val / max_val) * 100
                
                color = get_score_color(normalized)
                row_cols[3 + i].markdown(
                    f'<span style="background-color: {color}; color: white; padding: 3px 8px; '
                    f'border-radius: 10px; font-weight: bold;">{int(score_val)}</span>',
                    unsafe_allow_html=True
                )
            
            # Bouton CV
            cv_file = get_cv_file(row['Prénom'], row['Nom'])
            if cv_file:
                if row_cols[-1].button("👁️", key=f"btn_{idx}_{row['Model']}", help=f"Voir CV de {row['Prénom']} {row['Nom']}"):
                    # Récupérer les scores de tous les modèles pour ce candidat
                    candidate_all_models = df_matching[
                        (df_matching['Prénom'] == row['Prénom']) & 
                        (df_matching['Nom'] == row['Nom'])
                    ]
                    
                    # Filtrer selon le filtre de modèle actif
                    if model_filter != 'Tous':
                        candidate_all_models = candidate_all_models[candidate_all_models['Model'] == model_filter]
                    
                    model_scores = {}
                    for _, m_row in candidate_all_models.iterrows():
                        model_scores[m_row['Model']] = {
                            'score': m_row['Score global'],
                            'details': {col: m_row[col] for col in all_score_cols}
                        }
                    
                    st.session_state.selected_candidate = {
                        'prenom': row['Prénom'],
                        'nom': row['Nom'],
                        'cv_file': cv_file,
                        'model_scores': model_scores
                    }
                    st.rerun()
    
    # Colonne droite: Affichage du CV
    with col_cv:
        st.markdown('<div class="section-header">👤 CV du Candidat</div>', unsafe_allow_html=True)
        
        if st.session_state.selected_candidate is not None:
            candidate = st.session_state.selected_candidate
            cv_path = DATA_PATH / candidate['cv_file']
            model_scores = candidate.get('model_scores', {})
            
            # Header du candidat avec scores par modèle
            st.markdown(f"""
            <div style="
                background: #f8f9fa;
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 15px;
            ">
                <h3 style="margin: 0; color: #2c3e50;">
                    {candidate['prenom']} {candidate['nom']}
                </h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Afficher les scores pour chaque modèle
            for model_name, model_data in model_scores.items():
                score = model_data['score']
                color = get_score_color(score)
                st.markdown(f"""
                <div style="
                    background-color: {color};
                    color: white;
                    padding: 8px 12px;
                    border-radius: 8px;
                    margin-bottom: 8px;
                    display: inline-block;
                    margin-right: 10px;
                ">
                    <strong>{model_name}</strong>: {int(score)}/100
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("")  # Espacement
            
            # Charger les données parsées du candidat
            df_parsed = load_parsed_cvs()
            candidat_data = None
            if df_parsed is not None:
                candidat_match = df_parsed[
                    (df_parsed['prenom'] == candidate['prenom']) & 
                    (df_parsed['nom'] == candidate['nom'])
                ]
                if len(candidat_match) > 0:
                    candidat_data = candidat_match.iloc[0]
            
            # Bloc 1: Informations générales
            if candidat_data is not None:
                with st.expander("👤 Informations générales", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Nom:** {candidat_data['prenom']} {candidat_data['nom']}")
                        st.write(f"**Ville:** {candidat_data.get('ville', 'N/A')}")
                        st.write(f"**Email:** {candidat_data.get('email', 'N/A')}")
                        st.write(f"**Téléphone:** {candidat_data.get('telephone', 'N/A')}")
                    with col2:
                        st.write(f"**Années d'expérience:** {candidat_data.get('annees_experience', 'N/A')}")
                        st.write(f"**Diplôme IDE:** {candidat_data.get('diplome_ide_annee', 'N/A')}")
                        st.write(f"**Disponibilité:** {candidat_data.get('disponibilite', 'N/A')}")
            
            # Bloc 2: Expériences spécifiques
            if candidat_data is not None:
                with st.expander("🏥 Expériences spécifiques", expanded=False):
                    st.write(f"**Exp. Oncologie:** {candidat_data.get('experience_oncologie_annees', 'N/A')} ans")
                    if pd.notna(candidat_data.get('experience_oncologie_details')):
                        st.write(f"↳ {candidat_data['experience_oncologie_details']}")
                    
                    st.write(f"**Exp. Urologie:** {candidat_data.get('experience_urologie_annees', 'N/A')} ans")
                    if pd.notna(candidat_data.get('experience_urologie_details')):
                        st.write(f"↳ {candidat_data['experience_urologie_details']}")
                    
                    st.write(f"**Dispositif d'annonce:** {'Oui' if candidat_data.get('experience_dispositif_annonce') else 'Non'}")
                    if pd.notna(candidat_data.get('experience_dispositif_annonce_details')):
                        st.write(f"↳ {candidat_data['experience_dispositif_annonce_details']}")
            
            # Bloc 3: Compétences et Points Forts
            if candidat_data is not None:
                with st.expander("💪 Compétences et Points Forts", expanded=False):
                    if pd.notna(candidat_data.get('principales_competences_techniques')):
                        st.write(f"**Compétences techniques:** {candidat_data['principales_competences_techniques']}")
                    
                    if pd.notna(candidat_data.get('competences_relationnelles')):
                        st.write(f"**Compétences relationnelles:** {candidat_data['competences_relationnelles']}")
                    
                    if pd.notna(candidat_data.get('points_forts_pour_poste_annonce')):
                        st.success(f"**Points forts:** {candidat_data['points_forts_pour_poste_annonce']}")
                    
                    if pd.notna(candidat_data.get('points_vigilance')):
                        st.warning(f"**Points de vigilance:** {candidat_data['points_vigilance']}")
            
            # Détail des scores avec couleurs (pour chaque modèle)
            for model_name, model_data in model_scores.items():
                with st.expander(f"📊 Détail des scores - {model_name}", expanded=len(model_scores) == 1):
                    details = model_data['details']
                    max_scores = {
                        'Score global': 100,
                        'Compétences techniques': 30,
                        'Contexte métier': 10,
                        'Disponibilité': 5,
                        'Expérience': 25,
                        'Formation et certifications': 15,
                        'Soft skills': 15
                    }
                    for score_name, score_val in details.items():
                        max_val = max_scores.get(score_name, 100)
                        pct = (score_val / max_val) * 100
                        color = get_score_color(pct)
                        
                        st.markdown(f"**{score_name}:** {int(score_val)}/{max_val}")
                        st.markdown(
                            f'<div style="background-color: #e0e0e0; border-radius: 10px; height: 20px; width: 100%;">'
                            f'<div style="background-color: {color}; width: {pct}%; height: 100%; border-radius: 10px;"></div>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                        st.markdown("")  # Espacement
            
            # Affichage du CV
            with st.expander("📄 CV complet", expanded=False):
                display_pdf(cv_path, f"cv_{candidate['prenom']}_{candidate['nom']}")
        else:
            st.info("👈 Cliquez sur 👁️ pour afficher un CV")
            
            # Stats rapides
            if df_matching is not None:
                st.markdown("### 📈 Statistiques")
                
                # Par modèle
                for model in df_matching['Model'].unique():
                    df_model = df_matching[df_matching['Model'] == model]
                    avg_score = df_model['Score global'].mean()
                    st.metric(f"Score moyen ({model})", f"{avg_score:.1f}")


def view_parsed_cvs():
    """Vue des CVs parsés avec filtres"""
    st.markdown('<div class="section-header">📑 Données Extraites des CVs</div>', unsafe_allow_html=True)
    
    df = load_parsed_cvs()
    
    if df is None:
        st.error(f"❌ Fichier non trouvé: `{CV_PARSED_FILE}`")
        st.info("Placez le fichier CV_Parsed.xlsx dans le dossier data.")
        return
    
    # Colonnes principales
    colonnes_principales = [
        'prenom', 'nom', 'ville', 'annees_experience', 
        'diplome_ide_annee', 'experience_oncologie_annees',
        'experience_urologie_annees', 'experience_dispositif_annonce',
        'disponibilite', 'email', 'telephone'
    ]
    
    # Filtres
    st.markdown("### 🔍 Filtres")
    
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    
    with col_f1:
        villes = ['Toutes'] + sorted(df['ville'].dropna().unique().tolist())
        ville_filter = st.selectbox("Ville", villes)
    
    with col_f2:
        exp_min = st.number_input("Exp. minimum (années)", min_value=0, max_value=50, value=0)
    
    with col_f3:
        onco_filter = st.checkbox("Expérience oncologie", value=False)
    
    with col_f4:
        annonce_filter = st.checkbox("Expérience dispositif annonce", value=False)
    
    # Appliquer les filtres
    df_filtered = df.copy()
    
    if ville_filter != 'Toutes':
        df_filtered = df_filtered[df_filtered['ville'] == ville_filter]
    
    if exp_min > 0:
        df_filtered = df_filtered[df_filtered['annees_experience'] >= exp_min]
    
    if onco_filter:
        df_filtered = df_filtered[df_filtered['experience_oncologie_annees'].notna() & (df_filtered['experience_oncologie_annees'] > 0)]
    
    if annonce_filter:
        df_filtered = df_filtered[df_filtered['experience_dispositif_annonce'] == True]
    
    st.markdown(f"**{len(df_filtered)} candidat(s) trouvé(s)**")
    
    st.markdown("---")
    
    # Sélection des colonnes à afficher
    st.markdown("### 📋 Tableau des candidats")
    
    all_cols = df.columns.tolist()
    cols_to_remove = ['PromptID', 'Model', 'id_candidat']
    available_cols = [c for c in all_cols if c not in cols_to_remove]
    
    default_cols = [c for c in colonnes_principales if c in available_cols]
    selected_cols = st.multiselect(
        "Colonnes à afficher",
        available_cols,
        default=default_cols
    )
    
    if selected_cols:
        column_labels = {
            'prenom': 'Prénom',
            'nom': 'Nom',
            'ville': 'Ville',
            'annees_experience': 'Années Exp.',
            'diplome_ide_annee': 'Diplôme IDE',
            'experience_oncologie_annees': 'Exp. Onco (ans)',
            'experience_urologie_annees': 'Exp. Uro (ans)',
            'experience_dispositif_annonce': 'Disp. Annonce',
            'disponibilite': 'Disponibilité',
            'email': 'Email',
            'telephone': 'Téléphone',
            'experience_oncologie_details': 'Détails Onco',
            'experience_urologie_details': 'Détails Uro',
            'formations_complementaires': 'Formations',
            'principales_competences_techniques': 'Compétences Tech.',
            'competences_relationnelles': 'Comp. Relationnelles',
            'competences_coordination': 'Comp. Coordination',
            'points_forts_pour_poste_annonce': 'Points Forts',
            'points_vigilance': 'Points Vigilance',
            'experience_dispositif_annonce_details': 'Détails Disp. Annonce',
            'date_naissance': 'Date Naissance',
            'adresse': 'Adresse',
            'code_postal': 'Code Postal',
            'langues': 'Langues',
            'lettre_motivation_presente': 'Lettre Motiv.',
            'experience_etp_booleen': 'Exp. ETP',
            'experience_etp_formation_40h': 'Formation ETP 40h',
            'experience_soins_palliatifs_annees': 'Exp. Soins Palliatifs',
            'experience_soins_palliatifs_details': 'Détails Soins Palliatifs'
        }
        
        df_display = df_filtered[selected_cols].copy()
        df_display.columns = [column_labels.get(c, c) for c in selected_cols]
        
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        csv = df_filtered[selected_cols].to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 Télécharger en CSV",
            data=csv,
            file_name="candidats_filtres.csv",
            mime="text/csv"
        )
    else:
        st.warning("Sélectionnez au moins une colonne à afficher")
    
    # Section détails candidat
    st.markdown("---")
    st.markdown("### 🔎 Détails d'un candidat")
    
    candidat_options = df_filtered.apply(lambda x: f"{x['prenom']} {x['nom']}", axis=1).tolist()
    
    if candidat_options:
        selected_candidat = st.selectbox("Sélectionner un candidat", candidat_options)
        
        if selected_candidat:
            parts = selected_candidat.split(' ', 1)
            candidat_data = df_filtered[
                (df_filtered['prenom'] == parts[0]) & 
                (df_filtered['nom'] == parts[1])
            ].iloc[0]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 👤 Informations générales")
                st.write(f"**Nom:** {candidat_data['prenom']} {candidat_data['nom']}")
                st.write(f"**Ville:** {candidat_data.get('ville', 'N/A')}")
                st.write(f"**Email:** {candidat_data.get('email', 'N/A')}")
                st.write(f"**Téléphone:** {candidat_data.get('telephone', 'N/A')}")
                st.write(f"**Années d'expérience:** {candidat_data.get('annees_experience', 'N/A')}")
                st.write(f"**Diplôme IDE:** {candidat_data.get('diplome_ide_annee', 'N/A')}")
                st.write(f"**Disponibilité:** {candidat_data.get('disponibilite', 'N/A')}")
            
            with col2:
                st.markdown("#### 🏥 Expériences spécifiques")
                st.write(f"**Exp. Oncologie:** {candidat_data.get('experience_oncologie_annees', 'N/A')} ans")
                if pd.notna(candidat_data.get('experience_oncologie_details')):
                    st.write(f"↳ {candidat_data['experience_oncologie_details']}")
                
                st.write(f"**Exp. Urologie:** {candidat_data.get('experience_urologie_annees', 'N/A')} ans")
                if pd.notna(candidat_data.get('experience_urologie_details')):
                    st.write(f"↳ {candidat_data['experience_urologie_details']}")
                
                st.write(f"**Dispositif d'annonce:** {'Oui' if candidat_data.get('experience_dispositif_annonce') else 'Non'}")
                if pd.notna(candidat_data.get('experience_dispositif_annonce_details')):
                    st.write(f"↳ {candidat_data['experience_dispositif_annonce_details']}")
            
            st.markdown("#### 💪 Compétences et Points Forts")
            
            if pd.notna(candidat_data.get('principales_competences_techniques')):
                st.write(f"**Compétences techniques:** {candidat_data['principales_competences_techniques']}")
            
            if pd.notna(candidat_data.get('competences_relationnelles')):
                st.write(f"**Compétences relationnelles:** {candidat_data['competences_relationnelles']}")
            
            if pd.notna(candidat_data.get('points_forts_pour_poste_annonce')):
                st.success(f"**Points forts:** {candidat_data['points_forts_pour_poste_annonce']}")
            
            if pd.notna(candidat_data.get('points_vigilance')):
                st.warning(f"**Points de vigilance:** {candidat_data['points_vigilance']}")
    else:
        st.info("Aucun candidat ne correspond aux filtres sélectionnés")


def main():
    # Header avec logo
    col_logo, col_title = st.columns([1, 4])
    
    with col_logo:
        if LOGO_FILE.exists():
            st.image(str(LOGO_FILE), width=200)
    
    with col_title:
        st.markdown('<div class="main-header">📋 Matching CV - Fiche de Poste IDE Annonce Urologie</div>', unsafe_allow_html=True)
    
    # Onglets
    tab1, tab2 = st.tabs(["🎯 Matching", "📑 CVs Parsés"])
    
    with tab1:
        view_matching()
    
    with tab2:
        view_parsed_cvs()


if __name__ == "__main__":
    main()

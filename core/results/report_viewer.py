import streamlit as st
import json
import os
from pathlib import Path
from datetime import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Attack Tracing Dashboard",
    page_icon="🛡️",
    layout="wide"
)

# --- CSS POUR LE SCROLL ET LE STYLE ---
# Ce bloc force les containers à avoir une taille fixe avec scrollbar
st.markdown("""
    <style>
    [data-testid="stVerticalBlockBorderWrapper"] > div:nth-child(2) {
        max-height: 600px;
        overflow-y: auto;
        padding-right: 10px;
    }
    .main-header {
        font-size: 24px;
        font-weight: bold;
        color: #f0f2f6;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

def load_json_report(file_path):
    """Charge le fichier JSON en toute sécurité."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Erreur lors de la lecture de {file_path} : {e}")
        return None

def display_report_header(data):
    """Affiche les métriques principales du rapport."""
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Framework", data.get("framework", "Inconnu").upper())
    with col2:
        st.metric("Attaque", data.get("attack_name", "N/A"))
    with col3:
        target = data.get("target_url", "N/A")
        st.write(f"**Cible:**")
        st.code(target)

def render_garak_style(prompts):
    """Affiche les résultats format Garak (liste plate)."""
    for idx, p in enumerate(prompts):
        is_passed = p.get("passed", False)
        label = "✅ PASS" if is_passed else "❌ FAIL"
        state = "complete" if is_passed else "error"
        
        with st.status(f"{label} | Prompt #{idx+1} - Score: {p.get('score', 'N/A')}", state=state):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Prompt envoyé :**")
                st.info(p.get("prompt", "Vide"))
            with c2:
                st.markdown("**Réponse reçue :**")
                st.warning(p.get("response", "Pas de réponse"))
            
            if p.get("rationale"):
                st.markdown(f"**Raisonnement (Rationale) :**\n> {p.get('rationale')}")
            if p.get("detector"):
                st.caption(f"Détecteur utilisé : {p.get('detector')}")

def render_pyrit_style(conversation):
    """Affiche les résultats format PyRIT (conversationnelle)."""
    st.info(f"🎯 **Objectif :** {conversation.get('objective')}")
    
    for turn in conversation.get("turns", []):
        # On alterne le look selon le tour
        avatar = "user" if turn.get("turn") % 2 != 0 else "assistant"
        with st.chat_message(avatar):
            st.write(f"**Tour {turn.get('turn')}**")
            st.markdown(f"**Prompt:** {turn.get('prompt')}")
            st.markdown(f"**Réponse:** {turn.get('response')}")
            if turn.get("rationale"):
                st.caption(f"Verdict Évaluation : {turn.get('rationale')}")

def main():
    st.title("🛡️ Dashboard de suivi d'attaques")
    
    # Définition du dossier
    reports_path = Path("reports")
    
    if not reports_path.exists():
        st.error(f"Le dossier `{reports_path.absolute()}` n'existe pas.")
        return

    # Liste des fichiers .json
    files = sorted([f for f in os.listdir(reports_path) if f.endswith(".json")], reverse=True)

    if not files:
        st.info("Aucun rapport trouvé dans le dossier `/reports`.")
        return

    # Parcours des fichiers
    for filename in files:
        data = load_json_report(reports_path / filename)
        if not data:
            continue

        with st.expander(f"📄 Attack : {filename}", expanded=True):
            display_report_header(data)
            
            st.write("---")
            st.subheader("Détails des échanges")
            
            # Container avec bordure pour le scroll
            with st.container(border=True):
                if data.get("prompts"):
                    render_garak_style(data["prompts"])
                elif data.get("conversation"):
                    render_pyrit_style(data["conversation"])
                else:
                    st.warning("Format de données non reconnu (ni prompts, ni conversation).")

if __name__ == "__main__":
    main()
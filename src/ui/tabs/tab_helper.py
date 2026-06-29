"""
Helper functions para padrão comum de abas.
"""

import streamlit as st
from typing import List, Callable, Optional
from src.state import PIPELINE, is_step_completed

def render_tab_checklist(stage: str):
    """
    Renderiza um checklist horizontal simples e elegante.

    etapas: lista de nomes das etapas
    concluido_ate: quantidade de etapas concluídas
    """
        
    #retornar a quantidade de step em um stage
    nr_steps = len(PIPELINE[stage]["steps"])
    cols = st.columns(nr_steps)

    for i, step_key in enumerate(PIPELINE[stage]["steps"]):
        step_name = PIPELINE[stage]["steps"][step_key]["name"]
        done = is_step_completed(step_key)
        #print(f"step_key: {step_key}")
        with cols[i]:
            if done:
                status_icon = str("✅")
                st.success(f"Step {step_key}:\t\t{step_name}\n\nStatus:\t\t{status_icon}")
                #st.success(f"✓ {step_name}")
            else:
                status_icon = str("⏳")
                st.info(f"Step {step_key}:\t\t{step_name}\n\nStatus:\t\t{status_icon}")
                #st.info(f"○ {step_name}")

def render_result_cards(cards: List[dict]):
    """
    Renderiza cards de resultado resumido.
    
    Args:
        cards: Lista de dicionários com keys: label, value, delta (opcional)
    """
    if cards:
        st.subheader("Resumo:")
        cols = st.columns(len(cards))
        for i, card in enumerate(cards):
            with cols[i]:
                if 'delta' in card:
                    st.metric(card['label'], card['value'], card['delta'])
                else:
                    st.metric(card['label'], card['value'])
        st.divider()


def render_main_result(content: str, language: str = "text"):
    """
    Renderiza o bloco principal de resultado.
    
    Args:
        content: Conteúdo a ser exibido
        language: Linguagem para highlight (text, json, python, etc.)
    """
    st.subheader("Resultado:")
    st.code(content, language=language)
    st.divider()


def render_technical_details(content: str, label: str = "Detalhes técnicos"):
    """
    Renderiza detalhes técnicos em expander.
    
    Args:
        content: Conteúdo dos detalhes
        label: Rótulo do expander
    """
    with st.expander(label):
        st.code(content, language="text")


def render_next_step_button(label: str = "Próxima etapa", callback: Optional[Callable] = None):
    """
    Renderiza botão de próxima etapa.
    
    Args:
        label: Texto do botão
        callback: Função a ser executada ao clicar
    """
    if st.button(label):
        if callback:
            callback()
        return True
    return False



#def render_tab_header(titulo: str, descricao: str):
#    """
#    Renderiza o cabeçalho padrão de uma aba.
#    
#    Args:
#        titulo: Título da etapa
#        descricao: Descrição curta do objetivo
#    """
#    st.header(titulo)
#    st.caption(descricao)
#    st.divider()
#
#
#def render_micro_checklist(checklist_items: List[tuple]) -> dict:
#    """
#    Renderiza o checklist micro da etapa.
#    
#    Args:
#        checklist_items: Lista de tuplas (label, status_bool)
#        
#    Returns:
#        Dicionário com o estado de cada item
#    """
#    st.subheader("Checklist da etapa:")
#    
#    estado = {}
#    for label, status in checklist_items:
#        if status:
#            st.success(f"✓ {label}")
#        else:
#            st.caption(f"○ {label}")
#        estado[label] = status
#    
#    st.divider()
#    return estado
"""RSVP do Chá de Fraldas da Clara Sophie (Streamlit).

Persistência: Google Sheets (produção) ou CSV local (desenvolvimento).
Segredos: sempre em st.secrets, nunca no código.
"""
from __future__ import annotations

import csv
import hmac
import html
import inspect
import random
import re
import threading
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# -----------------------------------------------------------------------------
# CONFIGURAÇÕES E CONSTANTES
# -----------------------------------------------------------------------------
CSV_FILE_PATH = Path("confirmacoes.csv")  # só usado se o Google Sheets não estiver configurado
COLUNAS = ["Data", "Nome", "Presenca", "Acompanhantes", "Fralda", "Mensagem", "MostrarMensagem"]

FUSO_MANAUS = timezone(timedelta(hours=-4))  # Manaus não tem horário de verão

EVENTO_TITULO = "Chá de Fraldas da Clara Sophie"
EVENTO_INICIO_ISO = "2026-11-21T19:00:00-04:00"
EVENTO_INICIO_UTC = "20261121T230000Z"
EVENTO_FIM_UTC = "20261122T020000Z"  # término estimado: 22:00 (Manaus)
EVENTO_LOCAL = "Professora Emília Cavalcante, 84 - Santo Agostinho, Manaus - AM"

PRESENCA_OPCOES = {
    "Sim, com certeza! 🥰": "Sim",
    "Infelizmente não poderei ir 💔": "Não",
}
FRALDA_OPCOES = ["Prefiro surpreender", "Fraldas P", "Fraldas M", "Fraldas G", "Outro mimo"]

MAX_ACOMPANHANTES = 10
MAX_ENVIOS_POR_SESSAO = 3
INTERVALO_ENTRE_ENVIOS_S = 5
MAX_TENTATIVAS_ADMIN = 5

_TRAVA_ESCRITA = threading.Lock()

st.set_page_config(
    page_title="Chá de Fraldas - Clara Sophie",
    page_icon="🐑",
    layout="centered",
)


# -----------------------------------------------------------------------------
# SEGREDOS
# -----------------------------------------------------------------------------
def largura(funcao) -> dict:
    """Streamlit novo usa width="stretch"; o antigo usa use_container_width=True."""
    parametros = inspect.signature(funcao).parameters
    if "width" in parametros:
        return {"width": "stretch"}
    return {"use_container_width": True}


def get_secret(chave: str, padrao=None):
    """Lê um segredo sem quebrar se o arquivo/chave não existir."""
    try:
        return st.secrets[chave]
    except Exception:
        return padrao


# -----------------------------------------------------------------------------
# ESTILO (CSS)
# -----------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Great+Vibes&display=swap');

/* Fundo xadrez bege, igual ao convite */
html {
    background-color: #fbf7ef;
    background-image:
        linear-gradient(90deg, rgba(196,170,135,.26) 50%, transparent 50%),
        linear-gradient(rgba(196,170,135,.26) 50%, transparent 50%);
    background-size: 56px 56px;
    background-attachment: fixed;
}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stMain"] {
    background: transparent !important;
    font-family: 'Georgia', serif;
}

/* Nuvens passando ao fundo */
.nuvem {
    position: fixed; z-index: -1; pointer-events: none;
    background: #fff; border-radius: 100px; opacity: .9;
    box-shadow: 0 6px 18px rgba(160,130,100,.12);
    left: -260px;
    animation: derivar linear infinite;
}
.nuvem::before, .nuvem::after { content: ""; position: absolute; background: #fff; border-radius: 50%; }
.nuvem.n1 { width: 150px; height: 48px; top: 6%;  animation-duration: 70s; animation-delay: -20s; }
.nuvem.n1::before { width: 62px; height: 62px; top: -32px; left: 22px; }
.nuvem.n1::after  { width: 84px; height: 84px; top: -44px; left: 64px; }
.nuvem.n2 { width: 110px; height: 36px; top: 38%; animation-duration: 95s; animation-delay: -60s; opacity: .75; }
.nuvem.n2::before { width: 46px; height: 46px; top: -24px; left: 16px; }
.nuvem.n2::after  { width: 62px; height: 62px; top: -32px; left: 46px; }
.nuvem.n3 { width: 180px; height: 56px; top: 72%; animation-duration: 120s; animation-delay: -35s; opacity: .8; }
.nuvem.n3::before { width: 74px; height: 74px; top: -38px; left: 26px; }
.nuvem.n3::after  { width: 100px; height: 100px; top: -52px; left: 78px; }
@keyframes derivar { to { transform: translateX(calc(100vw + 520px)); } }

/* Cartão do cabeçalho */
.card-container {
    background-color: rgba(247,241,229,.96);
    border: 2px solid #d0bc9f;
    border-radius: 24px;
    padding: 18px 24px 28px;
    box-shadow: 0 6px 20px rgba(92,61,46,.08);
    text-align: center;
    margin-bottom: 18px;
    animation: entrar .9s ease both;
}
@keyframes entrar { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }

.ovelha { width: 150px; height: auto; margin: 0 auto; display: block; animation: flutuar 4s ease-in-out infinite; }
@keyframes flutuar { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
.olho { transform-box: fill-box; transform-origin: center; animation: piscar 5s infinite; }
@keyframes piscar { 0%,92%,100% { transform: scaleY(1); } 95% { transform: scaleY(.1); } }

.titulo-script {
    font-family: 'Great Vibes', 'Brush Script MT', cursive !important;
    color: #6b3f22 !important; font-weight: 400 !important;
    line-height: 1.05 !important; margin: 0 !important; padding: 0 !important;
}
.card-container .titulo-script.grande { font-size: 3.4rem !important; }
.card-container .titulo-script.nome { font-size: 3.8rem !important; margin-top: 2px !important; }
.card-container .subtitle { color: #7a5843; font-size: 1.05rem; margin: 6px 0 0; }
.titulo-secao {
    font-family: 'Great Vibes', 'Brush Script MT', cursive !important;
    color: #6b3f22 !important; font-size: 2.3rem !important; font-weight: 400 !important;
    text-align: center; margin: 24px 0 8px !important; padding: 0 !important;
}

/* Caixa com detalhes do evento */
.info-box {
    background-color: rgba(247,241,229,.96);
    border: 1px solid #e2d7c5;
    border-radius: 18px;
    padding: 18px 22px;
    margin: 14px 0;
    color: #5c3d2e;
}
.info-box p { margin: 8px 0; font-size: 1rem; line-height: 1.5; }

/* Formulário */
[data-testid="stForm"] {
    background: rgba(255,255,255,.94);
    border: 2px solid #d0bc9f;
    border-radius: 20px;
    padding: 22px;
}
[data-testid^="stBaseButton"] { border-radius: 25px !important; font-weight: bold !important; }
[data-testid="stBaseButton-primaryFormSubmit"], [data-testid="stBaseButton-primary"] {
    background-color: #a67c52 !important; border: none !important; color: #fff !important;
}
[data-testid="stBaseButton-primaryFormSubmit"]:hover, [data-testid="stBaseButton-primary"]:hover {
    background-color: #8c643e !important;
}

/* Mural de recados */
.recado {
    background: rgba(255,255,255,.95);
    border: 1px solid #e2d7c5; border-left: 5px solid #e8b4b8;
    border-radius: 14px; padding: 12px 16px; margin: 10px 0; color: #5c3d2e;
}
.recado b { color: #8c643e; }

/* Chuva de ovelhinhas e corações ao confirmar */
.chuva { position: fixed; top: -50px; z-index: 9999; pointer-events: none; opacity: 0; animation: cair linear forwards; }
@keyframes cair {
    0%   { transform: translateY(0) rotate(0deg); opacity: 1; }
    90%  { opacity: 1; }
    100% { transform: translateY(110vh) rotate(360deg); opacity: 0; }
}

.rodape { text-align: center; color: #8c6f5a; font-size: .85rem; margin: 26px 0 10px; line-height: 1.5; }

@media (max-width: 480px) {
    .card-container .titulo-script.grande { font-size: 2.6rem !important; }
    .card-container .titulo-script.nome { font-size: 3rem !important; }
}
@media (prefers-reduced-motion: reduce) {
    .nuvem, .ovelha, .olho, .card-container, .chuva { animation: none !important; }
    .chuva { display: none; }
}
</style>
"""

OVELHA_SVG = """
<svg class="ovelha" viewBox="0 0 160 150" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Ovelhinha">
  <g fill="#fffaf2" stroke="#e6d6bf" stroke-width="2">
    <ellipse cx="80" cy="122" rx="48" ry="26"/>
    <circle cx="42" cy="62" r="20"/><circle cx="58" cy="42" r="22"/><circle cx="82" cy="36" r="22"/>
    <circle cx="106" cy="42" r="22"/><circle cx="120" cy="62" r="20"/>
  </g>
  <ellipse cx="42" cy="82" rx="14" ry="8" fill="#f4c9c4" transform="rotate(25 42 82)"/>
  <ellipse cx="118" cy="82" rx="14" ry="8" fill="#f4c9c4" transform="rotate(-25 118 82)"/>
  <ellipse cx="80" cy="82" rx="36" ry="32" fill="#fff4e8" stroke="#e6d6bf" stroke-width="2"/>
  <g fill="#3b2a22">
    <circle class="olho" cx="66" cy="80" r="4.5"/><circle class="olho" cx="94" cy="80" r="4.5"/>
  </g>
  <g fill="#fff"><circle cx="67.6" cy="78.4" r="1.4"/><circle cx="95.6" cy="78.4" r="1.4"/></g>
  <circle cx="56" cy="92" r="6" fill="#f6b9b4" opacity=".6"/><circle cx="104" cy="92" r="6" fill="#f6b9b4" opacity=".6"/>
  <path d="M75 92 q5 5 10 0 q-5 -3 -10 0z" fill="#f2a7a7"/>
  <path d="M80 95 v3 M72 98 q8 7 16 0" fill="none" stroke="#b9776f" stroke-width="2" stroke-linecap="round"/>
  <g fill="#f2a1ae" stroke="#e58a9b" stroke-width="1.5" stroke-linejoin="round">
    <path d="M80 30 L62 18 Q56 30 62 42 Z"/><path d="M80 30 L98 18 Q104 30 98 42 Z"/>
  </g>
  <circle cx="80" cy="30" r="6" fill="#e58a9b"/>
</svg>
"""


# -----------------------------------------------------------------------------
# SANITIZAÇÃO E VALIDAÇÃO
# -----------------------------------------------------------------------------
_CONTROLE = re.compile(r"[\x00-\x1f\x7f]")


def limpar_texto(texto: str, limite: int) -> str:
    """Normaliza, remove caracteres de controle, colapsa espaços e limita o tamanho."""
    texto = unicodedata.normalize("NFC", texto or "")
    texto = _CONTROLE.sub(" ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto[:limite]


def neutralizar_formula(texto: str) -> str:
    """Evita 'CSV injection': células começando com = + - @ viram fórmulas no Excel."""
    if texto and texto[0] in "=+-@":
        return "'" + texto
    return texto


def chave_nome(nome: str) -> str:
    """Chave para detectar nomes repetidos ignorando acento, maiúscula e pontuação."""
    base = unicodedata.normalize("NFKD", nome.casefold())
    base = "".join(c for c in base if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", base)


def validar_nome(nome: str) -> str | None:
    letras = re.findall(r"[^\W\d_]", nome)
    if len(letras) < 3 or len(nome.split()) < 2:
        return "Informe seu nome e sobrenome."
    return None


# -----------------------------------------------------------------------------
# PERSISTÊNCIA (Google Sheets em produção, CSV local em desenvolvimento)
# -----------------------------------------------------------------------------
def usando_google_sheets() -> bool:
    """True só se o Google Sheets estiver realmente configurado (valores de exemplo não contam)."""
    conta = get_secret("gcp_service_account")
    sheet_id = str(get_secret("SHEET_ID", "") or "")
    if conta is None or not sheet_id or sheet_id.startswith("COLE_AQUI"):
        return False
    try:
        chave = str(conta.get("private_key", ""))
    except Exception:
        return False
    return "BEGIN PRIVATE KEY" in chave and "..." not in chave


@st.cache_resource(show_spinner=False)
def _planilha():
    import gspread

    cliente = gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
    aba = cliente.open_by_key(st.secrets["SHEET_ID"]).sheet1
    if not aba.row_values(1):
        aba.append_row(COLUNAS)
    return aba


def _ler_tudo() -> pd.DataFrame:
    if usando_google_sheets():
        df = pd.DataFrame(_planilha().get_all_records())
    elif CSV_FILE_PATH.exists():
        df = pd.read_csv(CSV_FILE_PATH, dtype=str).fillna("")
    else:
        df = pd.DataFrame()

    for coluna in COLUNAS:
        if coluna not in df.columns:
            df[coluna] = ""
    df = df[COLUNAS].copy()
    for coluna in ("Data", "Nome", "Presenca", "Fralda", "Mensagem", "MostrarMensagem"):
        df[coluna] = df[coluna].astype(str)
    df["Acompanhantes"] = pd.to_numeric(df["Acompanhantes"], errors="coerce").fillna(0).astype(int)
    return df


@st.cache_data(ttl=20, show_spinner=False)
def carregar_confirmacoes() -> pd.DataFrame:
    return _ler_tudo()


def salvar_confirmacao(registro: dict) -> bool:
    """Grava a confirmação. Retorna False se esse nome já confirmou antes."""
    with _TRAVA_ESCRITA:
        existentes = _ler_tudo()
        if chave_nome(registro["Nome"]) in {chave_nome(n) for n in existentes["Nome"]}:
            return False

        linha = [registro[c] for c in COLUNAS]
        if usando_google_sheets():
            _planilha().append_row(linha, value_input_option="RAW")
        else:
            novo_arquivo = not CSV_FILE_PATH.exists()
            with CSV_FILE_PATH.open("a", newline="", encoding="utf-8") as arquivo:
                escritor = csv.writer(arquivo)
                if novo_arquivo:
                    escritor.writerow(COLUNAS)
                escritor.writerow(linha)

    carregar_confirmacoes.clear()
    return True


# -----------------------------------------------------------------------------
# UTILITÁRIOS DE EVENTO (mapa, calendário, WhatsApp)
# -----------------------------------------------------------------------------
def link_maps() -> str:
    return "https://www.google.com/maps/search/?api=1&query=" + quote(EVENTO_LOCAL)


def link_google_agenda() -> str:
    detalhes = "Chá de fraldas da Clara Sophie. Sugestão de presente: fraldas (P, M ou G) ou um mimo."
    return (
        "https://calendar.google.com/calendar/render?action=TEMPLATE"
        f"&text={quote(EVENTO_TITULO)}&dates={EVENTO_INICIO_UTC}/{EVENTO_FIM_UTC}"
        f"&details={quote(detalhes)}&location={quote(EVENTO_LOCAL)}"
    )


def gerar_ics() -> str:
    def esc(t: str) -> str:
        return t.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;")

    agora = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    linhas = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Cha Clara Sophie//PT-BR", "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT", "UID:cha-clara-sophie-2026@rsvp", f"DTSTAMP:{agora}",
        f"DTSTART:{EVENTO_INICIO_UTC}", f"DTEND:{EVENTO_FIM_UTC}",
        f"SUMMARY:{esc(EVENTO_TITULO)}", f"LOCATION:{esc(EVENTO_LOCAL)}",
        "DESCRIPTION:" + esc("Sugestão de presente: fraldas (P, M ou G) ou um mimo."),
        "BEGIN:VALARM", "TRIGGER:-P1D", "ACTION:DISPLAY", "DESCRIPTION:Amanhã tem chá de fraldas da Clara Sophie!",
        "END:VALARM", "END:VEVENT", "END:VCALENDAR",
    ]
    return "\r\n".join(linhas) + "\r\n"


def link_whatsapp() -> str | None:
    numero = re.sub(r"\D", "", str(get_secret("WHATSAPP_NUMBER", "")))
    if not numero:
        return None
    if len(numero) in (10, 11):  # DDD + número, sem o código do Brasil
        numero = "55" + numero
    texto = quote("Olá! Tenho uma dúvida sobre o chá de fraldas da Clara Sophie.")
    return f"https://wa.me/{numero}?text={texto}"


# -----------------------------------------------------------------------------
# COMPONENTES VISUAIS
# -----------------------------------------------------------------------------
def renderizar_fundo_animado():
    st.markdown(
        '<div class="nuvem n1"></div><div class="nuvem n2"></div><div class="nuvem n3"></div>',
        unsafe_allow_html=True,
    )


def renderizar_cabecalho():
    # Atenção: HTML dentro de st.markdown não pode ter linha em branco nem recuo de 4+ espaços,
    # senão o Markdown trata o trecho como bloco de código.
    html_cabecalho = "".join([
        '<div class="card-container">',
        OVELHA_SVG.strip().replace("\n", ""),
        '<h1 class="titulo-script grande">Chá de Fraldas</h1>',
        '<div class="subtitle">Vamos comemorar a doce espera da</div>',
        '<h2 class="titulo-script nome">Clara Sophie</h2>',
        "</div>",
    ])
    st.markdown(html_cabecalho, unsafe_allow_html=True)


def _embutir_html(conteudo: str, altura: int) -> None:
    """st.iframe nas versões novas do Streamlit; components.html nas antigas.
    Só passe HTML escrito por nós aqui, nunca texto vindo de convidados."""
    if hasattr(st, "iframe"):
        st.iframe(conteudo, height=altura)
    else:
        components.html(conteudo, height=altura)


def renderizar_contagem_regressiva():
    _embutir_html(
        f"""
        <style>
          body {{ margin:0; font-family: Georgia, serif; color:#5c3d2e; text-align:center; }}
          .caixa {{ display:flex; gap:10px; justify-content:center; }}
          .un {{ background:#fff; border:2px solid #d0bc9f; border-radius:16px; padding:10px 0; width:76px; }}
          .un b {{ display:block; font-size:1.7rem; }}
          .un span {{ font-size:.8rem; color:#7a5843; }}
          .msg {{ font-size:1.3rem; padding:18px 0; }}
        </style>
        <div id="c" class="caixa"></div>
        <script>
          const alvo = new Date("{EVENTO_INICIO_ISO}").getTime();
          const el = document.getElementById("c");
          function tick() {{
            let d = alvo - Date.now();
            if (d <= 0) {{ el.innerHTML = '<div class="msg">🎉 É hoje! Vamos celebrar a Clara Sophie!</div>'; return; }}
            const s = Math.floor(d/1000);
            const v = [[Math.floor(s/86400),"dias"],[Math.floor(s%86400/3600),"horas"],
                       [Math.floor(s%3600/60),"min"],[s%60,"seg"]];
            el.innerHTML = v.map(x => '<div class="un"><b>'+String(x[0]).padStart(2,"0")+'</b><span>'+x[1]+'</span></div>').join("");
          }}
          tick(); setInterval(tick, 1000);
        </script>
        """,
        100,
    )


def renderizar_detalhes_evento():
    st.markdown(
        """
        <div class="info-box">
            <p>📅 <b>Data:</b> Sábado, 21 de Novembro</p>
            <p>⏰ <b>Horário:</b> 19:00</p>
            <p>📍 <b>Endereço:</b> Professora Emília Cavalcante n.º 84 - Bairro: Santo Agostinho</p>
            <p>🎁 <b>Sugestão de Presentes:</b> Fraldas (P, M ou G) • Mimo da sua preferência</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    colunas = st.columns(3)
    colunas[0].link_button("📍 Ver no mapa", link_maps(), **largura(st.link_button))
    colunas[1].link_button("📅 Google Agenda", link_google_agenda(), **largura(st.link_button))
    colunas[2].download_button(
        "⏰ Baixar .ics", gerar_ics(), file_name="cha-clara-sophie.ics",
        mime="text/calendar", **largura(st.download_button),
    )
    whatsapp = link_whatsapp()
    if whatsapp:
        st.link_button("💬 Falar com os pais no WhatsApp", whatsapp, **largura(st.link_button))


def chuva_de_emojis(quantidade: int = 26):
    emojis = ["🐑", "🤍", "☁️", "🎀", "🌸", "🐑"]
    itens = "".join(
        f'<span class="chuva" style="left:{random.randint(2, 96)}%; font-size:{random.randint(20, 36)}px;'
        f' animation-duration:{random.uniform(3.5, 6.5):.1f}s; animation-delay:{random.uniform(0, 2.5):.1f}s;">'
        f"{random.choice(emojis)}</span>"
        for _ in range(quantidade)
    )
    st.markdown(itens, unsafe_allow_html=True)


def renderizar_agradecimento():
    resposta = st.session_state["enviado"]
    if st.session_state.pop("mostrar_festa", False):
        chuva_de_emojis()
        if resposta["presenca"] == "Sim":
            st.balloons()

    if resposta["presenca"] == "Sim":
        texto = (
            f"Obrigado, <b>{html.escape(resposta['primeiro_nome'])}</b>! 🥰<br>"
            "Sua presença está confirmada. A Clara Sophie e a família mal podem esperar para te ver!"
        )
    else:
        texto = (
            f"Obrigado por avisar, <b>{html.escape(resposta['primeiro_nome'])}</b>! 💛<br>"
            "Sentiremos sua falta, mas agradecemos o carinho."
        )
    st.markdown(f'<div class="info-box" style="text-align:center;">{texto}</div>', unsafe_allow_html=True)


def renderizar_formulario_rsvp():
    st.markdown('<h2 class="titulo-secao">Confirmação de Presença</h2>', unsafe_allow_html=True)

    if "enviado" in st.session_state:
        renderizar_agradecimento()
        return

    with st.form("form_rsvp", clear_on_submit=False):
        nome = st.text_input("Seu nome e sobrenome:", max_chars=80)
        presenca_label = st.radio("Você poderá comparecer?", options=list(PRESENCA_OPCOES))
        acompanhantes = st.number_input(
            "Quantidade de acompanhantes (adultos/crianças):",
            min_value=0, max_value=MAX_ACOMPANHANTES, value=0, step=1,
            help="Se não for comparecer, deixe 0.",
        )
        fralda = st.selectbox(
            "O que pretende levar? (ajuda a equilibrar os tamanhos de fralda)",
            options=FRALDA_OPCOES,
        )
        mensagem = st.text_area("Deixe uma mensagem carinhosa para a Clara Sophie (opcional):", max_chars=300)
        mostrar_mural = st.checkbox(
            "Permito que meu primeiro nome e minha mensagem apareçam no mural desta página."
        )
        consentimento = st.checkbox(
            "Concordo em compartilhar meu nome e minhas respostas com os pais da Clara Sophie "
            "somente para organizar o evento. *"
        )
        enviar = st.form_submit_button("Confirmar Presença ✨", type="primary", **largura(st.form_submit_button))

    st.caption(
        "🔒 Coletamos apenas o necessário. Seus dados ficam visíveis só para os pais (no mural, apenas se você "
        "permitir), não são compartilhados com terceiros e serão apagados após o evento. "
        "Para corrigir ou remover sua resposta, fale com os pais."
    )

    if not enviar:
        return

    nome = limpar_texto(nome, 80)
    mensagem = limpar_texto(mensagem, 300)

    erro = validar_nome(nome)
    if erro:
        st.error(erro)
        return
    if not consentimento:
        st.error("Marque a caixa de concordância para enviar sua resposta.")
        return

    agora = time.time()
    if st.session_state.get("total_envios", 0) >= MAX_ENVIOS_POR_SESSAO:
        st.error("Limite de envios atingido. Se precisar de ajuda, fale com os pais.")
        return
    if agora - st.session_state.get("ultimo_envio", 0) < INTERVALO_ENTRE_ENVIOS_S:
        st.warning("Aguarde alguns segundos antes de enviar novamente.")
        return
    st.session_state["ultimo_envio"] = agora

    presenca = PRESENCA_OPCOES[presenca_label]
    vai = presenca == "Sim"
    registro = {
        "Data": datetime.now(FUSO_MANAUS).strftime("%d/%m/%Y %H:%M:%S"),
        "Nome": neutralizar_formula(nome),
        "Presenca": presenca,
        "Acompanhantes": int(acompanhantes) if vai else 0,
        "Fralda": fralda if vai else "",
        "Mensagem": neutralizar_formula(mensagem),
        "MostrarMensagem": "Sim" if (mostrar_mural and mensagem) else "Não",
    }

    try:
        salvo = salvar_confirmacao(registro)
    except Exception:
        st.error("Não foi possível salvar agora. Tente novamente em instantes ou fale com os pais.")
        return

    if not salvo:
        st.warning("Este nome já tem uma resposta registrada. Para alterá-la, fale com os pais.")
        return

    st.session_state["total_envios"] = st.session_state.get("total_envios", 0) + 1
    st.session_state["enviado"] = {"presenca": presenca, "primeiro_nome": nome.split()[0]}
    st.session_state["mostrar_festa"] = True
    st.rerun()


def renderizar_mural():
    try:
        df = carregar_confirmacoes()
    except Exception:
        return
    recados = df[(df["MostrarMensagem"] == "Sim") & (df["Mensagem"].str.strip() != "")]
    if recados.empty:
        return

    st.markdown('<h2 class="titulo-secao">Mural de Recados</h2>', unsafe_allow_html=True)
    for _, linha in recados.tail(10).iloc[::-1].iterrows():
        primeiro_nome = html.escape(linha["Nome"].split()[0])
        texto = html.escape(linha["Mensagem"])  # escape evita injeção de HTML/JS
        st.markdown(f'<div class="recado"><b>{primeiro_nome}</b><br>{texto}</div>', unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# ÁREA DOS PAIS (protegida por senha)
# -----------------------------------------------------------------------------
def senha_correta(digitada: str) -> bool:
    esperada = get_secret("ADMIN_PASSWORD")
    if not esperada:
        return False
    return hmac.compare_digest(digitada.encode("utf-8"), str(esperada).encode("utf-8"))


def renderizar_area_admin():
    st.markdown("---")
    with st.expander("🔒 Área dos Pais (ver confirmações)"):
        if not get_secret("ADMIN_PASSWORD"):
            st.info("Área desativada: defina ADMIN_PASSWORD nos secrets do app.")
            return

        if not st.session_state.get("admin_ok"):
            if st.session_state.get("tentativas_admin", 0) >= MAX_TENTATIVAS_ADMIN:
                st.error("Muitas tentativas incorretas. Tente novamente mais tarde.")
                return
            with st.form("login_admin"):
                senha = st.text_input("Senha:", type="password")
                entrar = st.form_submit_button("Entrar")
            if entrar:
                if senha_correta(senha):
                    st.session_state["admin_ok"] = True
                    st.rerun()
                st.session_state["tentativas_admin"] = st.session_state.get("tentativas_admin", 0) + 1
                time.sleep(1.5)  # freia tentativas automáticas
                st.error("Senha incorreta.")
            return

        try:
            df = carregar_confirmacoes()
        except Exception:
            st.error(
                "Não consegui ler as confirmações. Confira nos secrets o SHEET_ID e a chave da conta de "
                "serviço, e se a planilha foi compartilhada (como Editor) com o client_email dela."
            )
            return
        if df.empty:
            st.warning("Ainda não há nenhuma confirmação registrada.")
        else:
            confirmados = df[df["Presenca"] == "Sim"]
            total_pessoas = len(confirmados) + int(confirmados["Acompanhantes"].sum())

            c1, c2, c3 = st.columns(3)
            c1.metric("Respostas", len(df))
            c2.metric("Confirmados", len(confirmados))
            c3.metric("Pessoas no total", total_pessoas)

            st.write("**Fraldas/presentes planejados (confirmados):**")
            st.bar_chart(confirmados["Fralda"].replace("", "Não informado").value_counts())

            st.dataframe(df, hide_index=True, **largura(st.dataframe))
            st.download_button(
                "⬇️ Baixar lista (CSV)",
                df.to_csv(index=False).encode("utf-8-sig"),
                file_name="confirmacoes-cha-clara.csv",
                mime="text/csv",
            )
            st.caption("Este arquivo contém dados pessoais dos convidados. Não compartilhe e apague após o evento.")

        if not usando_google_sheets():
            st.warning("Modo local: usando CSV. Em produção, configure o Google Sheets para não perder os dados.")
        if st.button("Sair da área dos pais"):
            st.session_state["admin_ok"] = False
            st.rerun()


# -----------------------------------------------------------------------------
# EXECUÇÃO PRINCIPAL
# -----------------------------------------------------------------------------
def main():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    renderizar_fundo_animado()
    renderizar_cabecalho()
    renderizar_contagem_regressiva()
    renderizar_detalhes_evento()
    renderizar_formulario_rsvp()
    renderizar_mural()
    renderizar_area_admin()
    st.markdown(
        '<div class="rodape">Feito com carinho para a chegada da Clara Sophie 🐑💛</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Monitor de Convocações - CRBM 6
---------------------------------
Verifica periodicamente a página de concursos do CRBM 6 e envia um
alerta via WhatsApp (CallMeBot) quando detecta convocações novas.

Estratégia de detecção (três camadas, da mais específica para a mais
genérica — assim nada passa despercebido mesmo se o site mudar):

1) CARGO DE INTERESSE: procura especificamente por novas convocações
   de "Agente administrativo – AC". Esse é o alerta prioritário. 🎯

2) QUANTIDADE DE ITENS: conta quantos cards existem dentro do
   container da listagem (div.elementor-loop-container). Se o número
   aumentar, houve nova convocação — mesmo que o parser de texto não
   reconheça o formato.

3) LISTA COMPLETA: compara a lista de convocações extraídas do texto
   com a última salva, para reportar qualquer outra novidade.

Estado é salvo em state.json (comitado de volta no repositório pelo
workflow do GitHub Actions).
"""

import json
import os
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://crbm6.gov.br/concurso/"
STATE_FILE = Path(__file__).parent / "state.json"

# --- Onde a listagem de convocações fica na página ---
# ID do container externo observado no HTML do site.
CONTAINER_ID = "5b06574"
# Classe do grid que contém um card por convocação.
LOOP_CONTAINER_CLASS = "elementor-loop-container"

# --- Cargo que você quer monitorar prioritariamente ---
CARGO_INTERESSE = "agente administrativo"

# Formato observado no texto dos cards:
#   "Agente administrativo – AC 4º classificado convocação 18-08-2026"
# O travessão pode vir como – (en dash), — (em dash) ou - (hífen).
CONVOCACAO_PATTERN = re.compile(
    r"(?P<cargo>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s]{2,40}?)\s*[–—-]\s*"
    r"(?P<lista>[A-Z]{2,4})\s+"
    r"(?P<classificacao>\d+)[ºo°]?\s*classificad[oa]\s+"
    r"convoca[çc][ãa]o\s+"
    r"(?P<data>\d{2}-\d{2}-\d{2,4})",
    re.IGNORECASE,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


def fetch_soup() -> BeautifulSoup:
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def find_loop_container(soup: BeautifulSoup):
    """
    Localiza o grid que contém os cards de convocação.

    Tenta, em ordem:
    1. Dentro do div com o ID conhecido (mais preciso)
    2. Qualquer div com a classe do loop container (caso o ID mude)
    """
    outer = soup.find(id=CONTAINER_ID)
    if outer:
        container = outer.find("div", class_=LOOP_CONTAINER_CLASS)
        if container:
            return container

    # Fallback: procura o loop container em qualquer lugar da página
    return soup.find("div", class_=LOOP_CONTAINER_CLASS)


def count_items(container) -> int:
    """Conta os elementos filhos diretos (um card por convocação)."""
    if container is None:
        return 0
    return len([child for child in container.find_all(recursive=False)])


def extract_convocacoes(text: str):
    """Extrai a lista estruturada de convocações a partir do texto."""
    convocacoes = []
    for m in CONVOCACAO_PATTERN.finditer(text):
        convocacoes.append(
            {
                "cargo": " ".join(m.group("cargo").split()),
                "lista": m.group("lista").strip(),
                "classificacao": m.group("classificacao"),
                "data": m.group("data"),
            }
        )
    return convocacoes


def as_key(c: dict) -> str:
    return f"{c['cargo'].lower()}|{c['lista']}|{c['classificacao']}|{c['data']}"


def format_convocacao(c: dict) -> str:
    return f"{c['cargo']} – {c['lista']} {c['classificacao']}º classificado ({c['data']})"


def is_cargo_interesse(c: dict) -> bool:
    return CARGO_INTERESSE in c["cargo"].lower()


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"total_itens": None, "convocacoes": []}


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def send_whatsapp(message: str):
    phone = os.environ.get("CALLMEBOT_PHONE")
    apikey = os.environ.get("CALLMEBOT_APIKEY")
    if not phone or not apikey:
        print("AVISO: CALLMEBOT_PHONE ou CALLMEBOT_APIKEY não configurados; "
              "pulei o envio do WhatsApp. Mensagem que seria enviada:\n")
        print(message)
        return

    resp = requests.get(
        "https://api.callmebot.com/whatsapp.php",
        params={"phone": phone, "text": message, "apikey": apikey},
        timeout=30,
    )
    print(f"CallMeBot status: {resp.status_code} - {resp.text[:200]}")


def main():
    # --- 1. Busca a página ---
    try:
        soup = fetch_soup()
    except Exception as e:
        erro_msg = (
            "⚠️ CRBM 6 - Falha ao acessar a página de concursos.\n"
            f"Erro: {e}\n\n"
            f"URL monitorada: {URL}\n"
            "Pode ser que o link tenha mudado, ou o site esteja fora do ar. "
            "Vale conferir manualmente."
        )
        print(erro_msg, file=sys.stderr)
        send_whatsapp(erro_msg)
        sys.exit(1)

    container = find_loop_container(soup)

    if container is None:
        erro_msg = (
            "⚠️ CRBM 6 - Não encontrei a listagem de convocações na página.\n"
            f"Procurei pelo container '{LOOP_CONTAINER_CLASS}' "
            f"(dentro do ID '{CONTAINER_ID}').\n\n"
            f"O site pode ter mudado de estrutura. Confira: {URL}"
        )
        print(erro_msg, file=sys.stderr)
        send_whatsapp(erro_msg)
        sys.exit(1)

    # --- 2. Coleta os dados ---
    total_itens = count_items(container)
    texto = re.sub(r"\s+", " ", container.get_text(separator=" ")).strip()
    convocacoes = extract_convocacoes(texto)

    print(f"Itens no container: {total_itens}")
    print(f"Convocações reconhecidas pelo parser: {len(convocacoes)}")
    for c in convocacoes:
        print(f"  - {format_convocacao(c)}")

    # --- 3. Compara com o estado anterior ---
    state = load_state()
    total_anterior = state.get("total_itens")
    convocacoes_anteriores = state.get("convocacoes", [])

    if total_anterior is None:
        print("\nPrimeira execução: salvando estado inicial, sem alerta.")
        save_state({"total_itens": total_itens, "convocacoes": convocacoes})
        return

    chaves_anteriores = {as_key(c) for c in convocacoes_anteriores}
    novas = [c for c in convocacoes if as_key(c) not in chaves_anteriores]
    novas_interesse = [c for c in novas if is_cargo_interesse(c)]

    houve_aumento = total_itens > (total_anterior or 0)

    if not novas and not houve_aumento:
        print("\nNenhuma mudança detectada.")
        save_state({"total_itens": total_itens, "convocacoes": convocacoes})
        return

    # --- 4. Monta a mensagem ---
    partes = []

    if novas_interesse:
        partes.append(
            "🎯 NOVA CONVOCAÇÃO DE AGENTE ADMINISTRATIVO!\n"
            + "\n".join(f"• {format_convocacao(c)}" for c in novas_interesse)
        )

    outras = [c for c in novas if not is_cargo_interesse(c)]
    if outras:
        partes.append(
            "📋 Outras convocações novas:\n"
            + "\n".join(f"• {format_convocacao(c)}" for c in outras)
        )

    if houve_aumento and not novas:
        # O contador subiu mas o parser não reconheceu nada novo.
        # Pode ser mudança de formato — alerta genérico para conferir.
        partes.append(
            f"📈 A quantidade de itens na listagem aumentou "
            f"({total_anterior} → {total_itens}), mas não consegui identificar "
            "qual convocação é nova. Vale conferir manualmente."
        )
    elif houve_aumento:
        partes.append(f"(Total de itens: {total_anterior} → {total_itens})")

    msg = "🔔 CRBM 6 - Atualização na página de concursos\n\n" + "\n\n".join(partes)
    msg += f"\n\nConfira: {URL}"

    print("\n" + msg)
    send_whatsapp(msg)

    save_state({"total_itens": total_itens, "convocacoes": convocacoes})


if __name__ == "__main__":
    main()

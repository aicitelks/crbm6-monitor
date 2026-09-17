#!/usr/bin/env python3
"""
Monitor de Convocações - CRBM 6
---------------------------------
Verifica periodicamente a página de concursos do CRBM 6 e envia um
alerta via WhatsApp (CallMeBot) quando detecta uma convocação nova.

Duas camadas de detecção:
1) HASH do texto da seção inteira -> detecta QUALQUER mudança na página,
   mesmo que o parser abaixo não reconheça o formato exato.
2) PARSER de "Convocação DD-MM-AA · Cargo · Status" -> tenta listar
   especificamente o que mudou na mensagem do WhatsApp.

Estado é salvo em state.json (comitado de volta no repositório pelo
workflow do GitHub Actions).
"""

import hashlib
import json
import os
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://crbm6.gov.br/concurso/"
STATE_FILE = Path(__file__).parent / "state.json"

# Padrão observado na página: "Convocação 09-07-26 · Advogado · AC-1º classificado"
CONVOCACAO_PATTERN = re.compile(
    r"Convoca[cç][aã]o\s+(\d{2}-\d{2}-\d{2,4})\s*[·•\-–]\s*"
    r"([A-ZÀ-Úa-zà-ú0-9º°\s\.\-]{2,60}?)\s*[·•\-–]\s*"
    r"([^\n]{2,90}?)(?=\s*Convoca[cç][aã]o|\s*$)",
    re.IGNORECASE,
)


def fetch_page_text() -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    }
    resp = requests.get(URL, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove scripts/estilos para não poluir o texto
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ")
    # Normaliza espaços
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_convocacoes(full_text: str):
    matches = CONVOCACAO_PATTERN.findall(full_text)
    convocacoes = []
    for data, cargo, status in matches:
        convocacoes.append(
            {
                "data": data.strip(),
                "cargo": cargo.strip(" ."),
                "status": status.strip(" ."),
            }
        )
    return convocacoes


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"hash": None, "convocacoes": []}


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def send_whatsapp(message: str):
    phone = os.environ.get("CALLMEBOT_PHONE")
    apikey = os.environ.get("CALLMEBOT_APIKEY")
    if not phone or not apikey:
        print("AVISO: CALLMEBOT_PHONE ou CALLMEBOT_APIKEY não configurados; "
              "pulei o envio do WhatsApp. Mensagem que seria enviada:")
        print(message)
        return

    resp = requests.get(
        "https://api.callmebot.com/whatsapp.php",
        params={"phone": phone, "text": message, "apikey": apikey},
        timeout=30,
    )
    print(f"CallMeBot status: {resp.status_code} - {resp.text[:200]}")


def main():
    try:
        full_text = fetch_page_text()
    except Exception as e:
        erro_msg = (
            "⚠️ CRBM 6 - Falha ao acessar a página de concursos.\n"
            f"Erro: {e}\n\n"
            f"URL monitorada: {URL}\n"
            "Pode ser que o link tenha mudado de novo, ou o site esteja fora "
            "do ar temporariamente. Vale conferir manualmente."
        )
        print(erro_msg, file=sys.stderr)
        send_whatsapp(erro_msg)
        sys.exit(1)

    current_hash = text_hash(full_text)
    current_convocacoes = extract_convocacoes(full_text)

    state = load_state()
    previous_hash = state.get("hash")
    previous_convocacoes = state.get("convocacoes", [])

    if previous_hash is None:
        # Primeira execução: só salva o estado inicial, sem alertar
        print("Primeira execução: salvando estado inicial, sem alerta.")
        save_state(
            {"hash": current_hash, "convocacoes": current_convocacoes}
        )
        return

    if current_hash == previous_hash:
        print("Nenhuma mudança detectada.")
        return

    # Página mudou. Tenta identificar convocações novas especificamente.
    prev_set = {(c["data"], c["cargo"], c["status"]) for c in previous_convocacoes}
    curr_set = {(c["data"], c["cargo"], c["status"]) for c in current_convocacoes}
    novas = curr_set - prev_set

    if novas:
        linhas = [f"• {data} — {cargo} ({status})" for data, cargo, status in sorted(novas)]
        msg = (
            "🔔 CRBM 6 - Nova(s) convocação(ões) detectada(s)!\n\n"
            + "\n".join(linhas)
            + f"\n\nConfira: {URL}"
        )
    else:
        # Hash mudou mas o parser não achou diferença estruturada
        # (ex: mudou o layout, ou outro conteúdo da página)
        msg = (
            "🔔 CRBM 6 - A página de concursos foi atualizada.\n"
            "Não consegui identificar automaticamente qual convocação é nova, "
            f"dá uma olhada: {URL}"
        )

    print(msg)
    send_whatsapp(msg)

    save_state({"hash": current_hash, "convocacoes": current_convocacoes})


if __name__ == "__main__":
    main()

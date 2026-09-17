#!/usr/bin/env python3
"""
Monitor de Publicações - Diário Oficial da União (DOU)
--------------------------------------------------------
Verifica periodicamente se uma busca específica no site do DOU
(in.gov.br) passou a ter resultados (ex: convocação, nomeação,
portaria) e envia um alerta via WhatsApp (CallMeBot) quando isso
acontece.

Como funciona:
O resultado da busca do DOU vem embutido em um bloco <script> no
HTML da página, contendo uma lista JSON estruturada com cada
publicação encontrada (título, data, seção, link). Em vez de tentar
ler o texto "0 resultados" (frágil a mudanças de texto), o script lê
diretamente esse JSON.

Estado (quais publicações já foram vistas e alertadas) é salvo em
state_dou.json, comitado de volta no repositório pelo GitHub Actions.
"""

import json
import os
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# --- Configuração da busca ---
# Ajuste aqui o termo de busca, se precisar monitorar outro termo/pessoa.
SEARCH_QUERY = '"FABRICIO ALASTICO"'  # busca exata (entre aspas)
SEARCH_SECTIONS = "todos"  # 'todos' = todas as seções (1, 2 e 3)
SEARCH_EXACT_DATE = "all"  # 'all' = sem filtro de data

IN_API_BASE_URL = "https://www.in.gov.br/consulta/-/buscar/dou"
IN_WEB_BASE_URL = "https://www.in.gov.br/web/dou/-/"
SCRIPT_TAG_ID = "_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params"

STATE_FILE = Path(__file__).parent / "state_dou.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Cache-Control": "no-cache",
}


def fetch_results():
    payload = {
        "q": SEARCH_QUERY,
        "s": SEARCH_SECTIONS,
        "exactDate": SEARCH_EXACT_DATE,
        "sortType": "0",
    }
    resp = requests.get(IN_API_BASE_URL, params=payload, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.content, "html.parser")
    script_tag = soup.find("script", id=SCRIPT_TAG_ID)

    if script_tag is None:
        raise ValueError(
            "Não encontrei o bloco de resultados esperado na página. "
            "O site pode ter mudado de estrutura."
        )

    data = json.loads(script_tag.contents[0])
    return data.get("jsonArray", [])


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"seen_ids": []}


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
        results = fetch_results()
    except Exception as e:
        erro_msg = (
            "⚠️ Monitor DOU - Falha ao acessar a busca no in.gov.br.\n"
            f"Erro: {e}\n\n"
            "Vale conferir manualmente se o site mudou de estrutura."
        )
        print(erro_msg, file=sys.stderr)
        send_whatsapp(erro_msg)
        sys.exit(1)

    state = load_state()
    seen_ids = set(state.get("seen_ids", []))

    novos = [r for r in results if str(r.get("classPK")) not in seen_ids]

    print(f"Total de resultados encontrados: {len(results)}")
    print(f"Novos (ainda não alertados): {len(novos)}")

    if novos:
        linhas = []
        for r in novos:
            titulo = r.get("title", "Sem título")
            data_pub = r.get("pubDate", "")
            secao = r.get("pubName", "")
            link = IN_WEB_BASE_URL + r.get("urlTitle", "")
            linhas.append(f"• {data_pub} — {titulo} ({secao})\n  {link}")

        msg = (
            "🔔 DOU - Nova publicação encontrada para \"FABRICIO ALASTICO\"!\n\n"
            + "\n\n".join(linhas)
        )
        print(msg)
        send_whatsapp(msg)

        seen_ids.update(str(r.get("classPK")) for r in results)
        save_state({"seen_ids": sorted(seen_ids)})
    else:
        print("Nenhuma publicação nova. Nada a fazer.")


if __name__ == "__main__":
    main()

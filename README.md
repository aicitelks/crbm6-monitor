# Monitor de Convocações — CRBM 6 e DOU

Monitoramento automático de convocações de concurso público, com alertas
enviados direto no WhatsApp. Roda sozinho no GitHub Actions, sem custo e
sem precisar deixar nada ligado.

## 🎯 Objetivo

Acompanhar manualmente páginas de concurso é fácil de esquecer — e perder
o prazo de uma convocação pode custar a vaga. Este projeto automatiza esse
acompanhamento em duas frentes:

| Monitor | O que acompanha | Arquivo |
|---|---|---|
| **CRBM 6** | Novas convocações na página de concursos do CRBM 6 | `monitor.py` |
| **DOU** | Publicações no Diário Oficial da União com o termo buscado | `monitor_dou.py` |

Cada um roda de forma independente, com seu próprio agendamento e seu
próprio arquivo de estado.

---

## 📡 Monitor 1 — CRBM 6 (`monitor.py`)

Monitora: https://crbm6.gov.br/concurso/

### Como a detecção funciona

O script usa **três camadas**, da mais específica para a mais genérica, de
modo que nenhuma atualização passe despercebida — mesmo que o site mude de
layout:

**1. Cargo de interesse (alerta prioritário) 🎯**
Procura especificamente por novas convocações de **"Agente administrativo – AC"**.
Quando aparece uma, o alerta vem em destaque no topo da mensagem.

**2. Quantidade de itens 📈**
Conta quantos cards existem dentro do container da listagem
(`div.elementor-loop-container`, dentro do `div#5b06574`). Se esse número
aumentar, houve nova convocação — mesmo que o texto não seja reconhecido
pelo parser.

**3. Lista completa 📋**
Compara a lista de convocações extraídas do texto com a última salva, e
reporta qualquer outra novidade (Contador, Fiscal, etc.).

### Formato de texto reconhecido

O parser entende linhas neste formato:

```
Agente administrativo – AC 4º classificado convocação 18-08-2026
Contador – AC 3º classificado convocação 18-08-2026
Fiscal – AC 1º classificado convocação 03-08-2026
```

Aceita travessão (`–`), traço longo (`—`) ou hífen (`-`) como separador.

### Mudando o cargo monitorado

No topo do `monitor.py`:

```python
CARGO_INTERESSE = "agente administrativo"
```

Basta trocar por outro cargo (em minúsculas). Os demais continuam sendo
reportados na seção "Outras convocações novas".

---

## 📰 Monitor 2 — Diário Oficial da União (`monitor_dou.py`)

Monitora buscas no https://www.in.gov.br pelo termo configurado.

### Como a detecção funciona

O resultado da busca do DOU vem embutido em um bloco `<script>` no HTML da
página, contendo uma lista JSON estruturada com cada publicação encontrada.
O script lê diretamente esse JSON — bem mais confiável do que tentar
interpretar o texto "0 resultados", que pode mudar de redação a qualquer
momento.

Sempre que aparece uma publicação ainda não alertada, você recebe título,
data, seção e o link direto.

### Mudando o termo buscado

No topo do `monitor_dou.py`:

```python
SEARCH_QUERY = '"FABRICIO ALASTICO"'  # busca exata (entre aspas)
SEARCH_SECTIONS = "todos"             # todas as seções (1, 2 e 3)
SEARCH_EXACT_DATE = "all"             # sem filtro de data
```

---

## ⚙️ Instruções de configuração

### Passo 1 — Criar o repositório no GitHub

Crie um repositório (pode ser privado) e suba estes arquivos:

```
.
├── monitor.py
├── monitor_dou.py
├── requirements.txt
├── README.md
└── .github/
    └── workflows/
        ├── monitor.yml
        └── monitor_dou.yml
```

> **Dica:** ao subir pelo navegador, use **Add file → Create new file** e
digite o caminho completo no nome (ex: `.github/workflows/monitor.yml`).
> O GitHub cria as pastas automaticamente ao ver as barras `/`.

### Passo 2 — Ativar o WhatsApp (CallMeBot)

O CallMeBot é um serviço gratuito que envia mensagens de WhatsApp via API.

1. No celular, adicione o número **+34 621 08 34 84** aos contatos.
   *(Esse número muda de tempos em tempos — se não funcionar, confira o
   atual em https://www.callmebot.com/blog/free-api-whatsapp-messages/)*
2. Mande para esse número, pelo WhatsApp, a mensagem exata:
   ```
   I allow callmebot to send me messages
   ```
3. Você recebe de volta a sua **API Key**. Guarde esse número.

### Passo 3 — Configurar os Secrets

No repositório: **Settings → Secrets and variables → Actions → New repository secret**

| Nome | Valor |
|---|---|
| `CALLMEBOT_PHONE` | Seu número com código do país, ex: `5541999999999` |
| `CALLMEBOT_APIKEY` | A API Key recebida do CallMeBot |

Os dois monitores usam os **mesmos secrets** — não precisa duplicar.

### Passo 4 — Primeira execução

1. Vá na aba **Actions** do repositório.
2. Selecione o workflow desejado na lista à esquerda.
3. Clique em **Run workflow** → **Run workflow**.

Na primeira execução de cada monitor, **nenhum alerta é enviado** — o script
apenas salva o estado atual (a "foto inicial") em `state.json` /
`state_dou.json`. A partir da segunda execução, qualquer novidade gera alerta.

> ⚠️ O botão **Run workflow** só aparece quando o arquivo `.yml` já está na
> branch padrão (`main`). Se ainda estiver só em um PR, faça o merge primeiro.

### Ajustando a frequência

Nos arquivos `.github/workflows/*.yml`, a linha `cron` define o intervalo
(horário UTC):

```yaml
- cron: "0 */6 * * *"   # a cada 6 horas
```

Outros exemplos:

| Expressão | Frequência |
|---|---|
| `"0 * * * *"` | a cada hora |
| `"0 */12 * * *"` | a cada 12 horas |
| `"0 11,23 * * *"` | 2x por dia (8h e 20h no horário de Brasília) |
| `"0 11 * * 1-5"` | 8h da manhã, de segunda a sexta |

---

## 💻 Rodando localmente

Útil para testar mudanças antes de subir, ou para validar que a leitura do
site está funcionando.

### Pré-requisitos

- Python 3.9 ou superior
- `pip` instalado

### Instalação

```bash
# Clone o repositório
git clone https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
cd SEU_USITORIO

# (Opcional, mas recomendado) crie um ambiente virtual
python -m venv venv

# Ative o ambiente virtual
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows (PowerShell/CMD)

# Instale as dependências
pip install -r requirements.txt
```

### Executando

```bash
python monitor.py        # monitor do CRBM 6
python monitor_dou.py    # monitor do DOU
```

**Sem os secrets configurados**, o script roda normalmente, imprime tudo que
encontrou no terminal e mostra a mensagem que *seria* enviada — sem disparar
WhatsApp de verdade. É o modo ideal para testar.

Saída esperada do `monitor.py`:

```
Itens no container: 10
Convocações reconhecidas pelo parser: 8
  - Contador – AC 4º classificado (04-09-2026)
  - Fiscal – AC 2º classificado (24-08-2026)
  - Agente administrativo – AC 4º classificado (18-08-2026)
  ...

Primeira execução: salvando estado inicial, sem alerta.
```

### Testando com envio real de WhatsApp

Se quiser testar o envio de verdade, defina as variáveis de ambiente antes
de rodar:

```bash
# Linux / macOS
export CALLMEBOT_PHONE="5541999999999"
export CALLMEBOT_APIKEY="123456"
python monitor.py

# Windows (PowerShell)
$env:CALLMEBOT_PHONE="5541999999999"
$env:CALLMEBOT_APIKEY="123456"
python monitor.py
```

### Forçando um alerta para teste

Depois que o `state.json` já existe, edite-o manualmente reduzindo o
`total_itens` (ex: de `10` para `9`) ou removendo uma convocação da lista.

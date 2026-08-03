# Monitor de Convocações - CRBM 6

Verifica automaticamente https://crbm6.gov.br/concursos/ e te avisa no
WhatsApp quando sair uma convocação nova.

## Como funciona

1. GitHub Actions roda o script a cada 6 horas (você pode mudar o horário).
2. O script busca a página e compara com a última versão salva.
3. Se mudou algo, tenta identificar qual convocação é nova e te manda uma
   mensagem no WhatsApp via CallMeBot (serviço gratuito).
4. Se a página mudou mas o formato não bateu com o esperado, você recebe
   um alerta genérico avisando para conferir manualmente — assim você
   nunca perde uma atualização, mesmo se o layout do site mudar.

### Foto atual
A página encontra-se inicialmente com esse conteúdo:
<img width="651" height="693" alt="image" src="https://github.com/user-attachments/assets/efcba591-42d1-4eab-8a07-4086a6cc7baf" />

## Passo 1 — Criar o repositório no GitHub

1. Crie um repositório novo (pode ser privado) no GitHub, ex: `crbm6-monitor`.
2. Suba estes arquivos para ele (`monitor.py`, `requirements.txt`,
   `.github/workflows/monitor.yml`, este `README.md`).

Se quiser, faça isso direto pelo site do GitHub: clique em "Add file" →
"Upload files" e arraste os arquivos.

## Passo 2 — Ativar o WhatsApp (CallMeBot)

1. No seu celular, adicione o número **+34 644 59 71 65** aos contatos.
2. Mande para esse número, pelo WhatsApp, a mensagem exata:
   `I allow callmebot to send me messages`
3. Você vai receber uma resposta com sua **API Key** (um número).
   Guarde essa chave.

## Passo 3 — Configurar os "Secrets" no GitHub

No repositório: **Settings → Secrets and variables → Actions → New repository secret**

Crie dois secrets:

| Nome | Valor |
|---|---|
| `CALLMEBOT_PHONE` | Seu número com código do país, ex: `5541999999999` |
| `CALLMEBOT_APIKEY` | A API Key que o CallMeBot te enviou |

## Passo 4 — Primeira execução

1. Vá em **Actions** no repositório → selecione "Monitorar Convocações CRBM 6"
   → **Run workflow** (botão manual) para testar.
2. Na primeira execução, o script só salva o estado atual da página
   (não manda alerta ainda — é a "foto inicial").
3. Da próxima vez que a página mudar, você recebe o WhatsApp. 🎉

## Ajustando a frequência

No arquivo `.github/workflows/monitor.yml`, a linha:

```yaml
- cron: "0 */6 * * *"
```

controla o intervalo. Exemplos:
- `"0 8,20 * * *"` → 2x por dia (8h e 20h UTC)
- `"0 * * * *"` → a cada hora

---

###### Feito com Claude, revisado por mim ;P

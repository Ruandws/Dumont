# SPEC.md — OLX Deal Finder
> **Versão:** 2.2 | **Status:** MVP | **Princípio:** Spec guia tudo. Em caso de conflito, SPEC manda.

---

## 1. Visão e Objetivo

Sistema automatizado que monitora a OLX/DF, detecta anúncios de hardware subvalorizados e alerta o usuário via Telegram — permitindo agir sem estar na frente do computador.

**Usuário:** Revendedor ativo de hardware usado, sem acesso frequente ao computador onde o sistema roda.

**Definição de pronto:**

| Critério | Métrica |
|----------|---------|
| Velocidade | Anúncios detectados em ≤ 5 min |
| Score | `score = (média - preço) / média` correto para qualquer input válido |
| Alertas | Disparados **somente** quando `score ≥ 0.25` |
| Canal | Mensagem Telegram com título, preço, score e link |
| Integridade | Zero duplicatas no banco |
| Autonomia | Loop automático sem intervenção manual |
| Escopo | Apenas anúncios do Distrito Federal |

> Se qualquer critério falhar, a implementação não está completa.

---

## 2. Não-Objetivos (Fora do Escopo do MVP)

O agente **não deve implementar** nenhum dos itens abaixo. Se quiser adicionar qualquer um, deve parar e perguntar.

- Proxy rotation (playwright-stealth é suficiente para o MVP)
- Modelo de ML para scoring (a fórmula linear é suficiente)
- Outros marketplaces (Enjoei, Mercado Livre, Facebook)
- Histórico de médias além das 72h definidas
- Autenticação de usuário na UI
- Cobertura de regiões além do DF

---

## 3. Pipeline de Execução (Runtime)

Referência principal para implementar `scheduler.py`. Cada módulo recebe dados do anterior e entrega ao próximo — nenhum módulo chama outro fora desta sequência.

```
[APScheduler — a cada 5 min]
        │
        ▼
  browser.py ──── Inicia Playwright + stealth + User-Agent rotativo
        │         Falha: loga ERROR, aborta ciclo
        ▼
  crawler.py ──── Acessa SEARCH_URL do .env (OLX/DF)
        │         Pagina até 3 páginas OU early stop (nenhum anúncio novo na página)
        │         Delay aleatório 2–5s entre páginas
        │         Timeout/429: retry máx 2x; se persistir, pula página + loga WARNING
        ▼
  parser.py ───── Extrai por anúncio: título, preço, link, data_publicacao
        │         Campo ausente ou preço inválido: descarta, loga WARNING com URL
        ▼
  processor.py ── Normaliza preços (→ float), remove duplicatas por hash
        │
        ▼
  storage.py ──── Persiste apenas anúncios novos no SQLite
        │
        ▼
  deal_finder.py ─ Filtra últimas 72h → aplica blacklist → agrupa (mín. 3)
        │          → calcula score → filtra score ≥ 0.25
        ▼
  alert.py ─────── POST direto à API do Telegram por oportunidade
        │          Falha: loga ERROR, não interrompe ciclo
        ▼
  [Ciclo encerrado]
```

---

## 4. Tech Stack

| Componente | Tecnologia | Versão |
|------------|-----------|--------|
| Linguagem | Python | 3.14 |
| Scraping | Playwright | 1.58 |
| Stealth | playwright-stealth | 0.0.9 |
| Processamento | Pandas | 3.0.2 |
| Armazenamento | SQLite | 3.53.1 |
| Interface | Streamlit | 1.57.0 |
| Agendamento | APScheduler | 3.11.2 |
| Alertas | requests (stdlib-like) | 2.32.x |

> **Nota sobre Telegram:** Não usar `python-telegram-bot` — v20+ é async e conflita com APScheduler 3.x síncrono. Usar `requests.post()` diretamente na API REST do Telegram (`https://api.telegram.org/bot{TOKEN}/sendMessage`). Simples, síncrono, sem dependência extra.

> Não substitua tecnologias sem passar pelo processo `⚠️ Ask first` de §6.

---

## 5. Estrutura do Projeto

```
.
├── .env                 # Variáveis de ambiente (ver §5.1) — NUNCA commitar
├── .gitignore           # Ver §5.2
├── requirements.txt     # Dependências pinadas (gerado com pip freeze)
├── SPEC.md
└── src/
    ├── core/
    │   ├── browser.py       # Playwright + stealth + logger central
    │   ├── crawler.py       # Paginação, early stop, delays, retry
    │   ├── parser.py        # Extração de campos, descarte de inválidos
    │   └── scheduler.py     # Loop APScheduler, orquestra pipeline
    ├── data/
    │   ├── models.py        # Dataclass Deal
    │   ├── storage.py       # Leitura/escrita SQLite
    │   └── processor.py     # Normalização de preço, deduplicação
    ├── services/
    │   ├── alert.py         # POST Telegram via requests
    │   └── deal_finder.py   # Score, filtros, blacklist, normalização
    └── ui/
        └── app.py           # Interface Streamlit
```

### 5.1 Template `.env`

```dotenv
# OLX
SEARCH_URL=https://www.olx.com.br/eletronicos-e-celulares/computadores-e-acessorios/estado-df?q=gtx+1080

# Telegram
TELEGRAM_TOKEN=seu_token_aqui
TELEGRAM_CHAT_ID=seu_chat_id_aqui

# Configurações
SCHEDULER_INTERVAL_MINUTES=5
MAX_PAGES=3
SCORE_THRESHOLD=0.25
LOOKBACK_HOURS=72
MIN_GROUP_SIZE=3
```

### 5.2 `.gitignore` (entradas obrigatórias)

```gitignore
.env
*.db
*.sqlite3
playwright/.auth/
__pycache__/
.pytest_cache/
.ruff_cache/
```

---

## 6. Boundaries

### ✅ ALWAYS
- Seguir a estrutura de §5
- Type hints em todas as funções públicas
- Validar dados antes de salvar no banco
- Usar o logger central (`browser.py`) — nunca `print`
- Executar o self-check de §8 após cada tarefa

### ⚠️ ASK FIRST
- Alterar o modelo `Deal` (§9)
- Adicionar nova dependência
- Mudar `SCORE_THRESHOLD`, `LOOKBACK_HOURS` ou `MIN_GROUP_SIZE`
- Modificar o schema do banco SQLite
- Alterar a sequência do pipeline (§3)

### 🚫 NEVER
- Misturar scraping com lógica de negócio
- Hardcode de qualquer valor que está no `.env`
- Request sem delay entre páginas
- Criar/modificar arquivos fora de `src/` (exceto `SPEC.md`)
- Silenciar exceções (`except: pass`)
- Implementar mais de uma tarefa por sessão

---

## 7. Tarefas Modulares

> **Uma tarefa por sessão.** Para cada sessão: (1) leia a spec completa, (2) implemente apenas o módulo da tarefa, (3) execute o self-check de §8.

| # | Módulo | Input | Output |
|---|--------|-------|--------|
| 1 | `core/browser.py` | — | Playwright com stealth + logger configurado |
| 2 | `core/crawler.py` | `SEARCH_URL` do .env | Lista de URLs (máx 3 pág., early stop) |
| 3 | `core/parser.py` | HTML de um anúncio | `Dict` com campos ou descarte com WARNING |
| 4 | `data/models.py` + `data/storage.py` | Objeto `Deal` | Deal salvo no SQLite sem duplicata |
| 5 | `data/processor.py` | Lista de deals brutos | Lista com preço normalizado, sem duplicatas |
| 6 | `services/deal_finder.py` | Lista de `Deal` do banco | Lista filtrada com `score ≥ 0.25` |
| 7 | `services/alert.py` | Lista de oportunidades | Mensagem Telegram enviada por oportunidade |
| 8 | `core/scheduler.py` | — | Loop APScheduler orquestrando §3 completo |
| 9 | `ui/app.py` | Banco SQLite | Tabela de oportunidades na tela |

---

## 7.1 Regras de Negócio por Módulo

### Crawler
- `SEARCH_URL` deve incluir o parâmetro de estado do DF (já definido no `.env` template)
- Early stop: parar se nenhum anúncio da página atual já existir no banco
- Delay: `random.uniform(2, 5)` segundos entre páginas

### Parser
- Campos obrigatórios: `título`, `preço`, `url`, `data_publicacao`
- Qualquer campo ausente ou preço não parseável: descarta o anúncio inteiro, loga `WARNING` com URL

### Deal Finder
**Recorte temporal:** `data_publicacao >= agora - LOOKBACK_HOURS`

**Blacklist** (case-insensitive, checar se título *contém*):
```
"defeito", "não liga", "nao liga", "para retirar peça", "para retirada"
```

**Normalização de título** (aplicar nesta ordem antes de agrupar):
1. Lowercase
2. `unicodedata.normalize('NFKD')` + remove caracteres non-ASCII
3. Remove stopwords: `de da do para com sem em um uma`
4. Strip + colapso de espaços múltiplos

Exemplo: `"Placa de Vídeo GTX 1080 Ti 11GB"` → `"placa video gtx 1080 ti 11gb"`

**Score:**
- Calcular apenas se grupo tiver ≥ `MIN_GROUP_SIZE` anúncios após blacklist e recorte
- `score = (média_grupo - preço) / média_grupo`
- Ignorar score ≤ 0; filtrar apenas score ≥ `SCORE_THRESHOLD`

### Alert
Formato da mensagem Telegram:
```
🔥 [TÍTULO]
💰 R$ [PREÇO] | Score: [SCORE]%
📍 DF | [DATA]
🔗 [LINK]
```

### Scheduler + Logging
- Job em `try/except` completo; falha loga `ERROR` com traceback, não derruba o processo
- Logger central em `browser.py`, importado nos módulos de `core/`

| Situação | Nível |
|----------|-------|
| Ciclo iniciado/encerrado, deal salvo | `INFO` |
| Anúncio descartado, retry, falha Telegram | `WARNING` |
| Falha de módulo | `ERROR` |

Formato: `%(asctime)s [%(levelname)s] %(name)s: %(message)s` — destino: stdout

---

## 8. Self-Check

> Execute após cada implementação. Item ❌ → corrigir antes de encerrar.

```
[ ] Módulo correto conforme §5?
[ ] Respeita boundaries de §6?
[ ] Output esperado de §7 entregue?
[ ] Type hints em todas as funções públicas?
[ ] Nenhuma função > 30 linhas?
[ ] Nenhuma lógica de negócio fora de services/?
[ ] Dados validados antes de salvar?
[ ] Nenhum item dos Não-Objetivos (§2) implementado?
[ ] Erros logados com nível correto (nunca silenciados)?
[ ] Nenhum valor do .env hardcoded?
```

*LLM-as-Judge:* Para revisar código gerado, abrir sessão separada com: "Revise este código contra a SPEC.md §6 (Boundaries) e §7.1 (Regras de Negócio). Liste violações."

---

## 9. Modelo de Dados

```python
# src/data/models.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Deal:
    id: str                        # hash(url + data_publicacao) — determinístico
    titulo: str                    # Título original
    preco: float                   # Normalizado (nunca str)
    url: str                       # Link direto OLX
    data_publicacao: datetime
    score: Optional[float] = None  # None até deal_finder processar
```

---

## 10. Testes Obrigatórios

| Teste | Validação |
|-------|-----------|
| `test_calculate_score` | `price=300, avg=400` → `0.25` |
| `test_score_above_avg` | `price > avg` → score negativo |
| `test_no_duplicates` | Mesmo `id` 2x → 1 registro no banco |
| `test_price_normalization` | `"R$ 1.500,00"` → `1500.0` |
| `test_blacklist_filter` | Título com `"defeito"` → excluído |
| `test_72h_cutoff` | `data_publicacao` com 73h → excluído |
| `test_min_group_size` | Grupo com 2 anúncios → score não calculado |
| `test_title_normalization` | `"GTX 1080 Ti 11GB"` e `"gtx 1080ti - 11gb"` → mesmo grupo |
| `test_early_stop` | Página sem anúncios novos → crawler encerra antes da pág. 3 |

```bash
pytest -v                          # Testes
ruff check .                       # Lint
streamlit run src/ui/app.py        # UI
python src/core/scheduler.py       # Scraper manual
```

---

## Changelog

| Data | Versão | Mudança |
|------|--------|---------|
| 2026-05-09 | 2.2 | Auditoria final: removidas redundâncias, adicionados .env template,.gitignore, fix arquitetural Telegram (requests > python-telegram-bot), playwright-stealth pinado, requirements.txt referenciado |
| 2026-05-09 | 2.1 | Telegram, filtro DF, normalização, recorte temporal 72h, blacklist, anti-bot, logging, pipeline |
| 2026-05-09 | 2.0 | Refatoração Osmani |
| 2026-05-05 | 1.0 | Versão inicial |

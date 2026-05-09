# SPEC.md — OLX Deal Finder
> **Versão:** 2.1 | **Status:** MVP | **Princípio:** Spec guia tudo. Em caso de conflito, SPEC manda.

---

## 1. Visão e Objetivo

**O que é:** Sistema automatizado que monitora a OLX/DF, detecta anúncios subvalorizados de hardware e alerta o usuário via Telegram em tempo real.

**Por que existe:** Revendedores de peças de PC perdem oportunidades porque não conseguem monitorar o mercado 24/7. Este sistema faz isso por eles e notifica no celular, independente de onde o usuário esteja.

**Usuário:** Revendedor ativo de hardware usado que compra barato e revende com margem, sem acesso frequente ao computador onde o sistema roda.

**O que o usuário precisa:**
- Ver anúncios novos em menos de 5 minutos após publicação
- Ser notificado no Telegram imediatamente quando uma oportunidade surgir
- Saber de imediato se um preço está abaixo da média de mercado local (DF)
- Não perder tempo lendo anúncios sem valor
- Confiar que o sistema rodou sem precisar verificar manualmente

**Definição de pronto:**

| Critério | Métrica |
|----------|---------|
| Velocidade | Anúncios detectados em ≤ 5 min |
| Score correto | `score = (média - preço) / média` para qualquer input válido |
| Alertas precisos | Disparados **somente** quando `score ≥ 0.25` |
| Canal de alerta | Mensagem entregue no Telegram com título, preço, score e link |
| Integridade | Zero duplicatas no banco |
| Autonomia | Loop automático sem intervenção manual |
| Escopo geográfico | Apenas anúncios do Distrito Federal |

> Se qualquer critério falhar, a implementação não está completa.

---

## 2. Não-Objetivos (Fora do Escopo do MVP)

O agente **não deve implementar** nenhum dos itens abaixo, mesmo que pareça natural fazê-lo:

- Proxy rotation ou infraestrutura de evasão avançada (playwright-stealth é suficiente)
- Modelo de ML para scoring (a fórmula linear é suficiente para o MVP)
- Suporte a outros marketplaces (Enjoei, Mercado Livre, Facebook)
- Cache ou histórico de médias além das 72h definidas
- Autenticação de usuário na UI
- Cobertura de regiões além do Distrito Federal

> Se o agente quiser adicionar qualquer um destes, deve parar e perguntar.

---

## 3. Fluxo de Trabalho do Agente (Staged Workflow)

Siga estas etapas em ordem. **Não pule etapas.**

```
1. PLAN (read-only)
   └── Leia a spec completa antes de escrever qualquer código
   └── Entenda o módulo atual, seus inputs e outputs esperados (§8)
   └── Identifique dependências com outros módulos

2. IMPLEMENT
   └── Escreva apenas o módulo da tarefa atual
   └── Uma tarefa por sessão (ver §8)

3. SELF-CHECK
   └── Execute o checklist de §9 antes de encerrar
```

---

## 4. Pipeline de Execução (Runtime)

Este é o fluxo que ocorre a cada ciclo do scheduler. É a referência para implementar `scheduler.py`.

```
[APScheduler — a cada 5 min]
        │
        ▼
  browser.py ──── Inicia instância Playwright + stealth + User-Agent rotativo
        │         Em caso de falha: loga ERROR, aborta ciclo
        ▼
  crawler.py ──── Acessa SEARCH_URL (OLX/DF, do .env)
        │         Pagina até 3 páginas OU até não encontrar anúncios novos (early stop)
        │         Delay aleatório 2–5s entre páginas
        │         Timeout/429: retry (máx 2x com backoff), se persistir pula página + loga WARNING
        ▼
  parser.py ───── Para cada anúncio: extrai título, preço, link, data_publicacao
        │         Campo ausente ou preço inválido: descarta anúncio, loga WARNING com URL
        ▼
  processor.py ── Normaliza preços (→ float), remove duplicatas por hash (id)
        │
        ▼
  storage.py ──── Persiste apenas anúncios novos no SQLite
        │
        ▼
  deal_finder.py ─ Filtra anúncios das últimas 72h
        │          Aplica blacklist de títulos
        │          Agrupa por título normalizado (mín. 3 por grupo)
        │          Calcula score por anúncio
        │          Filtra score ≥ 0.25
        ▼
  alert.py ─────── Envia mensagem Telegram para cada oportunidade
        │          Falha de envio: loga ERROR, não interrompe ciclo
        ▼
  [Ciclo encerrado — aguarda próximo tick do scheduler]
```

**Regra de isolamento:** cada módulo recebe dados do anterior e entrega ao próximo. Nenhum módulo chama outro fora da sequência acima.

---

## 5. Tech Stack

| Componente | Tecnologia | Versão |
|------------|-----------|--------|
| Linguagem | Python | 3.14 |
| Scraping | Playwright | 1.58 |
| Stealth | playwright-stealth | latest |
| Processamento | Pandas | 3.0.2 |
| Armazenamento | SQLite | 3.53.1 |
| Interface | Streamlit | 1.57.0 |
| Agendamento | APScheduler | 3.11.2 |
| Alertas | python-telegram-bot | latest stable |

> Não substitua tecnologias sem passar pelo processo `⚠️ Ask first` de §7.

---

## 6. Estrutura do Projeto

```
src/
├── core/
│   ├── browser.py       # Setup Playwright + stealth + logger central
│   ├── crawler.py       # Navegação, paginação (máx 3 pág.), early stop, delays
│   ├── parser.py        # Extração de campos por anúncio, descarte de inválidos
│   └── scheduler.py     # Loop APScheduler, orquestra o pipeline completo
├── data/
│   ├── models.py        # Dataclasses (Deal)
│   ├── storage.py       # Leitura/escrita SQLite
│   └── processor.py     # Limpeza, normalização de preço, deduplicação
├── services/
│   ├── alert.py         # Envio de mensagens Telegram
│   └── deal_finder.py   # Normalização de título, score, filtros, blacklist
└── ui/
    └── app.py           # Interface Streamlit
```

**Regras:**
- Todo código novo vai dentro de `src/`
- Cada módulo tem uma única responsabilidade
- `crawler` e `parser` nunca chamam `deal_finder`; `deal_finder` nunca chama `crawler`
- O logger central é definido em `browser.py` e importado nos demais módulos de `core/`

---

## 7. Boundaries

### ✅ ALWAYS — Faça sem perguntar
- Seguir a estrutura de §6
- Type hints em todas as funções públicas
- Validar dados antes de salvar no banco
- Usar o logger central (não `print`) em todos os módulos de `core/`
- Executar o self-check de §9 após cada tarefa

### ⚠️ ASK FIRST — Pause e confirme com o usuário
- Alterar o modelo `Deal` (§10)
- Adicionar qualquer nova dependência
- Mudar o critério de score (atualmente 0.25)
- Alterar o recorte temporal (atualmente 72h)
- Alterar o mínimo de anúncios por grupo (atualmente 3)
- Modificar o schema do banco SQLite
- Alterar o fluxo de comunicação entre módulos

### 🚫 NEVER — Proibido absolutamente
- Misturar scraping com lógica de negócio em um mesmo arquivo
- Hardcode de URLs, tokens, credenciais ou configurações (use `.env`)
- Requests sem delay entre páginas
- Criar ou modificar arquivos fora de `src/`
- Commitar cookies ou tokens de sessão do Playwright
- Implementar mais de uma tarefa por sessão
- Silenciar exceções sem logar (`except: pass`)

---

## 8. Tarefas Modulares

> Uma tarefa por sessão. O agente recebe apenas a seção relevante, o modelo de dados (§10) e os boundaries (§7).

| # | Tarefa | Módulo | Input | Output esperado |
|---|--------|--------|-------|-----------------|
| 1 | Browser + Logger | `core/browser.py` | — | Instância Playwright com stealth ativa + logger configurado |
| 2 | Crawler | `core/crawler.py` | SEARCH_URL do .env | Lista de URLs de anúncios do DF (máx 3 pág., early stop) |
| 3 | Parser | `core/parser.py` | HTML de um anúncio | `Dict` com título, preço, link, data — ou descarta se inválido |
| 4 | Storage + Model | `data/storage.py` + `data/models.py` | Objeto `Deal` | Deal salvo no SQLite, sem duplicata |
| 5 | Processor | `data/processor.py` | Lista de deals brutos | Lista normalizada (preço float, sem duplicatas) |
| 6 | Deal Finder | `services/deal_finder.py` | Lista de `Deal` do banco | Lista com `score` preenchido, filtrada por `score ≥ 0.25` |
| 7 | Alert (Telegram) | `services/alert.py` | Lista de oportunidades | Mensagem Telegram enviada por oportunidade |
| 8 | Scheduler | `core/scheduler.py` | — | Loop APScheduler orquestrando o pipeline completo |
| 9 | UI | `ui/app.py` | Banco SQLite | Tabela de oportunidades renderizada |

---

## 8.1 Regras de Negócio por Módulo

### Crawler (`core/crawler.py`)
- URL de busca configurada via `SEARCH_URL` no `.env` (deve incluir filtro de região DF)
- Paginar no máximo 3 páginas
- **Early stop:** interromper se nenhum anúncio da página atual for novo (não presente no banco)
- Delay aleatório entre 2 e 5 segundos entre cada requisição de página
- Timeout ou HTTP 429: retry com backoff (máx 2 tentativas); se persistir, pular a página e logar `WARNING`

### Parser (`core/parser.py`)
- Extrair por anúncio: `título`, `preço`, `url`, `data_publicacao`
- Se qualquer campo estiver ausente ou o preço não for parseável: descartar o anúncio inteiro, logar `WARNING` com a URL, continuar para o próximo

### Deal Finder (`services/deal_finder.py`)

**Recorte temporal:** usar apenas anúncios com `data_publicacao` nas últimas 72 horas.

**Blacklist de títulos:** ignorar anúncios cujo título contenha qualquer uma das strings abaixo (case-insensitive):
```
"defeito", "não liga", "nao liga", "para retirar peça", "para retirada"
```

**Normalização de título (regra de agrupamento):**
Aplicar nesta ordem antes de agrupar:
1. Converter para lowercase
2. Remover acentos e caracteres especiais (`unicodedata.normalize`)
3. Remover stopwords: `"de", "da", "do", "para", "com", "sem", "em", "um", "uma"`
4. Strip e colapsar espaços múltiplos

Exemplo: `"Placa de Vídeo GTX 1080 Ti 11GB"` e `"GTX 1080Ti - 11gb EVGA"` → ambos normalizam para `"placa video gtx 1080 ti 11gb"`.

**Cálculo de score:**
- Mínimo de **3 anúncios** no grupo após blacklist e recorte temporal; caso contrário, não calcular
- `score = (média_do_grupo - preço_do_anúncio) / média_do_grupo`
- Score negativo = preço acima da média → descartar
- Filtrar apenas `score ≥ 0.25`

### Alert (`services/alert.py`)
- Enviar uma mensagem por oportunidade (token e chat_id no `.env`)
- Formato da mensagem:
  ```
  🔥 [TÍTULO]
  💰 R$ [PREÇO] | Score: [SCORE]%
  📍 DF | [DATA]
  🔗 [LINK]
  ```
- Falha de envio: logar `ERROR`, não interromper o ciclo

### Scheduler (`core/scheduler.py`)
- Intervalo: 5 minutos
- Cada job envolve o pipeline completo em `try/except`
- Falha em qualquer módulo: logar `ERROR` com traceback, aguardar próximo ciclo (não derrubar o processo)

---

## 9. Self-Check

> Execute após cada implementação. Se qualquer item for ❌, corrija antes de encerrar.

```
SELF-CHECK — [Nome da Tarefa]

[ ] Código está no módulo correto (§6)?
[ ] Respeita todos os boundaries de §7?
[ ] Cobre o output esperado da tarefa em §8?
[ ] Todas as funções públicas têm type hints?
[ ] Nenhuma função passa de 30 linhas?
[ ] Nenhuma lógica de negócio fora de services/?
[ ] Dados validados antes de salvar?
[ ] Nenhum item dos Não-Objetivos (§2) foi implementado?
[ ] Erros são logados (não silenciados) com o nível correto?
[ ] Nenhuma credencial ou URL hardcoded?
```

**LLM-as-Judge (para revisão de qualidade):**
Ao revisar código gerado, use o prompt abaixo numa sessão separada:
```
Revise este código em relação à SPEC.md.
Aponte violações de: separação de responsabilidades, type hints ausentes,
funções acima de 30 linhas, lógica de negócio fora de services/,
exceções silenciadas, e credenciais hardcoded.
```

---

## 10. Modelo de Dados

```python
# src/data/models.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Deal:
    id: str                        # Hash determinístico (url + data) — mesmo anúncio = mesmo id
    titulo: str                    # Título original do anúncio
    preco: float                   # Preço normalizado (float, nunca str)
    url: str                       # Link direto para o anúncio
    data_publicacao: datetime      # Data/hora de publicação
    score: Optional[float] = None  # None até o deal_finder processar
```

---

## 11. Anti-Bot: Estratégia de Scraping

| Camada | Técnica | Status |
|--------|---------|--------|
| Fingerprint | `playwright-stealth` (patcha `navigator.webdriver` e propriedades headless) | ✅ No escopo |
| Timing | Delay aleatório 2–5s entre páginas | ✅ No escopo |
| Identidade | User-Agent rotativo (lista definida em `browser.py`) | ✅ No escopo |
| Infraestrutura | Proxy residencial rotativo | 🚫 Fora do MVP |

A configuração de stealth e User-Agent é responsabilidade exclusiva de `browser.py`.

---

## 12. Logging

- Logger único configurado em `browser.py`, importado nos módulos de `core/`
- Níveis obrigatórios:

| Situação | Nível |
|----------|-------|
| Ciclo iniciado/encerrado, anúncio salvo | `INFO` |
| Anúncio descartado (campo inválido, blacklist) | `WARNING` |
| Retry de página, falha de envio Telegram | `WARNING` |
| Falha de módulo (crawler, browser, scheduler) | `ERROR` |

- Formato: `[TIMESTAMP] [NÍVEL] [módulo] mensagem`
- Destino: stdout (MVP)

---

## 13. Testes Obrigatórios (MVP)

| Teste | Validação |
|-------|-----------|
| `test_calculate_score` | `price=300, avg=400` → `score == 0.25` |
| `test_score_above_avg` | `price > avg` → `score < 0` |
| `test_no_duplicates` | Mesmo `id` inserido duas vezes → 1 registro |
| `test_price_normalization` | `"R$ 1.500,00"` → `1500.0` |
| `test_blacklist_filter` | Título com `"defeito"` → excluído do scoring |
| `test_72h_cutoff` | Anúncio com 73h de idade → excluído do scoring |
| `test_min_group_size` | Grupo com 2 anúncios → score não calculado |
| `test_title_normalization` | `"GTX 1080 Ti 11GB"` e `"gtx 1080ti - 11gb"` → mesmo grupo |
| `test_early_stop` | Página sem anúncios novos → crawler para antes da pág. 3 |

```bash
pytest -v                             # Testes
ruff check .                          # Lint
streamlit run src/ui/app.py           # UI
python src/core/scheduler.py          # Scraper manual
```

---

## Changelog

| Data | Versão | Mudança |
|------|--------|---------|
| 2026-05-09 | 2.1 | Adicionado: Telegram, filtro DF, normalização de título, recorte 72h, mín. 3 anúncios, blacklist, paginação limitada (3 pág. + early stop), delays 2–5s, anti-bot (stealth + UA rotativo), logging estruturado, error handling por módulo, pipeline de execução |
| 2026-05-09 | 2.0 | Refatoração baseada no framework Osmani |
| 2026-05-05 | 1.0 | Versão inicial |

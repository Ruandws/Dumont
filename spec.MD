# SPEC.md — OLX Deal Finder
> **Versão:** 2.0 | **Status:** MVP | **Princípio:** Spec guia tudo. Em caso de conflito, SPEC manda.

---

## 1. Visão e Objetivo

**O que é:** Sistema automatizado que monitora a OLX, detecta anúncios subvalorizados de hardware e alerta o usuário em tempo real.

**Por que existe:** Revendedores de peças de PC perdem oportunidades porque não conseguem monitorar o mercado 24/7. Este sistema faz isso por eles.

**Usuário:** Revendedor ativo de hardware usado que compra barato e revende com margem.

**O que o usuário precisa:**
- Ver anúncios novos em menos de 5 minutos após publicação
- Saber de imediato se um preço está abaixo da média de mercado
- Não perder tempo lendo anúncios sem valor

**Definição de pronto:**

| Critério | Métrica |
|----------|---------|
| Velocidade | Anúncios detectados em ≤ 5 min |
| Precisão de score| `score = (média - preço) / média` calculo acertivo para qualquer input |
| Alertas precisos | Disparados **somente** quando `score ≥ 0.25` |
| Integridade | Zero duplicatas no banco |
| Autonomia | Loop automático sem intervenção manual |

> Se qualquer critério falhar, a implementação não está completa. Não avance para a próxima tarefa.

---

## 2. Não-Objetivos (Fora do Escopo do MVP)

O agente **não deve implementar** nenhum dos itens abaixo, mesmo que pareça natural fazê-lo:

- Proxy rotation ou evasão de bloqueio de scraping
- Modelo de ML para scoring (a fórmula linear é suficiente para o MVP)
- Integração com Telegram, WhatsApp ou qualquer bot externo
- Suporte a outros marketplaces (Enjoei, Mercado Livre, Facebook)
- Cache ou histórico de médias entre sessões
- Autenticação de usuário na UI

> Estes itens existem para evitar scope creep. Se o agente quiser adicionar qualquer um, deve parar e perguntar.

---

## 3. Fluxo de Trabalho do Agente (Staged Workflow)

Siga estas etapas em ordem. **Não pule etapas.**

```
1. PLAN (read-only)
   └── Leia a spec completa antes de escrever qualquer código
   └── Entenda o módulo atual, seus inputs e outputs esperados (§7)
   └── Identifique dependências com outros módulos

2. IMPLEMENT
   └── Escreva apenas o módulo da tarefa atual
   └── Uma tarefa por sessão (ver §7)

3. SELF-CHECK
   └── Execute o checklist de §8 antes de encerrar
```

---

## 4. Tech Stack

| Componente | Tecnologia | Versão |
|------------|-----------|--------|
| Linguagem | Python | 3.14 |
| Scraping | Playwright | 1.58 |
| Processamento | Pandas | 3.0.2 |
| Armazenamento | SQLite | 3.53.1 |
| Interface | Streamlit | 1.57.0 |
| Agendamento | APScheduler | 3.11.2 |

> Não substitua tecnologias sem passar pelo processo `⚠️ Ask first` de §6.

---

## 5. Estrutura do Projeto

```
src/
├── core/
│   ├── browser.py       # Setup do Playwright
│   ├── crawler.py       # Navegação e paginação na OLX
│   ├── parser.py        # Extração de dados dos anúncios
│   └── scheduler.py     # Loop de agendamento (APScheduler)
├── data/
│   ├── models.py        # Dataclasses (Deal)
│   ├── storage.py       # Leitura/escrita SQLite
│   └── processor.py     # Limpeza, normalização, deduplicação
├── services/
│   ├── alert.py         # Disparo de notificações
│   └── deal_finder.py   # Score e filtragem de oportunidades
└── ui/
    └── app.py           # Interface Streamlit
```

**Regras:**
- Todo código novo vai dentro de `src/`
- Cada módulo tem uma única responsabilidade
- `crawler` e `parser` nunca chamam `deal_finder`; `deal_finder` nunca chama `crawler`

---

## 6. Boundaries

### ✅ ALWAYS — Faça sem perguntar
- Seguir a estrutura de §5
- Type hints em todas as funções públicas
- Validar dados antes de salvar no banco
- Executar o self-check de §8 após cada tarefa

### ⚠️ ASK FIRST — Pause e confirme com o usuário
- Alterar o modelo `Deal` (§9)
- Adicionar qualquer nova dependência
- Mudar o critério de score (atualmente 0.25)
- Modificar o schema do banco SQLite
- Alterar o fluxo de comunicação entre módulos

### 🚫 NEVER — Proibido absolutamente
- Misturar scraping com lógica de negócio em um mesmo arquivo
- Hardcode de URLs, tokens ou credenciais (use `.env`)
- Scraping sem delay entre requests
- Criar ou modificar arquivos fora de `src/`
- Commitar cookies ou tokens de sessão do Playwright
- Implementar mais de uma tarefa por sessão

---

## 7. Tarefas Modulares

> Uma tarefa por sessão. O agente recebe apenas a seção relevante, o modelo de dados (§9) e os boundaries (§6).

| # | Tarefa | Módulo | Input | Output esperado |
|---|--------|--------|-------|-----------------|
| 1 | Crawler | `core/crawler.py` | URL de busca da OLX | Lista de URLs de anúncios |
| 2 | Parser | `core/parser.py` | HTML de um anúncio | `Dict` com título, preço, link, data |
| 3 | Storage + Model | `data/storage.py` + `data/models.py` | Objeto `Deal` | Deal salvo no SQLite, sem duplicata |
| 4 | Processor | `data/processor.py` | Lista de deals brutos | Lista normalizada, sem duplicatas |
| 5 | Deal Finder | `services/deal_finder.py` | Lista de `Deal` | Lista com `score` preenchido, filtrada por `score ≥ 0.25` |
| 6 | Alert | `services/alert.py` | Lista de oportunidades | Notificação disparada |
| 7 | Scheduler | `core/scheduler.py` | — | Loop automático conectando todos os módulos |
| 8 | UI | `ui/app.py` | Banco SQLite | Tabela de oportunidades renderizada |

**Regra de negócio do Deal Finder (tarefa 5):**
- Agrupe anúncios por produto (normalize o título)
- Calcule média de preço do grupo
- `score = (média - preço) / média`
- Filtre apenas `score ≥ 0.25` (desconto de 25%+ abaixo da média)
- Não calcule score se o grupo tiver menos de 2 anúncios
- Score negativo = preço acima da média → descarte

---

## 8. Self-Check

> Execute após cada implementação. Se qualquer item for ❌, corrija antes de encerrar.

```
SELF-CHECK — [Nome da Tarefa]

[ ] Código está no módulo correto (§5)?
[ ] Respeita todos os boundaries de §6?
[ ] Cobre o output esperado da tarefa em §7?
[ ] Todas as funções públicas têm type hints?
[ ] Nenhuma função passa de 30 linhas?
[ ] Nenhuma lógica de negócio fora de services/?
[ ] Dados validados antes de salvar?
[ ] Nenhum item dos Não-Objetivos (§2) foi implementado?
```

**LLM-as-Judge (para revisão de qualidade):**
Ao revisar código gerado, use o prompt abaixo numa sessão separada:
```
Revise este código em relação à SPEC.md (seção de Boundaries e Estilo).
Aponte qualquer violação de separação de responsabilidades, type hints ausentes,
funções acima de 30 linhas ou lógica de negócio fora de services/.
```

---

## 9. Modelo de Dados

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

## 10. Testes Obrigatórios (MVP)

| Teste | Validação |
|-------|-----------|
| `test_calculate_score` | `price=300, avg=400` → `score == 0.25` |
| `test_score_above_avg` | `price > avg` → `score < 0` |
| `test_no_duplicates` | Mesmo `id` inserido duas vezes → 1 registro |
| `test_price_normalization` | `"R$ 1.500,00"` → `1500.0` |

```bash
pytest -v        # Rodar testes
ruff check .     # Lint
streamlit run src/ui/app.py   # UI
python src/core/scheduler.py  # Scraper manual
```

---

## Changelog

| Data | Versão | Mudança |
|------|--------|---------|
| 2026-05-09 | 2.0 | Refatoração baseada no framework Osmani (goal-first, não-objetivos, staged workflow, LLM-as-Judge) |
| 2026-05-05 | 1.0 | Versão inicial |

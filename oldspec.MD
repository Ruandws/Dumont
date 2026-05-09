# SPEC.md — OLX Deal Finder
> **Versão:** 1.0 | **Status:** MVP | **Princípio:** Especificação guia tudo. Código segue SPEC. Se conflito → SPEC manda.

---

## SUMÁRIO RÁPIDO (Para o Agente)
> Leia isto primeiro. Consulte as seções completas conforme a tarefa.

| Seção | O que cobre |
|-------|-------------|
| [1. Objetivo](#1-objetivo-por-quê) | Por que existe este sistema |
| [2. Critérios de Sucesso](#2-critérios-de-sucesso) | Quando está pronto e correto |
| [3. Tech Stack](#3-tech-stack) | Tecnologias específicas com versões |
| [4. Comandos](#4-comandos) | Executar, testar, lint — copie e cole |
| [5. Estrutura do Projeto](#5-estrutura-do-projeto) | Onde cada arquivo mora |
| [6. Fluxo Principal](#6-fluxo-principal) | Como o sistema se move de ponta a ponta |
| [7. Lógica de Negócio](#7-lógica-de-negócio-deal_finderpy) | Regras do deal_finder — core da aplicação |
| [8. Modelo de Dados](#8-modelo-de-dados) | Estrutura do `Deal` |
| [9. Estilo de Código](#9-estilo-de-código) | Convenções com exemplo real |
| [10. Testes](#10-testes) | O que validar e como |
| [11. Boundaries](#11-boundaries-crítico) | ✅ Sempre / ⚠️ Pergunte / 🚫 Nunca |
| [12. Tarefas Modulares](#12-tarefas-modulares) | Plano de execução isolada por agente |
| [13. Self-Check](#13-self-check) | Verificação após cada implementação |
| [14. Extensões Futuras](#14-extensões-futuras) | Fora do escopo do MVP |

---

## 1. Objetivo (Por Quê)

**O que:** Sistema automatizado que encontra oportunidades de compra na OLX com base em regras definidas pelo usuário.

**Por que:** Detectar anúncios subvalorizados antes da concorrência, alertar rapidamente e maximizar lucro em revenda de hardware.

**Usuário principal:** Revendedor de peças de PC que monitora o mercado de segunda mão ativamente.

**Jobs to be done:**
- Ver anúncios novos assim que publicados (< 5 min)
- Saber imediatamente se um preço está abaixo da média de mercado
- Não perder tempo lendo anúncios sem valor
- Confiar que o sistema rodou sem precisar verificar manualmente

---

## 2. Critérios de Sucesso

O sistema está funcionando corretamente quando:

| Critério | Métrica |
|----------|---------|
| Velocidade de detecção | Anúncios novos encontrados em **≤ 5 minutos** |
| Precisão do score | `score = (media - preco) / media` calculado corretamente para qualquer input |
| Qualidade dos alertas | Alertas disparados **apenas** quando `score >= 0.25` |
| Integridade dos dados | **Zero duplicatas** armazenadas no banco |
| Autonomia | Sistema roda automaticamente **sem intervenção manual** |

> **Conformance:** Se qualquer um dos critérios acima falhar, a implementação não está completa. Não avance para a próxima tarefa.

---

## 3. Tech Stack

> Seja preciso. Não substitua sem passar pelo processo de `⚠️ Ask first`.

| Componente | Tecnologia | Finalidade |
|------------|-----------|------------|
| Linguagem | **Python 3.14** | Base do projeto |
| Scraping | **Playwright 1.58** | Navegação e extração da OLX |
| Processamento | **Pandas 3.0.2** | Limpeza, normalização, agrupamento |
| Armazenamento | **SQLite 3.53.1** | Banco de dados local (MVP) |
| Interface | **Streamlit 1.57.0** | UI de monitoramento |
| Agendamento | **APScheduler 3.11.2** | Loop automático de execução |

---

## 4. Comandos

> Copie e execute direto. Sem ambiguidade.

```bash
# Rodar a aplicação (UI)
streamlit run src/ui/app.py

# Rodar o scraper manualmente
python src/core/scheduler.py

# Testes (implementar com pytest)
pytest -v

# Lint e formatação
ruff check .

# Git e versionamento
git add .
```

---

## 5. Estrutura do Projeto

```
src/
├── core/
│   ├── browser.py       # Setup e configuração do Playwright
│   ├── crawler.py       # Navegação e paginação na OLX
│   ├── parser.py        # Extração de dados dos anúncios
│   └── scheduler.py     # Loop de agendamento com APScheduler
├── data/
│   ├── models.py        # Estruturas de dados (dataclasses/Pydantic)
│   ├── storage.py       # Leitura e escrita no SQLite
│   └── processor.py     # Limpeza, normalização, deduplicação
├── services/
│   ├── alert.py         # Disparo de notificações
│   └── deal_finder.py   # Lógica de negócio: score e oportunidades
└── ui/
    └── app.py           # Interface Streamlit
```

**Regras de localização:**
- Todo código novo vai dentro de `src/`
- Nenhum arquivo fora de `src/` deve ser criado ou modificado pelo agente, com exceção de ``spec.md``
- Cada módulo tem responsabilidade única — não misture

---

## 6. Fluxo Principal

```
scheduler
   └── inicia execução periódica (APScheduler)
         └── crawler
               └── acessa OLX, navega páginas
                     └── parser
                           └── extrai: título, preço, link, data_publicacao, detalhes localizacao
                                 └── processor
                                       ├── remove duplicados
                                       └── padroniza preço (float, sem R$, sem pontos)
                                             └── storage
                                                   └── salva anúncios novos no SQLite
                                                         └── deal_finder
                                                               ├── agrupa por produto
                                                               ├── calcula média de preço
                                                               ├── calcula score
                                                               └── filtra oportunidades (score >= 0.25)
                                                                     └── alert
                                                                           └── dispara notificação
```

> **Lei de separação:** `crawler` e `parser` nunca chamam `deal_finder`. `deal_finder` nunca chama `crawler`. Cada camada fala apenas com a camada seguinte.

---

## 7. Lógica de Negócio (`deal_finder.py`)

**Entrada:** Lista de objetos `Deal` já salvos no banco

**Processo:**

```python
# Passo 1: Agrupar por produto (normalizar título)
# Passo 2: Calcular média de preço do grupo
avg_price = sum(prices) / len(prices)

# Passo 3: Calcular score por anúncio
score = (avg_price - price) / avg_price

# Passo 4: Filtrar oportunidades
opportunities = [deal for deal in deals if deal.score >= 0.25]
```

**Saída:** Lista de `Deal` com `score` preenchido, filtrada por oportunidades

**Critério MVP:**
- `score >= 0.25` → oportunidade (desconto de 25%+ abaixo da média)
- `score < 0` → preço acima da média → ignorar
- Sem dados suficientes para média (< 2 anúncios) → não calcular, não alertar

---

## 8. Modelo de Dados

**Arquivo:** `src/data/models.py`

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Deal:
    id: str                          # Hash único (url + data) para evitar duplicatas
    titulo: str                      # Título original do anúncio
    preco: float                     # Preço normalizado (float, sem formatação)
    url: str                         # Link direto para o anúncio na OLX
    data_publicacao: datetime        # Data/hora de publicação
    score: Optional[float] = None    # Calculado pelo deal_finder (None até processar)
```

**Contrato de dados:**
- `preco` sempre `float`, nunca `str`
- `id` gerado por hash determinístico — mesmo anúncio sempre gera mesmo `id`
- `score` é `None` quando não processado, `float` quando calculado

---

## 9. Estilo de Código

**Convenções:**
- Snake_case para tudo (variáveis, funções, arquivos)
- Funções com máximo de 30 linhas
- Type hints em todas as funções públicas
- Nenhuma lógica de negócio fora de `src/services/`
- Nenhum dado sensível hardcoded (URLs de config vão em `.env` ou arquivo de configuração)

**Exemplo canônico — use como referência:**

```python
def calculate_score(price: float, avg_price: float) -> float:
    """Retorna o score de desconto relativo à média do grupo."""
    if avg_price == 0:
        return 0.0
    return (avg_price - price) / avg_price
```

**Anti-padrões — nunca faça:**
```python
# ❌ Lógica de negócio no parser
def parse_deal(html):
    price = extract_price(html)
    score = (500 - price) / 500  # NUNCA: lógica de negócio aqui

# ❌ Dado sensível hardcoded
BASE_URL = "https://olx.com.br/search?q=gtx1080"  # NUNCA: vai em config
```

---

## 10. Testes

**MVP — validar obrigatoriamente:**

| Teste | O que verifica |
|-------|---------------|
| `test_calculate_score` | Score correto para price=300, avg=400 → 0.25 |
| `test_calculate_score_above_avg` | Score negativo quando price > avg |
| `test_remove_duplicates` | Mesmo `id` inserido duas vezes → apenas 1 registro |
| `test_price_normalization` | `"R$ 1.500,00"` → `1500.0` |

**Exemplo de teste esperado:**
```python
def test_calculate_score():
    assert calculate_score(price=300.0, avg_price=400.0) == 0.25

def test_no_opportunity_below_threshold():
    assert calculate_score(price=390.0, avg_price=400.0) < 0.25
```

**Futuro (pós-MVP):** Testes de integração com Playwright mockado, testes do storage com banco em memória.

---

## 11. Boundaries (Crítico)

### ✅ ALWAYS — Faça sem perguntar
- Seguir a estrutura de pastas definida em §5
- Separar scraping de lógica de negócio (lei de separação §6)
- Validar dados antes de salvar no banco
- Type hints em todas as funções públicas
- Executar self-check (§13) após cada implementação

### ⚠️ ASK FIRST — Pause e confirme com o usuário
- Mudar a estrutura do modelo `Deal` (§8)
- Adicionar nova dependência ao projeto
- Alterar o fluxo principal (§6)
- Mudar o critério de score (atualmente 0.25)
- Modificar o schema do banco SQLite

### 🚫 NEVER — Proibido absolutamente
- Misturar scraping com lógica de negócio em um mesmo módulo
- Hardcode de URLs, tokens, credenciais, configurações sensíveis
- Fazer scraping agressivo (sem delay entre requests — risco de bloqueio)
- Criar ou modificar arquivos fora de `src/`
- Commitar dados de sessão, cookies ou tokens do Playwright
- Fazer tudo em um único prompt — cada tarefa é isolada (§12)

---

## 12. Tarefas Modulares

> **Regra de ouro:** NUNCA implementar mais de uma tarefa por sessão de agente. Cada tarefa é autossuficiente.

| # | Tarefa | Módulo | Input esperado | Output esperado |
|---|--------|--------|----------------|-----------------|
| 1 | Criar crawler básico | `core/crawler.py` | URL da OLX | Lista de URLs de anúncios |
| 2 | Criar parser de dados | `core/parser.py` | HTML de um anúncio | Dict com título, preço, link, data |
| 3 | Implementar storage | `data/storage.py` + `data/models.py` | Objeto `Deal` | Deal salvo no SQLite sem duplicata |
| 4 | Implementar processor | `data/processor.py` | Lista de deals raw | Lista normalizada, sem duplicatas |
| 5 | Implementar score | `services/deal_finder.py` | Lista de `Deal` | Lista com `score` preenchido |
| 6 | Implementar alert | `services/alert.py` | Lista de oportunidades | Notificação disparada |
| 7 | Conectar scheduler | `core/scheduler.py` | — | Loop automático funcionando |
| 8 | UI básica Streamlit | `ui/app.py` | Banco SQLite | Tabela de oportunidades na tela |

**Para cada tarefa, o agente recebe apenas:**
- A seção desta SPEC relevante para aquela tarefa
- Os tipos de dados necessários (§8)
- Os boundaries (§11)
- O self-check (§13)

---

## 13. Self-Check

> **Obrigatório após cada implementação.** O agente responde antes de encerrar a sessão.

```
SELF-CHECK — [Nome da Tarefa]

[ ] Código está no módulo correto conforme §5?
[ ] Respeita os boundaries de §11?
[ ] Resolve o objetivo específico desta tarefa de §12?
[ ] Funções têm type hints?
[ ] Nenhuma função passa de 30 linhas?
[ ] Nenhuma lógica de negócio fora de services/?
[ ] Dados validados antes de salvar?

Se qualquer item for ❌ → corrigir ANTES de encerrar.
```

---

## 14. Extensões Futuras

> Fora do escopo do MVP. Não implementar agora. Registrado para referência.

- **Proxy rotation** — evitar bloqueio em alta frequência de scraping
- **ML para classificação** — modelo de scoring mais sofisticado que a fórmula linear
- **Integração Telegram** — alertas via bot no Telegram
- **Multi-marketplace** — estender para Enjoei, Mercado Livre, Facebook Marketplace
- **Cache de médias** — persistir médias históricas para scoring mais preciso

---

## Changelog

| Data | Versão | Mudança |
|------|--------|---------|
| 2026-05-05 | 1.0 | Versão inicial — MVP OLX Deal Finder |

---

*Este documento é a fonte da verdade. Código segue SPEC. Em caso de conflito, SPEC manda.*
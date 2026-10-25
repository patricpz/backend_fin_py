# Assistente Financeiro IA - Documentação Técnica

## Visão Geral

O Assistente Financeiro IA é um módulo inteligente que utiliza a API do Google Gemini para fornecer análises financeiras personalizadas, relatórios de redução de gastos e diagnósticos de saúde financeira.

## Arquitetura

```
app/ia/
├── __init__.py           # Exporta o FinancialAIAssistant
├── client.py             # Cliente wrapper para Google GenAI
├── ai_assistant.py       # Serviço principal com lógica de negócio
├── schemas.py            # Modelos Pydantic para requests/responses
└── prompts/              # Templates de prompts
    ├── __init__.py
    ├── analysis_gastos.py
    ├── relatorio_economia.py
    └── diagnostico.py

app/api/v1/
└── ai_assistant.py       # Rotas da API REST

claude/prompts/           # Documentação dos prompts (Markdown)
├── analysis_gastos.md
├── relatorio_economia.md
├── diagnostico.md
└── README.md
```

## Endpoints da API

### 1. Análise de Gastos
**POST** `/api/v1/ai/analyze-expenses`

Analisa padrões de consumo e identifica categorias de maior impacto.

**Request:**
```json
{
  "user_data": {
    "usuario": {
      "nome": "Carlos Silva",
      "meta_principal": "Criar reserva de emergência"
    },
    "resumo_geral": {
      "receita_total_mes": 12000,
      "despesa_total_mes": 9350,
      "saldo_liquido_mes": 2650
    },
    "despesas_por_categoria": {
      "moradia": {"valor": 3200, "porcentagem_da_receita": 26.67},
      "alimentacao": {"valor": 2100, "porcentagem_da_receita": 17.50},
      "lazer_e_estilo_de_vida": {"valor": 1400, "porcentagem_da_receita": 11.67}
    }
  },
  "period": "Agosto/2026"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "categorias_alto_impacto": [
      {
        "nome": "moradia",
        "valor": 3200,
        "porcentagem": 26.67,
        "sugestao": "Avaliar renegociação de aluguel/condomínio"
      }
    ],
    "oportunidades_economia": [
      {
        "categoria": "lazer_e_estilo_de_vida",
        "valor_atual": 1400,
        "valor_sugerido": 800,
        "economia_potencial": 600,
        "acao": "Substituir saídas por alternativas gratuitas"
      }
    ],
    "plano_acao": [
      {
        "prioridade": "ALTA",
        "categoria": "lazer_e_estilo_de_vida",
        "descricao": "Reduzir gastos de lazer em 40%",
        "estimativa_economia": 600
      }
    ]
  },
  "message": "Análise de gastos concluída"
}
```

---

### 2. Relatório de Redução de Gastos
**POST** `/api/v1/ai/economy-report`

Gera relatório detalhado com plano de ação mensurável.

**Request:**
```json
{
  "user_data": { ... },
  "period": "Agosto/2026"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "diagnostico_executivo": "Situação financeira positiva com oportunidade...",
    "situacao_liquida_atual": 2650,
    "principal_oportunidade": "Lazer e estilo de vida",
    "categorias_em_risco": [
      {
        "nome": "lazer_e_estilo_de_vida",
        "valor_atual": 1400,
        "valor_sugerido": 800,
        "reducao_percentual": 42.86,
        "impacto_qualidade_vida": "Baixo - alternativas gratuitas disponíveis"
      }
    ],
    "meta_reducao_mensal": 1500,
    "plano_acao": {
      "imediato": [
        "Reduzir lazer_e_estilo_de_vida para R$ 800",
        "Cancelar assinatura não utilizada"
      ],
      "estrategico": [
        "Negociar plano de academia",
        "Encontrar alternativas para outros_gastos"
      ]
    },
    "monitoramento": {
      "indicadores_chave": ["Gastos semanais por categoria", "Taxa de poupança"],
      "gatilhos_alerta": ["Gasto em lazer > R$ 200/semana"]
    }
  }
}
```

---

### 3. Diagnóstico Financeiro
**POST** `/api/v1/ai/diagnostic`

Avaliação completa da saúde financeira com recomendações por fase.

**Response:**
```json
{
  "success": true,
  "data": {
    "analise_geral": {
      "score_saude_geral": 75,
      "nivel_endividamento": 0.15,
      "taxa_poupanca": 22.08,
      "pontos_fortes": ["Renda estável", "Contas em dia", "Saldo positivo mensal"],
      "fraquezas": ["Fundo de emergência baixo", "Gastos supérfluos elevados"]
    },
    "recomendacoes": [
      {
        "fase": "FAZA_1",
        "titulo": "Construir Reserva de Emergência",
        "descricao": "Destinar 40% do saldo livre para reserva",
        "impacto_financeiro": 1000,
        "acao_prioritaria": true
      }
    ],
    "metas_smart": [
      {
        "meta": "Atingir 3 meses de despesas em reserva",
        "valor_atual": 5000,
        "valor_meta": 15000,
        "prazo": "6 meses",
        "responsabilidade": "Usuário"
      }
    ]
  }
}
```

---

### 4. Estratégias de Otimização
**POST** `/api/v1/ai/strategies`

Sugere estratégias personalizadas por prioridade.

**Request:**
```json
{
  "user_data": { ... },
  "priorities": ["emergência", "investimento", "redução_gastos"]
}
```

---

### 5. Análise de Transações
**POST** `/api/v1/ai/analyze-transactions`

Analisa transações individuais para padrões e oportunidades.

---

## Como Usar no Frontend

### Exemplo de Integração (React/TypeScript)

```typescript
interface UserData {
  usuario: {
    nome: string;
    meta_principal: string;
  };
  resumo_geral: {
    receita_total_mes: number;
    despesa_total_mes: number;
    saldo_liquido_mes: number;
  };
  despesas_por_categoria: Record<string, { valor: number; porcentagem_da_receita: number }>;
}

const API_BASE = '/api/v1';

async function analyzeExpenses(userData: UserData, period: string = 'mês atual') {
  const response = await fetch(`${API_BASE}/ai/analyze-expenses`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ user_data: userData, period })
  });
  return response.json();
}

async function getEconomyReport(userData: UserData, period: string = 'mês atual') {
  const response = await fetch(`${API_BASE}/ai/economy-report`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ user_data: userData, period })
  });
  return response.json();
}

async function getFinancialDiagnostic(userData: UserData, period: string = 'mês atual') {
  const response = await fetch(`${API_BASE}/ai/diagnostic`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ user_data: userData, period })
  });
  return response.json();
}
```

### Fluxo Recomendado

1. **Coleta de Dados**: Frontend busca dados financeiros do usuário (transações, categorias, contas)
2. **Construção do Payload**: Estrutura os dados no formato esperado pelos endpoints
3. **Chamada Paralela**: Pode chamar `analyze-expenses` + `diagnostic` em paralelo
4. **Exibição**: Mostra resultados em dashboards/cards no frontend

---

## Configuração

### Variáveis de Ambiente (.env)
```env
GEMINI_API_KEY=AIzaSyCheWvjgDkk9Xsn_jZinzCwhzItl-f9Cr4
```

### Dependências
```toml
google-genai>=2.29.0
python-dotenv>=1.0.0
```

---

## Prompts

Os prompts são armazenados em dois locais:

### 1. Código (Python) - `app/ia/prompts/`
Templates executáveis usados em runtime:
- `analysis_gastos.py` - `ANALYSIS_PROMPT`
- `relatorio_economia.py` - `ECONOMY_REPORT_PROMPT`
- `diagnostico.py` - `DIAGNOSTIC_PROMPT`

### 2. Documentação (Markdown) - `claude/prompts/`
Documentação legível para manutenção:
- `analysis_gastos.md`
- `relatorio_economia.md`
- `diagnostico.md`
- `README.md`

---

## Estrutura de Dados Esperada

O `user_data` deve conter:

```json
{
  "usuario": {
    "nome": "string",
    "meta_principal": "string"
  },
  "resumo_geral": {
    "moeda": "BRL",
    "saldo_total_disponivel": "number",
    "receita_total_mes": "number",
    "despesa_total_mes": "number",
    "saldo_liquido_mes": "number",
    "taxa_poupanca_pct": "number"
  },
  "contas_bancarias": "array",
  "cartoes_de_credito": "array",
  "despesas_por_categoria": "object",
  "transacoes_recentes": "array"
}
```

---

## Tratamento de Erros

Todos os endpoints retornam:
- **200**: Sucesso
- **400**: Erro de validação (ex: API key não configurada)
- **401**: Não autenticado
- **500**: Erro interno (ex: falha na API do Gemini)

---

## Segurança

- Endpoints protegidos por JWT (requer `get_current_user`)
- Dados financeiros não são armazenados na IA, apenas processados
- API Key do Gemini em variável de ambiente (não no código)
- Rate limiting via `slowapi` (configurado globalmente)

---

## Testes

```bash
# Iniciar servidor
uvicorn app.main:app --reload --port 8000

# Testar via Swagger UI
# Acesse: http://localhost:8000/docs
```

---

## Próximos Passos

1. **Cache de Respostas**: Implementar Redis para cache de análises recorrentes
2. **Streaming**: Adicionar suporte a streaming para respostas longas
3. **Histórico**: Salvar análises anteriores para comparação temporal
4. **Webhooks**: Notificar frontend quando análise assíncrona completar
5. **Métricas**: Adicionar telemetria de uso e qualidade das respostas

---

## Referências

- [Google GenAI Python SDK](https://github.com/googleapis/python-genai)
- [Gemini API Docs](https://ai.google.dev/gemini-api/docs)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
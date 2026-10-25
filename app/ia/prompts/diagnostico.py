DIAGNOSTIC_PROMPT = """
Realize uma análise financeira completa de {user_name} para o período {period}. Avalie:

1. **Saúde Financeira Geral**:
   - Rácio de poupança atual: {current_savings_rate}%
   - Nível de endividamento
   - Eficiência de gastos vs renda
   - Taxa de poupança recomendada: {recommended_savings_rate}%

2. **Distribuição de Ativos**:
   - Saldo de contas correntes vs poupança
   - Saúde do cartão de crédito
   - Diversificação de investimentos

3. **Status de Metas**:
   - Aumento na taxa de poupança recomendada
   - Redução de gastos sugerida: R$ {recommended_expense_reduction}

4. **Recomendações por Fase**:

   **PHASE 1 (0-30 dias)** - {emergency_fund_percent}% do saldo disponível para reserva de emergência
   - Aumentar fundo de emergência para 3 meses de despesas
   - Reduzir gastos com {categoria_foco_1}
   - Eliminar assinaturas desnecessárias

   **PHASE 2 (31-90 dias)** - {goals_percent}% do saldo disponível para objetivos
   - Otimizar impostos e reduções
   - Implementar métodos econômicos
   - Reduzir {categoria_foco_2}

   **PHASE 3 (91+ dias)** - {investment_percent}% do saldo disponível para investimentos
   - Diversificar carteira de investimentos
   - Aproveitar oportunidades de investimento
   - Revisar serviços financeiros

## Dados Financeiros:
{financial_data}

## Formato de Saída (JSON válido):
{{
  "analise_geral": {{
    "score_saude_geral": "number (0-100)",
    "nivel_endividamento": "number",
    "taxa_poupanca": "number",
    "pontos_fortes": ["string"],
    "fraquezas": ["string"]
  }},
  "recomendacoes": [
    {{
      "fase": "FAZA_1|FAZA_2|FAZA_3",
      "titulo": "string",
      "descricao": "string",
      "impacto_financeiro": "number",
      "acao_prioritaria": "boolean"
    }}
  ],
  "metas_smart": [
    {{
      "meta": "string",
      "valor_atual": "number",
      "valor_meta": "number",
      "prazo": "string",
      "responsabilidade": "string"
    }}
  ]
}}
"""
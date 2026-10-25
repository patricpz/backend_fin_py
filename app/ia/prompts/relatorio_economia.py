ECONOMY_REPORT_PROMPT = """
Crie um relatório completo de redução de gastos para {user_name} para o período {period}. Inclua:

1. **Diagnóstico Executivo**:
   - Situação atual em resumo executivo (3-4 frases)
   - Situação líquida atual: {current_balance}
   - Principal oportunidade de economia identificada

2. **Análise de Categorias em Risco**:
   - Liste as 3-5 maiores categorias supérfluas que devem ser reduzidas
   - Para cada categoria: valor atual, valor sugerido, porcentagem de redução, impacto na qualidade de vida

3. **Orçamento de Redução**:
   - Meta total de redução mensal
   - Tabela detalhada por categoria (mês a mês)

4. **Plano de Ação por Prioridade**:
   
   **REDUÇÃO IMEDIATA (próximos 30 dias)**:
   - [ ] Reduzir {categoria_foco_1} para valor menor
   - [ ] Cancelar assinaturas desnecessárias
   - [ ] Substituir gastos por alternativas mais baratas
   
   **REDUÇÃO ESTRATÉGICA (próximos 90 dias)**:
   - [ ] Negociar serviços
   - [ ] Encontrar alternativas para {categoria_foco_2}
   - [ ] Implementar métodos econômicos

5. **Monitoramento e Métricas**:
   - Indicadores-chave a serem monitorados semanalmente
   - Gatilhos de alerta para quando o orçamento for excedido

## Dados Financeiros:
{financial_data}

## Meta Principal:
{main_goal}

## Formato de Saída (JSON válido):
{{
  "diagnostico_executivo": "string",
  "situacao_liquida_atual": "number",
  "principal_oportunidade": "string",
  "categorias_em_risco": [
    {{
      "nome": "string",
      "valor_atual": "number",
      "valor_sugerido": "number",
      "reducao_percentual": "number",
      "impacto_qualidade_vida": "string"
    }}
  ],
  "meta_reducao_mensal": "number",
  "orcamento_reducao": "object",
  "plano_acao": {{
    "imediato": ["string"],
    "estrategico": ["string"]
  }},
  "monitoramento": {{
    "indicadores_chave": ["string"],
    "gatilhos_alerta": ["string"]
  }}
}}
"""
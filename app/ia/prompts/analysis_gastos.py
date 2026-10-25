ANALYSIS_PROMPT = """
Analise os dados financeiros do usuário {user_name} para o período {period}. Foque em:

1. **Identificação de categorias de alto gasto**: Quais categorias representam mais de 20% do total de gastos?
2. **Comparação de tendências**: Como os gastos variam mês a mês para cada categoria principal?
3. **Oportunidades de economia**: Identifique 3-5 categorias onde o usuário pode reduzir significativamente os gastos sem impactar a qualidade de vida
4. **Sugestões práticas**: Forneça ações concretas baseadas nos dados analisados
5. **Meta financeira**: Para o objetivo principal "{main_goal}", sugira ajustes necessários

## Dados Financeiros:
{financial_data}

## Formato de Saída (JSON válido):
{{
  "categorias_alto_impacto": [
    {{
      "nome": "string",
      "valor": "number",
      "porcentagem": "number",
      "sugestao": "string"
    }}
  ],
  "oportunidades_economia": [
    {{
      "categoria": "string",
      "valor_atual": "number",
      "valor_sugerido": "number",
      "economia_potencial": "number",
      "acao": "string"
    }}
  ],
  "plano_acao": [
    {{
      "prioridade": "ALTA|MEDIA|BAIXA",
      "categoria": "string",
      "descricao": "string",
      "estimativa_economia": "number"
    }}
  ]
}}
"""
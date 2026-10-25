from google import genai

mockDataJson = {
  "usuario": {
    "nome": "Carlos Silva",
    "periodo_analise": "Agosto/2026",
    "meta_principal": "Criar reserva de emergência e reduzir despesas supérfluas"
  },
  "resumo_geral": {
    "moeda": "BRL",
    "saldo_total_disponivel": 8450.00,
    "receita_total_mes": 12000.00,
    "despesa_total_mes": 9350.00,
    "saldo_liquido_mes": 2650.00,
    "taxa_poupanca_pct": 22.08
  },
  "contas_bancarias": [
    {
      "instituicao": "Banco Alfa",
      "tipo_conta": "Conta Corrente",
      "saldo": 3450.00
    },
    {
      "instituicao": "Banco Beta",
      "tipo_conta": "Reserva de Emergência (Rendimento 100% CDI)",
      "saldo": 5000.00
    }
  ],
  "cartoes_de_credito": [
    {
      "nome_cartao": "Visa Platinum",
      "limite_total": 15000.00,
      "fatura_atual": 4200.00,
      "limite_disponivel": 10800.00,
      "vencimento": "2026-08-25"
    }
  ],
  "despesas_por_categoria": {
    "moradia": {
      "valor": 3200.00,
      "porcentagem_da_receita": 26.67
    },
    "alimentacao": {
      "valor": 2100.00,
      "porcentagem_da_receita": 17.50
    },
    "lazer_e_estilo_de_vida": {
      "valor": 1400.00,
      "porcentagem_da_receita": 11.67
    },
    "transporte": {
      "valor": 850.00,
      "porcentagem_da_receita": 7.08
    },
    "assinaturas_e_servicos": {
      "valor": 350.00,
      "porcentagem_da_receita": 2.92
    },
    "outros_gastos": {
      "valor": 1450.00,
      "porcentagem_da_receita": 12.08
    }
  },
  "transacoes_recentes": [
    {
      "id": "tx_101",
      "data": "2026-08-14",
      "descricao": "Supermercado Extra",
      "categoria": "alimentacao",
      "tipo": "débito",
      "valor": 450.20
    },
    {
      "id": "tx_102",
      "data": "2026-08-12",
      "descricao": "Depósito Salário",
      "categoria": "receita",
      "tipo": "crédito",
      "valor": 12000.00
    },
    {
      "id": "tx_103",
      "data": "2026-08-10",
      "descricao": "Academia Fit",
      "categoria": "assinaturas_e_servicos",
      "tipo": "crédito",
      "valor": 119.90
    },
    {
      "id": "tx_104",
      "data": "2026-08-05",
      "descricao": "Jantar Restaurante",
      "categoria": "lazer_e_estilo_de_vida",
      "tipo": "crédito",
      "valor": 320.00
    }
  ]
}

# Configure sua chave de API salva nos Secrets do Colab (ícone de chave no menu esquerdo)
client = genai.Client(api_key=userdata.get("GEMINI_API_KEY"))

prompt = "Ola Gemini, tudo bem?"

prompt_contextualizado = "Qual o seu limite nessa interação de IA com backend?"

prompt_contextualizado = "Analise meu contexto financeiro com o meu usuario e me entregue de forma orgazida o meu status financeiro que esta presente nesse json" + str(mockDataJson)

prompt_para_financas_positivas = "Com a leitura do prompt" + str(prompt_contextualizado) + "Quero que faça um plano de investimentos em json para que meu usuario possa investir seu dinheiro"

response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents={prompt_para_financas_positivas}
)

print(response.text)
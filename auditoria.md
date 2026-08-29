Quero que você faça uma auditoria técnica completa deste projeto, que é um backend Python.

IMPORTANTE:
- NÃO altere nenhum arquivo inicialmente.
- NÃO crie arquivos.
- NÃO instale pacotes sem minha autorização.
- NÃO execute comandos destrutivos.
- NÃO faça migrations, DROP, DELETE, reset de banco ou alterações no banco.
- NÃO leia nem exiba o conteúdo de arquivos secretos, especialmente:
  .env
  .env.*
  *.pem
  *.key
  credentials*
  secrets*
- Nunca invente erros ou resultados.
- Se um comando falhar, mostre o erro real e explique sua causa.
- Se não conseguir verificar alguma coisa, diga explicitamente que não foi possível verificar.
- Não tente corrigir automaticamente os problemas.
- Ao encontrar um problema, registre o arquivo e a linha quando possível.

OBJETIVO:
Quero descobrir problemas reais no projeto antes de fazer qualquer alteração.

FASE 1 — ESTRUTURA
1. Analise a estrutura do projeto.
2. Identifique:
   - app/
   - tests/
   - alembic/
   - configurações
   - pyproject.toml
   - arquivos de dependências
   - Docker/configurações de infraestrutura, se existirem.
3. Explique brevemente a responsabilidade de cada parte importante.

FASE 2 — CONFIGURAÇÃO E DEPENDÊNCIAS
Analise:
- pyproject.toml
- configuração do uv
- versão do Python
- dependências
- dependências incompatíveis ou desnecessárias
- configuração de build
- configuração de lint
- configuração de testes.

Execute apenas comandos seguros para verificar essas informações.

FASE 3 — CÓDIGO
Analise o código dentro de app/.

Procure por:
- imports quebrados
- código inacessível
- variáveis não utilizadas
- funções com problemas
- tratamento incorreto de exceções
- problemas de async/await
- problemas de tipagem
- problemas de arquitetura
- duplicação de código
- possíveis bugs
- problemas de segurança
- configurações incorretas
- problemas de gerenciamento de conexão com banco
- problemas de autenticação/autorização
- problemas de validação de entrada
- problemas de logging.

Não assuma que algo é um erro apenas porque você faria de outra maneira.
Diferencie:
CRÍTICO
ALTO
MÉDIO
BAIXO
SUGESTÃO

FASE 4 — BANCO E ALEMBIC
Analise:
- models
- configuração do banco
- integração ORM
- migrations
- alembic/env.py
- versões das migrations
- possíveis conflitos entre models e migrations.

Execute somente comandos de leitura/diagnóstico.

NÃO execute:
- alembic upgrade
- alembic downgrade
- database reset
- DROP
- DELETE
- migrate
sem minha autorização explícita.

FASE 5 — TESTES
Execute os testes existentes.

Use comandos seguros, como:
pytest
ruff
mypy, caso esteja configurado.

Não altere os testes.

Para cada erro encontrado informe:

Arquivo:
Linha:
Erro:
Causa provável:
Impacto:
Como corrigir:
Confiança: alta/média/baixa

FASE 6 — BUILD
Verifique se o projeto consegue ser construído usando o gerenciador de dependências configurado.

Se houver erro de build, não tente corrigir automaticamente.

Explique:
1. qual etapa falhou;
2. qual pacote/componente causou o problema;
3. se o problema é código, dependência, configuração ou ambiente;
4. como corrigir.

FASE 7 — RELATÓRIO FINAL

No final, produza um relatório organizado assim:

# AUDITORIA DO PROJETO

## Resumo
- Estado geral:
- Quantidade de problemas:
- Problemas críticos:
- Problemas altos:
- Problemas médios:
- Problemas baixos:

## 1. Erros confirmados
Liste somente erros que foram realmente reproduzidos ou comprovados.

## 2. Possíveis problemas
Liste problemas que parecem existir, mas que não puderam ser confirmados.

## 3. Segurança
Liste vulnerabilidades ou riscos encontrados.

## 4. Banco/Alembic
Liste problemas relacionados ao banco e migrations.

## 5. Testes
Mostre os resultados dos testes.

## 6. Build
Mostre o resultado do build.

## 7. Recomendações
Crie uma ordem de prioridade para correção.

IMPORTANTE:
Não faça nenhuma alteração no projeto durante esta auditoria.
Depois de terminar, aguarde minha autorização antes de corrigir qualquer coisa.
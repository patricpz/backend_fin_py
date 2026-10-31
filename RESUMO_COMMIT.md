# Resumo das Alterações para Commit

Este documento consolida todas as implementações, correções e testes realizados no backend para orientar o registro no controle de versão (Git).

---

## 📌 Sugestão de Mensagem de Commit

```git
feat: adiciona notificacoes, web push vapid, despesas parceladas e correcao de saldo/tipo

- Ajusta calculo de saldo da Conta (balance) e tipo explicito de Transacao (receita/despesa/transferencia).
- Implementa endpoints de despesas parceladas (/expenses/installments) com ajuste de centavos e lock anti-concorrencia.
- Implementa central de notificacoes (/notifications) com paginacao opaca por cursor e contagem unread_count.
- Adiciona gestao de preferencias de alerta (/notification-preferences) com validacao IANA e quiet hours.
- Implementa suporte a Web Push com VAPID (/push/public-key e /push/subscriptions) com remocao automatica em 404/410.
- Cria motor de alertas com regras puras (rules.py), TemplateProvider e scheduler com APScheduler.
- Adiciona migracoes Alembic 004 e 005.
- Cria testes unitarios e de integracao (116 testes passando com 100% de sucesso).
- Adiciona guia completo de integracao frontend (GUIA_FRONTEND_NOVAS_FUNCIONALIDADES.md).
```

---

## 🚀 Principais Funcionalidades e Correções

### 1. Correção de Conta, Transação e Sinal do Saldo
* **Problema:** A Conta retornava `balance`, mas a Transação não informava `tipo`, gerando despesas com valores positivos e inconsistência de saldo no front.
* **Solução:**
  * Campo `tipo` explícito (`receita`, `despesa`, `transferencia`) garantido no modelo, repositórios, serviços e schemas.
  * Cálculo consolidado no banco: $\text{balance} = \text{saldo\_inicial} + \sum \text{receitas} - \sum \text{despesas}$.
  * Transferências tratadas com débito/crédito direto nas contas sem distorcer o fluxo de receitas/despesas.

### 2. Módulo de Despesas Parceladas (`/expenses/installments`)
* **Listagem plana (`GET /expenses/installments`):** Suporte a `include_completed=true|false`, métricas calculadas em tempo de execução (`progress_percent`, `paid_amount`, `remaining_amount`, `next_due_date`).
* **Ajuste de centavos:** Truncamento em 2 casas decimais e alocação do resíduo de centavos na última parcela (ex.: R$ 1.000 em 3x = 333,33 + 333,33 + 333,34).
* **Cálculo de vencimentos (`_add_months`):** Trata corretamente anos bissextos e meses com 28, 29, 30 e 31 dias.
* **Pagamento atômico (`PATCH /expenses/{id}/installments/pay`):** Concorrência protegida com `SELECT ... FOR UPDATE` (PostgreSQL) e lock transacional, retornando `409 Conflict` se a despesa já estiver quitada.
* **Ajuste manual (`PATCH /expenses/{id}/installments`):** Permite corrigir parcelas pagas com validação de intervalo `[0, installment_count]`.
* **Criação (`POST /expenses/installments` e `POST /expenses`):** Rejeita `paid_installments` na criação inicial (inicia em 0) e valida mínimo de 2 parcelas.

### 3. Central de Notificações (`/notifications`)
* **Listagem (`GET /notifications`):**
  * Paginação opaca via cursor codificado em Base64 (`created_at|id`) ordenado de forma decrescente com desempate por ID.
  * Validação de `limit` entre 1 e 50 (retorna `422` acima de 50).
  * Contador global `unread_count` invariante a filtros de página ou tipo.
* **Leitura:** `PATCH /notifications/{id}/read` (idempotente, 204 No Content) e `POST /notifications/read-all` (204 No Content).
* **Feedback (`POST /notifications/{id}/feedback`):** Ações aceitas (`opened`, `dismissed`, `helpful`, `not_helpful`, `executed`), gravando histórico e atualizando o status.
* **Rota de Teste (`POST /notifications/test`):** Habilitada apenas quando `APP_ENV=development` (retorna 404 em produção).

### 4. Preferências de Alertas (`/notification-preferences`)
* `GET /notification-preferences`: Retorna 200 criando automaticamente as preferências padrão se ainda não existirem (sem 404).
* `PUT /notification-preferences`: Validação estrita de sensibilidade (`low`, `medium`, `high`), fuso IANA via `zoneinfo`, limite diário [0, 20] e formato de quiet hours (`HH:MM`).

### 5. Web Push Notification com VAPID (`/push`)
* `GET /push/public-key`: Retorna a chave VAPID pública ou 503 se não configurada.
* `POST /push/subscriptions`: Validação HTTPS, campos criptográficos obrigatórios e upsert por endpoint (201 para nova, 200 para atualização).
* `DELETE /push/subscriptions/{id}`: 204 ou 404.
* **Despacho em Background:** Envio automático via `pywebpush` no pipeline do `NotificationService`, excluindo do banco inscrições que retornam status 404 ou 410 (GCM/FCM expirados).

### 6. Motor de Alertas e Agendador (`app/alerts/`)
* **Regras puras (`rules.py`):**
  * Excesso de orçamento em categorias (80% e 100%).
  * Pico de gastos (gasto único $\ge 3\times$ a média diária).
  * Parcela com vencimento em até 3 dias.
* **Templates e Insights (`insights.py`):** Arquitetura com interface `InsightProvider` e implementação determinística `TemplateProvider`.
* **Agendador (`scheduler.py`):** Integração com APScheduler para checks diários às 08:00 no fuso do usuário e horários para parcelas (`max_instances=1`, `coalesce=True`), controlado por `NOTIFICATION_JOBS_ENABLED`.

---

## 📂 Arquivos Alterados e Criados

### 1. Migrações de Banco de Dados
* `alembic/versions/004_add_parcelada_fields.py`: Adiciona colunas de parcelamento na tabela `transactions`.
* `alembic/versions/005_notifications_push_expenses.py`: Adiciona tabelas `notifications`, `notification_preferences`, `push_subscriptions`, `notification_feedback` e coluna `category_name`.

### 2. Modelos e Configuração
* `app/core/config.py`: Variáveis de ambiente VAPID, provedor de notificação e feature flags.
* `app/models/transaction.py`: Adição de `category_name` e propriedades de tipo/saldo.
* `app/models/notification.py`: Modelos SQLAlchemy para notificações, preferências, push e feedback.
* `app/models/__init__.py`: Exportação dos novos modelos.

### 3. Schemas (Pydantic v2)
* `app/schemas/transaction.py`: Ajuste de validação e exposição de `tipo` e `balance`.
* `app/schemas/account.py`: Garantia do campo `balance` coerente com o saldo calculado.
* `app/schemas/expense.py`: Schemas para criação, atualização e resposta plana de despesas parceladas.
* `app/schemas/notification.py`: Envelopes de listagem com cursor opaco, feedback e preferências.
* `app/schemas/push.py`: Validação de chaves VAPID e endpoints HTTPS.

### 4. Repositórios e Serviços
* `app/repositories/account_repository.py`: Cálculo unificado de saldo com receitas e despesas.
* `app/repositories/transaction_repository.py`: Ajuste de filtros e ordenação com tipo explícito.
* `app/repositories/notification_repository.py`: Paginação por cursor, unread_count, upsert de preferências e inscrições push.
* `app/services/transaction_service.py`: Tratamento de tipo e validações de saldo.
* `app/services/expense_service.py`: Lógica financeira de parcelas, centavos na última parcela e lock de concorrência.
* `app/services/notification_service.py`: Pipeline estrito de alertas, quiet hours, sensibilidade, deduplicação e push.

### 5. Regras de Alerta e Jobs
* `app/alerts/rules.py`: Funções puras de checagem financeira.
* `app/alerts/insights.py`: Provedor de templates e mensagens formatadas.
* `app/alerts/scheduler.py`: Jobs agendados com APScheduler.

### 6. Rotas e Endpoints (FastAPI)
* `app/api/v1/expenses.py`: Rotas de parcelamento (`/expenses/installments`, `/pay`, etc.).
* `app/api/v1/notifications.py`: Rotas de notificações, preferências e feedback.
* `app/api/v1/push.py`: Rotas de chaves públicas e subscrições Web Push.
* `app/main.py`: Inicialização do scheduler no lifespan e montagem de rotas tanto na raiz quanto em `/api/v1`.

### 7. Documentação e Testes
* `GUIA_FRONTEND_NOVAS_FUNCIONALIDADES.md`: Guia passo a passo com TypeScript, Service Worker e tabela De/Para.
* `FRONTEND_INTEGRATION.md`: Atualização da documentação existente.
* `tests/test_expense_installments_unit.py`: Testes unitários de regras, centavos e bissexto.
* `tests/test_expenses_api.py`: Testes de integração de CRUD, isolamento e concorrência.
* `tests/test_notifications_and_push_api.py`: Testes de integração de notificações, push, cursor e regras de ambiente.
* `tests/test_conta_transacao_saldo.py`: Testes de coerência de saldo e tipo explícito.

---

## 🧪 Status dos Testes

Execução completa da suíte de testes do projeto:

```bash
.\.venv\Scripts\python -m pytest
# Resultado: 116 passed in 18.63s (100% de sucesso)
```

---

## 💻 Comandos Sugeridos para o Commit

```bash
# 1. Adicionar os arquivos modificados e novos
git add alembic/versions/004_add_parcelada_fields.py
git add alembic/versions/005_notifications_push_expenses.py
git add app/
git add tests/
git add FRONTEND_INTEGRATION.md
git add GUIA_FRONTEND_NOVAS_FUNCIONALIDADES.md
git add RESUMO_COMMIT.md
git add pyproject.toml
git add .gitignore

# 2. Criar o commit
git commit -m "feat: adiciona notificacoes, web push vapid, despesas parceladas e correcao de saldo/tipo"

# 3. Enviar para a branch remota
git push origin main
```

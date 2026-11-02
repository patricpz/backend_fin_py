# Arquitetura e Funcionamento do Sistema de Notificações e Consultas

Este documento explica detalhadamente o funcionamento interno do motor de notificações, as regras de negócio, a esteira de processamento e a lógica de consultas da API.

---

## Sumário

1. [Visão Geral da Arquitetura](#1-visão-geral-da-arquitetura)
2. [Como Funcionam as Consultas (`GET /notifications`)](#2-como-funcionam-as-consultas-get-notifications)
   - [2.1 Paginação por Cursor Opaco](#21-paginação-por-cursor-opaco)
   - [2.2 Contador Global Invariante (`unread_count`)](#22-contador-global-invariante-unread_count)
   - [2.3 Filtros e Ordenação](#23-filtros-e-ordenação)
3. [Esteira de Processamento de Alertas (`processar_evento`)](#3-esteira-de-processamento-de-alertas-processar_evento)
4. [Gatilhos de Notificação (Regras e Scheduler)](#4-gatilhos-de-notificação-regras-e-scheduler)
5. [Ações do Usuário (Leitura e Feedbacks)](#5-ações-do-usuário-leitura-e-feedbacks)
6. [Preferências e Regras de Entrega](#6-preferências-e-regras-de-entrega)
7. [Web Push com VAPID](#7-web-push-com-vapid)
8. [Ambiente de Testes e Homologação](#8-ambiente-de-testes-e-homologação)

---

## 1. Visão Geral da Arquitetura

O sistema de notificações conecta eventos financeiros a comunicações no aplicativo (In-App) e no navegador/celular (Web Push via VAPID).

```
┌────────────────────────────────────────────────────────┐
│                   Gatilhos de Evento                  │
│  - Scheduler Diário (08:00): Orçamentos e Picos       │
│  - Scheduler Horário: Parcelas a Vencer (<= 3 dias)   │
│  - Rota de Homologação: POST /notifications/test      │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│         Esteira Estrita (NotificationService)          │
│  1. Tipo Habilitado?        5. Deduplicação Ativa?    │
│  2. Sensibilidade OK?       6. Geração de Texto        │
│  3. Fora de Quiet Hours?    7. Persistência no Banco   │
│  4. Limite Diário OK?       8. Web Push em Background  │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                   Consumo pelo Frontend                │
│  - GET /notifications (Cursor Opaco + unread_count)    │
│  - PATCH /notifications/{id}/read (Marca lida)         │
│  - POST /notifications/read-all (Limpa badge)          │
│  - POST /notifications/{id}/feedback (Métricas)        │
└────────────────────────────────────────────────────────┘
```

---

## 2. Como Funcionam as Consultas (`GET /notifications`)

### 2.1 Paginação por Cursor Opaco

Diferente da paginação tradicional por `offset/limit`, que sofre com inconsistências visuais e queda de performance quando novos itens chegam enquanto o usuário rola a tela, o endpoint `/notifications` utiliza **paginação por cursor baseada em chaves**.

#### Como o cursor é gerado?
1. O backend busca `limit + 1` registros ordenados por:
   ```sql
   ORDER BY created_at DESC, id DESC
   ```
2. Se a quantidade de registros for maior que o `limit`, existe uma próxima página.
3. O cursor é gerado a partir do último item da página atual, concatenando sua data e seu identificador único:
   $$\text{raw} = \text{"YYYY-MM-DDTHH:MM:SS.mmmmmm|UUID"}$$
4. O valor é codificado em **Base64 seguro para URL** (`base64.urlsafe_b64encode`) e retornado no campo `next_cursor`:
   ```json
   "next_cursor": "MjAyNi0xMC0zMVQxNTozNTo1M3w3ZTUyNTBlNy0wNWNkLTQ3YTUtOThhMy0zMjRkODQ4YTA0YTQ="
   ```

#### Como o backend consome o cursor na próxima página?
Quando o frontend envia `GET /notifications?cursor=<next_cursor>&limit=20`:
1. O backend decodifica o Base64 obtendo `(cursor_dt, cursor_id)`.
2. Aplica a cláusula SQL:
   ```sql
   WHERE (
       created_at < :cursor_dt
       OR (created_at = :cursor_dt AND id < :cursor_id)
   )
   ```
3. **Vantagem:** O desempate por `id` garante que notificações criadas exatamente no mesmo microsegundo nunca sejam perdidas ou duplicadas.
4. Quando não há mais páginas, `next_cursor` é `null`.
5. Se o cliente enviar um cursor corrompido ou inválido, a API retorna `400 Bad Request` com `{ "detail": "Cursor inválido" }`.

---

### 2.2 Contador Global Invariante (`unread_count`)

O campo `unread_count` retornado na resposta **não é a contagem dos itens retornados na página**, mas sim o **total global de notificações não lidas** daquele usuário.

```json
{
  "items": [ ... ],
  "next_cursor": "...",
  "unread_count": 3
}
```

* **Query Dedicada:**
  ```sql
  SELECT COUNT(*) FROM notifications 
  WHERE user_id = :user_id AND status = 'unread';
  ```
* **Invariância:** Mesmo que o frontend filtre a listagem por `type=overspending` ou por `status=read`, ou acesse a página 5, o `unread_count` continua retornando o total absoluto de notificações não lidas (ex.: `3`), permitindo que o badge no sino do cabeçalho da interface permaneça sempre sincronizado.

---

### 2.3 Filtros e Ordenação

* **Parâmetros da rota `GET /notifications`:**
  * `status` (opcional): `"unread"`, `"read"`, `"dismissed"`.
  * `type` (opcional): `"overspending"`, `"spending_spike"`, `"installment_due"`, `"tip"`, `"summary"`.
  * `cursor` (opcional): String Base64 recebida no `next_cursor` da página anterior.
  * `limit` (opcional): Inteiro de `1` a `50` (padrão `20`). Enviar valor superior a 50 retorna `422 Unprocessable Entity`.
* **Segurança e Isolamento:** Todas as consultas incluem obrigatoriamente a restrição `WHERE user_id = current_user.id`. Notificações de outros usuários nunca são retornadas.

---

## 3. Esteira de Processamento de Alertas (`processar_evento`)

Toda e qualquer notificação gerada pelo sistema passa obrigatoriamente pela esteira centralizada em `NotificationService.processar_evento`. A validação segue 8 etapas estritas:

| Etapa | Verificação | O que acontece se falhar |
|---|---|---|
| **1. Tipo Habilitado** | Verifica se o `event_type` está presente em `preferences.enabled_types`. | Ignora o evento (retorna `None`). |
| **2. Sensibilidade** | Avalia `sensitivity` do usuário (`low`, `medium`, `high`):<br>• `low`: Apenas estouro de 100% ou parcela vencendo hoje.<br>• `medium`: Estouro de 80% e 100%, picos, parcelas $\le 3$ dias, dicas e resumos.<br>• `high`: Todos os alertas sem restrição. | Ignora alertas de baixa urgência (retorna `None`). |
| **3. Quiet Hours** | Checa se o horário atual no fuso horário do usuário (`preferences.timezone`) está dentro do intervalo de silêncio (ex.: `22:00` às `07:00`). | Ignora o envio para não incomodar o usuário (retorna `None`). |
| **4. Limite Diário** | Conta quantas notificações o usuário já recebeu hoje no fuso dele. Se $\ge \text{daily\_limit}$ (padrão 3): | Ignora o envio (retorna `None`). |
| **5. Deduplicação** | Busca no banco se já existe uma notificação com a mesma `dedupe_key` para o mesmo `user_id`. | Bloqueia alertas repetidos no mesmo dia ou para a mesma parcela (retorna `None`). |
| **6. Geração de Texto** | O `InsightProvider` (`TemplateProvider`) gera o título humanizado, o corpo explicativo e o `payload` com URL relativa (`/notificacoes/...`). | - |
| **7. Persistência** | Insere o registro na tabela `notifications` com status `"unread"`. | - |
| **8. Web Push** | Se `preferences.channel_push` estiver ativo e houver subscrições cadastradas, despacha via protocolo Web Push (VAPID). | Se a subscrição retornar status `404` ou `410` (token expirado), ela é removida automaticamente do banco. |

---

## 4. Gatilhos de Notificação (Regras e Scheduler)

As notificações são geradas por tarefas agendadas em background através do **APScheduler** (`app/alerts/scheduler.py`):

### 4.1 Job Diário (08:00 no fuso do usuário) — `run_daily_checks`
1. **Excesso de Orçamento (`overspending`):**
   * Avalia os orçamentos ativos do mês (tanto por categoria quanto orçamentos gerais).
   * Se o gasto atingir **80%**: Dispara alerta informativo (nível 80).
   * Se o gasto atingir ou superar **100%**: Dispara alerta crítico (nível 100).
   * `dedupe_key`: `overspending_{categoria_id}_{mes}_{ano}_{nivel}`.
2. **Pico de Gastos (`spending_spike`):**
   * Calcula o gasto do dia atual vs. a média diária dos últimos 30 dias.
   * Se o gasto de hoje for $\ge 3\times$ a média diária: Dispara alerta de pico de gastos.
   * `dedupe_key`: `spike_{user_id}_{YYYY-MM-DD}`.

### 4.2 Job Horário — `run_hourly_installment_checks`
* **Parcelas a Vencer (`installment_due`):**
  * Localiza despesas parceladas ativas (`paid_installments < installment_count`).
  * Calcula a próxima data de vencimento (`next_due_date`).
  * Se o vencimento ocorrer em até **3 dias**: Dispara alerta com o valor da parcela e a data.
  * `dedupe_key`: `installment_due_{tx_id}_{parcela}_{YYYY-MM-DD}`.

---

## 5. Ações do Usuário (Leitura e Feedbacks)

### 5.1 Marcar como Lida — `PATCH /notifications/{id}/read`
* Atualiza `status = "read"` e preenche o timestamp `read_at`.
* **Idempotência:** Caso a notificação já esteja lida, a API retorna `204 No Content` sem alterar o `read_at` original.
* Retorna `404 Not Found` se o ID não existir ou se a notificação pertencer a outro usuário.

### 5.2 Marcar Todas como Lidas — `POST /notifications/read-all`
* Executa uma única query otimizada:
  ```sql
  UPDATE notifications 
  SET status = 'read', read_at = NOW() 
  WHERE user_id = :user_id AND status = 'unread';
  ```
* Retorna `204 No Content`. Imediatamente zera o `unread_count`.

### 5.3 Enviar Feedback — `POST /notifications/{id}/feedback`
Permite ao front registrar como o usuário interagiu com a notificação:
```json
{
  "action": "helpful"
}
```
* **Ações aceitas:**
  * `"opened"`: Altera automaticamente o status para `"read"` se ainda estava `"unread"`.
  * `"dismissed"`: Altera o status da notificação para `"dismissed"` (dispensada).
  * `"helpful"`: Registra avaliação positiva.
  * `"not_helpful"`: Registra avaliação negativa.
  * `"executed"`: Indica que o usuário clicou no link de ação sugerido.
* Toda ação insere um registro imutável na tabela `notification_feedback` para métricas e melhoria contínua dos insights.

---

## 6. Preferências e Regras de Entrega

Disponível em `GET /notification-preferences` e `PUT /notification-preferences`:

```json
{
  "enabled_types": ["overspending", "spending_spike", "installment_due", "tip", "summary"],
  "channel_in_app": true,
  "channel_push": true,
  "sensitivity": "medium",
  "quiet_hours_start": "22:00",
  "quiet_hours_end": "07:00",
  "timezone": "America/Sao_Paulo",
  "daily_limit": 3
}
```

* **Criação Automática:** Se o usuário nunca tiver configurado, o `GET` cria automaticamente os padrões sem emitir erro `404`.
* **Validação IANA:** O campo `timezone` é validado contra o banco oficial de fusos horários (`zoneinfo.ZoneInfo`).
* **Quiet Hours:** Os campos de início e fim devem vir ambos preenchidos no formato `HH:MM` ou ambos `null`.

---

## 7. Web Push com VAPID

O backend implementa o protocolo padrão do W3C para Push Notifications:

1. **Chave Pública (`GET /push/public-key`):**
   * Retorna `{ "public_key": "..." }` a partir da variável `VAPID_PUBLIC_KEY`.
   * Se o push não estiver configurado no servidor, retorna `503 Service Unavailable`.
2. **Inscrição de Aparelhos (`POST /push/subscriptions`):**
   * Valida se o `endpoint` é uma URL `https://`.
   * Realiza **Upsert** por endpoint: se o mesmo navegador ou dispositivo já estiver cadastrado, atualiza as chaves criptográficas (`p256dh` e `auth`) e o `user_id`. Retorna `201 Created` para nova inscrição e `200 OK` para atualização.
3. **Cancelamento (`DELETE /push/subscriptions/{id}`):**
   * Remove a inscrição do usuário e retorna `204 No Content`.
4. **Resiliência a Tokens Expirados:**
   * Quando o Google FCM ou Mozilla Push Service retorna status HTTP `404` ou `410` (Gone), o backend detecta a exceção e exclui o registro morto automaticamente do banco de dados.

---

## 8. Ambiente de Testes e Homologação

Para que a equipe de Frontend e QA possa testar a qualquer momento:

1. **Rota de Teste (`POST /notifications/test`):**
   * Gera imediatamente uma notificação de excesso de gastos para o usuário autenticado.
   * **Segurança:** Funciona exclusivamente quando `APP_ENV=development`. Em produção, a rota retorna `404 Not Found` (não 403, para ocultar sua existência).
2. **Script de Teste Manual:**
   * Pode ser executado no terminal a qualquer momento:
     ```bash
     .\.venv\Scripts\python test_notifications_manual.py
     ```
   * O script realiza o ciclo completo: cria usuário, autentica, dispara teste, lista pelo cursor, marca como lido e envia feedback.

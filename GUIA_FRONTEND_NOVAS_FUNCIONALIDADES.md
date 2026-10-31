# Guia de Implementação Frontend — Novas Funcionalidades e Ajustes

> **Público-alvo:** Desenvolvedores Frontend (React, Vue, Next.js ou PWA).  
> **Objetivo:** Fornecer um passo a passo claro, prático e com código pronto (TypeScript) para consumir as novas rotas e aplicar as correções feitas no backend.

---

## Sumário

1. [Visão Geral das Alterações](#1-visão-geral-das-alterações)
2. [Ajuste: Conta, Transação e Sinal do Saldo](#2-ajuste-conta-transação-e-sinal-do-saldo)
3. [Módulo: Despesas Parceladas (`/expenses/installments`)](#3-módulo-despesas-parceladas-expensesinstallments)
4. [Módulo: Notificações em Tempo Real (`/notifications`)](#4-módulo-notificações-em-tempo-real-notifications)
5. [Módulo: Preferências de Alertas (`/notification-preferences`)](#5-módulo-preferências-de-alertas-notification-preferences)
6. [Módulo: Web Push Notification com VAPID (`/push`)](#6-módulo-web-push-notification-com-vapid-push)
7. [Dicionário de Tipos TypeScript (Copy & Paste)](#7-dicionário-de-tipos-typescript-copy--paste)
8. [Tabela de Rotas, Métodos e Status HTTP](#8-tabela-de-rotas-métodos-e-status-http)

---

## 1. Visão Geral das Alterações

As seguintes novidades e correções foram implementadas na API:

| Módulo | O que mudou / Foi criado | Impacto no Front |
|---|---|---|
| **Transações & Contas** | Campo `tipo` explícito (`receita`, `despesa`, `transferencia`) e `balance` da conta calculado com coerência de sinal. | Elimina ambiguidade de sinal nas listas de transações e cards de saldo. |
| **Despesas Parceladas** | Nova rota `/expenses/installments` com progresso, centavos distribuídos na última parcela e endpoint atômico de pagamento com lock (`/pay`). | Renderização de cards de progresso ("Tablet 20% 2/10") e botão "Pagar Parcela". |
| **Central de Notificações** | Rotas `/notifications` com paginação opaca por cursor, contador global `unread_count` e envio de feedbacks (`opened`, `dismissed`, etc.). | Badge no sino de notificações, scroll infinito e tela de alertas. |
| **Preferências** | Rota `/notification-preferences` para controlar canais (push/in-app), sensibilidade, horários de silêncio e fuso horário. | Tela de "Configurações de Notificação" do usuário. |
| **Web Push (VAPID)** | Rotas `/push/public-key` e `/push/subscriptions` prontas para PWA/Navegador. | Ativação de notificações do navegador com Service Worker. |

> **Nota de Compatibilidade:** Todas as novas rotas estão disponíveis tanto na raiz (ex.: `/notifications`) quanto sob o prefixo `/api/v1/` (ex.: `/api/v1/notifications`).

---

## 2. Ajuste: Conta, Transação e Sinal do Saldo

### O Problema Anterior
A conta retornava o campo `balance`, mas a transação vinha sem o campo `tipo` explícito, fazendo com que despesas aparecessem como valores positivos no frontend ou gerassem inconsistência visual com o saldo.

### Como Funciona Agora

1. **Conta (`GET /accounts` e `GET /accounts/{id}`):**
   - O campo `balance` já reflete o saldo real e consolidado da conta:  
     $$\text{balance} = \text{saldo\_inicial} + \sum \text{receitas} - \sum \text{despesas}$$
   - Transferências entre contas debitam da conta de origem e creditam na conta de destino sem distorcer métricas globais de receitas e despesas.

2. **Transação (`GET /transactions`):**
   - Retorna sempre o campo `tipo` com um dos valores:
     - `"receita"`: entrada financeira.
     - `"despesa"`: saída financeira.
     - `"transferencia"`: movimentação entre contas.
   - O campo `valor` é retornado como string decimal (ex.: `"150.00"`).

### Recomendações para a UI do Frontend
```tsx
// Exemplo de helper para formatar valores no Frontend
export function formatTransactionValue(valor: string | number, tipo: 'receita' | 'despesa' | 'transferencia') {
  const num = typeof valor === 'string' ? parseFloat(valor) : valor;
  const formatted = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Math.abs(num));

  if (tipo === 'despesa') {
    return { text: `- ${formatted}`, color: 'text-red-500' };
  }
  if (tipo === 'receita') {
    return { text: `+ ${formatted}`, color: 'text-green-500' };
  }
  return { text: formatted, color: 'text-blue-500' };
}
```

---

## 3. Módulo: Despesas Parceladas (`/expenses/installments`)

Este módulo gerencia despesas que possuem parcelas mensais, calculando automaticamente percentual de progresso, vencimentos e ajuste de centavos.

### 3.1 Listar Despesas Parceladas — `GET /expenses/installments`

Retorna uma lista plana (`[]`) das despesas parceladas do usuário autenticado.

- **Query Param Opcional:** `include_completed=true` (por padrão é `false`, ocultando as já quitadas).

**Exemplo de Resposta (200 OK):**
```json
[
  {
    "id": "8a72b0c4-1234-4a5b-bcde-9f0a1b2c3d4e",
    "description": "Notebook Gamer",
    "category": "Eletrônicos",
    "total_amount": 3000.00,
    "installment_count": 10,
    "installment_amount": 300.00,
    "paid_installments": 2,
    "remaining_installments": 8,
    "progress_percent": 20,
    "paid_amount": 600.00,
    "remaining_amount": 2400.00,
    "first_due_date": "2026-09-10",
    "next_due_date": "2026-11-10",
    "is_completed": false
  }
]
```

> **Ajuste de Centavos:** Em casos onde o valor total não é perfeitamente divisível (ex.: R$ 1.000,00 em 3x):
> - Parcelas 1 e 2: `R$ 333,33`
> - Parcela 3 (última): `R$ 333,34`  
> O backend realiza essa distribuição automaticamente!

### 3.2 Criar Despesa Parcelada — `POST /expenses/installments`

**Payload:**
```json
{
  "description": "Smartphone Pro",
  "category": "Eletrônicos",
  "total_amount": 2500.00,
  "installment_count": 10,
  "first_due_date": "2026-11-15"
}
```
- Retorna `201 Created` com o objeto completo calculado.
- `paid_installments` inicia sempre em `0` e não deve ser enviado no body.

### 3.3 Pagar Parcela (Avançar 1 Parcela) — `PATCH /expenses/{id}/installments/pay`

- **Requisição:** Sem body.
- **Resposta:** `200 OK` com o objeto atualizado.
- **Regras:**
  - Incrementa atomicamente `paid_installments + 1`.
  - Se a despesa já estiver quitada (`is_completed: true`), retorna `409 Conflict` com `{ "detail": "Esta despesa já foi quitada" }`.
  - Caso a despesa não seja parcelada, retorna `422 Unprocessable Entity`.

### 3.4 Ajuste Manual de Parcelas Pagas — `PATCH /expenses/{id}/installments`

Permite corrigir o número de parcelas pagas caso o usuário tenha cometido um erro:

**Payload:**
```json
{
  "paid_installments": 5
}
```
- Validação: valor inteiro entre `0` e `installment_count`. Fora desse intervalo retorna `422`.

---

## 4. Módulo: Notificações em Tempo Real (`/notifications`)

A Central de Notificações avisa sobre:
- `overspending`: Excesso de gastos em categoria (80% e 100% do orçamento).
- `spending_spike`: Picos atípicos de gastos (gasto único $\ge 3\times$ a média diária).
- `installment_due`: Parcela vencendo em até 3 dias.
- `tip` e `summary`: Dicas financeiras e resumos consolidados.

### 4.1 Listar Notificações e Obter Não Lidas — `GET /notifications`

**Query Params:**
- `status`: `unread`, `read`, `dismissed` (opcional).
- `type`: `overspending`, `spending_spike`, `installment_due`, `tip`, `summary` (opcional).
- `cursor`: String opaca base64 para a próxima página (opcional).
- `limit`: Inteiro entre `1` e `50` (padrão `20`). Acima de 50 retorna `422`.

**Exemplo de Resposta (200 OK):**
```json
{
  "items": [
    {
      "id": "e45f9488-8254-4fb9-9650-e19efc237c15",
      "type": "overspending",
      "title": "Alimentação passou do limite",
      "body": "Você gastou R$ 1.180,00 de R$ 1.000,00 este mês.",
      "status": "unread",
      "created_at": "2026-10-31T12:00:00-03:00",
      "payload": {
        "categoria": "Alimentação",
        "orcado": 1000.0,
        "gasto": 1180.0,
        "percentual": 118.0,
        "url": "/notificacoes/e45f9488-8254-4fb9-9650-e19efc237c15"
      }
    }
  ],
  "next_cursor": "MjAyNi0xMC0zMVQxNTowMDowMHxlNDVmOTQ4OC0...",
  "unread_count": 3
}
```

> **Atenção ao `unread_count`:** Este número é o total global de notificações não lidas do usuário, calculado com query própria. Ele **não é afetado** por filtros de página, tipo ou status, sendo ideal para alimentar o badge de contador no sino do header!

### 4.2 Marcar como Lida — `PATCH /notifications/{id}/read`
- **Requisição:** Sem body.
- **Resposta:** `204 No Content`.
- Idempotente: se já estiver lida, não altera nada e continua retornando `204`.

### 4.3 Marcar Todas como Lidas — `POST /notifications/read-all`
- **Requisição:** Sem body.
- **Resposta:** `204 No Content`.

### 4.4 Enviar Feedback da Notificação — `POST /notifications/{id}/feedback`

Permite ao usuário interagir com a notificação:

**Payload:**
```json
{
  "action": "helpful"
}
```
**Valores aceitos:**
- `"opened"`: Marca a notificação como `read` caso estivesse `unread`.
- `"dismissed"`: Altera o status da notificação para `dismissed` (dispensada).
- `"helpful"`: Usuário achou útil.
- `"not_helpful"`: Usuário não achou útil.
- `"executed"`: Ação sugerida pela notificação foi realizada.

Retorna `204 No Content`. Se o valor for inválido, retorna `422`.

---

## 5. Módulo: Preferências de Alertas (`/notification-preferences`)

### 5.1 Obter Preferências — `GET /notification-preferences`
Se o usuário ainda não tiver registrado preferências, a API cria automaticamente as preferências padrão e retorna `200 OK` (nunca 404).

**Exemplo de Resposta:**
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

### 5.2 Salvar Preferências — `PUT /notification-preferences`
Substitui o objeto completo.

**Regras de Validação no Front:**
- `sensitivity`: `"low"`, `"medium"` ou `"high"`.
- `quiet_hours_start` e `quiet_hours_end`: Ambos preenchidos no formato `"HH:MM"` ou ambos `null`.
- `timezone`: Identificador IANA válido (ex.: `"America/Sao_Paulo"`, `"America/Fortaleza"`, `"UTC"`).
- `daily_limit`: Inteiro entre `0` e `20`.

---

## 6. Módulo: Web Push Notification com VAPID (`/push`)

Para receber notificações nativas no celular ou desktop via PWA/Service Worker:

### Fluxo de Registro no Frontend

```
1. Front solicita chave pública   ───> GET /push/public-key
2. Front obtém permissão           ───> Notification.requestPermission()
3. Service Worker gera inscrição  ───> registration.pushManager.subscribe()
4. Front envia ao Backend         ───> POST /push/subscriptions
```

### Passo 1: Obter a VAPID Public Key
```typescript
const res = await api.get('/push/public-key');
const { public_key } = res.data; // Retorna 200 com a chave ou 503 se não configurado
```

### Passo 2: Função utilitária para converter a chave base64
```typescript
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/\-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}
```

### Passo 3: Registrar a inscrição no Service Worker e enviar à API
```typescript
export async function enablePushNotifications(): Promise<boolean> {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    console.warn('Push não suportado neste navegador');
    return false;
  }

  const permission = await Notification.requestPermission();
  if (permission !== 'granted') {
    return false;
  }

  // 1. Obter VAPID public key da API
  const { data } = await api.get<{ public_key: string }>('/push/public-key');
  const convertedVapidKey = urlBase64ToUint8Array(data.public_key);

  // 2. Inscrever no PushManager
  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: convertedVapidKey,
  });

  const subJson = subscription.toJSON();

  // 3. Enviar ao backend (faz upsert inteligente por endpoint)
  await api.post('/push/subscriptions', {
    endpoint: subJson.endpoint,
    p256dh: subJson.keys?.p256dh,
    auth: subJson.keys?.auth,
    user_agent: navigator.userAgent,
  });

  return true;
}
```

### Passo 4: Código do Service Worker (`sw.js`)
Coloque no arquivo do seu Service Worker para exibir a notificação quando ela chegar:

```javascript
self.addEventListener('push', (event) => {
  if (!event.data) return;

  const data = event.data.json();
  const title = data.title || 'Alerta Financeiro';
  const options = {
    body: data.body,
    icon: '/icon-192.png',
    badge: '/badge-72.png',
    tag: data.tag || 'finance-alert',
    data: {
      url: data.url || '/notificacoes',
    },
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const urlToOpen = event.notification.data?.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url.includes(urlToOpen) && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
    })
  );
});
```

---

## 7. Dicionário de Tipos TypeScript (Copy & Paste)

Crie um arquivo `src/types/finance-api.d.ts` e cole os tipos abaixo:

```typescript
// ==========================================
// 1. Despesas Parceladas
// ==========================================
export interface InstallmentExpense {
  id: string;
  description: string;
  category: string;
  total_amount: number;
  installment_count: number;
  installment_amount: number;
  paid_installments: number;
  remaining_installments: number;
  progress_percent: number;
  paid_amount: number;
  remaining_amount: number;
  first_due_date: string; // YYYY-MM-DD
  next_due_date: string | null; // YYYY-MM-DD ou null se quitado
  is_completed: boolean;
}

export interface CreateInstallmentExpenseDTO {
  description: string;
  category: string;
  total_amount: number;
  installment_count: number; // Mínimo 2
  first_due_date: string; // YYYY-MM-DD
}

export interface UpdateInstallmentPaidDTO {
  paid_installments: number;
}

// ==========================================
// 2. Notificações
// ==========================================
export type NotificationType =
  | 'overspending'
  | 'spending_spike'
  | 'installment_due'
  | 'tip'
  | 'summary';

export type NotificationStatus = 'unread' | 'read' | 'dismissed';

export interface NotificationPayload {
  categoria?: string;
  orcado?: number;
  gasto?: number;
  percentual?: number;
  url?: string;
  [key: string]: unknown;
}

export interface NotificationItem {
  id: string;
  type: NotificationType;
  title: string;
  body: string;
  status: NotificationStatus;
  created_at: string; // ISO 8601
  payload?: NotificationPayload | null;
}

export interface NotificationListResponse {
  items: NotificationItem[];
  next_cursor: string | null;
  unread_count: number;
}

export type FeedbackAction =
  | 'opened'
  | 'dismissed'
  | 'helpful'
  | 'not_helpful'
  | 'executed';

export interface NotificationFeedbackDTO {
  action: FeedbackAction;
}

// ==========================================
// 3. Preferências de Alerta
// ==========================================
export type AlertSensitivity = 'low' | 'medium' | 'high';

export interface NotificationPreferences {
  enabled_types: NotificationType[];
  channel_in_app: boolean;
  channel_push: boolean;
  sensitivity: AlertSensitivity;
  quiet_hours_start: string | null; // HH:MM ou null
  quiet_hours_end: string | null;   // HH:MM ou null
  timezone: string;                 // IANA timezone
  daily_limit: number;              // 0 a 20
}

// ==========================================
// 4. Web Push
// ==========================================
export interface PushSubscriptionDTO {
  endpoint: string;
  p256dh: string;
  auth: string;
  user_agent?: string;
}

export interface PushPublicKeyResponse {
  public_key: string;
}
```

---

## 8. Tabela de Rotas, Métodos e Status HTTP

| Funcionalidade | Método | Rota | Status Sucesso | Status Erros Comuns |
|---|---|---|---|---|
| Listar parceladas | `GET` | `/expenses/installments` | `200 OK` | `401` |
| Criar despesa parcelada | `POST` | `/expenses/installments` | `201 Created` | `401`, `422` |
| Pagar 1 parcela | `PATCH` | `/expenses/{id}/installments/pay` | `200 OK` | `404`, `409` (já quitada), `422` |
| Corrigir parcelas pagas | `PATCH` | `/expenses/{id}/installments` | `200 OK` | `404`, `422` |
| Listar notificações | `GET` | `/notifications` | `200 OK` | `400` (cursor inválido), `401`, `422` (limit > 50) |
| Marcar notificação lida | `PATCH` | `/notifications/{id}/read` | `204 No Content` | `401`, `404` |
| Marcar todas lidas | `POST` | `/notifications/read-all` | `204 No Content` | `401` |
| Feedback de notificação | `POST` | `/notifications/{id}/feedback` | `204 No Content` | `401`, `404`, `422` |
| Obter preferências | `GET` | `/notification-preferences` | `200 OK` | `401` |
| Salvar preferências | `PUT` | `/notification-preferences` | `200 OK` | `401`, `422` |
| Obter chave VAPID | `GET` | `/push/public-key` | `200 OK` | `503` (não configurado) |
| Salvar Push Subscription | `POST` | `/push/subscriptions` | `201` (novo) / `200` (update) | `401`, `422` (não HTTPS) |
| Remover Push Subscription | `DELETE`| `/push/subscriptions/{id}` | `204 No Content` | `401`, `404` |
| Rota de teste (Dev only)| `POST` | `/notifications/test` | `200 OK` | `404` (em produção) |

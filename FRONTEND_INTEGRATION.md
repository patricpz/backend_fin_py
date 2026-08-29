# Guia de Integração — API Financeiro Pessoal

> Documento técnico voltado ao desenvolvimento do frontend PWA que consome esta API.

---

## Sumário

1. [Visão Geral](#1-visão-geral)
2. [Autenticação](#2-autenticação)
3. [Convenções](#3-convenções)
4. [Referência de Endpoints](#4-referência-de-endpoints)
   - 4.1 [Auth](#41-auth)
   - 4.2 [Contas](#42-contas)
   - 4.3 [Categorias](#43-categorias)
   - 4.4 [Transações](#44-transações)
   - 4.5 [Recorrências](#45-recorrências)
   - 4.6 [Orçamentos](#46-orçamentos)
   - 4.7 [Metas](#47-metas)
   - 4.8 [Relatórios](#48-relatórios)
   - 4.9 [Health](#49-health)
5. [Enums](#5-enums)
6. [Códigos de Erro](#6-códigos-de-erro)
7. [Regras de Negócio](#7-regras-de-negócio)
8. [Exemplo de Cliente HTTP (TypeScript)](#8-exemplo-de-cliente-http)
9. [Notas Conhecidas](#9-notas-conhecidas)

---

## 1. Visão Geral

| Campo           | Valor                                  |
|-----------------|----------------------------------------|
| Base URL        | `http://localhost:8000`                |
| Versão          | `/api/v1/`                             |
| Content-Type    | `application/json`                     |
| Formato JSON    | UTF-8                                  |
| Autenticação    | JWT Bearer (access + refresh tokens)   |
| CORS Origins    | `localhost:3000`, `localhost:5173` (configurável) |
| Credentials     | `allow_credentials: true`              |
| OpenAPI/Swagger | `/docs` (modo desenvolvimento)         |

> A API usa OpenAPI automático. O endpoint `GET /docs` mostra a interface Swagger interativa para teste rápido.

---

## 2. Autenticação

### Fluxo Completo

```
┌──────────┐         ┌──────────┐
│  FRONTEND │         │   API    │
└─────┬────┘         └────┬─────┘
      │  POST /register   │
      │  {nome,email,senha}│
      │──────────────────>│
      │   201 UserResponse │
      │<──────────────────│
      │                   │
      │  POST /login      │
      │  {email,senha}    │
      │──────────────────>│
      │  200 TokenResponse │
      │  {access_token,   │
      │   refresh_token,  │
      │   token_type}     │
      │<──────────────────│
      │                   │
      │  GET /me           │
      │  Authorization:   │
      │  Bearer <access>  │
      │──────────────────>│
      │   200 UserResponse │
      │<──────────────────│
      │                   │
      │  POST /refresh    │
      │  {refresh_token}  │
      │──────────────────>│
      │  200 TokenResponse │  (old refresh revoked, new pair issued)
      │<──────────────────│
      │                   │
      │  POST /logout     │
      │  Bearer <access>  │
      │──────────────────>│
      │   204 No Content   │  (ALL refresh tokens revoked)
      │<──────────────────│
```

### Endpoints de Auth

#### `POST /api/v1/auth/register` — Criar conta

**Request Body:**

```json
{
  "nome": "João Silva",
  "email": "joao@email.com",
  "senha": "minha1234"
}
```

| Campo   | Tipo   | Restrições                  |
|---------|--------|-----------------------------|
| nome    | string | 1–120 caracteres, obrigatório |
| email   | string | email válido (obrigatório)    |
| senha   | string | 8–100 caracteres, obrigatório |

**Response 201:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "nome": "João Silva",
  "email": "joao@email.com",
  "ativo": true,
  "criado_em": "2026-08-22T12:00:00"
}
```

> **Importante:** Ao registrar, a API cria automaticamente 10 categorias padrão para o usuário (7 despesas + 3 receitas). O frontend deve buscar categorias (`GET /categories/tree`) logo após o registro.

**Erros possíveis:**
| Status | Code          | Detail                        |
|--------|---------------|-------------------------------|
| 409    | EMAIL_EXISTS  | Email já cadastrado           |
| 422    | VALIDATION_ERROR | Body com campos inválidos  |

---

#### `POST /api/v1/auth/login` — Autenticar

**Request Body:**

```json
{
  "email": "joao@email.com",
  "senha": "minha1234"
}
```

**Response 200:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Erros possíveis:**
| Status | Code              | Detail                     |
|--------|-------------------|----------------------------|
| 401    | INVALID_CREDENTIALS | Email ou senha incorretos |
| 401    | USER_INACTIVE       | Usuário inativo           |

> **Rate limiting:** O endpoint de login está configurado para limite de 5 requisições/minuto por IP (`RATE_LIMIT_LOGIN`). Em caso de excesso, retorna **429** com code `RATE_LIMIT_EXCEEDED`.

---

#### `POST /api/v1/auth/refresh` — Renovar tokens (rotação)

**Request Body:**

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response 200:** Mesmo formato de `TokenResponse`.

> **Importante:** A cada refresh, o token antigo é **revogado** e um novo par (access + refresh) é emitido. O frontend **nunca deve reutilizar** um refresh_token após chamá-lo. Em caso de erro, fazer logout completo.

**Erros possíveis:**
| Status | Code         | Detail                       |
|--------|--------------|------------------------------|
| 401    | TOKEN_REVOKED | Token revogado ou inválido  |
| 401    | INVALID_TOKEN | Token com assinatura inválida |

---

#### `POST /api/v1/auth/logout` — Encerrar sessão

**Headers:** `Authorization: Bearer <access_token>`

**Response 204:** Sem corpo.

> Revoga **todos** os refresh tokens do usuário. O access token atual continua válido até expirar naturalmente (timeout de 30 min). Para expiração imediata do access token, o frontend deve removê-lo do armazenamento local.

---

#### `GET /api/v1/auth/me` — Perfil do usuário logado

**Headers:** `Authorization: Bearer <access_token>`

**Response 200:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "nome": "João Silva",
  "email": "joao@email.com",
  "ativo": true,
  "criado_em": "2026-08-22T12:00:00"
}
```

---

## 3. Convenções

### Formatos de Dados

| Tipo       | Formato na JSON                        | Exemplo                           |
|------------|----------------------------------------|-----------------------------------|
| UUID       | string                                 | `"550e8400-e29b-41d4-a716-..."` |
| Dinheiro   | **string decimal**                     | `"1234.50"`                       |
| Data       | `YYYY-MM-DD`                           | `"2026-08-22"`                   |
| DateTime   | ISO 8601 `YYYY-MM-DDTHH:MM:SS`        | `"2026-08-22T12:00:00"`         |
| Boolean    | `true` / `false`                       | `true`                            |
| Enum       | lowercase string                       | `"corrente"`, `"receita"`       |

> **Atenção com valores monetários:** O backend serializa `Decimal` como string. O frontend **deve** tratar como string para evitar perda de precisão. Para exibir R$ 1.234,50 use `parseFloat("1234.50").toLocaleString('pt-BR', {style:'currency', currency:'BRL'})`.

### Paginação

Todos os endpoints de listagem retornam o envelope:

```json
{
  "items": [...],
  "total": 45,
  "page": 1,
  "size": 20,
  "pages": 3
}
```

**Query params de paginação (todos opcionais):**

| Param | Default | Restrição         |
|-------|---------|-------------------|
| page  | 1       | ≥ 1               |
| size  | 20      | 1 ≤ size ≤ 100    |

### Formato de Erros

Todos os erros usam o envelope:

```json
{
  "detail": "Mensagem descritiva em português",
  "code": "CODIGO_VERBOSO"
}
```

> **Exceção:** Erros de validação do request body (422 do Pydantic) retornam o formato nativo do FastAPI com array de detalhes — ver seção 6.

---

## 4. Referência de Endpoints

### 4.1 Auth

| Método | Rota               | Autenticado | Descrição                   |
|--------|--------------------|-------------|------------------------------|
| POST   | `/auth/register`   | Não         | Criar conta                  |
| POST   | `/auth/login`      | Não         | Autenticar e obter tokens    |
| POST   | `/auth/refresh`    | Não         | Renovar tokens (rotação)     |
| POST   | `/auth/logout`     | Sim         | Revogar todos os refreshes   |
| GET    | `/auth/me`         | Sim         | Dados do usuário logado      |

---

### 4.2 Contas

| Método | Rota                          | Autenticado | Descrição                 |
|--------|-------------------------------|-------------|----------------------------|
| POST   | `/accounts`                   | Sim         | Criar conta                |
| GET    | `/accounts`                   | Sim         | Listar contas (paginado)   |
| GET    | `/accounts/{id}`              | Sim         | Detalhes de uma conta      |
| GET    | `/accounts/{id}/balance`      | Sim         | Saldo atualizado da conta  |
| PATCH  | `/accounts/{id}`              | Sim         | Atualizar conta (parcial)  |
| DELETE | `/accounts/{id}`              | Sim         | Remover conta (soft delete)|

#### Criar conta — `POST /accounts`

```json
// Request
{
  "nome": "Nubank",
  "tipo": "corrente",
  "saldo_inicial": "1500.00",
  "moeda": "BRL"
}
```

| Campo         | Tipo    | Restrições                               |
|---------------|---------|------------------------------------------|
| nome          | string  | 1–120, obrigatório                       |
| tipo          | enum    | AccountType, obrigatório                 |
| saldo_inicial | decimal | ≥ 0, padrão "0.00"                       |
| moeda         | string  | 3 caracteres, padrão "BRL"               |

**Response 201:**

```json
{
  "id": "...",
  "user_id": "...",
  "nome": "Nubank",
  "tipo": "corrente",
  "saldo_inicial": "1500.00",
  "moeda": "BRL",
  "ativo": true,
  "criado_em": "2026-08-22T12:00:00",
  "atualizado_em": "2026-08-22T12:00:00",
  "saldo_atual": "1500.00"
}
```

#### Saldo atualizado — `GET /accounts/{id}/balance`

Retorna o mesmo schema de AccountResponse com o `saldo_atual` recalculado com base em **transações confirmadas**.

> **Nota:** O endpoint de listagem (`GET /accounts`) também retorna `saldo_atual`, mas seu valor pode estar desatualizado ou zerado em ambientes com SQLite (ver [Notas Conhecidas](#9-notas-conhecidas)). Para saldo preciso, usar `/accounts/{id}/balance`.

#### Soft delete

`DELETE /accounts/{id}` retorna **204**. Se a conta possui transações vinculadas, ela é desativada (soft delete: `ativo = false`) em vez de removida fisicamente.

#### Atualizar — `PATCH /accounts/{id}`

Todos os campos são opcionais:

```json
{
  "nome": "Nubank Atualizado",
  "ativo": false
}
```

---

### 4.3 Categorias

| Método | Rota                          | Autenticado | Descrição                    |
|--------|-------------------------------|-------------|-------------------------------|
| POST   | `/categories`                 | Sim         | Criar categoria               |
| GET    | `/categories`                 | Sim         | Listar categorias (paginado)  |
| GET    | `/categories/tree`            | Sim         | Árvore hierárquica            |
| GET    | `/categories/{id}`            | Sim         | Detalhes de uma categoria     |
| PATCH  | `/categories/{id}`            | Sim         | Atualizar categoria (parcial) |
| DELETE | `/categories/{id}`            | Sim         | Remover (soft delete)         |

#### Criar categoria — `POST /categories`

```json
{
  "nome": "Restaurante",
  "tipo": "despesa",
  "cor": "#EF4444",
  "icone": "utensils",
  "categoria_pai_id": "uuid-da-categoria-pai"
}
```

| Campo           | Tipo   | Restrições                              |
|-----------------|--------|-----------------------------------------|
| nome            | string | 1–80 caracteres, obrigatório            |
| tipo            | enum   | `receita` ou `despesa`, obrigatório     |
| cor             | string | Hex color, padrão `#6366F1`             |
| icone           | string | Nome do ícone Lucide, padrão `"tag"`    |
| categoria_pai_id| uuid   | null (raiz) ou ID da pai (subcategoria) |

#### Listar — query params

| Param | Tipo | Descrição                   |
|-------|------|-----------------------------|
| tipo  | string | Filtrar por `receita` ou `despesa` |
| page  | int  | Página (default: 1)         |
| size  | int  | Itens/página (default: 20)  |

#### Árvore — `GET /categories/tree?tipo=despesa`

Retorna array aninhado (sem paginação):

```json
[
  {
    "id": "...",
    "nome": "Alimentação",
    "tipo": "despesa",
    "cor": "#EF4444",
    "icone": "utensils",
    "categoria_pai_id": null,
    "ativo": true,
    "criado_em": "...",
    "atualizado_em": "...",
    "children": [
      {
        "id": "...",
        "nome": "Restaurante",
        "tipo": "despesa",
        "cor": "#EF4444",
        "icone": "utensils",
        "categoria_pai_id": "uuid-pai",
        "ativo": true,
        "criado_em": "...",
        "atualizado_em": "...",
        "children": []
      }
    ]
  }
]
```

> **Categorias padrão** (criadas no registro):

| Nome             | Tipo    | Cor    | Ícone          |
|------------------|---------|--------|----------------|
| Alimentação      | despesa | #EF4444 | utensils      |
| Transporte       | despesa | #3B82F6 | car           |
| Moradia          | despesa | #8B5CF6 | home          |
| Lazer            | despesa | #EC4899 | gamepad-2     |
| Saúde            | despesa | #10B981 | heart-pulse   |
| Educação         | despesa | #F59E0B | graduation-cap |
| Outros           | despesa | #6B7280 | tag           |
| Salário          | receita | #22C55E | briefcase     |
| Investimentos    | receita | #14B8A6 | trending-up   |
| Outras Receitas  | receita | #84CC16 | plus-circle   |

---

### 4.4 Transações

| Método | Rota                              | Autenticado | Descrição              |
|--------|-----------------------------------|-------------|-------------------------|
| POST   | `/transactions`                   | Sim         | Criar transação         |
| GET    | `/transactions`                   | Sim         | Listar (paginado, filtros) |
| GET    | `/transactions/{id}`              | Sim         | Detalhes                |
| PATCH  | `/transactions/{id}`              | Sim         | Atualizar (parcial)     |
| DELETE | `/transactions/{id}`              | Sim         | Remover                 |
| POST   | `/transactions/{id}/confirm`      | Sim         | Confirmar transação     |

#### Criar transação — `POST /transactions`

**Headers:** `Idempotency-Key: <UUID>` (opcional, mas recomendado)

```json
{
  "conta_id": "uuid-conta-origem",
  "conta_destino_id": "uuid-conta-destino",
  "categoria_id": "uuid-categoria",
  "tipo": "despesa",
  "valor": "250.00",
  "data": "2026-08-22",
  "descricao": "Supermercado Extra",
  "observacoes": "Compras da semana",
  "status": "confirmado"
}
```

| Campo           | Tipo   | Restrições                                          |
|-----------------|--------|-----------------------------------------------------|
| conta_id        | uuid   | Obrigatório                                         |
| conta_destino_id| uuid   | Obrigatório **somente para** `tipo=transferencia`   |
| categoria_id    | uuid   | Obrigatório para receita/despesa, **nulo para transferência** |
| tipo            | enum   | Obrigatório                                         |
| valor           | decimal| > 0, até 2 casas decimais                           |
| data            | date   | Obrigatório (YYYY-MM-DD)                            |
| descricao       | string | 1–200 caracteres, obrigatório                       |
| observacoes     | string | Opcional                                            |
| status          | enum   | `pendente` ou `confirmado`, padrão `confirmado`     |
| anexo_url       | string | Opcional, até 500 caracteres                        |
| recorrencia_id  | uuid   | Preenchido automaticamente quando gerado por recorrência |
| idempotency_key | uuid   | Opcional no body (preferencial no header)           |

**Response 201:** `TransactionResponse` (mesmos campos + `id`, `user_id`, `criado_em`, `atualizado_em`)

> **Idempotency-Key (header):** Se já existe uma transação com essa chave, a API retorna a transação existente em vez de criar duplicada. Valores diferentes = transação nova.

#### Filtros — query params em `GET /transactions`

| Param        | Tipo  | Descrição                        |
|--------------|-------|----------------------------------|
| conta_id     | uuid  | Filtrar por conta                |
| categoria_id | uuid  | Filtrar por categoria            |
| tipo         | enum  | Filtrar por tipo                 |
| status       | enum  | Filtrar por status               |
| data_inicio  | date  | Data inicial do período (YYYY-MM-DD) |
| data_fim     | date  | Data final do período (YYYY-MM-DD)   |
| descricao    | string| Busca por texto na descrição     |

---

### 4.5 Recorrências

| Método | Rota                                    | Autenticado | Descrição                        |
|--------|-----------------------------------------|-------------|-----------------------------------|
| POST   | `/recurrences`                          | Sim         | Criar regra de recorrência        |
| GET    | `/recurrences`                          | Sim         | Listar (paginado)                 |
| GET    | `/recurrences/{id}`                     | Sim         | Detalhes                          |
| PATCH  | `/recurrences/{id}`                     | Sim         | Atualizar regra                   |
| DELETE | `/recurrences/{id}`                     | Sim         | Excluir regra                     |
| POST   | `/recurrences/generate`                 | Sim         | Gerar pendentes (todas)           |
| POST   | `/recurrences/{id}/generate`            | Sim         | Gerar pendentes (por ID)          |

#### Criar recorrência — `POST /recurrences`

```json
{
  "conta_id": "uuid-conta",
  "categoria_id": "uuid-categoria",
  "tipo": "despesa",
  "valor": "89.90",
  "frequencia": "mensal",
  "dia_do_mes": 15,
  "dia_semana": null,
  "data_inicio": "2026-09-01",
  "data_fim": "2026-12-31",
  "descricao": "Assinatura Netflix"
}
```

| Campo         | Tipo   | Restrições                                          |
|---------------|--------|-----------------------------------------------------|
| frequencia    | enum   | `diaria`, `semanal`, `mensal`, `anual`              |
| dia_do_mes    | int    | 1–31 (obrigatório para frequência `mensal`)        |
| dia_semana    | int    | 0–6 dom–sáb (obrigatório para frequência `semanal`)|
| data_inicio   | date   | Primeira execução possível                          |
| data_fim      | date   | Fim da série (null = indefinida)                     |

> **Modelo lazy (catch-up):** As transações **não são criadas imediatamente** quando a regra é definida. Elas são geradas sob demanda chamando `POST /recurrences/generate` (para todas as regras pendentes) ou `POST /recurrences/{id}/generate` (para uma regra específica). Isso evita necessidade de cron job no backend.
>
> **Recomendação para o frontend:** Chamar `/recurrences/generate` periodicamente (ex.: ao abrir o app) ou em um service worker.

**Response 201:**

```json
{
  "id": "...",
  "user_id": "...",
  "conta_id": "...",
  "categoria_id": "...",
  "tipo": "despesa",
  "valor": "89.90",
  "frequencia": "mensal",
  "dia_do_mes": 15,
  "dia_semana": null,
  "data_inicio": "2026-09-01",
  "data_fim": "2026-12-31",
  "descricao": "Assinatura Netflix",
  "proxima_execucao": "2026-09-15",
  "ativo": true,
  "criado_em": "...",
  "atualizado_em": "..."
}
```

#### Gerar transações — `POST /recurrences/generate?data_limite=2026-08-22`

```json
// Response
{
  "geradas": 3,
  "message": "3 transações geradas"
}
```

O parâmetro `data_limite` (opcional) define até qual data gerar transações. Padrão: data atual. Transações geradas recebem status `confirmado`.

---

### 4.6 Orçamentos

| Método | Rota                               | Autenticado | Descrição                |
|--------|------------------------------------|-------------|---------------------------|
| POST   | `/budgets`                         | Sim         | Criar orçamento           |
| GET    | `/budgets`                         | Sim         | Listar (paginado, filtros)|
| GET    | `/budgets/{id}`                    | Sim         | Detalhes                  |
| GET    | `/budgets/{id}/progress`           | Sim         | Progresso do orçamento    |
| PATCH  | `/budgets/{id}`                    | Sim         | Atualizar (parcial)       |
| DELETE | `/budgets/{id}`                    | Sim         | Excluir                   |

#### Criar orçamento — `POST /budgets`

```json
{
  "categoria_id": "uuid-categoria-despesa",
  "valor_limite": "2000.00",
  "mes": 8,
  "ano": 2026,
  "alerta_percentual": 80
}
```

| Campo            | Tipo  | Restrições                                    |
|------------------|-------|-----------------------------------------------|
| categoria_id     | uuid  | Deve ser categoria de tipo `despesa`          |
| valor_limite     | decimal | ≥ 0, obrigatório                           |
| mes              | int   | 1–12, obrigatório                             |
| ano              | int   | ≥ 2000, obrigatório                           |
| alerta_percentual| int   | 1–100, padrão 80 (gatilho de alerta em %)    |

> **Regra:** Um orçamento é único por (categoria, mês, ano). Tentar criar duplicado retorna **409 BUDGET_EXISTS**.
>
> **Subcategorias:** O progresso inclui gastos de subcategorias da categoria vinculada ao orçamento.

**Response 201:**

```json
{
  "id": "...",
  "user_id": "...",
  "categoria_id": "...",
  "valor_limite": "2000.00",
  "mes": 8,
  "ano": 2026,
  "alerta_percentual": 80,
  "criado_em": "...",
  "atualizado_em": "..."
}
```

#### Progresso — `GET /budgets/{id}/progress`

```json
{
  "budget_id": "...",
  "categoria_id": "...",
  "categoria_nome": "Alimentação",
  "valor_limite": "2000.00",
  "valor_gasto": "1580.00",
  "percentual": 79.0,
  "alerta": false,
  "mes": 8,
  "ano": 2026
}
```

| Campo          | Descrição                                            |
|----------------|------------------------------------------------------|
| valor_gasto    | Soma de despesas confirmadas (inclui subcategorias)  |
| percentual     | `(valor_gasto / valor_limite) * 100`                |
| alerta         | `true` se `percentual >= alerta_percentual`           |

#### Listar — query params

| Param | Tipo | Descrição                      |
|-------|------|--------------------------------|
| mes   | int  | Filtrar por mês                |
| ano   | int  | Filtrar por ano                |

---

### 4.7 Metas

| Método | Rota                                      | Autenticado | Descrição                      |
|--------|-------------------------------------------|-------------|---------------------------------|
| POST   | `/goals`                                  | Sim         | Criar meta                      |
| GET    | `/goals`                                  | Sim         | Listar (paginado)               |
| GET    | `/goals/{id}`                             | Sim         | Detalhes                        |
| GET    | `/goals/{id}/progress`                    | Sim         | Progresso                       |
| POST   | `/goals/{id}/contributions`               | Sim         | Adicionar aporte/retirada       |
| GET    | `/goals/{id}/contributions`               | Sim         | Listar contribuições (paginado) |
| PATCH  | `/goals/{id}`                             | Sim         | Atualizar meta (parcial)        |
| DELETE | `/goals/{id}`                             | Sim         | Excluir                         |

#### Criar meta — `POST /goals`

```json
{
  "nome": "Reserva de Emergência",
  "descricao": "6 meses de despesas",
  "valor_alvo": "30000.00",
  "data_alvo": "2027-06-30",
  "categoria": "Financeiro"
}
```

| Campo       | Tipo   | Restrições                   |
|-------------|--------|------------------------------|
| nome        | string | 1–120, obrigatório           |
| descricao   | string | até 500, opcional            |
| valor_alvo  | decimal | > 0, obrigatório            |
| data_alvo   | date   | opcional, prazo desejado    |
| categoria   | string | até 80, etiqueta livre       |

**Response 201:**

```json
{
  "id": "...",
  "user_id": "...",
  "nome": "Reserva de Emergência",
  "descricao": "6 meses de despesas",
  "valor_alvo": "30000.00",
  "data_alvo": "2027-06-30",
  "categoria": "Financeiro",
  "status": "em_andamento",
  "valor_atual": "0.00",
  "progresso_percentual": 0.0,
  "criado_em": "...",
  "atualizado_em": "..."
}
```

> `valor_atual` e `progresso_percentual` são calculados a partir das contribuições (não armazenados diretamente).

#### Adicionar contribuição — `POST /goals/{id}/contributions`

```json
{
  "valor": "500.00",
  "tipo": "aporte",
  "data": "2026-08-22",
  "observacao": "Depósito mensal"
}
```

| Campo    | Tipo   | Restrições                              |
|----------|--------|------------------------------------------|
| valor    | decimal | > 0, obrigatório                       |
| tipo     | enum   | `aporte` ou `retirada`, obrigatório     |
| data     | date   | Obrigatório                             |
| observacao | string | até 200, opcional                     |

> **Auto-conclusão:** Se ao adicionar um aporte o `valor_atual` atinge ou supera o `valor_alvo`, o status da meta muda automaticamente para `concluida`.

**Response 201:**

```json
{
  "id": "...",
  "goal_id": "...",
  "valor": "500.00",
  "tipo": "aporte",
  "data": "2026-08-22",
  "observacao": "Depósito mensal",
  "criado_em": "..."
}
```

#### Progresso — `GET /goals/{id}/progress`

```json
{
  "goal_id": "...",
  "valor_alvo": "30000.00",
  "valor_atual": "15000.00",
  "progresso_percentual": 50.0,
  "status": "em_andamento"
}
```

> **Nota:** O campo `progresso_percentual` é limitado a 100.0 (mesmo que valor_atual > valor_alvo).

#### Listar metas — query params

| Param  | Tipo   | Descrição                                       |
|--------|--------|--------------------------------------------------|
| status | string | Filtrar por `em_andamento`, `concluida`, `cancelada` |

---

### 4.8 Relatórios

| Método | Rota                              | Autenticado | Descrição                    |
|--------|-----------------------------------|-------------|-------------------------------|
| GET    | `/reports/monthly-summary`        | Sim         | Resumo mensal                 |
| GET    | `/reports/category-spending`      | Sim         | Gastos por categoria          |
| GET    | `/reports/balance-evolution`      | Sim         | Evolução do saldo             |
| GET    | `/reports/budget-vs-actual`       | Sim         | Orçado vs realizado           |

> Todos os relatórios são endpoints **GET com query params** (não corpo de requisição).

#### Resumo mensal — `GET /reports/monthly-summary?mes=8&ano=2026`

```json
{
  "mes": 8,
  "ano": 2026,
  "total_receitas": "8500.00",
  "total_despesas": "4200.00",
  "saldo": "4300.00",
  "total_transferencias_enviadas": "500.00",
  "total_transferencias_recebidas": "200.00"
}
```

> **Importante:** Todos os valores consideram apenas transações com status `confirmado`.

#### Gastos por categoria — `GET /reports/category-spending?mes=8&ano=2026`

```json
{
  "mes": 8,
  "ano": 2026,
  "total_despesas": "4200.00",
  "categorias": [
    {
      "categoria_id": "...",
      "categoria_nome": "Alimentação",
      "cor": "#EF4444",
      "icone": "utensils",
      "valor": "1200.00",
      "percentual": 28.57,
      "tipo": "despesa"
    },
    {
      "categoria_id": "...",
      "categoria_nome": "Moradia",
      "cor": "#8B5CF6",
      "icone": "home",
      "valor": "2000.00",
      "percentual": 47.62,
      "tipo": "despesa"
    }
  ]
}
```

#### Evolução do saldo — `GET /reports/balance-evolution?conta_id=UUID&mes=8&ano=2026`

```json
{
  "conta_id": "...",
  "conta_nome": "Nubank",
  "pontos": [
    { "data": "2026-08-01", "saldo": "1500.00" },
    { "data": "2026-08-02", "saldo": "1500.00" },
    { "data": "2026-08-03", "saldo": "1250.00" },
    ...
  ]
}
```

> Retorna um ponto por dia. O saldo de cada dia é o saldo da conta (saldo_inicial + Σconfirmadas até aquela data).

#### Orçado vs realizado — `GET /reports/budget-vs-actual?mes=8&ano=2026`

```json
{
  "mes": 8,
  "ano": 2026,
  "orcamentos": [
    {
      "categoria_id": "...",
      "categoria_nome": "Alimentação",
      "orcado": "2000.00",
      "realizado": "1580.00",
      "percentual": 79.0,
      "alerta": false
    }
  ]
}
```

---

### 4.9 Health

| Método | Rota     | Autenticado | Descrição          |
|--------|----------|-------------|---------------------|
| GET    | `/health`| Não         | Status da API       |

**Response 200:**

```json
{
  "status": "ok"
}
```

> Útil para o PWA verificar conectividade periodicamente (ex.: a cada retorno de aba, antes de sincronizar dados offline).

---

## 5. Enums

### AccountType

| Valor           | Descrição            |
|-----------------|----------------------|
| `corrente`      | Conta corrente       |
| `poupanca`      | Conta poupança       |
| `carteira`      | Carteira (dinheiro)  |
| `investimento`  | Conta de investimento|
| `cartao_credito`| Cartão de crédito    |

### TransactionType

| Valor          | Descrição       |
|----------------|-----------------|
| `receita`      | Receita         |
| `despesa`      | Despesa         |
| `transferencia`| Transferência   |

### TransactionStatus

| Valor        | Descrição   |
|--------------|-------------|
| `pendente`   | Pendente    |
| `confirmado` | Confirmado  |

### CategoryType

| Valor    | Descrição |
|----------|-----------|
| `receita`| Receita   |
| `despesa`| Despesa   |

### RecurrenceFrequency

| Valor     | Descrição |
|-----------|-----------|
| `diaria`  | Diária    |
| `semanal` | Semanal   |
| `mensal`  | Mensal    |
| `anual`   | Anual     |

### GoalStatus

| Valor          | Descrição    |
|----------------|--------------|
| `em_andamento` | Em andamento |
| `concluida`    | Concluída    |
| `cancelada`    | Cancelada    |

### GoalContributionType

| Valor     | Descrição |
|-----------|-----------|
| `aporte`  | Aporte    |
| `retirada`| Retirada  |

---

## 6. Códigos de Erro

### Envelope de erro padronizado

```json
{
  "detail": "Mensagem descritiva em português",
  "code": "CODIGO_VERBOSO"
}
```

### Tabela de códigos por domínio

| Code                    | Status | Descrição                                      |
|-------------------------|--------|-------------------------------------------------|
| `EMAIL_EXISTS`          | 409    | Email já cadastrado                             |
| `INVALID_CREDENTIALS`   | 401    | Email ou senha incorretos                       |
| `USER_INACTIVE`         | 401    | Usuário desativado                              |
| `TOKEN_REVOKED`         | 401    | Refresh token revogado/expirado                 |
| `INVALID_TOKEN`         | 401    | Access token inválido ou expirado               |
| `INVALID_TOKEN_TYPE`    | 401    | Token do tipo errado (ex: refresh em vez de access) |
| `MISSING_JTI`           | 401    | Refresh token sem claim jti                     |
| `USER_NOT_FOUND`        | 401    | Usuário não encontrado no banco                 |
| `NOT_FOUND`             | 404    | Recurso genérico não encontrado                 |
| `ACCOUNT_NOT_FOUND`     | 404    | Conta não encontrada                            |
| `ACCOUNT_INACTIVE`      | 400    | Conta está desativada                           |
| `CATEGORY_NOT_FOUND`    | 404    | Categoria não encontrada                        |
| `CATEGORY_INACTIVE`     | 400    | Categoria está desativada                       |
| `INVALID_CATEGORY_TYPE` | 400    | Tipo da categoria incompatível com operação     |
| `TRANSACTION_NOT_FOUND` | 404    | Transação não encontrada                        |
| `SAME_ACCOUNT_TRANSFER` | 400    | Origem e destino da transferência são iguais    |
| `TRANSFER_NO_CATEGORY`  | 400    | Transferência não deve ter categoria            |
| `RECURRENCE_NOT_FOUND`  | 404    | Recorrência não encontrada                      |
| `RECURRENCE_INACTIVE`   | 400    | Recorrência está inativa                        |
| `BUDGET_NOT_FOUND`      | 404    | Orçamento não encontrado                        |
| `BUDGET_EXISTS`         | 409    | Já existe orçamento para essa categoria/mês/ano |
| `BUDGET_INVALID_CATEGORY_TYPE` | 400 | Orçamento só aceita categorias de despesa |
| `GOAL_NOT_FOUND`        | 404    | Meta não encontrada                             |
| `GOAL_COMPLETED`        | 400    | Meta já concluída                               |
| `GOAL_CANCELLED`        | 400    | Meta cancelada                                  |
| `RATE_LIMIT_EXCEEDED`   | 429    | Muitas requisições                              |
| `INTEGRITY_ERROR`       | 409    | Violação de integridade do banco                |
| `VALIDATION_ERROR`      | 422    | Validação de campos (Pydantic)                  |
| `INTERNAL_ERROR`        | 500    | Erro interno do servidor                        |

### Formato de erro de validação FastAPI (422)

Quando o body/request tem campos com tipos inválidos, o FastAPI retorna seu formato nativo **antes** do handler customizado:

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

> O frontend deve tratar **dois** formatos de 422: o envelope `{detail, code}` do Pydantic e o array `{detail: [...]}` do FastAPI.

---

## 7. Regras de Negócio

Regras importantes que o frontend deve respeitar:

### Transações

- **Receita/Despesa:** `conta_id` obrigatório, `categoria_id` obrigatório e do tipo correto.
- **Transferência:** `conta_destino_id` obrigatório e diferente de `conta_id`. `categoria_id` deve ser nulo.
- **Valor:** sempre positivo (`> 0`). Decimal com até 2 casas decimais.
- **Idempotency:** Enviar `Idempotency-Key` (UUID) no header ao criar transações para evitar duplicatas no caso de retry de rede.

### Saldo

- **Apenas transações confirmadas** afetam o saldo das contas e os relatórios.
- Transações pendentes existem na tabela mas **não** entram em cálculos de saldo, orçamento ou relatório.

### Categorias

- Ao registrar, o usuário recebe 10 categorias padrão (7 despesas + 3 receitas).
- Categorias não podem ser deletadas se existem transações vinculadas (soft delete: inativar).

### Contas

- Contas com transações vinculadas sofrem soft delete (`ativo = false`) ao invés de exclusão física.

### Orçamentos

- Únicos por `(categoria_id, mes, ano)`. Criar duplicado retorna 409.
- Só aceitam categorias de tipo `despesa`.
- O progresso inclui gastos de **subcategorias** da categoria vinculada.

### Recorrências

- Não geram transações imediatamente ao criar a regra.
- Transações são geradas sob demanda via `POST /recurrences/generate`.
- Usar `idempotency_key` = `recurrence_id` nas transações geradas para evitar duplicatas.

### Metas

- `valor_atual` é computado em runtime (Σaportes − Σretiradas).
- Auto-conclusão: ao atingir o `valor_alvo`, status muda automaticamente para `concluida`.
- Não é possível adicionar contribuições a metas com status `concluida` ou `cancelada`.

---

## 8. Exemplo de Cliente HTTP (TypeScript)

### Cliente com auto-refresh (axios)

```typescript
import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface ApiError {
  detail: string;
  code: string;
}

const api = axios.create({ baseURL: API_BASE });

// ── Armazenamento de tokens (troque por sua solução) ──────────────────────
let accessToken: string | null = null;
let refreshToken: string | null = null;

export function setTokens(access: string, refresh: string) {
  accessToken = access;
  refreshToken = refresh;
  // Alternativa: salvar em httpOnly cookie via backend
}

export function clearTokens() {
  accessToken = null;
  refreshToken = null;
}

// ── Interceptor: injeta access token em cada request ──────────────────────
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (accessToken && config.headers) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// ── Interceptor: renova token automaticamente no 401 ──────────────────────
let isRefreshing = false;
let failedQueue: { resolve: (token: string) => void; reject: (err: unknown) => void }[] = [];

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach(({ resolve, reject }) =>
    error ? reject(error) : resolve(token!)
  );
  failedQueue = [];
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config;

    // Evitar loop infinito: não interceptar chamadas de refresh/login/register
    const skipPaths = ["/auth/login", "/auth/refresh", "/auth/register"];
    const isSkipPath = skipPaths.some((p) => original.url?.includes(p));

    if (error.response?.status === 401 && !isSkipPath && original) {
      if (isRefreshing) {
        // Enfileirar enquanto outro refresh está em andamento
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          if (original.headers) original.headers.Authorization = `Bearer ${token}`;
          return api(original);
        });
      }

      isRefreshing = true;

      try {
        if (!refreshToken) throw new Error("No refresh token");
        const { data } = await axios.post<TokenResponse>(
          `${API_BASE}/auth/refresh`,
          { refresh_token: refreshToken }
        );
        setTokens(data.access_token, data.refresh_token);
        processQueue(null, data.access_token);

        if (original.headers) original.headers.Authorization = `Bearer ${data.access_token}`;
        return api(original);
      } catch (refreshError) {
        processQueue(refreshError, null);
        clearTokens();
        // Redirecionar para login se necessário
        window.location.href = "/login";
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;

// ── Exemplo de uso ────────────────────────────────────────────────────────
export async function login(email: string, senha: string) {
  const { data } = await api.post<TokenResponse>("/auth/login", { email, senha });
  setTokens(data.access_token, data.refresh_token);
  return data;
}

export async function fetchTransactions(mes: number, ano: number) {
  const { data } = await api.get("/transactions", {
    params: { data_inicio: `${ano}-${String(mes).padStart(2, "0")}-01`,
              data_fim: `${ano}-${String(mes).padStart(2, "0")}-28`,
              page: 1, size: 100 },
  });
  return data; // { items, total, page, size, pages }
}

export async function createTransaction(payload: {
  conta_id: string;
  categoria_id: string;
  tipo: "receita" | "despesa";
  valor: string;
  data: string;
  descricao: string;
}) {
  const idempotencyKey = crypto.randomUUID(); // proteção contra retry
  const { data } = await api.post("/transactions", payload, {
    headers: { "Idempotency-Key": idempotencyKey },
  });
  return data;
}
```

### Padrão de chamadas demais módulos

```typescript
// Categorias
await api.get("/categories/tree", { params: { tipo: "despesa" } });

// Orçamentos
await api.post("/budgets", {
  categoria_id: "...",
  valor_limite: "2000.00",
  mes: 8,
  ano: 2026,
});

// Metas
await api.post("/goals/uuid-meta/contributions", {
  valor: "500.00",
  tipo: "aporte",
  data: "2026-08-22",
  observacao: "Aporte mensal",
});

// Relatórios
await api.get("/reports/monthly-summary", { params: { mes: 8, ano: 2026 } });
```

---

## 9. Notas Conhecidas

Pontos relevantes que podem afetar a integração frontend:

1. **Saldo na listagem de contas:** O schema `AccountResponse` inclui `saldo_atual`, mas na listagem o valor pode não estar 100% preciso. Para saldo confiável, usar `GET /accounts/{id}/balance` ou considerar o saldo calculado como aproximado no listing.

2. **Filtros de transações como query params:** O endpoint `GET /transactions` aceita filtros via query params (`conta_id`, `categoria_id`, `tipo`, `status`, `data_inicio`, `data_fim`, `descricao`). A param `descricao` faz busca por substring na descrição.

3. **Relatórios sem paginação:** Os endpoints de relatório retornam objetos únicos, não arrays paginados.

4. **Goal progress endpoint (GET /goals/{id}/progress):** Retorna objeto plano com `valor_atual` (Decimal como string) e `progresso_percentual` (float). **Não** usa schema Pydantic para resposta.

5. **Endpoint de health:** Pode ser usado pelo PWA como probe de conectividade offline/online. Não requer autenticação.

6. **Swagger em /docs:** Disponível apenas em ambiente de desenvolvimento para teste manual.

7. **UUIDs:** IDs de recursos (contas, categorias, transações, etc.) são UUIDs no formato `550e8400-e29b-41d4-a716-446655440000`.

8. **Strings decimais:** Valores monetários chegam como strings (ex: `"1234.50"`). Usar `parseFloat()` com cautela — para cálculos financeiros considerar aritmética baseada em centavos ou biblioteca decimal (`decimal.js`).

9. **CORS configurável:** As origins são definidas via variável `CORS_ORIGINS` no `.env` (array JSON). Para deploy em produção, adicionar o domínio da PWA.

10. **Geração de recorrências:** As transações de recorrências **não aparecem** até chamar `POST /recurrences/generate`. O frontend deve disparar essa chamada periodicamente ou ao carregar a tela principal.

---

*Documento gerado automaticamente a partir da análise do código-fonte em `W:\projetos\backend-fin-py` — agosto 2026.*

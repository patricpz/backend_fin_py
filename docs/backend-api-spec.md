# Backend API & Architecture Specification: Management Modules

This specification document outlines the database schema, business rules, and RESTful API endpoints required to implement the four management modules in the backend:
1. **Categories**
2. **Budgets**
3. **Financial Goals & Contributions**
4. **Reports & Analytics**

---

## 1. Global Architecture & Standards

### 1.1 Authentication & Multi-Tenancy
- All endpoints (except public authentication routes) must be secured via **JWT** using the `Authorization: Bearer <token>` header.
- **Strict Data Isolation:** Every query, creation, update, and deletion must be scoped to the authenticated `user_id` extracted from the token. Users must never access or modify data belonging to other accounts.

### 1.2 Data Formats & Field Naming
- The frontend adapter handles both `snake_case` (preferred for REST payloads) and standard formats.
- Monetary values:
  - Database: Stored as `NUMERIC(15, 2)` or `DECIMAL(15, 2)`.
  - API JSON: Returned as floating-point numbers or numeric strings (e.g. `150.50`).
- Timestamps: ISO 8601 strings in UTC (`YYYY-MM-DDTHH:mm:ss.sssZ`).
- Dates: `YYYY-MM-DD`.

### 1.3 Standard Error Responses
All error responses must follow a consistent format:
```json
{
  "statusCode": 400,
  "error": "Bad Request",
  "message": "Category with this name already exists for this user",
  "timestamp": "2026-10-25T20:30:00.000Z"
}
```

---

## 2. Database Schema (PostgreSQL DDL)

```sql
-- Extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ========================================================
-- 1. CATEGORIES TABLE
-- ========================================================
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('receita', 'despesa')),
    color VARCHAR(30) DEFAULT '#6B7280',
    icon VARCHAR(60) DEFAULT 'Tag',
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_user_category_name_type UNIQUE (user_id, name, type)
);

CREATE INDEX idx_categories_user_id ON categories(user_id);
CREATE INDEX idx_categories_parent_id ON categories(parent_id);

-- ========================================================
-- 2. BUDGETS TABLE
-- ========================================================
CREATE TABLE budgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    limit_amount NUMERIC(15, 2) NOT NULL CHECK (limit_amount > 0),
    month INT NOT NULL CHECK (month BETWEEN 1 AND 12),
    year INT NOT NULL CHECK (year >= 2020),
    alert_percentage INT DEFAULT 80 CHECK (alert_percentage BETWEEN 1 AND 100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_user_category_month_year UNIQUE (user_id, category_id, month, year)
);

CREATE INDEX idx_budgets_user_period ON budgets(user_id, year, month);

-- ========================================================
-- 3. FINANCIAL GOALS TABLE
-- ========================================================
CREATE TABLE goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    target_amount NUMERIC(15, 2) NOT NULL CHECK (target_amount > 0),
    target_date DATE,
    category VARCHAR(100),
    status VARCHAR(20) DEFAULT 'em_andamento' CHECK (status IN ('em_andamento', 'concluida', 'cancelada')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_goals_user_status ON goals(user_id, status);

-- ========================================================
-- 4. GOAL CONTRIBUTIONS (DEPOSITS / WITHDRAWALS) TABLE
-- ========================================================
CREATE TABLE goal_contributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    amount NUMERIC(15, 2) NOT NULL CHECK (amount > 0),
    type VARCHAR(20) NOT NULL CHECK (type IN ('aporte', 'retirada')),
    date DATE NOT NULL,
    observation TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_goal_contributions_goal_id ON goal_contributions(goal_id);
CREATE INDEX idx_goal_contributions_date ON goal_contributions(date);
```

---

## 3. Detailed Endpoint Contracts

### 3.1 Module 1: Categories (`/categories`)

#### `GET /categories`
Lists all categories belonging to the user.
- **Query Parameters:**
  - `type` or `tipo` *(optional)*: `'receita' | 'despesa'`
  - `active` *(optional)*: `boolean`
- **Response `200 OK`:**
```json
[
  {
    "id": "e4b2d354-97c7-4b78-b5e1-2f3b6d274001",
    "userId": "usr_12345",
    "name": "Alimentação",
    "type": "despesa",
    "color": "#EF4444",
    "icon": "Utensils",
    "parentId": null,
    "active": true
  }
]
```

#### `GET /categories/tree`
Returns root categories with nested subcategories.
- **Response `200 OK`:**
```json
[
  {
    "id": "e4b2d354-97c7-4b78-b5e1-2f3b6d274001",
    "name": "Alimentação",
    "type": "despesa",
    "color": "#EF4444",
    "icon": "Utensils",
    "parentId": null,
    "children": [
      {
        "id": "f8a1b2c3-1234-5678-90ab-cdef12345678",
        "name": "Supermercado",
        "type": "despesa",
        "color": "#F87171",
        "icon": "ShoppingCart",
        "parentId": "e4b2d354-97c7-4b78-b5e1-2f3b6d274001",
        "children": []
      }
    ]
  }
]
```

#### `POST /categories`
Creates a new category.
- **Request Body:**
```json
{
  "nome": "Restaurantes",
  "tipo": "despesa",
  "cor": "#F97316",
  "icone": "Coffee",
  "categoria_pai_id": "e4b2d354-97c7-4b78-b5e1-2f3b6d274001"
}
```
- **Response `201 Created`:** Returns created category object.

#### `PATCH /categories/:id`
Updates category fields.
- **Request Body (partial):**
```json
{
  "nome": "Restaurantes e Bares",
  "cor": "#FB923C",
  "icone": "Wine"
}
```

#### `DELETE /categories/:id`
Deletes a category.
- **Query Parameter:**
  - `migrar_para_id` *(optional, UUID)*: Target category to reassign existing transactions.
- **Business Rule:**
  - If the category has linked transactions and no `migrar_para_id` is supplied, reject with `409 Conflict`:
    `{ "message": "Category has transactions. Provide migrar_para_id to reassign before deletion." }`
  - If `migrar_para_id` is supplied, execute reassignment inside a database transaction before deleting.

---

### 3.2 Module 2: Budgets (`/budgets`)

#### `GET /budgets`
Lists budgets filtered by month and year.
- **Query Parameters:**
  - `mes` or `month` *(int, 1-12, required)*
  - `ano` or `year` *(int, required)*
- **Response `200 OK`:**
```json
[
  {
    "id": "b1a2c3d4-0001-4000-8000-000000000001",
    "userId": "usr_12345",
    "categoryId": "e4b2d354-97c7-4b78-b5e1-2f3b6d274001",
    "categoryName": "Alimentação",
    "limitAmount": 2000.00,
    "spent": 1450.50,
    "percentage": 72.52,
    "alertPercentage": 80,
    "alert": false,
    "month": 10,
    "year": 2026
  }
]
```

#### `GET /budgets/:id/progress`
Returns progress details for a specific budget.
- **Response `200 OK`:**
```json
{
  "budgetId": "b1a2c3d4-0001-4000-8000-000000000001",
  "categoryId": "e4b2d354-97c7-4b78-b5e1-2f3b6d274001",
  "categoryName": "Alimentação",
  "limitAmount": 2000.00,
  "spent": 1850.00,
  "percentage": 92.50,
  "alert": true,
  "month": 10,
  "year": 2026
}
```

#### `POST /budgets`
Creates a budget limit for a category in a specific period.
- **Request Body:**
```json
{
  "categoria_id": "e4b2d354-97c7-4b78-b5e1-2f3b6d274001",
  "valor_limite": 2000.00,
  "mes": 10,
  "ano": 2026,
  "percentual_alerta": 80
}
```

#### `PATCH /budgets/:id`
Updates budget limit or alert threshold.
- **Request Body:**
```json
{
  "valor_limite": 2500.00,
  "percentual_alerta": 85
}
```

#### `DELETE /budgets/:id`
Deletes the budget record. Returns `204 No Content`.

---

### 3.3 Module 3: Financial Goals (`/goals`)

#### `GET /goals`
Lists user goals.
- **Query Parameters:**
  - `status` *(optional)*: `'em_andamento' | 'concluida' | 'cancelada'`
- **Response `200 OK`:**
```json
[
  {
    "id": "g1a2b3c4-0001-5000-9000-000000000001",
    "userId": "usr_12345",
    "name": "Reserva de Emergência",
    "description": "6 meses de custo fixo",
    "targetAmount": 30000.00,
    "currentAmount": 15000.00,
    "progressPercentage": 50.00,
    "targetDate": "2027-12-31",
    "category": "Investimentos",
    "status": "em_andamento",
    "createdAt": "2026-01-15T10:00:00.000Z",
    "updatedAt": "2026-10-25T14:30:00.000Z"
  }
]
```

#### `GET /goals/:id/progress`
Calculates and returns current progress.
- **Response `200 OK`:**
```json
{
  "goalId": "g1a2b3c4-0001-5000-9000-000000000001",
  "targetAmount": 30000.00,
  "currentAmount": 15000.00,
  "progressPercentage": 50.00,
  "status": "em_andamento"
}
```

#### `POST /goals`
Creates a new goal.
- **Request Body:**
```json
{
  "nome": "Viagem Japão",
  "descricao": "Férias de 2027",
  "valor_alvo": 25000.00,
  "data_alvo": "2027-09-30",
  "categoria": "Lazer"
}
```

#### `POST /goals/:id/contributions`
Registers a deposit or withdrawal for a goal.
- **Request Body:**
```json
{
  "valor": 1200.00,
  "tipo": "aporte",
  "data": "2026-10-25",
  "observacao": "Economia do bônus salarial"
}
```
- **Validation Rule:**
  - If `tipo == 'retirada'`, ensure `valor <= currentAmount`. Reject with `400 Bad Request` if insufficient funds.

#### `GET /goals/:id/contributions`
Returns contribution history for the goal.
- **Query Parameters:** `page` *(int)*, `size` *(int)*
- **Response `200 OK`:**
```json
[
  {
    "id": "c1a2b3c4-0001-6000-9000-000000000001",
    "goalId": "g1a2b3c4-0001-5000-9000-000000000001",
    "amount": 1200.00,
    "type": "aporte",
    "date": "2026-10-25",
    "observation": "Economia do bônus salarial",
    "createdAt": "2026-10-25T14:30:00.000Z"
  }
]
```

---

### 3.4 Module 4: Reports & Analytics (`/reports`)

#### `GET /reports/monthly-summary`
Provides cash flow aggregates for the requested month.
- **Query Parameters:** `mes` (int, 1-12), `ano` (int)
- **Response `200 OK`:**
```json
{
  "month": 10,
  "year": 2026,
  "totalIncome": 12500.00,
  "totalExpenses": 8340.50,
  "balance": 4159.50,
  "totalTransfersSent": 1000.00,
  "totalTransfersReceived": 1000.00
}
```

#### `GET /reports/category-spending`
Returns expense breakdown grouped by category for donut/pie charts.
- **Query Parameters:** `mes` (int, 1-12), `ano` (int)
- **Response `200 OK`:**
```json
{
  "month": 10,
  "year": 2026,
  "total": 8340.50,
  "items": [
    {
      "categoryId": "e4b2d354-97c7-4b78-b5e1-2f3b6d274001",
      "categoryName": "Alimentação",
      "color": "#EF4444",
      "icon": "Utensils",
      "amount": 2500.00,
      "percentage": 29.97,
      "type": "despesa"
    },
    {
      "categoryId": "a2b3c4d5-0002-4000-8000-000000000002",
      "categoryName": "Moradia",
      "color": "#3B82F6",
      "icon": "Home",
      "amount": 3200.00,
      "percentage": 38.37,
      "type": "despesa"
    }
  ]
}
```

#### `GET /reports/balance-evolution`
Returns timeline data for balance and cash flow trend analysis.
- **Query Parameters:**
  - `ano` *(int)*: Returns all months of the year.
  - `conta_id` *(optional, UUID)*: Filters by specific account.
- **Response `200 OK`:**
```json
[
  { "month": 7, "year": 2026, "totalIncome": 11000.00, "totalExpenses": 7500.00, "balance": 3500.00 },
  { "month": 8, "year": 2026, "totalIncome": 11200.00, "totalExpenses": 8100.00, "balance": 3100.00 },
  { "month": 9, "year": 2026, "totalIncome": 12000.00, "totalExpenses": 7900.00, "balance": 4100.00 },
  { "month": 10, "year": 2026, "totalIncome": 12500.00, "totalExpenses": 8340.50, "balance": 4159.50 }
]
```

#### `GET /reports/budget-vs-actual`
Returns comparative data between budget caps and confirmed spending.
- **Query Parameters:** `mes` (int, 1-12), `ano` (int)
- **Response `200 OK`:**
```json
[
  {
    "categoryId": "e4b2d354-97c7-4b78-b5e1-2f3b6d274001",
    "categoryName": "Alimentação",
    "budgeted": 2000.00,
    "actual": 1850.00,
    "difference": 150.00,
    "percentage": 92.50
  },
  {
    "categoryId": "c3d4e5f6-0003-4000-8000-000000000003",
    "categoryName": "Lazer",
    "budgeted": 800.00,
    "actual": 920.00,
    "difference": -120.00,
    "percentage": 115.00
  }
]
```

---

## 4. Key Calculation Queries (Reference SQL)

### 4.1 Budget Realized Spending Calculation
To calculate spent amount for a budget category (including its subcategories):
```sql
SELECT COALESCE(SUM(t.amount), 0) AS spent
FROM transactions t
WHERE t.user_id = :userId
  AND t.type = 'despesa'
  AND t.status = 'confirmado'
  AND EXTRACT(MONTH FROM t.date) = :month
  AND EXTRACT(YEAR FROM t.date) = :year
  AND (
    t.category_id = :categoryId
    OR t.category_id IN (
      SELECT id FROM categories WHERE parent_id = :categoryId AND user_id = :userId
    )
  );
```

### 4.2 Goal Current Balance & Progress
```sql
SELECT
  g.id,
  g.target_amount,
  COALESCE(SUM(CASE WHEN c.type = 'aporte' THEN c.amount ELSE -c.amount END), 0) AS current_amount,
  ROUND(
    (COALESCE(SUM(CASE WHEN c.type = 'aporte' THEN c.amount ELSE -c.amount END), 0) / g.target_amount) * 100,
    2
  ) AS progress_percentage
FROM goals g
LEFT JOIN goal_contributions c ON c.goal_id = g.id
WHERE g.id = :goalId AND g.user_id = :userId
GROUP BY g.id, g.target_amount;
```

---

## 5. Development Roadmap & Milestones

1. **Sprint 1 (Categories):**
   - Run DDL for `categories`.
   - Implement `GET /categories`, `GET /categories/tree`, `POST /categories`, `PATCH /categories/:id`, and safe `DELETE /categories/:id`.
   - Seed default categories on new user registration (e.g. Alimentação, Transporte, Salário).

2. **Sprint 2 (Budgets):**
   - Run DDL for `budgets`.
   - Implement `GET /budgets`, `POST /budgets`, `PATCH /budgets/:id`, `DELETE /budgets/:id`.
   - Integrate spent calculation using confirmed transactions.

3. **Sprint 3 (Financial Goals):**
   - Run DDL for `goals` and `goal_contributions`.
   - Implement goals CRUD and `POST /goals/:id/contributions`.
   - Ensure withdrawal amount checks prevent negative goal balances.

4. **Sprint 4 (Reports & Aggregations):**
   - Implement report endpoints (`/reports/monthly-summary`, `/reports/category-spending`, `/reports/balance-evolution`, `/reports/budget-vs-actual`).
   - Add database indexes to optimize date range filtering on `transactions(user_id, date, status)`.

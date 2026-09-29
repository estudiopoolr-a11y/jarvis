-- Esquema PostgreSQL equivalente al modelo Kebo de Cloud Firestore.
-- Firebase Data Connect genera estas tablas a partir de schema.gql.
-- Un presupuesto es un techo mensual y nunca se resta de accounts.balance.

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    moneda TEXT NOT NULL DEFAULT 'COP',
    tema TEXT NOT NULL DEFAULT 'dark',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'cash',
    currency TEXT NOT NULL DEFAULT 'COP',
    institution TEXT NOT NULL DEFAULT '',
    bank_last4 TEXT NOT NULL DEFAULT '',
    balance DOUBLE PRECISION NOT NULL DEFAULT 0,
    icon TEXT NOT NULL DEFAULT '💰',
    color TEXT NOT NULL DEFAULT '#10b981',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    budget DOUBLE PRECISION NOT NULL DEFAULT 0,
    tipo TEXT NOT NULL DEFAULT 'variable',
    icono TEXT NOT NULL DEFAULT '📦',
    color TEXT NOT NULL DEFAULT '#3b82f6',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, nombre)
);

CREATE TABLE subcategories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    icono TEXT NOT NULL DEFAULT '📦',
    color TEXT NOT NULL DEFAULT '#6b7280',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (category_id, nombre)
);

CREATE TABLE budget_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    category_name TEXT NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    period CHAR(7) NOT NULL CHECK (period ~ '^[0-9]{4}-[0-9]{2}$'),
    year CHAR(4) NOT NULL,
    month CHAR(2) NOT NULL,
    rollover_from CHAR(7),
    rollover_amount DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, period, category_name)
);

CREATE TABLE recurring (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    nombre TEXT NOT NULL,
    monto DOUBLE PRECISION NOT NULL,
    frecuencia TEXT NOT NULL DEFAULT 'monthly',
    dia INTEGER NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    ultima_ejecucion TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    to_account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
    parent_id UUID REFERENCES transactions(id) ON DELETE CASCADE,
    recurring_id UUID REFERENCES recurring(id) ON DELETE SET NULL,
    type TEXT NOT NULL CHECK (type IN ('income', 'expense', 'transfer')),
    amount DOUBLE PRECISION NOT NULL,
    payee TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    fee DOUBLE PRECISION NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'cleared',
    tags TEXT[] NOT NULL DEFAULT '{}',
    date DATE NOT NULL,
    period CHAR(7) NOT NULL CHECK (period ~ '^[0-9]{4}-[0-9]{2}$'),
    is_split BOOLEAN NOT NULL DEFAULT FALSE,
    is_split_child BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE transaction_splits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    category_name TEXT NOT NULL,
    amount DOUBLE PRECISION NOT NULL
);

CREATE TABLE goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
    nombre TEXT NOT NULL,
    monto_objetivo DOUBLE PRECISION NOT NULL,
    current_amount DOUBLE PRECISION NOT NULL DEFAULT 0,
    fecha_limite TEXT NOT NULL DEFAULT '',
    completada BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE goal_contributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    monto DOUBLE PRECISION NOT NULL,
    fecha DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    day INTEGER NOT NULL,
    month TEXT NOT NULL,
    year TEXT NOT NULL,
    categoria TEXT NOT NULL DEFAULT '',
    monto DOUBLE PRECISION NOT NULL DEFAULT 0,
    done BOOLEAN NOT NULL DEFAULT FALSE,
    notified_at TIMESTAMPTZ,
    done_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE loans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    persona TEXT NOT NULL,
    monto DOUBLE PRECISION NOT NULL,
    monto_original DOUBLE PRECISION NOT NULL,
    monto_pagado DOUBLE PRECISION NOT NULL DEFAULT 0,
    monto_pendiente DOUBLE PRECISION NOT NULL,
    fecha DATE NOT NULL,
    nota TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pendiente',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE loan_payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id UUID NOT NULL REFERENCES loans(id) ON DELETE CASCADE,
    monto DOUBLE PRECISION NOT NULL,
    fecha DATE NOT NULL
);

CREATE TABLE scheduled_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    type TEXT NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    categoria_nombre TEXT NOT NULL,
    cuenta_nombre TEXT NOT NULL,
    payee TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    scheduled_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    tags TEXT[] NOT NULL DEFAULT '{}',
    executed_at TIMESTAMPTZ,
    tx_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE exchange_rates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    currency TEXT NOT NULL,
    rate DOUBLE PRECISION NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, currency)
);

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tarea TEXT NOT NULL,
    prioridad TEXT NOT NULL DEFAULT 'Media',
    fecha_limite TEXT NOT NULL DEFAULT 'Pronto',
    completada BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE fixed_payments (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    monto DOUBLE PRECISION NOT NULL,
    dia_mes INTEGER NOT NULL,
    categoria TEXT NOT NULL DEFAULT 'General',
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE profiles (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    datos JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    remitente TEXT NOT NULL,
    mensaje TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE legacy_budgets (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    categoria TEXT NOT NULL,
    limite DOUBLE PRECISION NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE legacy_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL,
    monto DOUBLE PRECISION NOT NULL,
    categoria TEXT NOT NULL,
    descripcion TEXT NOT NULL DEFAULT '',
    mes CHAR(7),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_transactions_user_period ON transactions (user_id, period);
CREATE INDEX idx_budget_items_user_period ON budget_items (user_id, period);
CREATE INDEX idx_accounts_user ON accounts (user_id);
CREATE INDEX idx_categories_user ON categories (user_id);

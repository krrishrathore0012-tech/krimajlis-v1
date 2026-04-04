-- KRIMAJLIS Supabase Schema
-- Run this once in the Supabase SQL editor at:
-- https://supabase.com/dashboard/project/aeoxabclkgcjhntynyoa/sql

-- Signals table: every signal generated gets frozen here
CREATE TABLE IF NOT EXISTS signals (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    signal_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    instrument_name TEXT,
    geography TEXT,
    direction TEXT NOT NULL,
    conviction FLOAT NOT NULL,
    loophole_type TEXT NOT NULL,
    alpha_layer TEXT,
    rationale TEXT,
    gap_to_theoretical FLOAT,
    expected_reversion_sessions INTEGER,
    regime_alignment BOOLEAN,
    causal_chain JSONB,
    regime_state JSONB,
    primary_node_snapshot JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    entry_window_expires_at TIMESTAMPTZ,
    validation_status TEXT DEFAULT 'PENDING',
    realized_direction TEXT,
    realized_move_pct FLOAT,
    outcome TEXT,
    validated_at TIMESTAMPTZ
);

-- Paper trades table
CREATE TABLE IF NOT EXISTS paper_trades (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    trade_id INTEGER,
    signal_id TEXT,
    ticker TEXT NOT NULL,
    direction TEXT NOT NULL,
    conviction FLOAT,
    entry_price FLOAT,
    exit_price FLOAT,
    realized_pnl FLOAT,
    status TEXT DEFAULT 'OPEN',
    outcome TEXT,
    alpha_layer TEXT,
    sessions_held INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ
);

-- Accuracy summary table
CREATE TABLE IF NOT EXISTS accuracy_summary (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    total_signals INTEGER,
    validated_signals INTEGER,
    hit_count INTEGER,
    miss_count INTEGER,
    overall_accuracy FLOAT,
    by_layer JSONB,
    by_loophole_type JSONB,
    by_geography JSONB,
    by_regime JSONB,
    rolling_7d_accuracy FLOAT,
    rolling_30d_accuracy FLOAT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_signals_created_at ON signals(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_validation_status ON signals(validation_status);
CREATE INDEX IF NOT EXISTS idx_signals_loophole_type ON signals(loophole_type);
CREATE INDEX IF NOT EXISTS idx_paper_trades_status ON paper_trades(status);

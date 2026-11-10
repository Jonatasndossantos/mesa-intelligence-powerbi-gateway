-- =============================================================================
-- MESA INTELLIGENCE · INFRAESTRUTURA SUPABASE (POSTGRESQL + RLS + REALTIME)
-- =============================================================================
-- Instruções:
-- 1. Acesse seu projeto em https://supabase.com/dashboard
-- 2. No menu lateral esquerdo, clique em "SQL Editor" -> "New query"
-- 3. Cole todo este conteúdo e clique em "Run" (ou Ctrl+Enter)
-- =============================================================================

-- 1. TABELA DE LOJAS (RESTAURANTES CONECTADOS)
CREATE TABLE IF NOT EXISTS public.lojas (
    idloja BIGINT PRIMARY KEY,
    nome TEXT NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    agent_status TEXT DEFAULT 'offline',
    agent_version TEXT DEFAULT '1.0.0',
    last_heartbeat_at TIMESTAMPTZ,
    corte DATE DEFAULT CURRENT_DATE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. TABELA DE CONTROLE DE ACESSO MULTI-TENANT (VÍNCULO USUÁRIO <-> LOJA)
CREATE TABLE IF NOT EXISTS public.user_lojas (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    idloja BIGINT REFERENCES public.lojas(idloja) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'cliente' CHECK (role IN ('admin', 'consultor', 'cliente')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, idloja)
);

-- Índice para acelerar verificação de RLS em cada query
CREATE INDEX IF NOT EXISTS idx_user_lojas_user_id ON public.user_lojas(user_id);
CREATE INDEX IF NOT EXISTS idx_user_lojas_idloja ON public.user_lojas(idloja);

-- 3. TABELA DE VENDAS MENSAIS (ESTRUTURADA PARA KPIS E REALTIME IMEDIATO)
CREATE TABLE IF NOT EXISTS public.vendas_mensais (
    idloja BIGINT NOT NULL REFERENCES public.lojas(idloja) ON DELETE CASCADE,
    mes TEXT NOT NULL, -- Formato 'YYYY-MM'
    pedidos_validos INTEGER NOT NULL DEFAULT 0,
    lancado NUMERIC(14,2) NOT NULL DEFAULT 0,
    excluidos NUMERIC(14,2) NOT NULL DEFAULT 0,
    venda_bruta NUMERIC(14,2) NOT NULL DEFAULT 0,
    descontos NUMERIC(14,2) NOT NULL DEFAULT 0,
    venda_liquida NUMERIC(14,2) NOT NULL DEFAULT 0,
    servico NUMERIC(14,2) NOT NULL DEFAULT 0,
    total_com_servico NUMERIC(14,2) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (idloja, mes)
);

CREATE INDEX IF NOT EXISTS idx_vendas_mensais_idloja ON public.vendas_mensais(idloja);

-- 4. TABELA HÍBRIDA DE MÓDULOS ANALÍTICOS POR LOJA (JSONB COMPRIMIDO DE ALTA VELOCIDADE)
-- Armazena fatias por loja: 'produtos', 'grupos', 'horas', 'excl', 'dre_lanc', 'fech_meio', 'dfc', etc.
CREATE TABLE IF NOT EXISTS public.loja_modulos (
    idloja BIGINT NOT NULL REFERENCES public.lojas(idloja) ON DELETE CASCADE,
    modulo TEXT NOT NULL,
    dados JSONB NOT NULL DEFAULT '[]'::jsonb,
    hash_md5 TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (idloja, modulo)
);

CREATE INDEX IF NOT EXISTS idx_loja_modulos_idloja ON public.loja_modulos(idloja);

-- =============================================================================
-- 5. FUNÇÃO DE SEGURANÇA (VERIFICAÇÃO DE ACESSO MULTI-TENANT)
-- =============================================================================
CREATE OR REPLACE FUNCTION public.user_has_loja_access(target_idloja BIGINT)
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.user_lojas ul
        WHERE ul.user_id = auth.uid()
          AND (
              ul.role IN ('admin', 'consultor')
              OR ul.idloja = target_idloja
          )
    );
$$;

-- =============================================================================
-- 6. ROW LEVEL SECURITY (RLS) - ISOLAMENTO BANCÁRIO ENTRE RESTAURANTES
-- =============================================================================
ALTER TABLE public.lojas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_lojas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vendas_mensais ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.loja_modulos ENABLE ROW LEVEL SECURITY;

-- Políticas para public.lojas
DROP POLICY IF EXISTS "Usuarios veem apenas lojas autorizadas" ON public.lojas;
CREATE POLICY "Usuarios veem apenas lojas autorizadas"
    ON public.lojas
    FOR SELECT
    TO authenticated
    USING (public.user_has_loja_access(idloja));

-- Políticas para public.user_lojas
DROP POLICY IF EXISTS "Usuarios veem seus proprios vinculos" ON public.user_lojas;
CREATE POLICY "Usuarios veem seus proprios vinculos"
    ON public.user_lojas
    FOR SELECT
    TO authenticated
    USING (user_id = auth.uid() OR public.user_has_loja_access(idloja));

-- Políticas para public.vendas_mensais
DROP POLICY IF EXISTS "Usuarios veem vendas apenas das lojas autorizadas" ON public.vendas_mensais;
CREATE POLICY "Usuarios veem vendas apenas das lojas autorizadas"
    ON public.vendas_mensais
    FOR SELECT
    TO authenticated
    USING (public.user_has_loja_access(idloja));

-- Políticas para public.loja_modulos
DROP POLICY IF EXISTS "Usuarios veem modulos apenas das lojas autorizadas" ON public.loja_modulos;
CREATE POLICY "Usuarios veem modulos apenas das lojas autorizadas"
    ON public.loja_modulos
    FOR SELECT
    TO authenticated
    USING (public.user_has_loja_access(idloja));

-- =============================================================================
-- 7. ATIVAÇÃO DO MOTOR DE TEMPO REAL (SUPABASE REALTIME WEBSOCKETS)
-- =============================================================================
ALTER TABLE public.lojas REPLICA IDENTITY FULL;
ALTER TABLE public.vendas_mensais REPLICA IDENTITY FULL;
ALTER TABLE public.loja_modulos REPLICA IDENTITY FULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables
        WHERE pubname = 'supabase_realtime' AND schemaname = 'public' AND tablename = 'lojas'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.lojas;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables
        WHERE pubname = 'supabase_realtime' AND schemaname = 'public' AND tablename = 'vendas_mensais'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.vendas_mensais;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables
        WHERE pubname = 'supabase_realtime' AND schemaname = 'public' AND tablename = 'loja_modulos'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.loja_modulos;
    END IF;
END $$;

-- =============================================================================
-- 8. FUNÇÃO UTILITÁRIA PARA VINCULAR USUÁRIOS POR E-MAIL (SEM PRECISAR DE UUID)
-- =============================================================================
CREATE OR REPLACE FUNCTION public.vincular_usuario_por_email(
    p_email TEXT,
    p_idloja BIGINT DEFAULT NULL,
    p_role TEXT DEFAULT 'cliente'
)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_uid UUID;
BEGIN
    SELECT id INTO v_uid FROM auth.users WHERE LOWER(email) = LOWER(TRIM(p_email)) LIMIT 1;
    IF v_uid IS NULL THEN
        RAISE EXCEPTION 'Usuário com e-mail % não encontrado em Authentication -> Users.', p_email;
    END IF;

    IF p_role = 'admin' AND p_idloja IS NULL THEN
        -- Vincula admin à loja padrão 10603 com role 'admin' (que libera acesso global na função RLS)
        INSERT INTO public.user_lojas (user_id, email, idloja, role)
        VALUES (v_uid, LOWER(TRIM(p_email)), 10603, 'admin')
        ON CONFLICT (user_id, idloja) DO UPDATE SET role = 'admin';
        RETURN 'Sucesso: ' || p_email || ' configurado como ADMIN (acesso a todas as lojas).';
    ELSE
        INSERT INTO public.user_lojas (user_id, email, idloja, role)
        VALUES (v_uid, LOWER(TRIM(p_email)), p_idloja, p_role)
        ON CONFLICT (user_id, idloja) DO UPDATE SET role = EXCLUDED.role;
        RETURN 'Sucesso: ' || p_email || ' vinculado à loja ' || p_idloja || ' com perfil ' || p_role;
    END IF;
END;
$$;

-- =============================================================================
-- 9. DADOS INICIAIS DAS LOJAS PILOTO (PRONTO PARA RECEBER SYNC)
-- =============================================================================
INSERT INTO public.lojas (idloja, nome, ativo, agent_status)
VALUES
    (10603, 'WORLD CAFE', TRUE, 'ready'),
    (15173, 'TEMPLO DO RAIMUNDAO', TRUE, 'ready')
ON CONFLICT (idloja) DO UPDATE
SET nome = EXCLUDED.nome, updated_at = NOW();

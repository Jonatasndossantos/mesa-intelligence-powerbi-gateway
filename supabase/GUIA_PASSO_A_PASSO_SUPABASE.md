# 🚀 Guia Rápido (2 Minutos): Configurando o Supabase para o MESA Intelligence

Este guia mostra como ativar o banco de dados em nuvem, autenticação por loja e motor de Tempo Real no **Plano Gratuito do Supabase (R$ 0/mês)**.

---

## Passo 1: Criar o Projeto Gratuito no Supabase
1. Acesse [https://supabase.com/dashboard](https://supabase.com/dashboard) e faça login (pode entrar com sua conta do GitHub).
2. Clique em **"New project"**.
3. Preencha:
   - **Name:** `mesa-intelligence`
   - **Database Password:** Crie uma senha forte (e anote se quiser).
   - **Region:** Escolha `South America (São Paulo)` para menor latência no Brasil.
4. Clique em **"Create new project"** e aguarde ~1 minuto enquanto o banco PostgreSQL é provisionado.

---

## Passo 2: Criar as Tabelas, Segurança (RLS) e Tempo Real
1. No menu lateral esquerdo do Supabase, clique no ícone **SQL Editor** (`>_`).
2. Clique em **"+ New query"**.
3. Abra o arquivo [`supabase/01_schema_and_rls.sql`](../supabase/01_schema_and_rls.sql) deste projeto, copie todo o conteúdo e cole no editor do Supabase.
4. Clique no botão verde **"Run"** (no canto inferior direito).
   - *Resultado esperado:* `"Success. No rows returned"` (Tabelas, políticas RLS bancárias e WebSockets Realtime criados!).

---

## Passo 3: Criar os Usuários de Acesso (Consultoria e Clientes)
1. No menu lateral esquerdo, clique em **Authentication** (ícone de cadeado/usuários) $\rightarrow$ **Users**.
2. Clique em **"Add user"** $\rightarrow$ **"Create new user"**.
3. Crie os usuários de teste (deixe a opção *"Auto Confirm User?"* **marcada**):
   - **Seu usuário Master (Consultoria MESA):** ex: `admin@mesa.com.br` + sua senha.
   - **Usuário Cliente World Café:** ex: `worldcafe@cliente.com` + senha.
   - **Usuário Cliente Templo do Raimundão:** ex: `raimundao@cliente.com` + senha.
4. Agora, volte no **SQL Editor** e rode apenas estas linhas (trocando pelos e-mails que você criou) para dizer ao banco quem vê qual loja:

```sql
-- 1. Dar acesso TOTAL (todas as lojas) para o consultor/admin da MESA:
SELECT public.vincular_usuario_por_email('admin@mesa.com.br', NULL, 'admin');

-- 2. Restringir o usuário do World Café APENAS à loja 10603:
SELECT public.vincular_usuario_por_email('worldcafe@cliente.com', 10603, 'cliente');

-- 3. Restringir o usuário do Raimundão APENAS à loja 15173:
SELECT public.vincular_usuario_por_email('raimundao@cliente.com', 15173, 'cliente');
```

---

## Passo 4: Copiar as Chaves do Projeto (`Project URL` e `API Keys`)
1. No menu lateral esquerdo do Supabase, vá em **Project Settings** (ícone de engrenagem lá embaixo) $\rightarrow$ **API** (ou **Data API / API Keys**).
2. Você verá 3 informações que usaremos:
   - **Project URL:** (ex: `https://xyzcompany.supabase.co`) $\rightarrow$ Usada no Site e no Agente.
   - ** Key `anon` / `public`:** $\rightarrow$ Usada no Site (`app_ao_vivo.html`). Ela é segura para ficar no frontend porque respeita o login e o RLS!
   - **Key `service_role` / `secret`:** $\rightarrow$ Usada **APENAS** no Agente Sincronizador (`mesa-sync-agent/config.env`) lá na máquina do Garçom Web para empurrar os dados para o banco. **Nunca coloque a `service_role` no HTML público.**

# 📦 MESA Sync Agent · Kit para a Máquina do Garçom Web

Esta pasta (`mesa-sync-agent/`) é **100% independente e portátil**. Você deve copiá-la para o computador onde o banco de dados do **Garçom Web** está rodando.

---

## Como Instalar na Máquina do Garçom Web (3 Passos)

### 1. Instalar o driver de conexão (apenas na 1ª vez)
Dê um duplo clique em:
```text
instalar_dependencias.bat
```
*(Requer Python 3 instalado na máquina).*

### 2. Configurar a senha local e a chave do Supabase
1. Faça uma cópia do arquivo `config.env.example` com o nome **`config.env`**.
2. Abra o `config.env` no Bloco de Notas e preencha:
   - `ID_LOJA` e `NOME_LOJA` (ex: `10603` e `WORLD CAFE`)
   - Se o Garçom Web usa MySQL direto (porta 3306), deixe `CONEXAO_MODO=MYSQL` e coloque o `MYSQL_USER` e `MYSQL_PASSWORD`.
   - Se o Garçom Web usa fonte de dados ODBC do Windows, mude para `CONEXAO_MODO=ODBC` e coloque o nome em `ODBC_DSN`.
   - Coloque a `SUPABASE_URL` e a `SUPABASE_SERVICE_ROLE_KEY` do seu projeto Supabase.

### 3. Testar e Iniciar a Transmissão Ao Vivo
1. Dê dois cliques em **`testar_conexao.bat`** para validar que ele enxergou as tabelas do Garçom Web e conectou ao Supabase.
2. Dê dois cliques em **`iniciar_agente.bat`**.
   - Ele ficará verificando alterações a cada **10 segundos**.
   - Só transmite para a nuvem quando o hash MD5 mudar (ou seja, quando entrar pedido novo, cancelamento ou fechamento de caixa).
   - Se o navegador estiver aberto no site do **MESA Intelligence**, os gráficos atualizarão sozinhos no mesmo segundo!

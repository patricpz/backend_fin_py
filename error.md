CONTEXTO DO ERRO:

Ao rodar `uvicorn app.main:app --reload`, a aplicação FastAPI falhou no startup 
com o seguinte erro durante o lifespan:

    OSError: Multiple exceptions: [Errno 10061] Connect call failed ('::1', 5432, 0, 0), 
    [Errno 10061] Connect call failed ('127.0.0.1', 5432)

CAUSA RAIZ:

A aplicação estava configurada para conectar a um Postgres local 
(127.0.0.1:5432 / ::1:5432), porém não havia nenhum servidor Postgres 
rodando nesse endereço/porta. O banco de dados real do projeto está 
hospedado no Neon (serviço de Postgres serverless na nuvem), então a 
DATABASE_URL local estava incorreta ou desatualizada.

CORREÇÃO APLICADA:

1. Substituir a DATABASE_URL local pela connection string fornecida pelo 
   Neon Console (aba "connection string"), convertendo o dialect para 
   usar o driver assíncrono asyncpg:

   Antes (Neon fornece):
   postgresql://neondb_owner:SENHA@ep-soft-water-ay5tw33y-pooler.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require

   Depois (ajustado para asyncpg + SQLAlchemy async):
   postgresql+asyncpg://neondb_owner:SENHA@ep-soft-water-ay5tw33y-pooler.c-5.us-east-2.aws.neon.tech/neondb

   Obs: os parâmetros `sslmode` e `channel_binding` foram removidos da 
   URL porque o driver asyncpg não os reconhece via query string.

2. Habilitar SSL explicitamente na criação do engine, já que o Neon exige 
   conexão criptografada:

   from sqlalchemy.ext.asyncio import create_async_engine

   engine = create_async_engine(
       DATABASE_URL,
       connect_args={"ssl": "require"},
   )

3. Armazenar a DATABASE_URL em variável de ambiente (.env), evitando 
   hardcode de credenciais no código-fonte.

RESULTADO ESPERADO:
Após a correção, `engine.begin()` no lifespan do FastAPI deve conseguir 
abrir conexão com o banco remoto no Neon sem erro de "Connect call failed", 
e a aplicação deve subir normalmente.
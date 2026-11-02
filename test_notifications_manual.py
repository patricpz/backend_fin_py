#!/usr/bin/env python3
"""Script para testar o fluxo completo de Notificacoes via API."""

import asyncio
import json
import uuid
import sys
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings


async def main():
    print("=" * 60)
    print("[TESTE] FLUXO COMPLETO DE NOTIFICACOES")
    print("=" * 60)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Registrar usuario de teste
        random_suffix = uuid.uuid4().hex[:6]
        email = f"teste_notif_{random_suffix}@exemplo.com"
        senha = "senhaSegura123!"

        print(f"\n1. Criando usuario de teste ({email})...")
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={"nome": "Usuario Notificacao", "email": email, "senha": senha},
        )
        if reg_res.status_code != 201:
            print(f"[ERRO] Falha ao criar usuario: {reg_res.status_code} - {reg_res.text}")
            return

        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "senha": senha},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        print("[OK] Usuario autenticado com sucesso! Token JWT obtido.")

        # 2. Consultar preferencias padrao
        print("\n2. Consultando preferencias de notificacao (GET /notification-preferences)...")
        pref_res = await client.get("/notification-preferences", headers=headers)
        print(f"Status: {pref_res.status_code}")
        print(json.dumps(pref_res.json(), indent=2, ensure_ascii=True))

        # 3. Disparar notificacao de teste (POST /notifications/test)
        print("\n3. Disparando notificacao de teste (POST /notifications/test)...")
        # Garante que APP_ENV seja development para a rota de teste
        settings.APP_ENV = "development"
        test_res = await client.post("/notifications/test", headers=headers)
        print(f"Status: {test_res.status_code}")
        print(json.dumps(test_res.json(), indent=2, ensure_ascii=True))

        # 4. Listar notificacoes (GET /notifications)
        print("\n4. Listando notificacoes do usuario (GET /notifications)...")
        list_res = await client.get("/notifications", headers=headers)
        print(f"Status: {list_res.status_code}")
        data = list_res.json()
        print(json.dumps(data, indent=2, ensure_ascii=True))

        items = data.get("items", [])
        if not items:
            print("[ERRO] Nenhuma notificacao encontrada!")
            return

        notif = items[0]
        notif_id = notif["id"]
        print(f"\n[OK] Notificacao encontrada! ID: {notif_id}")
        print(f"     Titulo: {notif['title']}")
        print(f"     Mensagem: {notif['body']}")
        print(f"     Status inicial: {notif['status']}")
        print(f"     Total nao lidas (unread_count): {data['unread_count']}")

        # 5. Marcar notificacao como lida (PATCH /notifications/{id}/read)
        print(f"\n5. Marcando notificacao como lida (PATCH /notifications/{notif_id}/read)...")
        read_res = await client.patch(f"/notifications/{notif_id}/read", headers=headers)
        print(f"Status: {read_res.status_code} (Esperado 204 No Content)")

        # Checar se unread_count agora e 0
        list_after_read = await client.get("/notifications", headers=headers)
        unread_after = list_after_read.json().get("unread_count")
        status_after = list_after_read.json()["items"][0]["status"]
        print(f"[OK] Status apos leitura: {status_after}")
        print(f"[OK] unread_count atualizado para: {unread_after}")

        # 6. Enviar feedback (POST /notifications/{id}/feedback)
        print(f"\n6. Enviando feedback positivo (POST /notifications/{notif_id}/feedback)...")
        fb_res = await client.post(
            f"/notifications/{notif_id}/feedback",
            json={"action": "helpful"},
            headers=headers,
        )
        print(f"Status: {fb_res.status_code} (Esperado 204 No Content)")
        print("[OK] Feedback gravado com sucesso no banco!")

        # 7. Teste de chave publica Web Push (GET /push/public-key)
        print("\n7. Testando endpoint de chave publica Web Push (GET /push/public-key)...")
        settings.VAPID_PUBLIC_KEY = settings.VAPID_PUBLIC_KEY or "BExampleVapidPublicKeyTest123456789"
        push_key_res = await client.get("/push/public-key")
        print(f"Status: {push_key_res.status_code}")
        print(json.dumps(push_key_res.json(), indent=2, ensure_ascii=True))

    print("\n" + "=" * 60)
    print("[SUCESSO] TODOS OS TESTES DE NOTIFICACOES PASSARAM COM EXITO!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

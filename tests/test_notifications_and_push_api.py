import uuid
from uuid import UUID
from decimal import Decimal
from unittest.mock import patch, MagicMock
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.services.notification_service import NotificationService
from app.alerts.scheduler import run_daily_checks


async def _create_user(client: AsyncClient, prefix: str = "user"):
    email = f"{prefix}-{uuid.uuid4()}@teste.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"nome": "Usuário Notif", "email": email, "senha": "password123"},
    )
    assert reg.status_code == 201, reg.text
    user_id = UUID(reg.json()["id"])

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "senha": "password123"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return user_id, headers


class TestNotificationsAPI:
    @pytest.mark.asyncio
    async def test_notifications_cursor_pagination_and_unread_count(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user_id, headers = await _create_user(client, "cursor-user")

        # Insere diretamente 5 notificações via NotificationService
        service = NotificationService(db_session)
        # Garante preferências com limite diário alto para teste
        await service.update_preferences(user_id, {"daily_limit": 20})
        for i in range(5):
            await service.processar_evento(
                user_id=user_id,
                event_type="tip" if i % 2 == 0 else "summary",
                data={"message": f"Mensagem teste {i}", "url": f"/teste/{i}"},
                dedupe_key=f"tip_summary_{user_id}_{i}",
            )
        await db_session.commit()

        # 1. Página 1 com limit=2
        res1 = await client.get("/notifications?limit=2", headers=headers)
        assert res1.status_code == 200
        p1 = res1.json()
        assert len(p1["items"]) == 2
        assert p1["unread_count"] == 5
        assert p1["next_cursor"] is not None

        # 2. Página 2 usando cursor da página 1
        cursor1 = p1["next_cursor"]
        res2 = await client.get(f"/notifications?limit=2&cursor={cursor1}", headers=headers)
        assert res2.status_code == 200
        p2 = res2.json()
        assert len(p2["items"]) == 2
        assert p2["unread_count"] == 5
        assert p2["next_cursor"] is not None

        # Garante que os itens da página 2 não repetem os da página 1
        ids_p1 = {item["id"] for item in p1["items"]}
        ids_p2 = {item["id"] for item in p2["items"]}
        assert ids_p1.isdisjoint(ids_p2)

        # 3. Página 3 usando cursor da página 2
        cursor2 = p2["next_cursor"]
        res3 = await client.get(f"/notifications?limit=2&cursor={cursor2}", headers=headers)
        assert res3.status_code == 200
        p3 = res3.json()
        assert len(p3["items"]) == 1
        assert p3["next_cursor"] is None
        assert p3["unread_count"] == 5

        # 4. Invariância do unread_count sob filtros
        res_filter = await client.get("/notifications?type=tip", headers=headers)
        assert res_filter.status_code == 200
        assert res_filter.json()["unread_count"] == 5  # total unread inalterado pelo filtro

        # 5. Cursor inválido retorna 400
        res_bad_cursor = await client.get("/notifications?cursor=nao_eh_base64_valido", headers=headers)
        assert res_bad_cursor.status_code == 400
        assert res_bad_cursor.json()["detail"] == "Cursor inválido"

        # 6. Limit acima de 50 retorna 422
        res_high_limit = await client.get("/notifications?limit=51", headers=headers)
        assert res_high_limit.status_code == 422

    @pytest.mark.asyncio
    async def test_read_and_read_all_idempotent(self, client: AsyncClient, db_session: AsyncSession):
        user_id, headers = await _create_user(client, "read-user")

        service = NotificationService(db_session)
        await service.update_preferences(user_id, {"daily_limit": 10})
        n1 = await service.processar_evento(user_id, "tip", {"message": "Dica 1"}, dedupe_key=f"d1_{user_id}")
        n2 = await service.processar_evento(user_id, "tip", {"message": "Dica 2"}, dedupe_key=f"d2_{user_id}")
        await db_session.commit()
        n1_id = str(n1.id)

        # 1. Marcar n1 como read via PATCH /notifications/{id}/read (retorna 204)
        r_read1 = await client.patch(f"/notifications/{n1_id}/read", headers=headers)
        assert r_read1.status_code == 204

        # Idempotência: marcar novamente retorna 204
        r_read1_dup = await client.patch(f"/notifications/{n1_id}/read", headers=headers)
        assert r_read1_dup.status_code == 204

        # unread_count deve ser 1
        list_res = await client.get("/notifications", headers=headers)
        assert list_res.json()["unread_count"] == 1

        # 2. POST /notifications/read-all retorna 204 e zera unread_count
        r_read_all = await client.post("/notifications/read-all", headers=headers)
        assert r_read_all.status_code == 204

        list_res2 = await client.get("/notifications", headers=headers)
        assert list_res2.json()["unread_count"] == 0

    @pytest.mark.asyncio
    async def test_feedback_actions(self, client: AsyncClient, db_session: AsyncSession):
        user_id, headers = await _create_user(client, "fb-user")

        service = NotificationService(db_session)
        n = await service.processar_evento(user_id, "tip", {"message": "Dica FB"}, dedupe_key=f"fb_{user_id}")
        await db_session.commit()
        n_id = str(n.id)

        # 1. Action inválida retorna 422
        r_inv = await client.post(f"/notifications/{n_id}/feedback", json={"action": "curtiu"}, headers=headers)
        assert r_inv.status_code == 422

        # 2. Action opened altera status para read
        r_open = await client.post(f"/notifications/{n_id}/feedback", json={"action": "opened"}, headers=headers)
        assert r_open.status_code == 204

        res_check = await client.get("/notifications", headers=headers)
        item = res_check.json()["items"][0]
        assert item["status"] == "read"

        # 3. Action dismissed altera status para dismissed
        r_dism = await client.post(f"/notifications/{n_id}/feedback", json={"action": "dismissed"}, headers=headers)
        assert r_dism.status_code == 204

        res_check2 = await client.get("/notifications", headers=headers)
        item2 = res_check2.json()["items"][0]
        assert item2["status"] == "dismissed"

    @pytest.mark.asyncio
    async def test_notification_preferences_get_and_put(self, client: AsyncClient):
        user_id, headers = await _create_user(client, "pref-user")

        # 1. GET cria preferências padrão e retorna 200 sem 404
        r_get = await client.get("/notification-preferences", headers=headers)
        assert r_get.status_code == 200
        p = r_get.json()
        assert p["channel_in_app"] is True
        assert p["channel_push"] is False
        assert p["sensitivity"] == "medium"
        assert p["daily_limit"] == 3
        assert "overspending" in p["enabled_types"]

        # 2. PUT substitui o objeto completo
        payload = {
            "enabled_types": ["overspending", "spending_spike"],
            "channel_in_app": True,
            "channel_push": True,
            "sensitivity": "high",
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "07:00",
            "timezone": "America/Sao_Paulo",
            "daily_limit": 5,
        }
        r_put = await client.put("/notification-preferences", json=payload, headers=headers)
        assert r_put.status_code == 200
        p_updated = r_put.json()
        assert p_updated["enabled_types"] == ["overspending", "spending_spike"]
        assert p_updated["sensitivity"] == "high"
        assert p_updated["timezone"] == "America/Sao_Paulo"
        assert p_updated["daily_limit"] == 5

        # 3. Validação: timezone inválido retorna 422
        bad_tz = dict(payload, timezone="Planeta/Marte")
        assert (await client.put("/notification-preferences", json=bad_tz, headers=headers)).status_code == 422

        # 4. Validação: quiet hours apenas um preenchido retorna 422
        bad_qh = dict(payload, quiet_hours_start="22:00", quiet_hours_end=None)
        assert (await client.put("/notification-preferences", json=bad_qh, headers=headers)).status_code == 422

        # 5. Validação: daily_limit fora de [0, 20] retorna 422
        bad_lim = dict(payload, daily_limit=25)
        assert (await client.put("/notification-preferences", json=bad_lim, headers=headers)).status_code == 422

    @pytest.mark.asyncio
    async def test_push_endpoints_and_webpush_mock(self, client: AsyncClient):
        user_id, headers = await _create_user(client, "push-user")

        # 1. GET /push/public-key sem chave retorna 503
        with patch.object(settings, "VAPID_PUBLIC_KEY", None):
            res_no_key = await client.get("/push/public-key")
            assert res_no_key.status_code == 503
            assert "não está configurado" in res_no_key.json()["detail"]

        # GET /push/public-key com chave retorna 200
        with patch.object(settings, "VAPID_PUBLIC_KEY", "BPublicKeyTest123"):
            res_key = await client.get("/push/public-key")
            assert res_key.status_code == 200
            assert res_key.json()["public_key"] == "BPublicKeyTest123"

        # 2. POST /push/subscriptions cria nova inscrição (201)
        sub_payload = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/fake-device-1",
            "p256dh": "BNc_test_p256dh",
            "auth": "k8J_test_auth",
            "user_agent": "Mozilla/5.0 TestBrowser",
        }
        res_sub1 = await client.post("/push/subscriptions", json=sub_payload, headers=headers)
        assert res_sub1.status_code == 201
        sub_id = res_sub1.json()["id"]

        # Upsert: mesmo endpoint atualiza e retorna 200
        res_sub_upsert = await client.post("/push/subscriptions", json=sub_payload, headers=headers)
        assert res_sub_upsert.status_code == 200
        assert res_sub_upsert.json()["id"] == sub_id

        # 3. Endpoint não-HTTPS retorna 422
        bad_sub = dict(sub_payload, endpoint="http://insecure.endpoint.com")
        assert (await client.post("/push/subscriptions", json=bad_sub, headers=headers)).status_code == 422

        # 4. DELETE /push/subscriptions/{id} remove (204) e 404 se não existir
        res_del = await client.delete(f"/push/subscriptions/{sub_id}", headers=headers)
        assert res_del.status_code == 204

        res_del_404 = await client.delete(f"/push/subscriptions/{sub_id}", headers=headers)
        assert res_del_404.status_code == 404

    @pytest.mark.asyncio
    async def test_webpush_dispatch_and_removal_on_410(self, client: AsyncClient, db_session: AsyncSession):
        user_id, headers = await _create_user(client, "webpush-dispatch")

        # Cadastra subscription
        sub_payload = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/expired-device-token",
            "p256dh": "BNc_fake_p256dh",
            "auth": "fake_auth",
        }
        await client.post("/push/subscriptions", json=sub_payload, headers=headers)

        # Habilita push nas preferências
        await client.put(
            "/notification-preferences",
            json={
                "enabled_types": ["tip"],
                "channel_in_app": True,
                "channel_push": True,
                "sensitivity": "high",
                "timezone": "America/Fortaleza",
                "daily_limit": 5,
            },
            headers=headers,
        )

        from pywebpush import WebPushException

        mock_response = MagicMock()
        mock_response.status_code = 410

        with patch("pywebpush.webpush", side_effect=WebPushException("Subscription expired", response=mock_response)) as mock_wp:
            with patch.object(settings, "VAPID_PRIVATE_KEY", "mock_private_key"):
                service = NotificationService(db_session)
                await service.processar_evento(
                    user_id=user_id,
                    event_type="tip",
                    data={"message": "Dica push"},
                    dedupe_key=f"push_test_{user_id}",
                )
                await db_session.commit()

                assert mock_wp.called

        # Confirma que a subscription expirada (410) foi removida do banco
        from app.repositories.notification_repository import NotificationRepository
        repo = NotificationRepository(db_session)
        subs = await repo.get_user_push_subscriptions(user_id)
        assert len(subs) == 0

    @pytest.mark.asyncio
    async def test_job_deduplication_two_runs_same_day(self, client: AsyncClient, db_session: AsyncSession):
        user_id, headers = await _create_user(client, "dedupe-user")

        service = NotificationService(db_session)
        # Execução 1
        n1 = await service.processar_evento(
            user_id=user_id,
            event_type="tip",
            data={"message": "Dica diária"},
            dedupe_key=f"daily_tip_{user_id}_2026-10-31",
        )
        assert n1 is not None

        # Execução 2 no mesmo dia com a mesma dedupe_key deve ser ignorada
        n2 = await service.processar_evento(
            user_id=user_id,
            event_type="tip",
            data={"message": "Dica diária"},
            dedupe_key=f"daily_tip_{user_id}_2026-10-31",
        )
        assert n2 is None
        await db_session.commit()

        res_list = await client.get("/notifications", headers=headers)
        assert res_list.status_code == 200
        # Apenas 1 notificação criada
        assert len(res_list.json()["items"]) == 1

    @pytest.mark.asyncio
    async def test_isolation_between_users(self, client: AsyncClient, db_session: AsyncSession):
        user_a, headers_a = await _create_user(client, "iso-a")
        user_b, headers_b = await _create_user(client, "iso-b")

        service = NotificationService(db_session)
        notif_a = await service.processar_evento(user_a, "tip", {"message": "Segredo A"}, dedupe_key=f"a_{user_a}")
        await db_session.commit()
        notif_a_id = str(notif_a.id)

        # Usuário B tenta ler notificação de A -> 404
        res_read = await client.patch(f"/notifications/{notif_a_id}/read", headers=headers_b)
        assert res_read.status_code == 404

        # Usuário B tenta dar feedback em notificação de A -> 404
        res_fb = await client.post(f"/notifications/{notif_a_id}/feedback", json={"action": "opened"}, headers=headers_b)
        assert res_fb.status_code == 404

    @pytest.mark.asyncio
    async def test_notifications_test_endpoint_env_restriction(self, client: AsyncClient):
        user_id, headers = await _create_user(client, "test-route-user")

        # Em development, retorna 200
        with patch.object(settings, "APP_ENV", "development"):
            res_dev = await client.post("/notifications/test", headers=headers)
            assert res_dev.status_code == 200
            assert "Notificação de teste" in res_dev.json()["message"]

        # Em production, retorna 404 (nunca 403)
        with patch.object(settings, "APP_ENV", "production"):
            res_prod = await client.post("/notifications/test", headers=headers)
            assert res_prod.status_code == 404

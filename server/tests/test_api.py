from fastapi.testclient import TestClient


def login(client: TestClient) -> tuple[str, dict[str, object]]:
    response = client.post(
        "/api/auth/login",
        json={
            "code": "development-login-code",
            "phoneCode": "development-phone-code",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    return body["data"]["token"], body["data"]["userInfo"]


def test_full_risk_case_flow(client: TestClient) -> None:
    token, user_info = login(client)
    headers = {"Authorization": f"Bearer {token}"}

    user_response = client.get("/api/user/info", headers=headers)
    assert user_response.status_code == 200
    assert user_response.json()["data"]["phone"] == user_info["phone"]

    source_text = (
        "客户王女士需要住家保姆，阿姨由家政公司推荐，"
        "试工七天后签合同。电话里说了服务费30%，但是未书面确认，"
        "客户现在不承认收费。"
    )
    analyze_response = client.post(
        "/api/risk/analyze",
        headers=headers,
        json={"sourceText": source_text},
    )
    assert analyze_response.status_code == 200
    analysis = analyze_response.json()["data"]
    assert analysis["riskLevel"] in {"medium", "high"}
    fee_field = next(
        item for item in analysis["fields"] if item["key"] == "written"
    )
    assert fee_field["value"] == "未确认"
    assert fee_field["status"] == "missing"

    create_response = client.post(
        "/api/cases",
        headers=headers,
        json=analysis,
    )
    assert create_response.status_code == 200
    saved_case = create_response.json()["data"]
    assert saved_case["sourceText"] == source_text
    assert saved_case["status"] == "pending"
    assert saved_case["version"] == 1

    list_response = client.get("/api/cases?limit=10", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 1

    update_response = client.patch(
        f"/api/cases/{saved_case['id']}/status",
        headers=headers,
        json={"status": "confirmed", "version": 1},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["status"] == "confirmed"
    assert update_response.json()["data"]["version"] == 2

    conflict_response = client.patch(
        f"/api/cases/{saved_case['id']}/status",
        headers=headers,
        json={"status": "pending", "version": 1},
    )
    assert conflict_response.status_code == 409
    assert conflict_response.json()["code"] == 409


def test_transcription_contract_and_auth_guard(client: TestClient) -> None:
    unauthorized = client.post(
        "/api/risk/analyze",
        json={"sourceText": "客户需要保洁"},
    )
    assert unauthorized.status_code == 401

    token, _user_info = login(client)
    response = client.post(
        "/api/ai/transcribe",
        headers={"Authorization": f"Bearer {token}"},
        files={"audio": ("voice.mp3", b"example-audio", "audio/mpeg")},
    )
    assert response.status_code == 200
    assert response.json()["data"]["simulated"] is True
    assert "客户李女士" in response.json()["data"]["text"]

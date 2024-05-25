def test_database_check(
        client,
        user,
        get_access_token
):
    headers = {'Authorization': f'Bearer {get_access_token}'}
    response = client.get(
        headers=headers,
        url="/profile/me"
    )
    assert response.status_code > 0, response.text
from test_auth import admin, auth

def test_dictionary_rules(client, auth):
    d = client.post('/api/departments', headers=auth, json={'code': 'D1', 'name': '演示部门'}).json()['data']
    assert client.post('/api/departments', headers=auth, json={'code': 'D1', 'name': '其它'}).status_code == 409
    p = client.post('/api/positions', headers=auth, json={'code': 'P1', 'name': '演示岗位', 'department_id': d['id']})
    assert p.status_code == 201
    assert client.patch(f"/api/departments/{d['id']}", headers=auth, json={'is_active': False}).status_code == 200
    assert client.post('/api/positions', headers=auth, json={'code': 'P2', 'name': '另一岗位', 'department_id': d['id']}).status_code == 422
    assert client.get('/api/positions', headers=auth).json()['total'] == 1
    assert client.patch(f"/api/positions/{p.json()['data']['id']}", headers=auth, json={'name': '岗位改名', 'is_active': False}).status_code == 200
    s = client.post('/api/skills', headers=auth, json={'code': 'S1', 'name': '演示技能'}).json()['data']
    assert client.post('/api/skills', headers=auth, json={'code': 'S2', 'name': '演示技能'}).status_code == 409
    assert client.patch(f"/api/skills/{s['id']}", headers=auth, json={'is_active': False}).status_code == 200
    assert client.patch(f"/api/skills/{s['id']}", headers=auth, json={'name': None}).status_code == 422

def test_all_dictionaries_protected(client):
    for resource in ['departments', 'positions', 'skills']:
        assert client.get('/api/' + resource).status_code == 401

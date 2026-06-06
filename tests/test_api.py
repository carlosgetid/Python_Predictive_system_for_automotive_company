import unittest
import json
import jwt
import datetime
from backend.app import create_app
from backend.api.routes import SECRET_KEY

class AuthIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_login_invalid_credentials(self):
        # 1. Intentar hacer login con credenciales inválidas (debe retornar 401)
        response = self.client.post('/login', json={
            "username": "usuario_falso",
            "password": "wrong_password"
        })
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn("error", data)

    def test_login_valid_credentials(self):
        # 2. Intentar hacer login con credenciales sembradas (ej. lfernandez / teo123)
        response = self.client.post('/login', json={
            "username": "lfernandez",
            "password": "teo123"
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn("token", data)
        self.assertIn("user", data)
        self.assertEqual(data["user"]["username"], "lfernandez")
        self.assertEqual(data["user"]["rol"], "Analista Logística")

    def test_protected_endpoint_without_token(self):
        # 3. Acceso sin token a endpoint protegido (debe retornar 401)
        response = self.client.post('/api/v1/trigger_ingestion')
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data["error"], "Token faltante o inválido")

    def test_protected_endpoint_invalid_token(self):
        # 4. Acceso con token inválido (debe retornar 401)
        headers = {"Authorization": "Bearer token_invalido_de_prueba"}
        response = self.client.post('/api/v1/trigger_ingestion', headers=headers)
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data.decode('utf-8'))
        self.assertTrue(data["error"].startswith("Token inválido:"))

    def test_protected_endpoint_unauthorized_role(self):
        # 5. Acceso con token válido pero rol no autorizado (ej. Vendedora para /predict)
        # Generar token manual para un usuario con rol 'Vendedora'
        token = jwt.encode({
            'id': 999,
            'username': 'test_vendedora',
            'rol': 'Vendedora',
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        }, SECRET_KEY, algorithm="HS256")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.post('/api/v1/trigger_ingestion', headers=headers)
        
        # Debe retornar 403 Forbidden
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data["error"], "No tienes permisos para realizar esta acción")

    def test_protected_endpoint_authorized_role(self):
        # 6. Acceso con token válido y rol autorizado (ej. Logistica para /predict)
        # Generar token manual para un usuario con rol 'Logistica'
        token = jwt.encode({
            'id': 998,
            'username': 'test_logistica',
            'rol': 'Logistica',
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        }, SECRET_KEY, algorithm="HS256")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.post('/predict', json={
            "id_producto": "PROD-001",
            "fecha_str": "2026-06-15"
        }, headers=headers)
        
        # Como es una petición con rol válido, debe pasar el decorator require_role.
        # Puede retornar 404 si el producto no existe o 200 si existiera, pero NO debe retornar 401 ni 403.
        self.assertIn(response.status_code, [200, 404])

if __name__ == '__main__':
    unittest.main()

"""
Unit tests for Azure Functions
"""

import unittest
import json
from api.function_app import health_check, attestation
import azure.functions as func


class TestFunctionApp(unittest.TestCase):
    
    def test_health_check(self):
        """Test health check endpoint"""
        req = func.HttpRequest(
            method='GET',
            body=None,
            url='/api/health',
            params={}
        )
        
        response = health_check(req)
        self.assertEqual(response.status_code, 200)
        
        body = json.loads(response.get_body())
        self.assertEqual(body['status'], 'healthy')
    
    def test_attestation_get(self):
        """Test GET attestation endpoint"""
        req = func.HttpRequest(
            method='GET',
            body=None,
            url='/api/attestation',
            params={}
        )
        
        response = attestation(req)
        self.assertEqual(response.status_code, 200)
    
    def test_attestation_post(self):
        """Test POST attestation endpoint"""
        test_data = {
            "name": "John Doe",
            "date": "2026-01-08",
            "reason": "Sick leave"
        }
        
        req = func.HttpRequest(
            method='POST',
            body=json.dumps(test_data).encode('utf-8'),
            url='/api/attestation',
            params={}
        )
        
        response = attestation(req)
        self.assertEqual(response.status_code, 201)


if __name__ == '__main__':
    unittest.main()

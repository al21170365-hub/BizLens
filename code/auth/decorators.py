from functools import wraps
from flask import request, jsonify, current_app, g
import jwt
from datetime import datetime
from auth.jwt_handler import JWTHandler

def token_required(f):
    """Decorador para proteger endpoints"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Verificar token en header Authorization
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # Formato esperado: "Bearer <token>"
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({
                    'success': False,
                    'message': 'Formato de token inválido. Use: Bearer <token>'
                }), 401

        # También verificar en query parameters (para compatibilidad)
        if not token and 'token' in request.args:
            token = request.args.get('token')
        
        if not token:
            return jsonify({
                'success': False,
                'message': 'Token requerido'
            }), 401

        # Decodificar y validar token
        payload = JWTHandler.decode_token(token)
        if 'error' in payload:
            return jsonify({
                'success': False,
                'message': payload['error']
            }), 401

        # Agregar información del usuario al contexto
        g.current_user = payload
        
        return f(*args, **kwargs)
    return decorated

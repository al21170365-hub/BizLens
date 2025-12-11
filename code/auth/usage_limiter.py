# auth/usage_limiter.py
import sqlite3
from datetime import datetime, date
import os

class UsageLimiter:
    def __init__(self, db_path='./auth/usage.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Inicializa la base de datos de uso"""
        # Crear directorio auth si no existe
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla para seguimiento de uso diario
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_usage (
                user_id TEXT NOT NULL,
                usage_date DATE NOT NULL,
                count INTEGER DEFAULT 0,
                last_used TIMESTAMP,
                PRIMARY KEY (user_id, usage_date)
            )
        ''')
        
        # Tabla para usuarios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Índices para mejor performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_usage_user ON daily_usage(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_usage_date ON daily_usage(usage_date)')
        
        conn.commit()
        conn.close()
    
    def check_and_increment_usage(self, user_id, max_uses=100):
        """
        Verifica si el usuario puede realizar una operación
        e incrementa su contador de uso
        """
        today = date.today().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Obtener o crear registro de uso del día
            cursor.execute('''
                INSERT OR IGNORE INTO daily_usage (user_id, usage_date, count)
                VALUES (?, ?, 0)
            ''', (user_id, today))
            
            # Obtener conteo actual
            cursor.execute('''
                SELECT count FROM daily_usage 
                WHERE user_id = ? AND usage_date = ?
            ''', (user_id, today))
            
            result = cursor.fetchone()
            current_count = result[0] if result else 0
            
            # Verificar límite
            if current_count >= max_uses:
                conn.close()
                return False, f"Límite diario alcanzado. Has usado {current_count} de {max_uses} solicitudes permitidas."
            
            # Incrementar contador
            cursor.execute('''
                UPDATE daily_usage 
                SET count = count + 1, last_used = CURRENT_TIMESTAMP
                WHERE user_id = ? AND usage_date = ?
            ''', (user_id, today))
            
            conn.commit()
            remaining = max_uses - (current_count + 1)
            
            conn.close()
            return True, f"Solicitud completada. Usos restantes hoy: {remaining}/{max_uses}"
            
        except Exception as e:
            conn.close()
            return False, f"Error al verificar uso: {str(e)}"
    
    def get_today_usage(self, user_id):
        """Obtiene el uso actual del día"""
        today = date.today().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT count FROM daily_usage 
            WHERE user_id = ? AND usage_date = ?
        ''', (user_id, today))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else 0
    
    def create_user(self, user_id, username, role='user'):
        """Crea un nuevo usuario"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO users (user_id, username, role)
                VALUES (?, ?, ?)
            ''', (user_id, username, role))
            
            conn.commit()
            conn.close()
            return True, "Usuario creado exitosamente"
            
        except sqlite3.IntegrityError:
            conn.close()
            return False, "El usuario ya existe"
        except Exception as e:
            conn.close()
            return False, f"Error al crear usuario: {str(e)}"
    
    def get_user(self, username):
        """Obtiene usuario por nombre"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id, username, role FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'user_id': result[0],
                'username': result[1],
                'role': result[2]
            }
        return None
    
    def reset_old_usage(self):
        """Elimina registros de uso antiguos (más de 30 días)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM daily_usage WHERE usage_date < date("now", "-30 days")')
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted

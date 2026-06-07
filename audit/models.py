from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    class Action(models.TextChoices):
        REGISTER = 'REGISTER', 'Registro'
        LOGIN = 'LOGIN', 'Inicio de sesión'
        LOGOUT = 'LOGOUT', 'Cierre de sesión'
        CREATE = 'CREATE', 'Creación'
        READ = 'READ', 'Consulta'
        UPDATE = 'UPDATE', 'Actualización'
        DELETE = 'DELETE', 'Eliminación'
        DEACTIVATE = 'DEACTIVATE', 'Desactivación'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=20, choices=Action.choices, db_index=True)
    resource_type = models.CharField(max_length=50, blank=True)
    resource_id = models.CharField(max_length=50, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        verbose_name = 'Log de Auditoría'
        verbose_name_plural = 'Logs de Auditoría'

    def __str__(self):
        user_str = self.user.email if self.user else 'anónimo'
        return f'[{self.timestamp:%Y-%m-%d %H:%M}] {self.action} — {user_str}'

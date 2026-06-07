def get_client_ip(request) -> str | None:
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_action(
    user=None,
    action: str = '',
    request=None,
    resource_type: str = '',
    resource_id: str = '',
    metadata: dict | None = None,
) -> None:
    """Record an audit event. Silently swallows exceptions so logging never
    breaks the main request flow."""
    from .models import AuditLog
    try:
        ip_address = get_client_ip(request) if request else None
        user_agent = ''
        if request:
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:512]

        AuditLog.objects.create(
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else '',
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except Exception:
        pass

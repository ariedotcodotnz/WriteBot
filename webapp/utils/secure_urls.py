"""
Secure URL signing utilities using itsdangerous.

Implements Instagram-grade security for file download URLs:
- Time-limited signed URLs (default 1 hour expiry)
- User-bound signatures (URLs tied to specific user)
- Resource-bound signatures (URLs tied to specific file/resource)
- Tamper-proof using HMAC-SHA512
- Optional IP binding for extra security
"""

import hashlib
import hmac
import os
import time
from functools import wraps
from typing import Optional, Dict, Any, Tuple

from flask import current_app, request, abort, jsonify
from flask_login import current_user
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature


# Default expiration time in seconds (1 hour)
DEFAULT_EXPIRY = 3600

# Salt for different token types (prevents token reuse across different purposes)
SALTS = {
    'file_download': 'secure-file-download-v1',
    'batch_result': 'secure-batch-result-v1',
    'job_download': 'secure-job-download-v1',
    'style_preview': 'secure-style-preview-v1',
    'batch_file': 'secure-batch-file-v1',
}


def get_serializer(salt: str = 'file_download') -> URLSafeTimedSerializer:
    """
    Get a URLSafeTimedSerializer configured with the app's secret key.

    Args:
        salt: Purpose-specific salt to prevent token reuse across different endpoints.

    Returns:
        Configured URLSafeTimedSerializer instance.
    """
    secret_key = current_app.config.get('SECRET_KEY')
    if not secret_key:
        raise RuntimeError('SECRET_KEY must be configured for secure URLs')

    return URLSafeTimedSerializer(
        secret_key,
        salt=SALTS.get(salt, salt),
        signer_kwargs={
            'key_derivation': 'hmac',
            'digest_method': hashlib.sha512
        }
    )


def generate_signed_url(
    resource_type: str,
    resource_id: str,
    user_id: Optional[int] = None,
    expiry: int = DEFAULT_EXPIRY,
    extra_data: Optional[Dict[str, Any]] = None,
    bind_ip: bool = False
) -> str:
    """
    Generate a signed token for secure resource access.

    Args:
        resource_type: Type of resource (e.g., 'batch_result', 'job_download').
        resource_id: Unique identifier for the resource.
        user_id: User ID to bind the token to (uses current_user if not provided).
        expiry: Token expiration time in seconds.
        extra_data: Additional data to include in the token.
        bind_ip: Whether to bind the token to the requester's IP address.

    Returns:
        Signed token string.
    """
    if user_id is None and current_user and current_user.is_authenticated:
        user_id = current_user.id

    payload = {
        'r': resource_id,  # resource
        't': resource_type,  # type
        'u': user_id,  # user
        'e': int(time.time()) + expiry,  # expiry timestamp
        'n': hashlib.sha256(os.urandom(16)).hexdigest()[:16],  # nonce
    }

    if bind_ip:
        # Include hashed IP for binding (privacy-preserving)
        client_ip = request.remote_addr or ''
        payload['ip'] = hashlib.sha256(client_ip.encode()).hexdigest()[:16]

    if extra_data:
        payload['x'] = extra_data

    serializer = get_serializer(resource_type)
    return serializer.dumps(payload)


def verify_signed_url(
    token: str,
    resource_type: str,
    expected_resource_id: Optional[str] = None,
    max_age: Optional[int] = None,
    require_user: bool = True,
    check_ip: bool = False
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Verify a signed URL token.

    Args:
        token: The signed token to verify.
        resource_type: Expected resource type.
        expected_resource_id: Expected resource ID (if known).
        max_age: Maximum age in seconds (uses embedded expiry if None).
        require_user: Whether to require user authentication match.
        check_ip: Whether to verify IP binding.

    Returns:
        Tuple of (is_valid, payload, error_message).
    """
    if not token:
        return False, None, 'Missing security token'

    serializer = get_serializer(resource_type)

    try:
        # Use a generous max_age for initial decode, we'll check expiry manually
        payload = serializer.loads(token, max_age=max_age or 86400)
    except SignatureExpired:
        return False, None, 'Security token has expired'
    except BadSignature:
        return False, None, 'Invalid security token'
    except Exception as e:
        current_app.logger.warning(f'Token verification failed: {e}')
        return False, None, 'Token verification failed'

    # Check embedded expiry
    if payload.get('e', 0) < time.time():
        return False, None, 'Security token has expired'

    # Check resource type
    if payload.get('t') != resource_type:
        return False, None, 'Invalid token type'

    # Check resource ID if provided
    if expected_resource_id and payload.get('r') != expected_resource_id:
        return False, None, 'Resource mismatch'

    # Check user binding
    if require_user:
        if not current_user or not current_user.is_authenticated:
            return False, None, 'Authentication required'
        if payload.get('u') != current_user.id:
            return False, None, 'Token not valid for this user'

    # Check IP binding
    if check_ip and 'ip' in payload:
        client_ip = request.remote_addr or ''
        client_ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()[:16]
        if payload['ip'] != client_ip_hash:
            return False, None, 'Token not valid from this location'

    return True, payload, None


def require_signed_url(
    resource_type: str,
    resource_param: str = 'token',
    id_param: Optional[str] = None,
    require_user: bool = True,
    check_ip: bool = False
):
    """
    Decorator to require a valid signed URL token for an endpoint.

    Args:
        resource_type: Type of resource being protected.
        resource_param: Query parameter name for the token.
        id_param: URL parameter name for resource ID verification.
        require_user: Whether to require user authentication match.
        check_ip: Whether to verify IP binding.

    Returns:
        Decorator function.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = request.args.get(resource_param)

            if not token:
                return jsonify({'error': 'Missing security token'}), 403

            # Get expected resource ID from URL parameters if specified
            expected_id = None
            if id_param:
                expected_id = str(kwargs.get(id_param, ''))

            is_valid, payload, error = verify_signed_url(
                token=token,
                resource_type=resource_type,
                expected_resource_id=expected_id,
                require_user=require_user,
                check_ip=check_ip
            )

            if not is_valid:
                current_app.logger.warning(
                    f'Signed URL verification failed: {error} '
                    f'(type={resource_type}, ip={request.remote_addr})'
                )
                return jsonify({'error': error}), 403

            # Store payload in request context for use in the endpoint
            request.signed_url_payload = payload

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_download_url(
    endpoint: str,
    resource_type: str,
    resource_id: str,
    expiry: int = DEFAULT_EXPIRY,
    **url_params
) -> str:
    """
    Generate a complete signed download URL.

    Args:
        endpoint: Flask endpoint name.
        resource_type: Type of resource for signing.
        resource_id: Resource identifier.
        expiry: Token expiration in seconds.
        **url_params: Additional URL parameters.

    Returns:
        Complete signed URL.
    """
    from flask import url_for

    token = generate_signed_url(
        resource_type=resource_type,
        resource_id=resource_id,
        expiry=expiry
    )

    return url_for(endpoint, token=token, **url_params, _external=False)


# Convenience functions for specific resource types

def sign_batch_result(job_id: str, expiry: int = DEFAULT_EXPIRY) -> str:
    """Generate signed token for batch result download."""
    return generate_signed_url('batch_result', str(job_id), expiry=expiry)


def sign_batch_file(job_id: str, filename: str, expiry: int = DEFAULT_EXPIRY) -> str:
    """Generate signed token for individual batch file access."""
    resource_id = f"{job_id}:{filename}"
    return generate_signed_url('batch_file', resource_id, expiry=expiry)


def sign_job_download(job_id: int, expiry: int = DEFAULT_EXPIRY) -> str:
    """Generate signed token for job download."""
    return generate_signed_url('job_download', str(job_id), expiry=expiry)


def sign_style_preview(style_id: str, expiry: int = 7200) -> str:
    """Generate signed token for style preview (longer expiry for browsing)."""
    return generate_signed_url('style_preview', style_id, expiry=expiry)

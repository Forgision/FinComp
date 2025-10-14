from slowapi import Limiter
from slowapi.util import get_remote_address

# Use client IP as rate limit key
limiter = Limiter(key_func=get_remote_address)
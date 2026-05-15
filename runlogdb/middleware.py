from django.contrib.auth import get_user_model
from django.contrib.auth.middleware import get_user


class DevBypassMiddleware:
    """Auto-authenticate every request as a dev user when AUTH_ENABLED=False.

    Inserted into MIDDLEWARE only when settings.AUTH_ENABLED is False, so
    @login_required decorators pass without a real SSO flow.
    """

    _DEV_USERNAME = "dev"

    def __init__(self, get_response):
        self._get_response = get_response
        self._dev_user = None

    def _get_or_create_dev_user(self):
        if self._dev_user is None:
            User = get_user_model()
            user, _ = User.objects.get_or_create(
                username=self._DEV_USERNAME,
                defaults={"is_staff": True, "is_superuser": True},
            )
            self._dev_user = user
        return self._dev_user

    def __call__(self, request):
        if not request.user.is_authenticated:
            request.user = self._get_or_create_dev_user()
        return self._get_response(request)

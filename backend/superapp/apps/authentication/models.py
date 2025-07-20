import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from guardian.mixins import GuardianUserMixin


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        if not email:
            raise ValueError("Users must have an email address")

        user = self.model(
            email=self.normalize_email(email),
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None):
        """
        Creates and saves a superuser with the given email, date of
        birth and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

    def get_by_natural_key(self, *args):
        """
        Get a user by their natural key (email, phone number, or anonymous ID).
        """
        if len(args) == 1:
            key = args[0]
        else:
            # Handle case where natural key is unpacked as individual characters
            key = ''.join(args)
            
        return self.get(
            Q(email=key) |
            Q(phone_number=key) |
            Q(anonymous_id=key)
        )


class User(AbstractUser, GuardianUserMixin):
    username = None
    password = models.CharField(_("password"), max_length=128, blank=True, null=False)

    anonymous_id = models.CharField(_("Anonymous ID"), max_length=512, blank=True, null=True, unique=True)
    anonymous_id_verified = models.DateTimeField(_("Anonymous ID verified"), blank=True, null=True)

    email = models.EmailField(_("email address"), blank=True, null=True, unique=True)
    email_verified = models.DateTimeField(_("Email verified"), blank=True, null=True)
    
    phone_number = models.CharField(_("Phone number"), max_length=255, blank=True, null=True, unique=True)
    phone_number_verified = models.DateTimeField(_("Phone number verified"), blank=True, null=True)
    checkout_phone_number = models.CharField(_("Checkout phone number"), max_length=255, blank=True, null=True)
    photo_url = models.CharField(max_length=255, blank=True, null=True)

    address = models.CharField(max_length=1024, blank=True, null=True)

    is_staff = models.BooleanField(
        _("staff status"),
        default=True,
        help_text=_("Designates whether the user can log into this admin site."),
    )

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    modified_at = models.DateTimeField(_("modified at"), auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['anonymous_id'],
                name='unique_anonymous_id',
                condition=~Q(anonymous_id=None)
            ),
            models.UniqueConstraint(
                fields=['email'],
                name='unique_email',
                condition=~Q(email=None)
            ),
            models.UniqueConstraint(
                fields=['phone_number'],
                name='unique_phone_number',
                condition=~Q(phone_number=None)
            ),
        ]
        verbose_name = _("user")
        verbose_name_plural = _("users")
        permissions = (
            ("can_view_dashboard", "Can view dashboard"),
            ("can_view_custom_page", "Can view custom page"),
            ("is_normal_user", "Is a normal user?"),
        )

    def __str__(self):
        if self.email or self.phone_number:
            if self.full_name:
                return f"{self.full_name} {self.email or self.phone_number}"
            return f"{self.email or self.phone_number}"

        return f"Anonymous {self.pk}"

    def save(self, *args, **kwargs):
        if not self.password:
            self.password = uuid.uuid4().hex

        super().save(*args, **kwargs)

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.last_name} {self.first_name}"

        return None

    @property
    def is_normal_user(self):
        return not self.is_superuser and self.has_perm("authentication.is_normal_user")

    @property
    def is_anonymous(self):
        return not self.email_verified and not self.phone_number_verified

    def natural_key(self):
        """Return a natural key for serialization."""
        if self.email:
            return (self.email,)
        elif self.phone_number:
            return (self.phone_number,)
        else:
            return (self.anonymous_id or f"anonymous-{self.pk}",)



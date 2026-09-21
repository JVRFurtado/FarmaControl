from django.contrib import admin
from .models import Users
from django.contrib.auth import admin as admin_auth_django
from .forms import UserChargeForm
from .forms import UserCreationForm

@admin.register(Users)
class UsersAdmin(admin_auth_django.UserAdmin):
    form = UserChargeForm
    add_form = UserCreationForm
    model = Users
    fieldsets = admin_auth_django.UserAdmin.fieldsets + (
        ('Cargo', {'fields': ('cargo',)}), 
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'cargo'),
        }),
    )


# Register your models here.

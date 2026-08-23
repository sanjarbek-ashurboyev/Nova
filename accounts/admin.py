from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from accounts.models import District, Region, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ['phone']
    list_display = ['phone', 'first_name', 'last_name', 'role', 'balance', 'is_staff']
    list_filter = ['role', 'is_staff', 'is_superuser', 'is_active']
    search_fields = ['phone', 'first_name', 'last_name', 'email']
    list_select_related = ['district']
    autocomplete_fields = ['district', 'referrer']
    readonly_fields = ['last_login', 'date_joined', 'api_key']

    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ("Shaxsiy ma'lumotlar", {
            'fields': ('first_name', 'last_name', 'email', 'district', 'description'),
        }),
        ('Rol va hisob', {'fields': ('role', 'balance', 'referrer', 'telegram_id', 'api_key')}),
        ('Ruxsatlar', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Muhim sanalar', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'usable_password', 'password1', 'password2',
                       'first_name', 'last_name', 'role', 'district'),
        }),
    )


class DistrictInline(admin.TabularInline):
    model = District
    extra = 1


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['title', 'district_count']
    search_fields = ['title']
    inlines = [DistrictInline]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('districts')

    @admin.display(description='Tumanlar soni')
    def district_count(self, obj):
        return len(obj.districts.all())


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ['title', 'region']
    list_filter = ['region']
    search_fields = ['title', 'region__title']
    list_select_related = ['region']

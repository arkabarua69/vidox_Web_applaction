# downloader/admin.py
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path
from django.utils.html import format_html
from django.utils import timezone

import csv
from .models import ContactMessage


# --- Simple CSV export action ---
def export_as_csv(admin_model, request, queryset):
    """
    Export selected rows as CSV. Attached to ContactMessageAdmin actions.
    """
    meta = admin_model.model._meta
    field_names = ["id", "name", "email", "subject", "message", "created_at"]

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename={meta.label_lower}_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )
    writer = csv.writer(response)
    writer.writerow(field_names)
    for obj in queryset:
        writer.writerow([getattr(obj, f) for f in field_names])
    return response


export_as_csv.short_description = "Export selected to CSV"


# --- ContactMessageAdmin ---
@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "short_name",
        "email",
        "short_subject",
        "preview_message",
        "created_at",
        "action_reply",
    )
    list_display_links = ("id", "short_name")
    list_filter = ("created_at",)
    search_fields = ("name", "email", "subject", "message")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    actions = [export_as_csv, "mark_as_handled"]

    readonly_fields = ("created_at",)

    def short_name(self, obj):
        return obj.name if len(obj.name) <= 30 else obj.name[:27] + "..."

    short_name.short_description = "Name"

    def short_subject(self, obj):
        return obj.subject if obj.subject else "-"

    short_subject.short_description = "Subject"

    def preview_message(self, obj):
        txt = obj.message or ""
        if len(txt) > 80:
            return txt[:77] + "..."
        return txt

    preview_message.short_description = "Message"

    def mark_as_handled(self, request, queryset):
        """
        Example action placeholder. If you add an 'is_handled' boolean to model you can implement this.
        For now we'll just show a message.
        """
        self.message_user(
            request, f"{queryset.count()} messages marked as handled (placeholder)."
        )

    mark_as_handled.short_description = "Mark selected as handled (placeholder)"

    def action_reply(self, obj):
        """
        Quick reply link: opens the contact page prefilled (example).
        You can modify to point to a mailto: or a custom reply interface.
        """
        mailto = f"mailto:{obj.email}?subject=Re:%20{obj.subject or 'Your%20message'}"
        return format_html(
            '<a class="button" href="{}" style="padding:.25rem .5rem; border-radius:.4rem; background:#0d6efd; color:white; text-decoration:none;">Reply</a>',
            mailto,
        )

    action_reply.short_description = "Quick Reply"
    action_reply.allow_tags = True


# --- Custom AdminSite (optional but more 'professional') ---
from django.contrib.admin import AdminSite


class VidoxAdminSite(AdminSite):
    site_header = "VIDOX Admin"
    site_title = "VIDOX Management"
    index_title = "VIDOX Administration"

    # add a tiny overview dashboard view to admin
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("overview/", self.admin_view(self.overview_view), name="overview"),
        ]
        return custom_urls + urls

    def overview_view(self, request):
        # minimal stats
        total_msgs = ContactMessage.objects.count()
        last_24h = ContactMessage.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=1)
        ).count()
        recent = ContactMessage.objects.order_by("-created_at")[:6]

        html = [
            "<div style='padding:24px;'>",
            "<h1>VIDOX Admin Overview</h1>",
            f"<p><strong>Total messages:</strong> {total_msgs}</p>",
            f"<p><strong>Last 24h:</strong> {last_24h}</p>",
            "<h3>Latest messages</h3>",
            "<ul>",
        ]
        for m in recent:
            html.append(
                f"<li><strong>{m.name}</strong> — {m.email} — {m.created_at.strftime('%Y-%m-%d %H:%M')}</li>"
            )
        html.append("</ul>")
        html.append("</div>")
        return HttpResponse("".join(html))


# create an instance of the custom site and optionally register models here
vidox_admin_site = VidoxAdminSite(name="vidox_admin")
# register ContactMessage with the new site as well
vidox_admin_site.register(ContactMessage, ContactMessageAdmin)

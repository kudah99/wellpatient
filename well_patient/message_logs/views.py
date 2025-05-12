from django.shortcuts import render
from .models import MessageLog
from account.models import CustomUser as User
from django.db.models import OuterRef, Subquery, Max
from django.urls import reverse
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from unfold.views import UnfoldModelAdminViewMixin
from django.views.decorators.csrf import csrf_exempt
import json
from patients.utils import send_whatsapp
from django.utils import timezone
# Create your views here.


class ChatDashboardView(UnfoldModelAdminViewMixin, TemplateView):
    title = "Chat Dashboard"
    permission_required = ()
    template_name = "chats/live.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get query parameters
        platform_filter = self.request.GET.get("platform")
        search_query = self.request.GET.get("search", "").strip()
        user_id = self.kwargs.get("user_id")

        # Subquery to get the latest message timestamp for each user
        latest_message_subquery = (
            MessageLog.objects.filter(user=OuterRef("pk"))
            .order_by("-timestamp")
            .values("timestamp")[:1]
        )

        # Base queryset for users
        users = User.objects.annotate(
            last_message_time=Subquery(latest_message_subquery)
        ).order_by("-live", "-last_message_time")

        # Apply platform filter if provided
        if platform_filter:
            users = users.filter(platform=platform_filter)

        # Apply search filter if provided
        if search_query:
            users = users.filter(wisrod_account_id__icontains=search_query)

        # Get specific user and messages if user_id is provided
        user = None
        messages = None
        if user_id:
            user = get_object_or_404(User, id=user_id)
            messages = MessageLog.objects.filter(user=user).order_by("timestamp")

        context.update({
            "users": users,
            "platform_filter": platform_filter,
            "user": user,
            "messages": messages,
            "end_chat_url": reverse('end_chat'), 
        })
        return context

@csrf_exempt
def send_message(request, user_id):
    if request.method == "POST":
        
        data = json.loads(request.body)
        print(data)
        message_text = data.get("message")

        user = User.objects.get(id=user_id)
        MessageLog.objects.create(user=user, message=message_text, is_reply=True, platform=user.platform, timestamp=timezone.now())

        send_whatsapp(user.whatsapp_number, message_text)

        return JsonResponse({"status": "Message sent"})

@csrf_exempt
def end_chat(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_id = data.get("user_id")

        try:
            user = User.objects.get(id=user_id)
            user.live = False
            user.save()

            # Send chat end notification via WebSocket (or another method)
            # Example: send_message_to_user(user.id, "Live chat ended.")

            return JsonResponse({"message": "Chat ended successfully."})
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found."}, status=404)

    return JsonResponse({"error": "Invalid request."}, status=400)
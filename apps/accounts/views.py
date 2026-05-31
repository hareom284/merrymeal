from django.contrib.auth import login, logout
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import EmailLoginForm


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("/")
    if request.method == "POST":
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            login(request, form.cleaned_data["user"])
            return HttpResponseRedirect(request.GET.get("next", "/"))
    else:
        form = EmailLoginForm()
    return render(request, "accounts/login.html", {"form": form})


@require_http_methods(["POST"])
def logout_view(request):
    logout(request)
    return redirect(reverse("accounts:login"))

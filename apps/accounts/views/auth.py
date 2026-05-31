from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.accounts.forms import EmailLoginForm
from apps.accounts.services import sign_in, sign_out


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            user = sign_in(request, **form.cleaned_data)
            if user is not None:
                return HttpResponseRedirect(request.GET.get("next", "/"))
            form.add_error(None, "Invalid email or password")
    else:
        form = EmailLoginForm()

    return render(request, "accounts/login.html", {"form": form})


@require_http_methods(["POST"])
def logout_view(request):
    sign_out(request)
    return redirect(reverse("accounts:login"))

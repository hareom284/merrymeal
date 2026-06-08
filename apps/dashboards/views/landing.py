from django.shortcuts import redirect, render


def landing_view(request):
    if request.user.is_authenticated:
        return redirect("/dashboard/")
    return render(request, "dashboards/landing.html")

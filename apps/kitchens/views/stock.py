from datetime import date

from django.shortcuts import redirect, render
from django.urls import reverse

from apps.core.decorators import role_required
from apps.kitchens.forms.stock import StockReceiveForm
from apps.kitchens.models import Kitchen
from apps.kitchens.services.stock import receive_batch


@role_required("kitchen_staff", "admin")
def stock_receive_view(request):
    kitchens = Kitchen.objects.all()
    single_kitchen = kitchens.first() if kitchens.count() == 1 else None

    if request.method == "POST":
        form = StockReceiveForm(request.POST)
        if form.is_valid():
            batch = receive_batch(
                user=request.user,
                kitchen=form.cleaned_data["kitchen"],
                ingredient=form.cleaned_data["ingredient"],
                quantity=form.cleaned_data["quantity"],
                expiration_date=form.cleaned_data["expiration_date"],
                received_at=form.cleaned_data["received_at"],
                lot_number=form.cleaned_data.get("lot_number") or None,
            )
            return redirect(f"{reverse('kitchens:stock_receive')}?created={batch.pk}")
    else:
        initial = {"received_at": date.today()}
        if single_kitchen:
            initial["kitchen"] = single_kitchen.pk
        form = StockReceiveForm(initial=initial)

    return render(
        request,
        "kitchens/stock/receive.html",
        {
            "form": form,
            "single_kitchen": single_kitchen,
            "just_created_id": request.GET.get("created"),
        },
    )

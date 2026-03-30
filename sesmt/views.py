from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render


def _paginate_mock_list(request, items):
    paginator = Paginator(items, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return {
        "page_obj": page_obj,
        "total_count": len(items),
        "pagination_query": "",
    }


@login_required
def home(request):
    return render(request, 'sesmt/index.html')


@login_required
def atendimento_index(request):
    return render(request, 'sesmt/atendimento/index.html')


@login_required
def atendimento_list(request):
    items = [
        {"id": 521, "data": "29/03/2026", "paciente": "João Silva", "tipo": "Primeiros socorros", "status": "Em andamento", "status_badge": "warning"},
        {"id": 520, "data": "29/03/2026", "paciente": "Maria Souza", "tipo": "Encaminhamento", "status": "Concluído", "status_badge": "success"},
        {"id": 519, "data": "28/03/2026", "paciente": "Carlos Lima", "tipo": "Observação", "status": "Crítico", "status_badge": "danger"},
    ]
    return render(request, 'sesmt/atendimento/list.html', _paginate_mock_list(request, items))


@login_required
def atendimento_view(request, pk):
    context = {'atendimento_id': pk}
    return render(request, 'sesmt/atendimento/view.html', context)


@login_required
def atendimento_new(request):
    return render(request, 'sesmt/atendimento/new.html')


@login_required
def atendimento_export(request):
    return render(request, 'sesmt/atendimento/export.html')


@login_required
def manejo_index(request):
    return render(request, 'sesmt/manejo/index.html')


@login_required
def manejo_list(request):
    items = [
        {"id": 611, "data": "29/03/2026", "especie": "Quati", "tipo": "Resgate", "status": "Em andamento", "status_badge": "warning"},
        {"id": 610, "data": "29/03/2026", "especie": "Coruja", "tipo": "Soltura", "status": "Concluído", "status_badge": "success"},
        {"id": 609, "data": "28/03/2026", "especie": "Gambá", "tipo": "Transporte", "status": "Pendente", "status_badge": "danger"},
    ]
    return render(request, 'sesmt/manejo/list.html', _paginate_mock_list(request, items))


@login_required
def manejo_view(request, pk):
    context = {'manejo_id': pk}
    return render(request, 'sesmt/manejo/view.html', context)


@login_required
def manejo_new(request):
    return render(request, 'sesmt/manejo/new.html')


@login_required
def manejo_export(request):
    return render(request, 'sesmt/manejo/export.html')


@login_required
def flora_index(request):
    return render(request, 'sesmt/flora/index.html')


@login_required
def flora_list(request):
    items = [
        {"id": 711, "data": "29/03/2026", "especie": "Araucária", "area": "Área Norte", "status": "Em andamento", "status_badge": "warning"},
        {"id": 710, "data": "29/03/2026", "especie": "Ipê-amarelo", "area": "Trilha", "status": "Concluído", "status_badge": "success"},
        {"id": 709, "data": "28/03/2026", "especie": "Samambaia", "area": "Recepção", "status": "Pendente", "status_badge": "danger"},
    ]
    return render(request, 'sesmt/flora/list.html', _paginate_mock_list(request, items))


@login_required
def flora_view(request, pk):
    context = {'flora_id': pk}
    return render(request, 'sesmt/flora/view.html', context)


@login_required
def flora_new(request):
    return render(request, 'sesmt/flora/new.html')


@login_required
def flora_export(request):
    return render(request, 'sesmt/flora/export.html')

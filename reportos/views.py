from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home(request):
    return render(
        request,
        "reportos/index.html",
        {
            "module_title": "Central do ReportOS",
            "module_description": (
                "Base inicial do modulo PWA para operacao em campo, com foco em "
                "Atendimento, Flora e Fauna/Manejo."
            ),
            "reportos_scope": [
                {
                    "title": "Atendimento",
                    "description": "Fluxo de campo com pessoa, contato, saude, remocao, testemunhas e evidencias.",
                    "status": "Mapeado no legado",
                },
                {
                    "title": "Flora",
                    "description": "Registro de campo com area, local, acao inicial, medicoes, fotos e geolocalizacao.",
                    "status": "Mapeado no legado",
                },
                {
                    "title": "Fauna e Manejo",
                    "description": "Fluxo previsto a partir do legado de manejo, com captura, soltura e acionamento institucional.",
                    "status": "Mapeado no legado",
                },
            ],
        },
    )


@login_required
def atendimento_home(request):
    return render(
        request,
        "reportos/atendimento/index.html",
        {
            "module_title": "Central de Atendimento",
            "module_description": "Base inicial do fluxo de atendimento em campo para o ReportOS.",
        },
    )


@login_required
def manejo_home(request):
    return render(
        request,
        "reportos/manejo/index.html",
        {
            "module_title": "Central de Manejo",
            "module_description": "Base inicial do fluxo de fauna e manejo operacional para o ReportOS.",
        },
    )


@login_required
def flora_home(request):
    return render(
        request,
        "reportos/flora/index.html",
        {
            "module_title": "Central de Flora",
            "module_description": "Base inicial do fluxo de registro ambiental de flora para o ReportOS.",
        },
    )

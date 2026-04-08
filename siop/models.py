from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.urls import reverse

from sigo.models import Anexo, Assinatura, BaseModel, Foto, Pessoa, Unidade
from sigo_core.catalogos import (
    catalogo_achado_classificacao_label,
    catalogo_achado_situacao_label,
    catalogo_achado_status_label,
    catalogo_ativo_label,
    catalogo_area_label,
    catalogo_chave_area,
    catalogo_chave_label,
    catalogo_chave_numero,
    catalogo_cracha_provisorio_label,
    catalogo_funcao_ativo_label,
    catalogo_local_label,
    catalogo_natureza_label,
    catalogo_p1_label,
    catalogo_tipo_label,
    catalogo_tipo_pessoa_label,
)

class Ocorrencia(BaseModel):
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, null=True, blank=True, related_name="ocorrencias", verbose_name="Unidade")
    unidade_sigla = models.CharField(max_length=50, null=True, blank=True, verbose_name="Sigla da Unidade", db_index=True)
    tipo_pessoa = models.CharField(max_length=30, verbose_name="Tipo Pessoa", blank=False, null=False, db_index=True)
    data_ocorrencia = models.DateTimeField(verbose_name="Data e Hora da Ocorrência", db_index=True)
    natureza = models.CharField(max_length=50, verbose_name="Natureza", null=False, blank=False, db_index=True)
    tipo = models.CharField(max_length=50, verbose_name="Tipo", null=False, blank=False, db_index=True)
    area = models.CharField(max_length=50, verbose_name="Área", null=False, blank=False, db_index=True)
    local = models.CharField(max_length=50, verbose_name="Local", null=False, blank=False, db_index=True)
    cftv = models.BooleanField(verbose_name="Possui imagens CFTV?", default=False)
    bombeiro_civil = models.BooleanField(verbose_name="Acionou BC?", default=False, db_index=True)
    anexos = GenericRelation(Anexo)
    status = models.BooleanField(verbose_name="Ocorrência Finalizada?", default=False, db_index=True)
    descricao = models.TextField(verbose_name="Descrição da Ocorrência", blank=True, null=True)

    class Meta:
        verbose_name = "Ocorrência"
        verbose_name_plural = "Ocorrências"
        ordering = ["-data_ocorrencia"]

    def normalizar_campos(self):
        self.normalize_string_fields(
            required_fields=("tipo_pessoa", "natureza", "tipo", "area", "local"),
            nullable_fields=("descricao",),
        )

    def clean(self):
        super().clean()
        errors = {}

        if not self.tipo_pessoa:
            errors["tipo_pessoa"] = "O tipo de pessoa é obrigatório."
        if not self.data_ocorrencia:
            errors["data_ocorrencia"] = "A data e hora da ocorrência são obrigatórias."
        if not self.natureza:
            errors["natureza"] = "A natureza é obrigatória."
        if not self.tipo:
            errors["tipo"] = "O tipo é obrigatório."
        if not self.area:
            errors["area"] = "A área é obrigatória."
        if not self.local:
            errors["local"] = "O local é obrigatório."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.normalizar_campos()
        self.preencher_unidade_sigla()
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        when = self.data_ocorrencia.strftime("%d/%m/%Y %H:%M") if self.data_ocorrencia else "sem data"
        return f"{self.natureza} - {self.tipo} - {self.local} ({when})"

    def get_absolute_url(self):
        return reverse("siop:ocorrencias_view", kwargs={"pk": self.pk})

    @property
    def tipo_pessoa_label(self):
        return catalogo_tipo_pessoa_label(self.tipo_pessoa)

    @property
    def natureza_label(self):
        return catalogo_natureza_label(self.natureza)

    @property
    def tipo_label(self):
        return catalogo_tipo_label(self.natureza, self.tipo)

    @property
    def area_label(self):
        return catalogo_area_label(self.area)

    @property
    def local_label(self):
        return catalogo_local_label(self.area, self.local)

class AcessoColaboradores(BaseModel):
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, null=True, blank=True, related_name="acessos_colaboradores", verbose_name="Unidade")
    unidade_sigla = models.CharField(max_length=50, null=True, blank=True, verbose_name="Sigla da Unidade", db_index=True)
    entrada = models.DateTimeField(verbose_name="Data e Hora da Entrada", db_index=True, null=False, blank=False)
    saida = models.DateTimeField(verbose_name="Data e Hora da Saída", db_index=True, null=True, blank=True)
    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name="acessos_colaboradores")
    placa_veiculo = models.CharField(max_length=20, verbose_name="Placa do Veículo", null=True, blank=True)
    p1 = models.CharField(max_length=50, verbose_name="P1", db_index=True)
    anexos = GenericRelation(Anexo)
    descricao_acesso = models.TextField(verbose_name="Descrição de Acesso Colaboradores", blank=True)

    class Meta:
        verbose_name = "Acesso de Colaboradores"
        verbose_name_plural = "Acessos de Colaboradores"
        ordering = ["-entrada", "-criado_em"]
        constraints = [
            models.CheckConstraint(
                condition=Q(saida__isnull=True) | Q(saida__gte=F("entrada")),
                name="acesso_colaboradores_saida_maior_ou_igual_entrada",
            )
        ]
        indexes = [
            models.Index(fields=["p1", "-entrada"]),
        ]

    def clean(self):
        super().clean()

        errors = {}

        if not self.entrada:
            errors["entrada"] = "A data e hora da entrada são obrigatórias."
        if not self.p1:
            errors["p1"] = "P1 é obrigatório."
        if self.saida and self.entrada and self.saida < self.entrada:
            errors["saida"] = "A saída não pode ser anterior à entrada."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.normalize_string_fields(
            required_fields=("p1", "descricao_acesso"),
            nullable_fields=("placa_veiculo",),
            upper_fields=("placa_veiculo",),
        )
        self.preencher_unidade_sigla()
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        pessoas_label = self.pessoa.nome if self.pessoa_id and self.pessoa.nome else "sem pessoa"
        when = self.entrada.strftime("%d/%m/%Y %H:%M") if self.entrada else "sem entrada"
        return f"Acesso de Colaboradores - {pessoas_label} ({when})"

    def get_absolute_url(self):
        return reverse("siop:acesso_colaboradores_view", kwargs={"pk": self.pk})

    @property
    def pessoas_nomes_display(self):
        return self.pessoa.nome if self.pessoa_id and self.pessoa.nome else ""

    @property
    def pessoas_documentos_display(self):
        return self.pessoa.documento if self.pessoa_id and self.pessoa.documento else ""

    @property
    def pessoas_resumo_display(self):
        return self.pessoas_nomes_display

    @property
    def pessoas_documentos_resumo_display(self):
        return self.pessoas_documentos_display

    @property
    def status_label(self):
        return "Concluído" if self.saida else "Em aberto"

    @property
    def p1_label(self):
        label = catalogo_p1_label(self.p1)
        if label and label != self.p1:
            return label
        return str(self.p1 or "").replace("_", " ").strip().title()

class AcessoTerceiros(BaseModel):
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, null=True, blank=True, related_name="acessos_terceiros", verbose_name="Unidade")
    unidade_sigla = models.CharField(max_length=50, null=True, blank=True, verbose_name="Sigla da Unidade", db_index=True)
    entrada = models.DateTimeField(verbose_name="Data e Hora da Entrada", db_index=True, null=False, blank=False)
    saida = models.DateTimeField(verbose_name="Data e Hora da Saída", db_index=True, null=True, blank=True)
    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name="acessos_terceiros")
    empresa = models.CharField(max_length=255, verbose_name="Empresa", null=True, blank=True)
    placa_veiculo = models.CharField(max_length=20, verbose_name="Placa do Veículo", null=True, blank=True)
    p1 = models.CharField(max_length=50, verbose_name="P1", db_index=True)
    anexos = GenericRelation(Anexo)
    descricao_acesso = models.TextField(verbose_name="Descrição de Acesso Terceiros", blank=True)

    class Meta:
        verbose_name = "Acesso de Terceiros"
        verbose_name_plural = "Acessos de Terceiros"
        ordering = ["-entrada", "-criado_em"]
        constraints = [
            models.CheckConstraint(
                condition=Q(saida__isnull=True) | Q(saida__gte=F("entrada")),
                name="acesso_terceiros_saida_maior_ou_igual_entrada",
            )
        ]
        indexes = [
            models.Index(fields=["pessoa", "-entrada"]),
            models.Index(fields=["p1", "-entrada"]),
        ]

    def clean(self):
        super().clean()

        errors = {}

        if not self.pessoa_id:
            errors["pessoa"] = "A pessoa é obrigatória."

        if not self.entrada:
            errors["entrada"] = "A data/hora de entrada é obrigatória."

        if not self.p1:
            errors["p1"] = "O campo P1 é obrigatório."

        if self.entrada and self.saida and self.saida < self.entrada:
            errors["saida"] = "A data/hora de saída não pode ser anterior à entrada."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.normalize_string_fields(
            required_fields=("p1", "descricao_acesso"),
            nullable_fields=("empresa", "placa_veiculo"),
            upper_fields=("placa_veiculo",),
        )
        self.preencher_unidade_sigla()
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def nome(self):
        return self.pessoa.nome if self.pessoa_id else ""

    @property
    def documento(self):
        return self.pessoa.documento if self.pessoa_id else ""

    @property
    def descricao(self):
        return self.descricao_acesso

    def __str__(self):
        when = self.entrada.strftime("%d/%m/%Y %H:%M") if self.entrada else "sem entrada"
        pessoa_nome = self.pessoa.nome if self.pessoa_id else "sem pessoa"
        pessoa_documento = self.pessoa.documento if self.pessoa_id else "sem documento"
        return f"{pessoa_nome} ({pessoa_documento}) - {when}"

    def get_absolute_url(self):
        return reverse("siop:acesso_terceiros_view", kwargs={"pk": self.pk})

class AchadosPerdidos(BaseModel):
    FINAL_STATUS = {"entregue", "descarte", "doacao"}

    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, null=True, blank=True, related_name="achados_perdidos", verbose_name="Unidade")
    unidade_sigla = models.CharField(max_length=50, null=True, blank=True, verbose_name="Sigla da Unidade", db_index=True)
    tipo = models.CharField(max_length=50, verbose_name="Classificação do Item", null=False, blank=False, db_index=True)
    situacao = models.CharField(max_length=20, verbose_name="Situação do Item", null=True, blank=True, db_index=True)
    descricao = models.TextField(verbose_name="Descrição do Item", blank=False, null=False)
    local = models.CharField(max_length=30, verbose_name="Local do Achado/Perdido", null=False, blank=False, db_index=True)
    area = models.CharField(max_length=30, verbose_name="Área do Achado/Perdido", null=False, blank=False, db_index=True)
    organico = models.BooleanField(verbose_name="Orgânico?", null=False, default=True)
    colaborador = models.CharField(max_length=255, verbose_name="Colaborador Responsável", null=True, blank=True)
    setor = models.CharField(max_length=255, verbose_name="Setor do Colaborador", null=True, blank=True)
    data_devolucao = models.DateTimeField(verbose_name="Data e Hora da Devolução", null=True, blank=True, db_index=True)
    anexos = GenericRelation(Anexo)
    fotos = GenericRelation(Foto)
    assinaturas = GenericRelation(Assinatura)
    ciop = models.CharField(max_length=100, verbose_name="CIOP", null=True, blank=True, db_index=True)
    status = models.CharField(max_length=20, verbose_name="Status do Item", null=False, blank=False, db_index=True)
    pessoa = models.ForeignKey(Pessoa, on_delete=models.SET_NULL, null=True, blank=True, related_name="pessoa_achados_perdidos", verbose_name="Pessoa Recebeu Item")

    class Meta:
        verbose_name = "Achado e Perdido"
        verbose_name_plural = "Achados e Perdidos"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["tipo", "-criado_em"]),
            models.Index(fields=["status", "-criado_em"]),
            models.Index(fields=["area", "local"]),
        ]

    def normalizar_campos(self):
        self.normalize_string_fields(
            required_fields=("tipo", "situacao", "descricao", "local", "area", "status"),
            nullable_fields=("colaborador", "setor", "ciop"),
        )

    def clean(self):
        super().clean()

        errors = {}

        if not self.tipo:
            errors["tipo"] = "A classificação do item é obrigatória."

        if not self.situacao:
            errors["situacao"] = "A situação do item é obrigatória."

        if not self.descricao:
            errors["descricao"] = "A descrição do item é obrigatória."

        if not self.local:
            errors["local"] = "O local do achado/perdido é obrigatório."

        if not self.area:
            errors["area"] = "A área do achado/perdido é obrigatória."

        if not self.status:
            errors["status"] = "O status do item é obrigatório."

        if self.data_devolucao and not self.pessoa_id:
            errors["pessoa"] = "Informe a pessoa que recebeu o item ao registrar a devolução."

        if self.status.lower() in self.FINAL_STATUS:
            if not self.pessoa_id:
                errors["pessoa"] = "Informe a pessoa que recebeu o item para concluir com este status."
            if not self.data_devolucao:
                errors["data_devolucao"] = "Informe a data e hora da devolução para concluir com este status."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.normalizar_campos()
        self.preencher_unidade_sigla()
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        base = f"{self.situacao or self.tipo} - {self.tipo} - {self.local}"
        if self.status:
            return f"{base} ({self.status})"
        return base

    def get_absolute_url(self):
        return reverse("siop:achados_perdidos_view", kwargs={"pk": self.pk})

    @property
    def tipo_label(self):
        return catalogo_achado_classificacao_label(self.tipo)

    @property
    def situacao_label(self):
        return catalogo_achado_situacao_label(self.situacao)

    @property
    def status_label(self):
        return catalogo_achado_status_label(self.status)

    @property
    def area_label(self):
        return catalogo_area_label(self.area)

    @property
    def local_label(self):
        return catalogo_local_label(self.area, self.local)

class ControleAtivos(BaseModel):
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, null=True, blank=True, related_name="controles_ativos", verbose_name="Unidade")
    unidade_sigla = models.CharField(max_length=50, null=True, blank=True, verbose_name="Sigla da Unidade", db_index=True)
    retirada = models.DateTimeField(verbose_name="Data e Hora da Retirada", db_index=True, null=False, blank=False)
    devolucao = models.DateTimeField(verbose_name="Data e Hora da Devolução", db_index=True, null=True, blank=True)
    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name="controles_ativos")
    equipamento = models.CharField(max_length=255, verbose_name="Equipamento", null=False, blank=False)
    destino = models.CharField(max_length=255, verbose_name="Destino", null=False, blank=False)
    observacao = models.TextField(verbose_name="Observação", blank=True, null=True)

    def __str__(self):
        when = self.retirada.strftime("%d/%m/%Y %H:%M") if self.retirada else "sem retirada"
        return f"{self.equipamento} - {self.destino} ({when})"

    def get_absolute_url(self):
        return reverse("siop:controle_ativos_view", kwargs={"pk": self.pk})

    @property
    def equipamento_label(self):
        return catalogo_ativo_label(self.equipamento)

    @property
    def destino_label(self):
        return catalogo_funcao_ativo_label(self.destino)


class ControleChaves(BaseModel):
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, null=True, blank=True, related_name="controles_chaves", verbose_name="Unidade")
    unidade_sigla = models.CharField(max_length=50, null=True, blank=True, verbose_name="Sigla da Unidade", db_index=True)
    retirada = models.DateTimeField(verbose_name="Data e Hora da Retirada", db_index=True, null=False, blank=False)
    devolucao = models.DateTimeField(verbose_name="Data e Hora da Devolução", db_index=True, null=True, blank=True)
    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name="controles_chaves")
    chave = models.CharField(max_length=255, verbose_name="Chave", null=False, blank=False, db_index=True)
    observacao = models.TextField(verbose_name="Observação", blank=True, null=True)

    def __str__(self):
        when = self.retirada.strftime("%d/%m/%Y %H:%M") if self.retirada else "sem retirada"
        return f"{self.chave} ({when})"

    def get_absolute_url(self):
        return reverse("siop:controle_chaves_view", kwargs={"pk": self.pk})

    @property
    def chave_label(self):
        return catalogo_chave_label(self.chave)

    @property
    def chave_numero(self):
        return catalogo_chave_numero(self.chave)

    @property
    def chave_area(self):
        return catalogo_chave_area(self.chave)

class CrachaProvisorio(BaseModel):
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, null=True, blank=True, related_name="crachas_provisorios", verbose_name="Unidade")
    unidade_sigla = models.CharField(max_length=50, null=True, blank=True, verbose_name="Sigla da Unidade", db_index=True)
    cracha = models.CharField(max_length=50, verbose_name="Crachá", db_index=True, null=False, blank=False)
    entrega = models.DateTimeField(verbose_name="Data e Hora da Entrega", db_index=True, null=False, blank=False)
    devolucao = models.DateTimeField(verbose_name="Data e Hora da Devolução", db_index=True, null=True, blank=True)
    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name="crachas_provisorios")
    documento = models.CharField(max_length=20, verbose_name="Documento da Pessoa", null=True, blank=True)
    observacao = models.TextField(verbose_name="Observação", blank=True, null=True)

    def get_absolute_url(self):
        return reverse("siop:crachas_provisorios_view", kwargs={"pk": self.pk})

    @property
    def cracha_label(self):
        return catalogo_cracha_provisorio_label(self.cracha)

class ControleEfetivo(BaseModel):
    plantao = models.CharField(max_length=100, verbose_name="Responsável Plantão", null=True, blank=True, db_index=True)
    atendimento = models.CharField(max_length=255, verbose_name="Responsável Atendimento", null=True, blank=True)
    bilheteria = models.CharField(max_length=255, verbose_name="Responsável Bilheteria", null=True, blank=True)
    bombeiro_civil = models.CharField(max_length=255, verbose_name="Bombeiro Civil 1", null=True, blank=True)
    bombeiro_civil_2 = models.CharField(max_length=255, verbose_name="Bombeiro Civil 2", null=True, blank=True)
    bombeiro_hidraulico = models.CharField(max_length=255, verbose_name="Bombeiro Hidráulico", null=True, blank=True)
    ciop = models.CharField(max_length=100, verbose_name="CIOP", null=True, blank=True, db_index=True)    
    eletrica = models.CharField(max_length=255, verbose_name="Responsável Elétrica", null=True, blank=True)
    artifice_civil = models.CharField(max_length=255, verbose_name="Responsável Artífice Civil", null=True, blank=True)
    ti = models.CharField(max_length=255, verbose_name="Responsável TI", null=True, blank=True)
    facilities = models.CharField(max_length=255, verbose_name="Responsável Facilities", null=True, blank=True)
    manutencao = models.CharField(max_length=255, verbose_name="Responsável Manutenção", null=True, blank=True, db_column="manutenção")
    jardinagem = models.CharField(max_length=255, verbose_name="Responsável Jardinagem", null=True, blank=True)
    limpeza = models.CharField(max_length=255, verbose_name="Responsável Limpeza", null=True, blank=True)
    seguranca_trabalho = models.CharField(max_length=255, verbose_name="Responsável Segurança do Trabalho", null=True, blank=True)
    seguranca_patrimonial = models.CharField(max_length=255, verbose_name="Responsável Segurança Patrimonial", null=True, blank=True)
    meio_ambiente = models.CharField(max_length=255, verbose_name="Responsável Meio Ambiente", null=True, blank=True)
    engenharia = models.CharField(max_length=255, verbose_name="Responsável Engenharia", null=True, blank=True)
    estapar = models.CharField(max_length=255, verbose_name="Responsável Estapar", null=True, blank=True)
    observacao = models.TextField(verbose_name="Observação", blank=True, null=True)

    def __str__(self):
        return f"Efetivo #{self.pk or 'novo'} - Atendimento: {self.atendimento}"

    def get_absolute_url(self):
        return reverse("siop:efetivo_view", kwargs={"pk": self.pk})

class LiberacaoAcesso(BaseModel):
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, null=True, blank=True, related_name="liberacoes_acesso", verbose_name="Unidade")
    unidade_sigla = models.CharField(max_length=50, null=True, blank=True, verbose_name="Sigla da Unidade", db_index=True)
    pessoas = models.ManyToManyField(Pessoa, related_name="liberacoes_acesso", verbose_name="Pessoas")
    chegadas_registradas = models.JSONField(default=list, blank=True, verbose_name="Pessoas com chegada registrada")
    motivo = models.TextField(verbose_name="Motivo da Liberação de Acesso", blank=False, null=False)
    data_liberacao = models.DateTimeField(verbose_name="Data e Hora da Liberação de Acesso", db_index=True)
    empresa = models.CharField(max_length=255, verbose_name="Empresa", null=True, blank=True)
    solicitante = models.CharField(max_length=255, verbose_name="Solicitante", null=True, blank=True)
    anexos = GenericRelation(Anexo)

    def __str__(self):
        if not self.pk:
            pessoas_label = "sem pessoas"
        else:
            pessoas = list(self.pessoas.all()[:2])
            total = self.pessoas.count()
            if total == 0:
                pessoas_label = "sem pessoas"
            elif total == 1:
                pessoas_label = pessoas[0].nome
            else:
                pessoas_label = f"{pessoas[0].nome} e mais {total - 1}"
        when = self.data_liberacao.strftime("%d/%m/%Y %H:%M") if self.data_liberacao else "sem data"
        return f"Liberação de Acesso - {pessoas_label} ({when})"

    def get_absolute_url(self):
        return reverse("siop:liberacao_acesso_view", kwargs={"pk": self.pk})

    @property
    def pessoas_nomes_display(self):
        if not self.pk:
            return ""
        return ", ".join(
            pessoa.nome
            for pessoa in self.pessoas.all()
            if pessoa.nome
        )

    @property
    def pessoas_documentos_display(self):
        if not self.pk:
            return ""
        return ", ".join(
            pessoa.documento
            for pessoa in self.pessoas.all()
            if pessoa.documento
        )

    @property
    def pessoas_resumo_display(self):
        if not self.pk:
            return ""
        pessoas = [pessoa.nome for pessoa in self.pessoas.all() if pessoa.nome]
        if not pessoas:
            return ""
        if len(pessoas) == 1:
            return pessoas[0]
        return f"{pessoas[0]} + {len(pessoas) - 1}"

    @property
    def pessoas_documentos_resumo_display(self):
        if not self.pk:
            return ""
        documentos = [pessoa.documento for pessoa in self.pessoas.all() if pessoa.documento]
        if not documentos:
            return ""
        if len(documentos) == 1:
            return documentos[0]
        return f"{documentos[0]} + {len(documentos) - 1}"

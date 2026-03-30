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
    catalogo_area_label,
    catalogo_local_label,
    catalogo_natureza_label,
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

    def clean(self):
        super().clean()
        errors = {}
        self.tipo_pessoa = (self.tipo_pessoa or "").strip()
        self.natureza = (self.natureza or "").strip()
        self.tipo = (self.tipo or "").strip()
        self.area = (self.area or "").strip()
        self.local = (self.local or "").strip()
        self.descricao = (self.descricao or "").strip() or None

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
        if not self.unidade_sigla and self.unidade_id:
            self.unidade_sigla = self.unidade.sigla
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.natureza} - {self.tipo} - {self.local} ({self.data_ocorrencia.strftime('%d/%m/%Y %H:%M')})"

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

        self.p1 = (self.p1 or "").strip()
        self.empresa = (self.empresa or "").strip() or None
        self.placa_veiculo = (self.placa_veiculo or "").strip().upper() or None
        self.descricao_acesso = (self.descricao_acesso or "").strip()

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
        if not self.unidade_sigla and self.unidade_id:
            self.unidade_sigla = self.unidade.sigla
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

    def clean(self):
        super().clean()

        errors = {}

        self.tipo = (self.tipo or "").strip()
        self.situacao = (self.situacao or "").strip()
        self.descricao = (self.descricao or "").strip()
        self.local = (self.local or "").strip()
        self.area = (self.area or "").strip()
        self.colaborador = (self.colaborador or "").strip() or None
        self.setor = (self.setor or "").strip() or None
        self.ciop = (self.ciop or "").strip() or None
        self.status = (self.status or "").strip()

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
        if not self.unidade_sigla and self.unidade_id:
            self.unidade_sigla = self.unidade.sigla
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

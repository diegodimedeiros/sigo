import hashlib

from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from sigo.models import Anexo, Assinatura, BaseModel, Contato, Foto, Geolocalizacao, Pessoa, Unidade

class Testemunha(Pessoa):
    contato = models.OneToOneField(Contato, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Testemunha"
        verbose_name_plural = "Testemunhas"

    def __str__(self):
        return self.nome

class ControleAtendimento(BaseModel):
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, null=True, blank=True, related_name="controles_atendimento", verbose_name="Unidade")
    unidade_sigla = models.CharField(max_length=50, null=True, blank=True, verbose_name="Sigla da Unidade", db_index=True)
    tipo_pessoa = models.CharField(
        max_length=50,
        verbose_name="Tipo de Pessoa",
        null=False,
        blank=False,
        db_index=True,
    )
    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name="controles_atendimento")
    contato = models.ForeignKey(
        Contato,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="controles_atendimento",
    )
    area_atendimento = models.CharField(
        max_length=50,
        verbose_name="Área de Atendimento",
        null=False,
        blank=False,
        db_index=True,
    )
    local = models.CharField(max_length=50, verbose_name="Local de Atendimento", null=False, blank=False, db_index=True)
    data_atendimento = models.DateTimeField(verbose_name="Data e Hora do Atendimento", db_index=True)
    tipo_ocorrencia = models.CharField(max_length=50, verbose_name="Tipo de Ocorrência", null=False, blank=False, db_index=True)
    possui_acompanhante = models.BooleanField(verbose_name="Acompanhante?", default=False)
    acompanhante_pessoa = models.ForeignKey(
        Pessoa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="atendimentos_como_acompanhante",
        verbose_name="Nome do Acompanhante",
    )
    grau_parentesco = models.CharField(max_length=100, verbose_name="Grau de Parentesco", null=True, blank=True)
    doenca_preexistente = models.BooleanField(verbose_name="Doença Preexistente?", default=False)
    descricao_doenca = models.TextField(verbose_name="Descrição da Doença", null=True, blank=True)
    alergia = models.BooleanField(verbose_name="Alergia?", default=False)
    descricao_alergia = models.TextField(verbose_name="Descrição da Alergia", null=True, blank=True)
    plano_saude = models.BooleanField(verbose_name="Possui Plano de Saúde?", default=False)
    nome_plano_saude = models.CharField(max_length=255, verbose_name="Nome do Plano de Saúde", null=True, blank=True)
    numero_carteirinha = models.CharField(max_length=100, verbose_name="Número da Carteirinha", null=True, blank=True)
    primeiros_socorros = models.CharField(max_length=50, verbose_name="Primeiros Socorros", null=True, blank=True)
    atendimentos = models.BooleanField(verbose_name="Atendimento Realizado?", default=False)
    recusa_atendimento = models.BooleanField(verbose_name="Recusa de Atendimento?", default=False, db_index=True)
    responsavel_atendimento = models.CharField(max_length=255, verbose_name="Responsável pelo Atendimento", null=True, blank=True)
    seguiu_passeio = models.BooleanField(verbose_name="Seguiu para o Passeio?", default=False)
    houve_remocao = models.BooleanField(verbose_name="Remoção?", default=False)
    transporte = models.CharField(max_length=100, verbose_name="Transporte Utilizado", null=True, blank=True)
    encaminhamento = models.CharField(max_length=255, verbose_name="Encaminhamento", null=True, blank=True)
    hospital = models.CharField(max_length=255, verbose_name="Hospital", null=True, blank=True)
    medico_responsavel = models.CharField(max_length=255, verbose_name="Médico Responsável", null=True, blank=True)
    crm = models.CharField(max_length=100, verbose_name="CRM do Médico", null=True, blank=True)
    descricao = models.TextField(verbose_name="Descrição do Atendimento", blank=False, null=False)
    testemunhas = models.ManyToManyField(
        Testemunha,
        blank=True,
        related_name="atendimentos_como_testemunha",
        verbose_name="Testemunhas",
    )
    anexos = GenericRelation(Anexo)
    fotos = GenericRelation(Foto)
    geolocalizacoes = GenericRelation(Geolocalizacao)
    assinaturas = GenericRelation(Assinatura)
    hash_atendimento = models.CharField(max_length=64, verbose_name="Hash do Atendimento", null=True, blank=True, db_index=True, unique=True)

    class Meta:
        verbose_name = "Controle de Atendimento"
        verbose_name_plural = "Controles de Atendimento"
        ordering = ["-data_atendimento", "-criado_em"]
        indexes = [
            models.Index(fields=["pessoa", "-data_atendimento"]),
            models.Index(fields=["tipo_ocorrencia", "-data_atendimento"]),
            models.Index(fields=["area_atendimento", "-data_atendimento"]),
        ]

    def normalizar_campos(self):
        self.normalize_string_fields(
            required_fields=("tipo_pessoa", "area_atendimento", "local", "tipo_ocorrencia", "descricao"),
            nullable_fields=(
                "grau_parentesco",
                "descricao_doenca",
                "descricao_alergia",
                "nome_plano_saude",
                "numero_carteirinha",
                "primeiros_socorros",
                "responsavel_atendimento",
                "transporte",
                "encaminhamento",
                "hospital",
                "medico_responsavel",
                "crm",
            ),
        )

    def clean(self):
        super().clean()
        errors = {}
        if not self.tipo_pessoa: errors["tipo_pessoa"] = "O tipo de pessoa é obrigatório."
        if not self.pessoa_id: errors["pessoa"] = "A pessoa é obrigatória."
        if not self.area_atendimento: errors["area_atendimento"] = "A área de atendimento é obrigatória."
        if not self.local: errors["local"] = "O local de atendimento é obrigatório."
        if not self.data_atendimento: errors["data_atendimento"] = "A data e hora do atendimento são obrigatórias."
        if not self.tipo_ocorrencia: errors["tipo_ocorrencia"] = "O tipo de ocorrência é obrigatório."
        if not self.descricao: errors["descricao"] = "A descrição do atendimento é obrigatória."
        if not self.responsavel_atendimento: errors["responsavel_atendimento"] = "O responsável pelo atendimento é obrigatório."
        if not self.recusa_atendimento:
            if self.possui_acompanhante and not self.acompanhante_pessoa_id: errors["acompanhante_pessoa"] = "Informe o acompanhante."
            if self.possui_acompanhante and not self.grau_parentesco: errors["grau_parentesco"] = "Informe o grau de parentesco."
            if self.houve_remocao and not self.transporte: errors["transporte"] = "Informe o transporte quando houver remoção."
            if self.houve_remocao and not self.encaminhamento: errors["encaminhamento"] = "Informe o encaminhamento quando houver remoção."
            if self.houve_remocao and not self.hospital: errors["hospital"] = "Informe o hospital quando houver remoção."
            if self.doenca_preexistente and not self.descricao_doenca: errors["descricao_doenca"] = "Informe a descrição da doença preexistente."
            if self.alergia and not self.descricao_alergia: errors["descricao_alergia"] = "Informe a descrição da alergia."
            if self.plano_saude and not self.nome_plano_saude: errors["nome_plano_saude"] = "Informe o nome do plano de saúde."
        if errors: raise ValidationError(errors)

    def _build_hash_atendimento(self):
        documento = self.pessoa.documento if self.pessoa_id else ""
        data_atendimento = self.data_atendimento.isoformat() if self.data_atendimento else ""
        payload = f"{self.pk}|{documento}|{data_atendimento}|{self.atendimentos}|{self.descricao}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def save(self, *args, **kwargs):
        self.normalizar_campos()
        self.preencher_unidade_sigla()
        self.full_clean()
        super().save(*args, **kwargs)
        novo_hash = self._build_hash_atendimento()
        if self.hash_atendimento != novo_hash:
            self.hash_atendimento = novo_hash
            super().save(update_fields=["hash_atendimento"])

    @property
    def hashes_fotos(self):
        # Cada Foto ja gera hash_arquivo/hash_arquivo_atual automaticamente ao salvar.
        return [
            foto.hash_arquivo_atual or foto.hash_arquivo
            for foto in self.fotos.all()
        ]

    def __str__(self):
        when = self.data_atendimento.strftime("%d/%m/%Y %H:%M") if self.data_atendimento else "sem data"
        pessoa_nome = self.pessoa.nome if self.pessoa_id else "sem pessoa"
        pessoa_documento = self.pessoa.documento if self.pessoa_id else "sem documento"
        return f"{pessoa_nome} ({pessoa_documento}) - {when}"

    def get_absolute_url(self):
        return reverse("sesmt:atendimento_view", args=[self.pk])

class Manejo(BaseModel):
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, null=True, blank=True, related_name="manejos", verbose_name="Unidade")
    unidade_sigla = models.CharField(max_length=50, null=True, blank=True, verbose_name="Sigla da Unidade", db_index=True)
    data_hora = models.DateTimeField(verbose_name="Data e Hora do Manejo", null=False, blank=False, db_index=True)
    
    classe = models.CharField(max_length=25, verbose_name="Classe", null=False, blank=False, db_index=True)
    nome_cientifico = models.CharField(max_length=255, verbose_name="Nome Científico", null=True, blank=True)
    nome_popular = models.CharField(max_length=255, verbose_name="Nome Popular", null=True, blank=True)
    estagio_desenvolvimento = models.CharField(max_length=50, verbose_name="Estágio de Desenvolvimento", null=True, blank=True)
    
    area_captura = models.CharField(max_length=50, verbose_name="Área", null=False, blank=False, db_index=True)
    local_captura = models.CharField(max_length=50, verbose_name="Local", null=False, blank=False, db_index=True)
    descricao_local = models.TextField(verbose_name="Descrição do Local", blank=True)

    importancia_medica = models.BooleanField(verbose_name="Importância Médica?", default=False)
    realizado_manejo = models.BooleanField(verbose_name="Manejo Realizado?", default=False, db_index=True)
    responsavel_manejo = models.CharField(max_length=255, verbose_name="Responsável pelo Manejo", null=True, blank=True)
    
    area_soltura = models.CharField(max_length=50, verbose_name="Área de Soltura", null=True, blank=True, db_index=True)
    local_soltura = models.CharField(max_length=50, verbose_name="Local de Soltura", null=True, blank=True, db_index=True)
    descricao_local_soltura = models.TextField(verbose_name="Descrição do Local de Soltura", blank=True)

    acionado_orgao_publico = models.BooleanField(verbose_name="Acionou Órgão Público?", default=False)
    orgao_publico = models.CharField(max_length=255, verbose_name="Órgão Público", null=True, blank=True)
    numero_boletim_ocorrencia = models.CharField(max_length=100, verbose_name="Número do Boletim de Ocorrência", null=True, blank=True)
    motivo_acionamento = models.TextField(verbose_name="Motivo do Acionamento", blank=True)

    observacoes = models.TextField(verbose_name="Observações", blank=True)

    geolocalizacoes = GenericRelation(Geolocalizacao)
    fotos = GenericRelation(Foto)        
    anexos = GenericRelation(Anexo)

    class Meta:
        verbose_name = "Manejo"
        verbose_name_plural = "Manejos"
        ordering = ["-data_hora", "-criado_em"]
        indexes = [
            models.Index(fields=["classe", "-data_hora"]),
            models.Index(fields=["area_captura", "-data_hora"]),
            models.Index(fields=["local_captura", "-data_hora"]),
        ]

    @property
    def geolocalizacao_captura(self):
        return self.geolocalizacoes.filter(tipo="captura").first()

    @property
    def geolocalizacao_soltura(self):
        return self.geolocalizacoes.filter(tipo="soltura").first()

    @property
    def fotos_captura(self):
        return self.fotos.filter(tipo=Foto.TIPO_CAPTURA)

    @property
    def fotos_soltura(self):
        return self.fotos.filter(tipo=Foto.TIPO_SOLTURA)

    def clean(self):
        super().clean()

        errors = {}

        if not self.data_hora:
            errors["data_hora"] = "A data e hora do manejo são obrigatórias."
        if not self.classe:
            errors["classe"] = "A classe é obrigatória."
        if not self.area_captura:
            errors["area_captura"] = "A área de captura é obrigatória."
        if not self.local_captura:
            errors["local_captura"] = "O local de captura é obrigatório."
        if self.realizado_manejo and not self.responsavel_manejo:
            errors["responsavel_manejo"] = "Informe o responsável quando o manejo for realizado."

        informou_soltura = any(
            [
                self.area_soltura,
                self.local_soltura,
                self.descricao_local_soltura,
            ]
        )
        if informou_soltura:
            if not self.area_soltura:
                errors["area_soltura"] = "Informe a área de soltura."
            if not self.local_soltura:
                errors["local_soltura"] = "Informe o local de soltura."

        if self.acionado_orgao_publico and not self.orgao_publico:
            errors["orgao_publico"] = "Informe o órgão público acionado."

        if errors:
            raise ValidationError(errors)

    def normalizar_campos(self):
        self.normalize_string_fields(
            required_fields=("classe", "area_captura", "local_captura", "descricao_local", "descricao_local_soltura", "motivo_acionamento", "observacoes"),
            nullable_fields=("nome_cientifico", "nome_popular", "estagio_desenvolvimento", "responsavel_manejo", "area_soltura", "local_soltura", "orgao_publico", "numero_boletim_ocorrencia"),
        )

    def save(self, *args, **kwargs):
        self.normalizar_campos()
        self.preencher_unidade_sigla()
        self.full_clean()
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("sesmt:manejo_view", args=[self.pk])

    def __str__(self):
        when = self.data_hora.strftime("%d/%m/%Y %H:%M") if self.data_hora else "sem data"
        especie = self.nome_popular or self.nome_cientifico or self.classe
        return f"{especie} - {self.local_captura} ({when})"

class Flora(BaseModel):
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, null=True, blank=True, related_name="floras", verbose_name="Unidade")
    unidade_sigla = models.CharField(max_length=50, null=True, blank=True, verbose_name="Sigla da Unidade", db_index=True)
    responsavel_registro = models.CharField(max_length=255, verbose_name="Responsável pelo Registro", null=False, blank=False)
    local = models.CharField(max_length=50, verbose_name="Localização", null=False, blank=False, db_index=True)
    area = models.CharField(max_length=50, verbose_name="Área", null=False, blank=False, db_index=True)
    popular = models.CharField(max_length=255, verbose_name="Nome Popular", null=True, blank=True)
    especie = models.CharField(max_length=255, verbose_name="Espécie", null=True, blank=True)
    nativa = models.BooleanField(verbose_name="Nativa?", default=False)
    isolamento_area = models.BooleanField(verbose_name="Isolamento de Área?", default=False)
    estado_fitossanitario = models.CharField(max_length=50, verbose_name="Estado Fitossanitário", null=True, blank=True)
    descricao = models.TextField(verbose_name="Descrição", blank=True)
    justificativa = models.TextField(verbose_name="Justificativa para Registro", blank=True)
    condicao = models.CharField(max_length=50, verbose_name="Condição", null=True, blank=True)
    acao_realizada = models.CharField(max_length=50, verbose_name="Ação Realizada", null=True, blank=True)

    fotos = GenericRelation(Foto)
    geolocalizacoes = GenericRelation(Geolocalizacao)

    data_hora_inicio = models.DateTimeField(verbose_name="Data e Hora do Registro", null=False, blank=False, db_index=True)
    data_hora_fim = models.DateTimeField(verbose_name="Data e Hora do Término", null=True, blank=True, db_index=True)

    diametro_peito = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Diâmetro à Altura do Peito (cm)", null=True, blank=True)
    altura_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Altura Total (m)", null=True, blank=True)
    zona = models.CharField(max_length=50, verbose_name="Zona", null=True, blank=True)
    responsavel_tecnico = models.CharField(max_length=255, verbose_name="Responsável Técnico", null=True, blank=True)

    class Meta:
        verbose_name = "Flora"
        verbose_name_plural = "Flora"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["area", "local"]),
            models.Index(fields=["especie", "-criado_em"]),
            models.Index(fields=["estado_fitossanitario", "-criado_em"]),
        ]

    @property
    def geolocalizacao(self):
        return self.geolocalizacoes.first()

    @property
    def foto_antes(self):
        foto = self.fotos.filter(tipo=Foto.TIPO_FLORA_ANTES).order_by("criado_em", "id").first()
        if foto:
            return foto
        return self.fotos.order_by("criado_em", "id").first()

    @property
    def foto_depois(self):
        foto = self.fotos.filter(tipo=Foto.TIPO_FLORA_DEPOIS).order_by("criado_em", "id").first()
        if foto:
            return foto
        fotos = list(self.fotos.order_by("criado_em", "id")[:2])
        return fotos[1] if len(fotos) > 1 else None

    def clean(self):
        super().clean()

        errors = {}

        if not self.responsavel_registro:
            errors["responsavel_registro"] = "O responsável pelo registro é obrigatório."

        if not self.data_hora_inicio:
            errors["data_hora_inicio"] = "A data e hora do registro é obrigatória."

        if not self.local:
            errors["local"] = "A localização é obrigatória."

        if not self.area:
            errors["area"] = "A área é obrigatória."

        if not self.condicao:
            errors["condicao"] = "A condição é obrigatória."

        if not self.justificativa:
            errors["justificativa"] = "A justificativa para registro é obrigatória."

        if self.acao_realizada and not self.descricao:
            errors["descricao"] = "A descrição é obrigatória quando houver ação realizada."

        if self.data_hora_inicio and self.data_hora_fim and self.data_hora_fim < self.data_hora_inicio:
            errors["data_hora_fim"] = "A data e hora do término não pode ser anterior ao registro."

        if self.diametro_peito is not None and self.diametro_peito <= 0:
            errors["diametro_peito"] = "O diâmetro à altura do peito deve ser maior que zero."

        if self.altura_total is not None and self.altura_total <= 0:
            errors["altura_total"] = "A altura total deve ser maior que zero."

        if errors:
            raise ValidationError(errors)

    def normalizar_campos(self):
        self.normalize_string_fields(
            required_fields=("responsavel_registro", "local", "area", "descricao", "justificativa"),
            nullable_fields=("especie", "popular", "estado_fitossanitario", "condicao", "acao_realizada", "zona", "responsavel_tecnico"),
        )

    def save(self, *args, **kwargs):
        self.normalizar_campos()
        self.preencher_unidade_sigla()
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        identificacao = self.popular or self.especie or "Sem identificação informada"
        return f"{identificacao} - {self.local}"

    def get_absolute_url(self):
        return reverse("sesmt:flora_view", args=[self.pk])

class Himenoptero(BaseModel):
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, null=True, blank=True, related_name="himenopteros", verbose_name="Unidade")
    unidade_sigla = models.CharField(max_length=50, null=True, blank=True, verbose_name="Sigla da Unidade", db_index=True)
    responsavel_registro = models.CharField(max_length=255, verbose_name="Responsável pelo Registro", null=False, blank=False)
    local = models.CharField(max_length=50, verbose_name="Localização", null=False, blank=False, db_index=True)
    area = models.CharField(max_length=50, verbose_name="Área", null=False, blank=False, db_index=True)
    descricao_local = models.TextField(verbose_name="Descrição do Local", blank=True)
    hipomenoptero = models.CharField(max_length=50, verbose_name="Himenóptero", null=True, blank=True)
    popular = models.CharField(max_length=255, verbose_name="Nome Popular", null=True, blank=True)
    especie = models.CharField(max_length=255, verbose_name="Espécie", null=True, blank=True)
    proximidade_pessoas = models.CharField(max_length=50, verbose_name="Proximidade de Pessoas", null=False, blank=False, db_index=True)
    classificacao_risco = models.CharField(max_length=50, verbose_name="Classificação de Risco", null=False, blank=False, db_index=True)
    isolamento_area = models.BooleanField(verbose_name="Isolamento de Área?", default=False)
    observacao = models.TextField(verbose_name="Observações", blank=True)
    justificativa_tecnica = models.TextField(verbose_name="Justificativa Técnica", blank=True)
    condicao = models.CharField(max_length=50, verbose_name="Condição", null=True, blank=True)
    acao_realizada = models.CharField(max_length=50, verbose_name="Ação Realizada", null=True, blank=True)

    fotos = GenericRelation(Foto)
    geolocalizacoes = GenericRelation(Geolocalizacao)

    data_hora_inicio = models.DateTimeField(verbose_name="Data e Hora do Registro", null=False, blank=False, db_index=True)
    data_hora_fim = models.DateTimeField(verbose_name="Data e Hora do Término", null=True, blank=True, db_index=True)    
    responsavel_tecnico = models.CharField(max_length=255, verbose_name="Responsável Técnico", null=True, blank=True)

    class Meta:
        verbose_name = "Himenóptero"
        verbose_name_plural = "Himenópteros"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["area", "local"]),
            models.Index(fields=["hipomenoptero", "-criado_em"]),
            models.Index(fields=["classificacao_risco", "-criado_em"]),
        ]

    @property
    def geolocalizacao(self):
        return self.geolocalizacoes.first()

    @property
    def foto_principal(self):
        return self.fotos.order_by("criado_em", "id").first()

    def clean(self):
        super().clean()

        errors = {}

        if not self.responsavel_registro:
            errors["responsavel_registro"] = "O responsável pelo registro é obrigatório."

        if not self.data_hora_inicio:
            errors["data_hora_inicio"] = "A data e hora do registro é obrigatória."

        if not self.local:
            errors["local"] = "A localização é obrigatória."

        if not self.area:
            errors["area"] = "A área é obrigatória."

        if not self.hipomenoptero:
            errors["hipomenoptero"] = "O tipo de himenóptero é obrigatório."

        if not self.proximidade_pessoas:
            errors["proximidade_pessoas"] = "A proximidade de pessoas é obrigatória."

        if not self.classificacao_risco:
            errors["classificacao_risco"] = "A classificação de risco é obrigatória."

        if not self.descricao_local:
            errors["descricao_local"] = "A descrição do local é obrigatória."

        if self.data_hora_inicio and self.data_hora_fim and self.data_hora_fim < self.data_hora_inicio:
            errors["data_hora_fim"] = "A data e hora do término não pode ser anterior ao registro."

        if self.acao_realizada and not self.observacao:
            errors["observacao"] = "As observações são obrigatórias quando houver ação realizada."

        if errors:
            raise ValidationError(errors)

    def normalizar_campos(self):
        self.normalize_string_fields(
            required_fields=(
                "responsavel_registro",
                "local",
                "area",
                "descricao_local",
                "observacao",
                "justificativa_tecnica",
            ),
            nullable_fields=(
                "hipomenoptero",
                "popular",
                "especie",
                "proximidade_pessoas",
                "classificacao_risco",
                "condicao",
                "acao_realizada",
                "responsavel_tecnico",
            ),
        )

    def save(self, *args, **kwargs):
        self.normalizar_campos()
        self.preencher_unidade_sigla()
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        identificacao = self.popular or self.especie or self.hipomenoptero or "Sem identificação informada"
        return f"{identificacao} - {self.local}"

    def get_absolute_url(self):
        return reverse("sesmt:himenopteros_view", args=[self.pk])

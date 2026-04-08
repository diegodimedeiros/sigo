import hashlib
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from sigo_core.shared.normalizers import normalize_digits, normalize_text, normalize_upper
from sigo_core.shared.upload_validators import validation_size

User = get_user_model()

class BaseModel(models.Model):
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    modificado_em = models.DateTimeField(auto_now=True, verbose_name="Modificado em")
    criado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="%(class)s_criados",
        verbose_name="Criado por",
    )
    modificado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="%(class)s_modificados",
        verbose_name="Modificado por",
    )

    class Meta:
        abstract = True

    @staticmethod
    def normalize_string_value(value, *, blank_to_none=False, upper=False):
        if value is None:
            return None if blank_to_none else ""
        normalized = str(value).strip()
        if upper:
            normalized = normalized.upper()
        if blank_to_none and not normalized:
            return None
        return normalized

    def normalize_string_fields(self, *, required_fields=(), nullable_fields=(), upper_fields=()):
        for field_name in required_fields:
            setattr(
                self,
                field_name,
                self.normalize_string_value(
                    getattr(self, field_name, None),
                    blank_to_none=False,
                    upper=field_name in upper_fields,
                ),
            )
        for field_name in nullable_fields:
            setattr(
                self,
                field_name,
                self.normalize_string_value(
                    getattr(self, field_name, None),
                    blank_to_none=True,
                    upper=field_name in upper_fields,
                ),
            )

    def preencher_unidade_sigla(self):
        if hasattr(self, "unidade") and getattr(self, "unidade_id", None) and not getattr(self, "unidade_sigla", None):
            self.unidade_sigla = self.unidade.sigla

class GenericRelationModel(models.Model):
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="sigo_%(class)s_set",
    )
    object_id = models.PositiveBigIntegerField()
    objeto = GenericForeignKey("content_type", "object_id")

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["content_type", "object_id"])
        ]

class BaseArquivo(BaseModel, GenericRelationModel):
    nome_arquivo = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    tamanho = models.PositiveIntegerField(default=0)
    arquivo = models.BinaryField(validators=[validation_size], verbose_name="Arquivo")
    hash_arquivo = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    hash_arquivo_atual = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    class Meta:
        abstract = True

    def gerar_hash(self, conteudo):
        return hashlib.sha256(conteudo).hexdigest()

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.arquivo:
            conteudo = bytes(self.arquivo)
            self.tamanho = len(conteudo)
            self.hash_arquivo_atual = self.gerar_hash(conteudo)

            if not self.hash_arquivo:
                self.hash_arquivo = self.hash_arquivo_atual

        return super().save(*args, **kwargs)

class Geolocalizacao(BaseModel, GenericRelationModel):
    tipo = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Tipo da Geolocalização",
    )
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    hash_geolocalizacao = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
        unique=True,
    )

    class Meta:
        verbose_name = "Geolocalização"
        verbose_name_plural = "Geolocalizações"
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id", "tipo", "latitude", "longitude"],
                name="unique_geolocalizacao_por_objeto",
            ),
            models.UniqueConstraint(
                fields=["content_type", "object_id", "tipo"],
                condition=Q(tipo__isnull=False),
                name="unique_geolocalizacao_tipo_por_objeto",
            ),
        ]

    def __str__(self):
        return f"Lat: {self.latitude}, Lon: {self.longitude}"

    def clean(self):
        super().clean()

        errors = {}

        if self.latitude is None:
            errors["latitude"] = "Latitude é obrigatória."
        elif not (Decimal("-90") <= self.latitude <= Decimal("90")):
            errors["latitude"] = "Latitude inválida. Deve estar entre -90 e 90."

        if self.longitude is None:
            errors["longitude"] = "Longitude é obrigatória."
        elif not (Decimal("-180") <= self.longitude <= Decimal("180")):
            errors["longitude"] = "Longitude inválida. Deve estar entre -180 e 180."

        if errors:
            raise ValidationError(errors)

    def gerar_hash_geolocalizacao(self):
        payload = f"{self.content_type_id}|{self.object_id}|{self.tipo or ''}|{self.latitude}|{self.longitude}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def save(self, *args, **kwargs):
        self.full_clean()
        self.hash_geolocalizacao = self.gerar_hash_geolocalizacao()
        return super().save(*args, **kwargs)

class Anexo(BaseArquivo):
    class Meta:
        verbose_name = "Anexo"
        verbose_name_plural = "Anexos"
        ordering = ["-criado_em"]

    def __str__(self):
        return self.nome_arquivo

class Foto(BaseArquivo):
    TIPO_CAPTURA = "captura"
    TIPO_SOLTURA = "soltura"
    TIPO_FLORA_ANTES = "flora_antes"
    TIPO_FLORA_DEPOIS = "flora_depois"
    TIPO_CHOICES = (
        (TIPO_CAPTURA, "Captura"),
        (TIPO_SOLTURA, "Soltura"),
        (TIPO_FLORA_ANTES, "Flora Antes"),
        (TIPO_FLORA_DEPOIS, "Flora Depois"),
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default=TIPO_CAPTURA,
        db_index=True,
        verbose_name="Tipo da Foto",
    )
    geolocalizacoes = GenericRelation(Geolocalizacao)

    class Meta:
        verbose_name = "Foto"
        verbose_name_plural = "Fotos"
        ordering = ["-criado_em"]

    def __str__(self):
        return self.nome_arquivo

class Assinatura(BaseArquivo):
    hash_assinatura = models.CharField(
        max_length=64,
        verbose_name="Hash da Assinatura",
        null=True,
        blank=True,
        db_index=True,
        unique=True,
    )
    geolocalizacoes = GenericRelation(Geolocalizacao)

    class Meta:
        verbose_name = "Assinatura"
        verbose_name_plural = "Assinaturas"
        ordering = ["-criado_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id"],
                name="sigo_assinatura_unique_objeto",
            )
        ]

    def __str__(self):
        return self.nome_arquivo

    def clean(self):
        super().clean()

        errors = {}

        if not self.arquivo:
            errors["arquivo"] = "O arquivo da assinatura é obrigatório."

        if not self.content_type_id:
            errors["content_type"] = "O tipo do objeto relacionado é obrigatório."

        if not self.object_id:
            errors["object_id"] = "O objeto relacionado é obrigatório."

        if errors:
            raise ValidationError(errors)

    def gerar_hash_assinatura(self, conteudo: bytes) -> str:
        return hashlib.sha256(conteudo).hexdigest()

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError(
                {"__all__": "Assinatura não pode ser alterada após criada."}
            )

        self.full_clean()
        conteudo = bytes(self.arquivo)
        self.tamanho = len(conteudo)
        self.hash_arquivo_atual = self.gerar_hash(conteudo)
        self.hash_arquivo = self.hash_arquivo_atual
        self.hash_assinatura = self.gerar_hash_assinatura(conteudo)
        return super().save(*args, **kwargs)

class Pessoa(models.Model):
    nome = models.CharField(max_length=255, verbose_name="Nome Completo", blank=False, null=False)
    documento = models.CharField(max_length=50, verbose_name="Documento", blank=False, null=False)
    orgao_emissor = models.CharField(max_length=50, verbose_name="Órgão Emissor", blank=True, null=True)
    sexo = models.CharField(max_length=10, verbose_name="Sexo", blank=True, null=True)
    data_nascimento = models.DateField(verbose_name="Data de Nascimento", blank=True, null=True)
    nacionalidade = models.CharField(max_length=50, verbose_name="Nacionalidade", blank=True, null=True)

    class Meta:
        verbose_name = "Pessoa"
        verbose_name_plural = "Pessoas"

    def __str__(self):
        return f"{self.nome} ({self.documento})"

class Contato(models.Model):
    telefone = models.CharField(max_length=20, verbose_name="Telefone", blank=True, null=True)
    email = models.EmailField(verbose_name="E-mail", blank=True, null=True)
    endereco = models.CharField(max_length=255, verbose_name="Endereço", blank=True, null=True)
    bairro = models.CharField(max_length=100, verbose_name="Bairro", blank=True, null=True)
    cidade = models.CharField(max_length=100, verbose_name="Cidade", blank=True, null=True)
    estado = models.CharField(max_length=100, verbose_name="Estado", blank=True, null=True)
    provincia = models.CharField(max_length=100, verbose_name="Província", blank=True, null=True)
    pais = models.CharField(max_length=100, verbose_name="País", blank=True, null=True)

    class Meta:
        verbose_name = "Contato"
        verbose_name_plural = "Contatos"

    def __str__(self):
        return self.email or self.telefone or "Contato"


class Unidade(models.Model):
    nome = models.CharField(max_length=255, unique=True, verbose_name="Nome da Unidade")
    sigla = models.CharField(max_length=50, blank=True, null=True, verbose_name="Sigla")
    cnpj = models.CharField(max_length=18, blank=True, null=True, verbose_name="CNPJ")
    cidade = models.CharField(max_length=100, blank=True, null=True, verbose_name="Cidade")
    uf = models.CharField(max_length=2, blank=True, null=True, verbose_name="UF")
    ativo = models.BooleanField(default=True, verbose_name="Ativa?")

    class Meta:
        verbose_name = "Unidade"
        verbose_name_plural = "Unidades"
        ordering = ["nome"]

    def normalizar_campos(self):
        self.nome = normalize_text(self.nome)
        self.sigla = normalize_upper(self.sigla) or None
        self.cnpj = normalize_digits(self.cnpj) or None
        self.cidade = normalize_text(self.cidade) or None
        self.uf = normalize_upper(self.uf) or None

    def clean(self):
        super().clean()

    def save(self, *args, **kwargs):
        self.normalizar_campos()
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        if self.sigla:
            return f"{self.nome} ({self.sigla})"
        return self.nome


class ConfiguracaoSistema(models.Model):
    codigo = models.CharField(
        max_length=20,
        unique=True,
        default="default",
        editable=False,
        verbose_name="Código",
    )
    unidade_ativa = models.ForeignKey(
        Unidade,
        on_delete=models.PROTECT,
        related_name="configuracoes_ativas",
        verbose_name="Unidade ativa",
    )

    class Meta:
        verbose_name = "Configuração do Sistema"
        verbose_name_plural = "Configurações do Sistema"

    def save(self, *args, **kwargs):
        self.codigo = "default"
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Configuração principal - {self.unidade_ativa}"

    @classmethod
    def get_solo(cls):
        return cls.objects.select_related("unidade_ativa").order_by("id").first()


class NotificacaoQuerySet(models.QuerySet):
    def visiveis_para_usuario(self, *, user, modulo=None, unidade=None):
        if not user or not user.is_authenticated:
            return self.none()

        queryset = self.filter(ativo=True)
        queryset = queryset.filter(Q(usuario__isnull=True) | Q(usuario=user))
        queryset = queryset.filter(Q(grupo__isnull=True) | Q(grupo__in=user.groups.all()))

        if unidade is not None:
            queryset = queryset.filter(Q(unidade__isnull=True) | Q(unidade=unidade))

        if modulo:
            queryset = queryset.filter(Q(modulo="") | Q(modulo=modulo))

        return queryset.distinct()


class Notificacao(models.Model):
    MODULO_SIGO = "sigo"
    MODULO_SIOP = "siop"
    MODULO_SESMT = "sesmt"
    MODULO_CHOICES = (
        ("", "Todos os módulos"),
        (MODULO_SIGO, "SIGO"),
        (MODULO_SIOP, "SIOP"),
        (MODULO_SESMT, "SESMT"),
    )

    TIPO_INFO = "info"
    TIPO_SUCESSO = "sucesso"
    TIPO_ALERTA = "alerta"
    TIPO_ERRO = "erro"
    TIPO_CHOICES = (
        (TIPO_INFO, "Informação"),
        (TIPO_SUCESSO, "Sucesso"),
        (TIPO_ALERTA, "Alerta"),
        (TIPO_ERRO, "Erro"),
    )

    titulo = models.CharField(max_length=120, verbose_name="Título")
    mensagem = models.CharField(max_length=255, verbose_name="Mensagem")
    link = models.CharField(max_length=255, blank=True, verbose_name="Link")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default=TIPO_INFO, db_index=True)
    unidade = models.ForeignKey(
        Unidade,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notificacoes",
        verbose_name="Unidade alvo",
    )
    modulo = models.CharField(
        max_length=20,
        choices=MODULO_CHOICES,
        blank=True,
        default="",
        db_index=True,
        verbose_name="Módulo alvo",
    )
    grupo = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notificacoes",
        verbose_name="Grupo alvo",
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notificacoes",
        verbose_name="Usuário alvo",
    )
    lidos_por = models.ManyToManyField(
        User,
        blank=True,
        related_name="notificacoes_lidas",
        verbose_name="Lidas por",
    )
    ativo = models.BooleanField(default=True, verbose_name="Ativa?")
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criada em")

    objects = NotificacaoQuerySet.as_manager()

    class Meta:
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"
        ordering = ["-criado_em"]

    def normalizar_campos(self):
        self.titulo = normalize_text(self.titulo)
        self.mensagem = normalize_text(self.mensagem)
        self.link = normalize_text(self.link)

    def clean(self):
        super().clean()

        if not self.titulo:
            raise ValidationError({"titulo": "Informe o título da notificação."})
        if not self.mensagem:
            raise ValidationError({"mensagem": "Informe a mensagem da notificação."})
        if (self.grupo_id or self.usuario_id) and not self.modulo:
            raise ValidationError(
                {"modulo": "Informe o módulo para notificações direcionadas por grupo ou usuário."}
            )

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        self.normalizar_campos()
        self.full_clean()
        return super().save(*args, **kwargs)

    def get_tipo_css(self):
        if self.tipo == self.TIPO_SUCESSO:
            return "notif-success"
        if self.tipo == self.TIPO_ALERTA:
            return "notif-warning"
        if self.tipo == self.TIPO_ERRO:
            return "notif-danger"
        return "notif-primary"


# Modelo para representar o operador do sistema, vinculado a um usuário do Django #
class Operador(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="operador",
        verbose_name="Usuário",
    )
    foto = models.BinaryField(
        blank=True,
        null=True,
        validators=[validation_size],
        verbose_name="Foto",
    )
    foto_nome_arquivo = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nome do arquivo")
    foto_mime_type = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tipo MIME")
    foto_tamanho = models.PositiveIntegerField(default=0, verbose_name="Tamanho")

    class Meta:
        verbose_name = "Operador"
        verbose_name_plural = "Operadores"

    def __str__(self):
        full_name = self.user.get_full_name()
        return full_name if full_name else self.user.username


def get_unidade_ativa():
    config = ConfiguracaoSistema.get_solo()
    if config is None:
        return None
    return config.unidade_ativa

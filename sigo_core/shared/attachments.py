from django.contrib.contenttypes.models import ContentType


def create_attachments_for_instance(*, instance, model_class, anexo_model, files):
    if not files:
        return

    content_type = ContentType.objects.get_for_model(model_class)

    for file_obj in files:
        if not file_obj:
            continue

        file_name = getattr(file_obj, "name", "")
        file_size = getattr(file_obj, "size", 0)

        if not file_name or file_size <= 0:
            continue

        anexo_model.objects.create(
            content_type=content_type,
            object_id=instance.id,
            nome_arquivo=file_name,
            mime_type=getattr(file_obj, "content_type", ""),
            tamanho=file_size,
            arquivo=file_obj.read(),
        )
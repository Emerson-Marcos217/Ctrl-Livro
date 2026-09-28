from django.db import migrations, models


def copiar_categorias(apps, schema_editor):
    Livro = apps.get_model("livro", "Livro")
    Vinculo = Livro.categorias.through
    banco = schema_editor.connection.alias
    for livro in Livro.objects.using(banco).all().iterator():
        Vinculo.objects.using(banco).create(
            livro_id=livro.pk, categoria_id=livro.categoria_id,
        )


class Migration(migrations.Migration):
    dependencies = [("livro", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="livro",
            name="categorias",
            field=models.ManyToManyField(
                to="livro.categoria",
                related_name="livros",
                verbose_name="Categorias",
                help_text="Selecione de 1 a 3 categorias.",
            ),
        ),
        # A volta para uma única categoria perderia as novas associações.
        migrations.RunPython(copiar_categorias),
        migrations.RemoveField(model_name="livro", name="categoria"),
    ]

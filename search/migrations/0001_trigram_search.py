from django.db import migrations


class Migration(migrations.Migration):
    """
    PostgreSQL pg_trgm extension va trigram indexlar yaratish.
    Bu migration faqat bir marta ishlaydi.
    """

    dependencies = [
        # O'zingizning oxirgi migration'ingizni yozing
        # ("anime", "0001_initial"),
        # ("person", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- pg_trgm extensionni yoqish
                CREATE EXTENSION IF NOT EXISTS pg_trgm;

                -- Anime title uchun trigram index
                CREATE INDEX IF NOT EXISTS idx_anime_title_trgm
                ON anime_anime USING GIN (title gin_trgm_ops);

                -- Person fullname uchun trigram index
                CREATE INDEX IF NOT EXISTS idx_person_fullname_trgm
                ON person_person USING GIN (fullname gin_trgm_ops);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS idx_anime_title_trgm;
                DROP INDEX IF EXISTS idx_person_fullname_trgm;
            """,
        )
    ]

from django.core.management.base import BaseCommand

from apps.episode.demo import attach_demo_to_episodes, find_demo_mp4


class Command(BaseCommand):
    help = "Copy Downloads/demo.mp4 into media and attach it to every Episode without a Master."

    def handle(self, *args, **options):
        src = find_demo_mp4()
        if not src:
            self.stderr.write('demo.mp4 topilmadi (Downloads yoki ANIMEE_DEMO_MP4).')
            return
        created, url = attach_demo_to_episodes(src)
        self.stdout.write(self.style.SUCCESS(f'{created} ta qismga {url} qo‘yildi.'))

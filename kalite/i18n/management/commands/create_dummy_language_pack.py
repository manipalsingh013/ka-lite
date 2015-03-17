"""

The create_dummy_language_pack command downloads the 'en' language
pack from the central server and creates a new language pack based on
that. Make sure you have internet!

"""

import accenting
import json
import os
import polib
import requests
import tempfile
import zipfile
from cStringIO import StringIO

from django.conf import settings
from django.core.management.base import NoArgsCommand

from fle_utils.general import ensure_dir
from kalite.i18n import get_language_pack_url, get_locale_path

logging = settings.LOG

BASE_LANGUAGE_PACK = "en"       # language where we base the dummy langpack from
TARGET_LANGUAGE_PACK = "eo"     # what the "dummy" language's language code. Will be. Sorry, Esperantists.


class Command(NoArgsCommand):

    def handle_noargs(self, **options):
        langpack_zip = download_language_pack(BASE_LANGUAGE_PACK)
        django_mo_contents, djangojs_mo_contents = retrieve_mo_files(langpack_zip)
        dummy_django_mo, dummy_djangojs_mo = (create_mofile_with_dummy_strings(django_mo_contents, filename="django.mo"),
                                              create_mofile_with_dummy_strings(djangojs_mo_contents, filename="djangojs.mo"))


def download_language_pack(lang):
    url = get_language_pack_url(lang)

    try:
        resp = requests.get(url)
        resp.raise_for_status()
    except requests.ConnectionError as e:
        logging.error("Error downloading %s language pack: %s" % (lang, e))

    return zipfile.ZipFile(StringIO(resp.content))


def retrieve_mo_files(langpack_zip):
    return (langpack_zip.read("LC_MESSAGES/django.mo"),
            langpack_zip.read("LC_MESSAGES/djangojs.mo"))


def create_mofile_with_dummy_strings(filecontents, filename):
    target_lang_dir = get_locale_path(TARGET_LANGUAGE_PACK)
    molocation = os.path.join(target_lang_dir, "LC_MESSAGES")

    ensure_dir(molocation)

    # create the language metadata file. Needed for KA Lite to
    # actually detect the language
    barebones_metadata = {
        "code": TARGET_LANGUAGE_PACK,
        'software_version': VERSION,
        'language_pack_version': 1,
        'percent_translated': 100,
        'subtitle_count': 0,
        "name": "DEBUG",
        'native_name': 'DEBUG',
    }

    lang_metadata_path = os.path.join(
        target_lang_dir,
        "%s_metadata.json" % TARGET_LANGUAGE_PACK
    )
    with open(lang_metadata_path, "w") as f:
        json.dump(barebones_metadata, f)

    # Now create the actual MO files
    mo_file_path = os.path.join(molocation, filename)
    # Alright, so polib can only read (p|m)ofiles already written to
    # disk, so let's go write it to a temporary file first
    # with tempfile.NamedTemporaryFile(delete=True) as tmp:
    #     tmp.write(filecontents)
    with open(mo_file_path, "w") as f:
        f.write(filecontents)

    mofile = polib.mofile(mo_file_path)
    for moentry in mofile:
        accenting.convert_msg(moentry)
    mofile.save(fpath=mo_file_path)

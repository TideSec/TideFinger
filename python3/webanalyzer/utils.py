#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import zipfile
import logging
import requests
import subprocess
import urllib.request

__all__ = ["update"]

logger = logging.getLogger(__file__)


def update(repository: str, path: str) -> bool:
    version_file = os.path.join(path, 'VERSION')
    if os.path.exists(version_file) and os.path.isfile(version_file):
        with open(version_file) as fd:
            version = fd.read().strip()

        if version:
            rp = requests.get("https://raw.githubusercontent.com/%s/master/VERSION" % repository)
            if version == rp.text.strip():
                logger.warning("already at the latest revision '%s'" % version)
                return True

    if not os.system("git version"):
        return _update_rules_from_git(repository, path)
    else:
        return _update_rule_from_file(repository, path)


def _update_rules_from_git(repository: str, path: str) -> bool:
    if os.path.exists(os.path.join(path, '.git')):
        cmd = "cd %s && git checkout . && git pull" % path
    else:
        cmd = "git clone --depth 1 https://github.com/%s.git %s" % (repository, path)

    try:
        p = subprocess.Popen(cmd, shell=True)
    except Exception as e:
        logger.error("download zip file error", exc_info=e)
        return False

    return p.wait() == 0


def _update_rule_from_file(repository: str, path: str) -> bool:
    logger.warning(("not a git repository. It is recommended to clone the 'webanalyzer/rules' repository "
                    "from GitHub (e.g. 'git clone --depth 1 https://github.com/%s.git')" % repository))

    def reporthook(a, b, c):
        if a % 10 == 0:
            logger.warning('download size %d KB', (b * a) / 1024)

    try:
        download_url = "https://github.com/%s/archive/master.zip" % repository
        logger.warning("downloading %s" % download_url)
        zip_file, _ = urllib.request.urlretrieve(download_url, reporthook=reporthook)
    except Exception as e:
        logger.error("download zip file error", exc_info=e)
        return False

    try:
        with zipfile.ZipFile(zip_file) as fd:
            for info in fd.infolist():
                info.filename = info.filename.replace('rules-master/', '')
                if info.filename:
                    fd.extract(info, path)
    except Exception as e:
        logger.error("unzip zip file error", exc_info=e)
        return False

    return True

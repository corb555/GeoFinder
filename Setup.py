#!/usr/bin/env python
# -*- coding: utf-8 -*-


# To use the 'upload' functionality of this file:
#   python Setup.py upload

import io
import os
import sys
from shutil import rmtree

from setuptools import find_packages, setup, Command

# Package meta-data.
NAME = "geofinder"
DESCRIPTION = "GEDCOM Genealogy address validation and geocoding using geonames.org data"
URL = "https://github.com/corb555/GeoFinder"
EMAIL = "corb@aol.com"
AUTHOR = "Mike Herbert"
REQUIRES_PYTHON = '>=3.6.0'
VERSION = None

# What packages are required for this module to be executed?
REQUIRED = [
    'unidecode', 'phonetics'
]

# What packages are optional?
EXTRAS = {
    # 'fancy feature': ['django'],
}

# The rest you shouldn't have to touch too much :)
# ------------------------------------------------
# Except, perhaps the License and Trove Classifiers!
# If you do change the License, remember to change the Trove Classifier for that!

here = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this will only work if 'README.md' is present in your MANIFEST.in file!
try:
    with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = '\n' + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION

# Load the package's __version__.py module as a dictionary.
about = {}
if not VERSION:
    project_slug = NAME.lower().replace("-", "_").replace(" ", "_")
    with open(os.path.join(here, project_slug, '__version__.py')) as f:
        exec(f.read(), about)
else:
    about['__version__'] = VERSION


class UploadCommand(Command):
    """Support setup.py upload."""

    description = 'Build and publish the package.'
    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print('\033[1m{0}\033[0m'.format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.status('Removing previous builds…')
            rmtree(os.path.join(here, 'dist'))
        except OSError:
            pass

        self.status('Building Source and Wheel (universal) distribution…')
        os.system('python3 setup.py sdist bdist_wheel')

        self.status('Uploading the package to PyPI via Twine…')
        os.system('python3 -m twine upload  dist/*')

        self.status('Pushing git tags…')
        os.system(f'git tag v{about["__version__"]}')
        os.system('git push --tags')

        sys.exit()


# Where the magic happens:
setup(
    name=NAME,
    version=about['__version__'],
    description=DESCRIPTION,
    long_description=long_description,
    author=AUTHOR,
    author_email=EMAIL,
    url=URL,
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*", "tests.*"]),
    # If your package is a single module, use this instead of 'packages':
    # py_modules=['mypackage'],

    entry_points={
        'gui_scripts': [
            'geofinder = geofinder.GeoFinder:entry'
        ],
    },
    install_requires=REQUIRED,
    extras_require=EXTRAS,
    package_data={'geofinder': ['images/*.gif']},
    include_package_data=True,
    license='MIT',
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Natural Language :: English",
        "Topic :: Sociology :: Genealogy"
    ],
    # $ setup.py publish support.
    cmdclass={
        'upload': UploadCommand,
    },
)

"""
setuptools.setup(
    name="geofinder",
    version="0.2.0",
    author="Mike Herbert",
    author_email="corb@aol.com",
    description="GEDCOM Genealogy address validation and geocoding using geonames.org data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/corb555/GeoFinder",
    packages=setuptools.find_packages(),
    install_requires=[
          'unidecode',
        'phonetics'
      ],
    package_data={'geofinder': ['images/*.gif']},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Natural Language :: English",
        "Topic :: Sociology :: Genealogy"
    ],
    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'gui_scripts': [
            'geofinder = geofinder.GeoFinder:entry'
        ],
    },
)
"""

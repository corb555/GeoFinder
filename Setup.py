import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="geofinder",
    version="0.1.3",
    author="Mike Herbert",
    author_email="corb@aol.com",
    description="GEDCOM Genealogy address validation and geocoding using geonames.org data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/corb555/GeoFinder",
    packages=setuptools.find_packages(),
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
        'console_scripts': [
            'geofinder = geofinder.GeoFinder:entry',
        ],
    },
)

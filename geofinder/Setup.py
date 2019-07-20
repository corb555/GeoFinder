import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="geofinder-pkg-corb555",
    version="0.1.0",
    author="Mike Herbert",
    author_email="corb@aol.com",
    description="GEDCOM Genealogy address validation and geocoding using geonames.org data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/corb555/GeoFinder",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD 2-Clause License",
        "Operating System :: OS Independent",
    ],
)
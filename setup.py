from setuptools import find_packages, setup


setup(
    name='umeta',
    author='Brandon Davis',
    author_email='git@subdavis.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click',
        'fastapi',
        'marshmallow-sqlalchemy',
        'marshmallow-dataclass',
        'marshmallow-union',
        'requests',
    ],
    license='Apache Software License 2.0',
    setup_requires=['setuptools-git'],
    entry_points={'console_scripts': ['umeta = umeta.cli:cli']},
)

from setuptools import find_packages, setup

setup(
    name='SBS2',
    version='2.0',
    packages=find_packages(exclude=['test']),
    package_data={"sbs2.webapps": ['*.tpl']},
    include_package_data=True,
    author='Matt Lyles',
    author_email='lyles.matt@gmail.com',
    description='Sequenced Blob Storage Solution (SBS2) is a "buffet of utilities" to store and retrieve organized'
                'binary content using one or more backing storage technologies with a singular interface.',
    install_requires=[
        'annotated-types',
        'sortedcontainers',
        'PyYAML',
        'dacite',
        'botocore',
        'boto3',
        'boto3-type-annotations',
        'sqlitedict',
        'bottle',
        'bottle-fdsend',
    ],
    extras_require={
        'developer': [
            'mypy',
            'flake8',
            'types-PyYAML'
        ]
    }
)

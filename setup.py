from setuptools import setup, find_packages

setup(
    name='my_package',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'requests',
        'pandas',
        'json',
        'secrets',
        're',
        'bs4',
        'os',
        'time',
        'random'
    ],
    description='A package for easy interaction with the MAL API',
    author='Nathan Van Lingen',
    author_email='nathan.vanlingen1614@gmail.com',
    url='https://github.com/MALBuddy/MALBuddy'
)
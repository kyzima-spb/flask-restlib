import os

from setuptools import setup, find_packages


def read_file(filename):
    with open(os.path.join(os.path.dirname(__file__), filename)) as f:
        return f.read()


readme = read_file('README.rst')

setup(
    name='flask-restlib',
    use_scm_version={
        'relative_to': __file__,
        'local_scheme': lambda version: '',
    },
    description='Another extension for REST API.',
    long_description=readme,
    url='https://github.com/kyzima-spb/flask-restlib',
    license='MIT',
    author='Kirill Vercetti',
    author_email='office@kyzima-spb.com',
    packages=find_packages(),
    include_package_data=True,
    setup_requires=['setuptools_scm'],
    install_requires=[
        'Authlib>=0.15',
        'Flask>=1.0,<2',
        'Flask-Login>=0.5',
        'flask-marshmallow>=0.14',
        'flask-useful>=0.1.dev18',
        'webargs>=8.0',
    ],
    extras_require={
        'sqla': [
            'SQLAlchemy>=1.3,<1.4',
            'Flask-SQLAlchemy>=2.0',
            'sqlalchemy-utils>=0.37',
            'marshmallow-sqlalchemy>=0.24',
        ],
        'mongoengine': [
            'mongoengine>=0.23',
        ],
    },
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Flask',
        'Development Status :: 3 - Alpha',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)

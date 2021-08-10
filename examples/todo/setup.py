import os

from setuptools import setup, find_packages


def read_file(filename):
    with open(os.path.join(os.path.dirname(__file__), filename)) as f:
        return f.read()


# readme = read_file('README.rst')

setup(
    name='todo',
    version='0.1.0',
    # use_scm_version={
    #     'relative_to': __file__,
    #     'local_scheme': lambda version: '',
    # },
    url='https://github.com/kyzima-spb/flask-restlib/tree/dev-master/examples/todo',
    description='Demo example of a REST API for a todo application built on top of flask-restlib.',
    # long_description=readme,
    license='MIT',
    author='Kirill Vercetti',
    author_email='office@kyzima-spb.com',
    packages=find_packages(),
    include_package_data=True,
    setup_requires=['setuptools_scm'],
    install_requires=[
        'Flask>=2',
        'Flask-Bcrypt>=0.7',
        # 'flask-restlib[mongoengine]>=0.1',
    ],
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

from setuptools import setup, find_packages

setup(
    name='auth-server',
    version='0.1.0',
    url='https://github.com/kyzima-spb/flask-restlib/tree/dev-master/examples/auth-server',
    description='Demo example of a REST API for a OAuth 2.0 server built on top of flask-restlib.',
    license='MIT',
    author='Kirill Vercetti',
    author_email='office@kyzima-spb.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Flask>=2',
        'Flask-Bcrypt>=0.7',
        # 'flask-restlib[sqla]>=0.1',
        'PyMySQL>=0.10',
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
